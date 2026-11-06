import copy
import logging
import logging.config

import pytest

from galaxy.config import (
    COMPLIANCE_LOGGER_NAME,
    default_log_config,
    LOGGING_CONFIG_DEFAULT,
    LogLevelFilter,
)

ALL_RECORDS = {"debug record", "info record", "warning record", "error record", "compliance record"}


@pytest.fixture
def restore_logging():
    """Restore the global logging configuration changed by logging.config.dictConfig()"""
    root = logging.getLogger()
    root_state = (root.level, root.handlers[:])
    loggers_state = {
        name: (logger.level, logger.handlers[:], logger.propagate, logger.disabled)
        for name, logger in logging.root.manager.loggerDict.items()
        if isinstance(logger, logging.Logger)
    }
    yield
    root.setLevel(root_state[0])
    root.handlers[:] = root_state[1]
    for name, logger in logging.root.manager.loggerDict.items():
        if not isinstance(logger, logging.Logger):
            continue
        level, handlers, propagate, disabled = loggers_state.get(name, (logging.NOTSET, [], True, False))
        logger.setLevel(level)
        logger.handlers[:] = handlers
        logger.propagate = propagate
        logger.disabled = disabled


@pytest.mark.parametrize(
    "log_level, expected",
    [
        ("TRACE", ALL_RECORDS),
        ("DEBUG", ALL_RECORDS),
        ("INFO", ALL_RECORDS - {"debug record"}),
        ("WARNING", {"warning record", "error record", "compliance record"}),
        ("ERROR", {"error record", "compliance record"}),
    ],
)
def test_default_log_config_log_level(log_level, expected, restore_logging, capsys):
    logging_conf = default_log_config(log_level)
    # The "stack" formatter and filter come from galaxy.web_stack, which is not
    # a dependency of the galaxy-config package, and are irrelevant to levels.
    # Replace them with a plain formatter and a no-op filter respectively.
    logging_conf["formatters"]["stack"] = {"format": "%(name)s %(levelname)s %(message)s"}
    logging_conf["filters"]["stack"] = {}
    # The console handler logs to sys.stderr, which is captured by capsys
    logging.config.dictConfig(logging_conf)
    log = logging.getLogger("galaxy.test")
    log.debug("debug record")
    log.info("info record")
    log.warning("warning record")
    log.error("error record")
    logging.getLogger(COMPLIANCE_LOGGER_NAME).info("compliance record")

    stderr = capsys.readouterr().err
    logged = {record for record in ALL_RECORDS if record in stderr}
    assert logged == expected


def test_default_log_config_does_not_modify_default():
    original = copy.deepcopy(LOGGING_CONFIG_DEFAULT)
    default_log_config("WARNING")
    assert LOGGING_CONFIG_DEFAULT == original


def test_log_level_filter_unknown_level():
    with pytest.raises(ValueError):
        LogLevelFilter("NOT_A_LEVEL")
