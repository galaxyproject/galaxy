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

    def format(self, key: str, value: Any) -> FormattedMetric | None:
        """Render a metric for display, or None to record it without displaying it.

        Returning None is how a plugin says "collected, but this particular value is not worth
        showing" -- a metric that is uninteresting at some values and interesting at others.
        Safety levels are the other way to keep a metric out of the UI, but they decide per
        metric name rather than per value.
        """
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
