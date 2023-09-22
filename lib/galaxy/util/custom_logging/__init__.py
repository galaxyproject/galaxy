import logging
import types

# Add custom "TRACE" log level for ludicrous verbosity.
LOGLV_TRACE = 5
logging.addLevelName(LOGLV_TRACE, "TRACE")


def trace(self, message, *args, **kws):
    if self.isEnabledFor(LOGLV_TRACE):
        self._log(LOGLV_TRACE, message, args, **kws)


def get_logger(name=None):
    logger = logging.getLogger(name)
    logger.trace = types.MethodType(trace, logger)
    return logger
