"""Utilities related to formatting job metrics for human consumption."""


class JobMetricFormatter:
    """Format job metric key-value pairs for human consumption in Web UI."""

    def format(self, key, value):
        return (str(key), str(value))


def seconds_to_str(value):
    """Convert seconds to a simple simple string describing the amount of time."""
    if value < 60:
        return "%s seconds" % round(value, 2)
    elif value < 3600:
        return "%s minutes" % round(value / 60, 2)
    else:
        return "{} hours and {} minutes".format(value // 3600, round((value % 3600) / 60, 2))
