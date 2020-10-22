"""Utilities related to formatting job metrics for human consumption."""


class JobMetricFormatter:
    """Format job metric key-value pairs for human consumption in Web UI."""

    def format(self, key, value):
        return (str(key), str(value))


def seconds_to_str(value):
    """Convert seconds to a simple simple string describing the amount of time."""
    mins, secs = divmod(value, 60)
    hours, mins = divmod(mins, 60)
    if value < 60:
        return "%s seconds" % secs
    elif value < 3600:
        return "%s minutes" % mins
    else:
        return "%s hours and %s minutes" % (hours, mins)
