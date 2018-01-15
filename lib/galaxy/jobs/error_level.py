

# These determine stdio-based error levels from matching on regular expressions
# and exit codes. They are meant to be used comparatively, such as showing
# that warning < fatal. This is really meant to just be an enum.
class StdioErrorLevel(object):
    NO_ERROR = 0
    LOG = 1
    WARNING = 2
    FATAL = 3
    FATAL_OOM = 4
    MAX = 4
    descs = {
        NO_ERROR: 'No error',
        LOG: 'Log',
        WARNING: 'Warning',
        FATAL: 'Fatal error',
        FATAL_OOM: 'Out of memory error',
    }

    @staticmethod
    def desc(error_level):
        err_msg = "Unknown error"
        if error_level > 0 and error_level <= StdioErrorLevel.MAX:
            err_msg = StdioErrorLevel.descs[error_level]
        return err_msg
