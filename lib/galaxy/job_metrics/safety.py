from enum import Enum


class Safety(Enum):
    UNSAFE = 2
    POTENTIALLY_SENSITVE = 4
    SAFE = 6


DEFAULT_SAFETY = Safety.POTENTIALLY_SENSITVE


__all__ = (
    "DEFAULT_SAFETY",
    "Safety",
)
