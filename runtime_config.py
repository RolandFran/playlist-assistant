"""Zentrale Laufzeitkonfiguration der Playlist-Engine.

Die Werte sind bewusst Home-Assistant-unabhängig. Eine spätere App kann eine
``RuntimeConfig`` aus ihren Einstellungen erzeugen und an die Engine geben.
"""

from dataclasses import dataclass
import argparse


DEFAULT_TODAY_SIZE = 200
DEFAULT_RARE_WEIGHT = 50
DEFAULT_ARTIST_MIN_GAP = 10


class RuntimeConfigError(ValueError):
    """Eine Benutzerkonfiguration enthält ungültige Laufzeitwerte."""


@dataclass(frozen=True)
class RuntimeConfig:
    """Benutzerseitige Laufzeitwerte für die Today-Auswahl.

    ``rare_weight`` bleibt auf der Benutzer-Skala von 0 bis 100.
    ``long_weight`` wird daraus abgeleitet, damit beide Gewichtungen immer
    zusammen 100 ergeben. Die normalisierten Faktoren sind nur für die
    Scoring-Formel bestimmt.
    """

    today_size: int = DEFAULT_TODAY_SIZE
    rare_weight: int = DEFAULT_RARE_WEIGHT
    artist_min_gap: int = DEFAULT_ARTIST_MIN_GAP

    def __post_init__(self):
        _require_positive_int("today_size", self.today_size)
        _require_weight("rare_weight", self.rare_weight)
        _require_non_negative_int("artist_min_gap", self.artist_min_gap)

    @property
    def long_weight(self) -> int:
        """Den zu ``rare_weight`` komplementären Long-Anteil liefern."""
        return 100 - self.rare_weight

    @property
    def rare_weight_factor(self) -> float:
        return self.rare_weight / 100.0

    @property
    def long_weight_factor(self) -> float:
        return self.long_weight / 100.0


def get_runtime_config() -> RuntimeConfig:
    """Liefert die lokalen Defaults, bis eine spätere App Werte bereitstellt."""
    return RuntimeConfig()


def add_runtime_config_arguments(parser: argparse.ArgumentParser) -> None:
    """Ergänzt einen CLI-Übergabepunkt für die Werte der Scoring-Engine.

    Die Argumente haben absichtlich keinen argparse-Default. Dadurch bleibt
    ``RuntimeConfig`` die einzige Stelle, die die produktiven Defaults und
    deren Validierung festlegt.
    """
    group = parser.add_argument_group("Laufzeitkonfiguration für das Scoring")
    group.add_argument("--today-size", type=int, metavar="ANZAHL")
    group.add_argument("--rare-weight", type=int, metavar="0-100")
    group.add_argument("--artist-min-gap", type=int, metavar="ANZAHL")


def runtime_config_from_args(args: argparse.Namespace) -> RuntimeConfig:
    """Erzeugt eine validierte Konfiguration aus optionalen CLI-Werten."""
    values = {
        name: value
        for name, value in (
            ("today_size", getattr(args, "today_size", None)),
            ("rare_weight", getattr(args, "rare_weight", None)),
            ("artist_min_gap", getattr(args, "artist_min_gap", None)),
        )
        if value is not None
    }
    return RuntimeConfig(**values)


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
