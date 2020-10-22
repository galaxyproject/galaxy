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
        return f"{secs} second{'s' if secs != 1 else ''}"
    elif value >= 60 and value <= 119:
        return "1 minute"
    elif value >= 120 and value < 3600:
        return f"{mins} minutes"
    elif value >= 3600 and value < 7200:
        if mins == 1:
            return "1 hour and 1 minute"
        else:
            return f"1 hour and {mins} minutes"
    else:
        if mins == 1:
            return f"{hours} hours and 1 minute"
        else:
            return f"{hours} hours and {mins} minutes"
