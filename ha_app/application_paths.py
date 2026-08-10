"""Persistent runtime paths for the Playlist Assistant engine.

The engine does not depend on a particular host.  A host may provide a
dedicated data directory; without one, the existing project-local layout is
used for local CLI compatibility.
"""

import argparse
from dataclasses import dataclass
from pathlib import Path


APPLICATION_DIR = Path(__file__).resolve().parent


@dataclass(frozen=True)
class ApplicationPaths:
    """Locations owned by Playlist Assistant's persistent runtime data."""

    data_dir: Path

    @classmethod
    def default(cls) -> "ApplicationPaths":
        """Return the existing project-local data layout used by the CLI."""
        return cls(APPLICATION_DIR)

    @classmethod
    def from_data_dir(cls, data_dir: str | Path | None) -> "ApplicationPaths":
        """Use ``data_dir`` when supplied, otherwise preserve local defaults."""
        if data_dir is None:
            return cls.default()
        return cls(Path(data_dir).expanduser())

    @property
    def database_path(self) -> Path:
        return self.data_dir / "playlist_assistant.db"

    @property
    def reports_dir(self) -> Path:
        return self.data_dir / "reports"

    @property
    def backups_dir(self) -> Path:
        """Reserve the persistent location for future backup output."""
        return self.data_dir / "backups"

    @property
    def scoring_report_path(self) -> Path:
        return self.reports_dir / "scoring_output.txt"

    @property
    def today_report_path(self) -> Path:
        return self.reports_dir / "today_output.txt"

    @property
    def today_tracks_path(self) -> Path:
        return self.reports_dir / "today_tracks.json"

    def ensure_runtime_directories(self) -> None:
        """Create only the selected persistent data locations when needed."""
        self.reports_dir.mkdir(parents=True, exist_ok=True)


def add_data_dir_argument(parser: argparse.ArgumentParser) -> None:
    """Add the host-facing persistent-data handoff without a user setting."""
    parser.add_argument(
        "--data-dir",
        metavar="DIRECTORY",
        help="Persistent application data directory for this run.",
    )


def application_paths_from_args(args: argparse.Namespace) -> ApplicationPaths:
    """Build paths from an optional CLI handoff argument."""
    return ApplicationPaths.from_data_dir(getattr(args, "data_dir", None))
