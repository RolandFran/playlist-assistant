import argparse
import subprocess
import sys
from pathlib import Path

from application_storage import ApplicationStorage
from runtime_config import add_runtime_config_arguments, runtime_config_from_args
from runtime import RuntimeOrchestrator


PROJECT_DIR = Path(__file__).resolve().parent

SCRIPTS = {
    "history": "collector.py",
    "sources": "sync.py",
    "score": "scoring.py",
    "publish": "publish.py",
}


def run_script(script_name, *args):
    script_path = PROJECT_DIR / script_name

    if not script_path.exists():
        raise RuntimeError(f"Datei fehlt: {script_path}")

    command = [
        sys.executable,
        str(script_path),
        *args,
    ]

    print()
    print("=" * 70)
    print(f"START: {script_name}")
    print("=" * 70)

    result = subprocess.run(
        command,
        cwd=PROJECT_DIR,
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"{script_name} ist mit Exit-Code "
            f"{result.returncode} fehlgeschlagen."
        )

    print()
    print(f"OK: {script_name}")


def run_history(recover_after=None):
    args = []

    if recover_after:
        args.extend([
            "--recover-after",
            recover_after,
        ])

    run_script(
        SCRIPTS["history"],
        *args,
    )


def run_sources(force_full=False):
    args = ["--full"] if force_full else []

    run_script(
        SCRIPTS["sources"],
        *args,
    )


def run_score(config=None):
    args = runtime_config_to_cli_args(config)
    run_script(SCRIPTS["score"], *args)


def run_publish(write=False):
    args = ["--write"] if write else []

    run_script(
        SCRIPTS["publish"],
        *args,
    )


def run_today(write=False, force_full_sources=False, config=None):
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

    result = create_runtime_orchestrator().run_today(
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


def create_runtime_orchestrator():
    """Create the reusable orchestration boundary for explicit runtime jobs."""
    return RuntimeOrchestrator(
        history_runner=run_history,
        sources_runner=run_sources,
        score_runner=run_score,
        publish_runner=run_publish,
        status_store=ApplicationStorage(PROJECT_DIR / "playlist_assistant.db"),
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

    sources_parser = subparsers.add_parser(
        "sources",
        help="Mit #today-source markierte Spotify-Playlists synchronisieren.",
    )
    sources_parser.add_argument(
        "--full",
        action="store_true",
        help="Alle Sources vollstaendig neu laden.",
    )

    score_parser = subparsers.add_parser(
        "score",
        help="Today-Auswahl neu berechnen.",
    )
    add_runtime_config_arguments(score_parser)

    publish_parser = subparsers.add_parser(
        "publish",
        help="Today-Auswahl fuer Spotify pruefen/veroeffentlichen.",
    )
    publish_parser.add_argument(
        "--write",
        action="store_true",
        help="Tatsaechlich nach Spotify schreiben.",
    )

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
        "--artist-min-gap", str(config.artist_min_gap),
    ]


def main():
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "history":
        result = create_runtime_orchestrator().run_history(
            recover_after=args.recover_after,
        )
        if not result.success:
            raise result.error

    elif args.command == "sources":
        run_sources(
            force_full=args.full,
        )

    elif args.command == "score":
        run_score(runtime_config_from_args(
            args, ApplicationStorage(PROJECT_DIR / "playlist_assistant.db").load_runtime_config()
        ))

    elif args.command == "publish":
        run_publish(
            write=args.write,
        )

    elif args.command == "today":
        run_today(
            write=args.write,
            force_full_sources=args.full_sources,
            config=runtime_config_from_args(
                args, ApplicationStorage(PROJECT_DIR / "playlist_assistant.db").load_runtime_config()
            ),
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
