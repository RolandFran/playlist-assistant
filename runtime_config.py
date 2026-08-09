"""Central runtime configuration for the playlist engine.

The values are intentionally independent of Home Assistant. A later app can
create a ``RuntimeConfig`` from its settings and provide it to the engine.
"""

from dataclasses import dataclass
import argparse


DEFAULT_TODAY_SIZE = 200
DEFAULT_RARE_WEIGHT = 50
DEFAULT_ARTIST_MIN_GAP = 10
DEFAULT_HISTORY_POLL_MINUTES = 90


class RuntimeConfigError(ValueError):
    """A user configuration contains invalid runtime values."""


@dataclass(frozen=True)
class RuntimeConfig:
    """User-facing runtime values for the Today selection.

    ``rare_weight`` remains on the user scale of 0 to 100. ``long_weight`` is
    derived from it so the two weights always total 100. Normalized factors are
    intended only for the scoring formula.
    """

    today_size: int = DEFAULT_TODAY_SIZE
    rare_weight: int = DEFAULT_RARE_WEIGHT
    artist_min_gap: int = DEFAULT_ARTIST_MIN_GAP
    history_poll_minutes: int = DEFAULT_HISTORY_POLL_MINUTES

    def __post_init__(self):
        _require_positive_int("today_size", self.today_size)
        _require_weight("rare_weight", self.rare_weight)
        _require_non_negative_int("artist_min_gap", self.artist_min_gap)
        _require_positive_int("history_poll_minutes", self.history_poll_minutes)

    @property
    def long_weight(self) -> int:
        """Return the Long portion complementary to ``rare_weight``."""
        return 100 - self.rare_weight

    @property
    def rare_weight_factor(self) -> float:
        return self.rare_weight / 100.0

    @property
    def long_weight_factor(self) -> float:
        return self.long_weight / 100.0


def get_runtime_config(db_path=None) -> RuntimeConfig:
    """Load persisted application settings, or central defaults on first run."""
    from application_storage import ApplicationStorage

    return ApplicationStorage(db_path).load_runtime_config()


def add_runtime_config_arguments(parser: argparse.ArgumentParser) -> None:
    """Add a CLI handoff point for scoring-engine values.

    The arguments deliberately have no argparse default. This keeps
    ``RuntimeConfig`` as the only place defining production defaults and their
    validation.
    """
    group = parser.add_argument_group("Laufzeitkonfiguration für das Scoring")
    group.add_argument("--today-size", type=int, metavar="ANZAHL")
    group.add_argument("--rare-weight", type=int, metavar="0-100")
    group.add_argument("--artist-min-gap", type=int, metavar="ANZAHL")


def runtime_config_from_args(
    args: argparse.Namespace, base_config: RuntimeConfig | None = None
) -> RuntimeConfig:
    """Apply optional CLI overrides to persisted or central configuration."""
    base_config = base_config or get_runtime_config()
    values = {
        name: value
        for name, value in (
            ("today_size", getattr(args, "today_size", None)),
            ("rare_weight", getattr(args, "rare_weight", None)),
            ("artist_min_gap", getattr(args, "artist_min_gap", None)),
        )
        if value is not None
    }
    return RuntimeConfig(
        today_size=values.get("today_size", base_config.today_size),
        rare_weight=values.get("rare_weight", base_config.rare_weight),
        artist_min_gap=values.get("artist_min_gap", base_config.artist_min_gap),
        history_poll_minutes=base_config.history_poll_minutes,
    )


def _require_positive_int(name: str, value: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise RuntimeConfigError(f"{name} muss eine positive ganze Zahl sein.")


def _require_non_negative_int(name: str, value: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise RuntimeConfigError(
            f"{name} muss eine nicht-negative ganze Zahl sein."
        )


def _require_weight(name: str, value: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 100:
        raise RuntimeConfigError(
            f"{name} muss eine ganze Zahl zwischen 0 und 100 sein."
        )
