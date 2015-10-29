from .interface import ToolStdioExitCode
from .interface import ToolStdioRegex


def error_on_exit_code():
    exit_code_lower = ToolStdioExitCode()
    exit_code_lower.range_start = float("-inf")
    exit_code_lower.range_end = -1
    _set_fatal(exit_code_lower)
    exit_code_high = ToolStdioExitCode()
    exit_code_high.range_start = 1
    exit_code_high.range_end = float("inf")
    _set_fatal(exit_code_high)
    return [exit_code_lower, exit_code_high], []


def aggressive_error_checks():
    exit_codes, _ = error_on_exit_code()
    # these regexes are processed as case insensitive by default
    regexes = [
        _error_regex("exception:"),
        _error_regex("error:")
    ]
    return exit_codes, regexes


def _error_regex(match):
    regex = ToolStdioRegex()
    _set_fatal(regex)
    regex.match = match
    regex.stdout_match = True
    regex.stderr_match = True
    return regex


def _set_fatal(obj):
    from galaxy.jobs.error_level import StdioErrorLevel
    obj.error_level = StdioErrorLevel.FATAL
