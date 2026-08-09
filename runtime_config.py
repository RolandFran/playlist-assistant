"""Zentrale Laufzeitkonfiguration der Playlist-Engine.

Die Werte sind bewusst Home-Assistant-unabhängig. Eine spätere App kann eine
``RuntimeConfig`` aus ihren Einstellungen erzeugen und an die Engine geben.
"""

from dataclasses import dataclass


DEFAULT_TODAY_SIZE = 200
DEFAULT_RARE_WEIGHT = 50
DEFAULT_LONG_WEIGHT = 50
DEFAULT_ARTIST_MIN_GAP = 10


class RuntimeConfigError(ValueError):
    """Eine Benutzerkonfiguration enthält ungültige Laufzeitwerte."""


@dataclass(frozen=True)
class RuntimeConfig:
    """Benutzerseitige Laufzeitwerte für die Today-Auswahl.

    Gewichtungen bleiben auf der Benutzer-Skala von 0 bis 100. Die
    normalisierten Faktoren sind nur für die Scoring-Formel bestimmt.
    """

    today_size: int = DEFAULT_TODAY_SIZE
    rare_weight: int = DEFAULT_RARE_WEIGHT
    long_weight: int = DEFAULT_LONG_WEIGHT
    artist_min_gap: int = DEFAULT_ARTIST_MIN_GAP

    def __post_init__(self):
        _require_positive_int("today_size", self.today_size)
        _require_weight("rare_weight", self.rare_weight)
        _require_weight("long_weight", self.long_weight)
        _require_non_negative_int("artist_min_gap", self.artist_min_gap)

        if self.rare_weight + self.long_weight != 100:
            raise RuntimeConfigError(
                "rare_weight und long_weight müssen zusammen 100 ergeben."
            )

    @property
    def rare_weight_factor(self) -> float:
        return self.rare_weight / 100.0

    @property
    def long_weight_factor(self) -> float:
        return self.long_weight / 100.0


def get_runtime_config() -> RuntimeConfig:
    """Liefert die lokalen Defaults, bis eine spätere App Werte bereitstellt."""
    return RuntimeConfig()


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
