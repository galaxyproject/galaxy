import logging
from typing import (
    Any,
    cast,
    Optional,
)


class GalaxyLogger(logging.Logger):
    def trace(self, message: object, *args: Any, **kwargs: Any) -> None:
        if self.isEnabledFor(LOGLV_TRACE):
            self._log(LOGLV_TRACE, message, args, **kwargs)


# Add custom "TRACE" log level for ludicrous verbosity.
LOGLV_TRACE = 5
logging.addLevelName(LOGLV_TRACE, "TRACE")
logging.setLoggerClass(GalaxyLogger)


def get_logger(name: Optional[str] = None) -> GalaxyLogger:
    logger = logging.getLogger(name)
    return cast(GalaxyLogger, logger)
