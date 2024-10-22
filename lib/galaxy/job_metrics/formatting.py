"""Utilities related to formatting job metrics for human consumption."""

from typing import (
    Any,
    NamedTuple,
)


class FormattedMetric(NamedTuple):
    title: str
    value: str


class JobMetricFormatter:
    """Format job metric key-value pairs for human consumption in Web UI."""

    def format(self, key: str, value: Any) -> FormattedMetric:
        return FormattedMetric(key, str(value))


def seconds_to_str(value: int) -> str:
    """Convert seconds to a simple simple string describing the amount of time."""
    mins, secs = divmod(value, 60)
    hours, mins = divmod(mins, 60)

    if value < 60:
        return f"{secs} second{'s' if secs != 1 else ''}"
    elif value < 3600:
        return f"{mins} minute{'s' if mins != 1 else ''}"
    else:
        return f"{hours} hour{'s' if hours != 1 else ''} and {mins} minute{'s' if mins != 1 else ''}"
