import argparse
import subprocess
import sys
import re
from pathlib import Path

from application_storage import ApplicationStorage
from application_paths import (
    ApplicationPaths,
    add_data_dir_argument,
    application_paths_from_args,
)
from runtime_config import add_runtime_config_arguments, runtime_config_from_args
from runtime import RuntimeOrchestrator
from client import SpotifyRateLimited


PROJECT_DIR = Path(__file__).resolve().parent

SCRIPTS = {
    "history": "collector.py",
    "sources": "sync.py",
    "score": "scoring.py",
    "publish": "publish.py",
}


class ScriptFailure(RuntimeError):
    """A safe, actionable failure returned by one of the finite pipeline jobs."""

    def __init__(self, script_name: str, returncode: int, detail: str):
        self.script_name = script_name
        self.returncode = returncode
        self.detail = detail
        super().__init__(f"{script_name} failed (exit code {returncode}): {detail}")


def _retry_after(output: str) -> int | None:
    match = re.search(r"Retry will occur after:\s*(\d+)\s*s", output, re.I)
    return int(match.group(1)) if match else None


def _failure_detail(output: str) -> str:
    """Keep the final useful program error, never command lines or secrets."""
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    for line in reversed(lines):
        if line.startswith("FEHLER:"):
            return line.removeprefix("FEHLER:").strip()
        if "error=" in line.lower() or "failed" in line.lower():
            return line[-500:]
    return lines[-1][-500:] if lines else "No safe error detail was produced."


def run_script(script_name, *args, paths: ApplicationPaths | None = None):
    script_path = PROJECT_DIR / script_name

    if not script_path.exists():
        raise RuntimeError(f"Datei fehlt: {script_path}")

    command = [
        sys.executable,
        str(script_path),
        *args,
    ]
    if paths is not None and paths != ApplicationPaths.default():
        command.extend(["--data-dir", str(paths.data_dir)])

    print()
    print("=" * 70)
    print(f"START: {script_name}")
    print("=" * 70)

    result = subprocess.run(command, cwd=PROJECT_DIR, text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)

    if result.returncode != 0:
        output = (result.stderr or "") + "\n" + (result.stdout or "")
        detail = _failure_detail(output)
        if "rate limit" in detail.lower():
            raise SpotifyRateLimited(detail, retry_after=_retry_after(output))
        raise ScriptFailure(script_name, result.returncode, detail)

    print()
    print(f"OK: {script_name}")


def run_history(recover_after=None, *, paths: ApplicationPaths | None = None):
    args = []

    if recover_after:
        args.extend([
            "--recover-after",
            recover_after,
        ])

    run_script(
        SCRIPTS["history"],
        *args,
        paths=paths,
    )


def run_sources(force_full=False, *, paths: ApplicationPaths | None = None):
    args = ["--full"] if force_full else []

    run_script(SCRIPTS["sources"], *args, paths=paths)


def run_score(config=None, *, paths: ApplicationPaths | None = None):
    args = runtime_config_to_cli_args(config)
    run_script(SCRIPTS["score"], *args, paths=paths)


def run_publish(write=False, *, paths: ApplicationPaths | None = None):
    args = ["--write"] if write else []

    run_script(
        SCRIPTS["publish"],
        *args,
        paths=paths,
    )


def run_today(
    write=False,
    force_full_sources=False,
    config=None,
    *,
    paths: ApplicationPaths | None = None,
):
    """
    Complete Today pipeline.

    The order is deliberately fixed:
      1. Update history
      2. Synchronize sources
      3. Recalculate scoring
      4. Publish

    This prevents publish.py from accidentally publishing a selection based on
    outdated history or source state.
    """
    print()
    print("# Playlist Assistant - Today Pipeline")
    print()

    result = create_runtime_orchestrator(paths).run_today(
        write=write,
        force_full_sources=force_full_sources,
        config=config,
    )

    if not result.success:
        raise result.error

    print()
    print("=" * 70)

    if write:
        print("TODAY FERTIG: Playlist wurde bei Spotify aktualisiert.")
    else:
        print(
            "TODAY DRY-RUN FERTIG: "
            "Spotify wurde nicht veraendert."
        )
        print(
            "Fuer den echten Lauf: python run.py today --write"
        )

    print("=" * 70)


def create_runtime_orchestrator(paths: ApplicationPaths | None = None):
    """Create the reusable orchestration boundary for explicit runtime jobs."""
    paths = paths or ApplicationPaths.default()
    return RuntimeOrchestrator(
        history_runner=lambda **kwargs: run_history(paths=paths, **kwargs),
        sources_runner=lambda **kwargs: run_sources(paths=paths, **kwargs),
        score_runner=lambda **kwargs: run_score(paths=paths, **kwargs),
        publish_runner=lambda **kwargs: run_publish(paths=paths, **kwargs),
        status_store=ApplicationStorage(paths.database_path),
    )


def build_parser():
    parser = argparse.ArgumentParser(
        description="Zentraler Einstiegspunkt fuer Playlist Assistant."
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    history_parser = subparsers.add_parser(
        "history",
        help="Recently Played in die lokale History uebernehmen.",
    )
    history_parser.add_argument(
        "--recover-after",
        metavar="ISO_TIMESTAMP",
        help="Gezielter History-Recovery-Lauf ab einem ISO-Zeitpunkt.",
    )
    add_data_dir_argument(history_parser)

    sources_parser = subparsers.add_parser(
        "sources",
        help="Mit #today-source markierte Spotify-Playlists synchronisieren.",
    )
    sources_parser.add_argument(
        "--full",
        action="store_true",
        help="Alle Sources vollstaendig neu laden.",
    )
    add_data_dir_argument(sources_parser)

    score_parser = subparsers.add_parser(
        "score",
        help="Today-Auswahl neu berechnen.",
    )
    add_runtime_config_arguments(score_parser)
    add_data_dir_argument(score_parser)

    publish_parser = subparsers.add_parser(
        "publish",
        help="Today-Auswahl fuer Spotify pruefen/veroeffentlichen.",
    )
    publish_parser.add_argument(
        "--write",
        action="store_true",
        help="Tatsaechlich nach Spotify schreiben.",
    )
    add_data_dir_argument(publish_parser)

    today_parser = subparsers.add_parser(
        "today",
        help="History -> Sources -> Scoring -> Publish ausfuehren.",
    )
    today_parser.add_argument(
        "--write",
        action="store_true",
        help=(
            "Am Ende tatsaechlich nach Spotify schreiben. "
            "Ohne diese Option bleibt Publish ein Dry-Run."
        ),
    )
    add_data_dir_argument(today_parser)
    add_runtime_config_arguments(today_parser)
    today_parser.add_argument(
        "--full-sources",
        action="store_true",
        help=(
            "Sources innerhalb der Today-Pipeline vollstaendig neu laden. "
            "Normalerweise nicht noetig."
        ),
    )

    return parser


def runtime_config_to_cli_args(config):
    """Pass only explicitly set values to the scoring process."""
    if config is None:
        return []

    return [
        "--today-size", str(config.today_size),
        "--rare-weight", str(config.rare_weight),
        "--artist-gap", str(config.artist_gap),
    ]


def main():
    parser = build_parser()
    args = parser.parse_args()
    paths = application_paths_from_args(args)

    if args.command == "history":
        result = create_runtime_orchestrator(paths).run_history(
            recover_after=args.recover_after,
        )
        if not result.success:
            raise result.error

    elif args.command == "sources":
        run_sources(
            force_full=args.full,
            paths=paths,
        )

    elif args.command == "score":
        run_score(runtime_config_from_args(
            args, ApplicationStorage(paths.database_path).load_runtime_config()
        ), paths=paths)

    elif args.command == "publish":
        run_publish(
            write=args.write,
            paths=paths,
        )

    elif args.command == "today":
        run_today(
            write=args.write,
            force_full_sources=args.full_sources,
            config=runtime_config_from_args(
                args, ApplicationStorage(paths.database_path).load_runtime_config()
            ),
            paths=paths,
        )

    else:
        parser.error(
            f"Unbekannter Befehl: {args.command}"
        )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print()
        print("Abgebrochen.")
        sys.exit(130)
    except Exception as exc:
        print()
        print(f"FEHLER: {exc}", file=sys.stderr)
        sys.exit(1)
