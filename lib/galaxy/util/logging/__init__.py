import logging 
from typing import List, Dict


TRACE = logging.DEBUG - 5

log = logging.getLogger(__name__)


def addTraceLoggingLevel():
    addLoggingLevel('TRACE', TRACE)


def set_logging_levels_from_config(configuration: dict):
    all_logger_names = logging.Logger.manager.loggerDict.keys()
    settings = dict()
    for name,level in configuration.items():
        if type(level) == int:
            level = logging.getLevelName(level)
        else:
            level = level.upper()
        if name.endswith(".*"):
            pattern = name[:-2]
            for name in all_logger_names:
                if name.startswith(pattern):
                    settings[name] = level
        else:
            settings[name] = level
    for name,level in settings.items():
        logging.getLogger(name).setLevel(level)


def _get_level_info(logger) -> Dict[str, str]:
    '''
    Get the level and effective level of a logger

    :param logger: The logger to get the info for
    :type logger: logging.Logger

    :return: The level and effective level of the logger
    :rtype: Dict[str, str]
    '''
    if logger is None:
        return {
            "name": "None",
            "level": "NOTSET",
            "effective": "NOTSET"
        }
    return {
        "name": logger.name,
        "level": logging.getLevelName(logger.level),
        "effective": logging.getLevelName(logger.getEffectiveLevel())
    }


def get_logger_names() -> List[str]:
    '''
    Gets the names of all the currently configured loggers.

    :return: The names of all the currently configured loggers
    :rtype: List[str]
    '''
    log.info("Getting a list of all configured loggers")
    logger_dict = logging.Logger.manager.loggerDict
    loggers = [name for name in logger_dict if isinstance(logger_dict[name], logging.Logger)]
    return loggers



def get_log_levels(name) -> Dict[str, Dict[str, str]]:
    '''
    Get the log level for a one or more loggers. If no name is provided then
    the levels for all loggers is returned.

    :param name: The name of the logger to get the level for
    :type name: str

    :return: The log level for the logger
    :rtype: Dict[str, Dict[str, str]]
    '''
    # if not trans.user_is_admin:
    #     log.warning("Only admins can get log level")
    #     raise AdminRequiredException()
    log.info("Getting level for logger %s", name)
    loggers = get_logger_names()
    if name is None:
        result = {}
        for logger_name in loggers:
            logger = logging.getLogger(logger_name)
            result[logger_name] = _get_level_info(logger)
        return result
    elif name.endswith(".*"):
        result = {}
        pattern = name[:-2]
        for logger_name in [logger for logger in loggers if logger.startswith(pattern)]:
            logger = logging.getLogger(logger_name)
            result[logger_name] = _get_level_info(logger)
        return result
    elif name in loggers:
        logger = logging.getLogger(name)
        return { name: _get_level_info(logger) }
    log.warning("Logger %s not found", name)
    return { "UNKNOWN": _get_level_info(None) }


def set_log_levels(name, level) -> List[Dict[str,str]]:
    '''
    Set the log level for a one or more loggers.

    To set the level for a single logger, pass the name of the logger. To set
    the level for all loggers that start with a certain prefix, e.g. all the logger
    in a particular package, pass the prefix followed by ".*".


    :param name: The name of the logger(s) to set the level for
    :type name: str
    :param level: The level to set the logger to
    :type level: str

    :return: The log level for the logger
    :rtype: LoggerLevelInfo
    '''
    # if not trans.user_is_admin:
    #     log.warning("Only admins can set log level")
    #     raise AdminRequiredException()
    log.info("Setting level for logger %s to %s", name, level)
    result = []
    loggers = get_logger_names()
    if name.endswith(".*"):
        pattern = name[:-2]
        for logger_name in [logger for logger in loggers if logger.startswith(pattern)]:
            logger = logging.getLogger(logger_name)
            logger.setLevel(level)
            result.append(_get_level_info(logger))
        return result
    elif name in loggers:
        logger = logging.getLogger(name)
        logger.setLevel(level)
        result.append(_get_level_info(logger))
    else:
        log.warning("Logger %s not found", name)
    return result


def addLoggingLevel(levelName, levelNum, methodName=None):
    """
    A modified version of the method found at
    https://stackoverflow.com/a/35804945/1691778

    Rather than raising an AttributeError we simply return if the levelName or
    methodName already exist.

    --- Original Docstring ---

    Comprehensively adds a new logging level to the `logging` module and the
    currently configured logging class.

    `levelName` becomes an attribute of the `logging` module with the value
    `levelNum`. `methodName` becomes a convenience method for both `logging`
    itself and the class returned by `logging.getLoggerClass()` (usually just
    `logging.Logger`). If `methodName` is not specified, `levelName.lower()` is
    used.

    This method was inspired by the answers to Stack Overflow post
    http://stackoverflow.com/q/2183233/2988730, especially
    http://stackoverflow.com/a/13638084/2988730

    Example
    -------
    >>> addLoggingLevel('TRACE', logging.DEBUG - 5)
    >>> logging.getLogger(__name__).setLevel("TRACE")
    >>> logging.getLogger(__name__).trace('that worked')
    >>> logging.trace('so did this')
    >>> logging.TRACE
    5

    """
    if not methodName:
        methodName = levelName.lower()

    if hasattr(logging, levelName) or hasattr(logging, methodName) or hasattr(logging.getLoggerClass(), methodName):
        logging.warning("Attempted to add logging level %s with level number %d and method name %s, but one or more already exist", levelName, levelNum, methodName)
        # traceback.print_stack()
        return

    # TDOD: Do we really want to do this here?
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s [%(levelname)s] %(name)s %(filename)s:%(lineno)d - %(message)s')

    def logForLevel(self, message, *args, **kwargs):
        if self.isEnabledFor(levelNum):
            self._log(levelNum, message, args, **kwargs)
    def logToRoot(message, *args, **kwargs):
        logging.log(levelNum, message, *args, **kwargs)

    logging.addLevelName(levelNum, levelName)
    setattr(logging, levelName, levelNum)
    setattr(logging.getLoggerClass(), methodName, logForLevel)
    setattr(logging, methodName, logToRoot)
    logging.info("Trace level logging has been enabled")


class DebuggingLogHander(logging.Handler):
    """
    A log handler used during testing to capture log records in memory so we
    can validate what has been logged.
    """
    def __init__(self):
        logging.Handler.__init__(self)
        self.records = []

    def emit(self, record):
        self.records.append(record)

    def reset(self):
        self.records = []

    def get_records(self):
        return self.records
