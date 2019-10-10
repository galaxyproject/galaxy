"""Utilities related to formatting job metrics for human consumption."""


class JobMetricFormatter(object):
    """Format job metric key-value pairs for human consumption in Web UI."""

    def format(self, key, value):
        return (str(key), str(value))


def seconds_to_str(value):
    """Convert seconds to a simple simple string describing the amount of time."""
    if value < 60:
        return "%s seconds" % value
    elif value < 3600:
        return "%s minutes" % (value / 60)
    else:
        return "%s hours and %s minutes" % (value / 3600, (value % 3600) / 60)
