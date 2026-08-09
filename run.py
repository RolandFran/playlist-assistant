import argparse
import subprocess
import sys
from pathlib import Path


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


def run_score():
    run_script(SCRIPTS["score"])


def run_publish(write=False):
    args = ["--write"] if write else []

    run_script(
        SCRIPTS["publish"],
        *args,
    )


def run_today(write=False, force_full_sources=False):
    """
    Komplette Today-Pipeline.

    Reihenfolge ist absichtlich fest:
      1. History aktualisieren
      2. Sources synchronisieren
      3. Scoring neu berechnen
      4. Publish

    Dadurch kann publish.py nicht versehentlich eine Auswahl auf Basis
    eines veralteten History-/Source-Stands veröffentlichen.
    """
    print()
    print("# Playlist Assistant - Today Pipeline")
    print()

    run_history()
    run_sources(force_full=force_full_sources)
    run_score()
    run_publish(write=write)

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

    subparsers.add_parser(
        "score",
        help="Today-Auswahl neu berechnen.",
    )

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
    today_parser.add_argument(
        "--full-sources",
        action="store_true",
        help=(
            "Sources innerhalb der Today-Pipeline vollstaendig neu laden. "
            "Normalerweise nicht noetig."
        ),
    )

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "history":
        run_history(
            recover_after=args.recover_after,
        )

    elif args.command == "sources":
        run_sources(
            force_full=args.full,
        )

    elif args.command == "score":
        run_score()

    elif args.command == "publish":
        run_publish(
            write=args.write,
        )

    elif args.command == "today":
        run_today(
            write=args.write,
            force_full_sources=args.full_sources,
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
