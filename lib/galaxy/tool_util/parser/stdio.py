import math


class StdioErrorLevel:
    """
    These determine stdio-based error levels from matching on regular expressions
    and exit codes. They are meant to be used comparatively, such as showing
    that warning < fatal. This is really meant to just be an enum.
    """

    NO_ERROR = 0
    LOG = 1
    QC = 1.1
    WARNING = 2
    FATAL = 3
    FATAL_OOM = 4
    MAX = 4
    descs = {
        NO_ERROR: "No error",
        LOG: "Log",
        QC: "QC",
        WARNING: "Warning",
        FATAL: "Fatal error",
        FATAL_OOM: "Out of memory error",
    }

    @staticmethod
    def desc(error_level):
        err_msg = "Unknown error"
        if error_level > 0 and error_level <= StdioErrorLevel.MAX:
            err_msg = StdioErrorLevel.descs[error_level]
        return err_msg


class ToolStdioExitCode:
    """
    This is a container for the <stdio> element's <exit_code> subelement.
    The exit_code element has a range of exit codes and the error level.
    """

    def __init__(self, as_dict=None):
        as_dict = as_dict or {}
        self.range_start = as_dict.get("range_start", -math.inf)
        self.range_end = as_dict.get("range_end", math.inf)
        self.error_level = as_dict.get("error_level", StdioErrorLevel.FATAL)
        self.desc = as_dict.get("desc", "")

    def to_dict(self):
        return {
            "class": "ToolStdioExitCode",
            "range_start": self.range_start,
            "range_end": self.range_end,
            "error_level": self.error_level,
            "desc": self.desc,
        }


class ToolStdioRegex:
    """
    This is a container for the <stdio> element's regex subelement.
    The regex subelement has a "match" attribute, a "sources"
    attribute that contains "output" and/or "error", and a "level"
    attribute that contains "warning" or "fatal".
    """

    def __init__(self, as_dict=None):
        as_dict = as_dict or {}
        self.match = as_dict.get("match", "")
        self.stdout_match = as_dict.get("stdout_match", False)
        self.stderr_match = as_dict.get("stderr_match", False)
        self.error_level = as_dict.get("error_level", StdioErrorLevel.FATAL)
        self.desc = as_dict.get("desc", "")

    def to_dict(self):
        return {
            "class": "ToolStdioRegex",
            "match": self.match,
            "stdout_match": self.stdout_match,
            "stderr_match": self.stderr_match,
            "error_level": self.error_level,
            "desc": self.desc,
        }


def error_on_exit_code(out_of_memory_exit_code=None):
    exit_codes = []

    if out_of_memory_exit_code:
        exit_code_oom = ToolStdioExitCode()
        exit_code_oom.range_start = int(out_of_memory_exit_code)
        exit_code_oom.range_end = int(out_of_memory_exit_code)
        _set_oom(exit_code_oom)
        exit_codes.append(exit_code_oom)

    exit_code_lower = ToolStdioExitCode()
    exit_code_lower.range_start = -math.inf
    exit_code_lower.range_end = -1
    _set_fatal(exit_code_lower)
    exit_codes.append(exit_code_lower)
    exit_code_high = ToolStdioExitCode()
    exit_code_high.range_start = 1
    exit_code_high.range_end = math.inf
    _set_fatal(exit_code_high)
    exit_codes.append(exit_code_high)
    return exit_codes, []


def aggressive_error_checks():
    exit_codes, _ = error_on_exit_code()
    # these regexes are processed as case insensitive by default
    regexes = [
        _oom_regex("MemoryError"),
        _oom_regex("std::bad_alloc"),
        _oom_regex("java.lang.OutOfMemoryError"),
        _oom_regex("Out of memory"),
        _error_regex("exception:"),
        _error_regex("error:"),
    ]
    return exit_codes, regexes


def _oom_regex(match):
    regex = ToolStdioRegex()
    _set_oom(regex)
    regex.match = match
    regex.stdout_match = True
    regex.stderr_match = True
    return regex


def _error_regex(match):
    regex = ToolStdioRegex()
    _set_fatal(regex)
    regex.match = match
    regex.stdout_match = True
    regex.stderr_match = True
    return regex


def _set_oom(obj):
    obj.error_level = StdioErrorLevel.FATAL_OOM


def _set_fatal(obj):
    obj.error_level = StdioErrorLevel.FATAL
