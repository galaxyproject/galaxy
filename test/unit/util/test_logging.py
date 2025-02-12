import logging.config
import types


from galaxy.util.logging import TRACE, get_logger_names, get_log_levels, set_log_levels, addTraceLoggingLevel
addTraceLoggingLevel()


SIMPLE_LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': True,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'level': 'DEBUG',
            'formatter': 'simple',
            'stream': 'ext://sys.stdout',
        },
        'test': {
            'class': 'logging.StreamHandler',
            'level': 'DEBUG',
            'formatter': 'simple',
            'stream': 'ext://sys.stdout'
        }
    },
    'formatters': {
        'simple': {
            'format': '%(name)s: %(message)s',
        },
    },
    'loggers': {
        'console': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
        'test': {
            'handlers': ['test'],
            'level': 'WARNING',
            'propagate': False,
        }
    },
}

def test_trace_level_exists():
    assert hasattr(logging, 'TRACE')
    assert hasattr(logging, 'trace')
    assert logging.TRACE == TRACE
    assert type(getattr(logging, 'TRACE')) == int
    assert isinstance(getattr(logging, 'trace'), types.FunctionType)


def test_logging_get_names():
    logging.config.dictConfig(SIMPLE_LOGGING_CONFIG)

    index = get_logger_names()
    assert len(index) > 1
    # This is the only two loggers that we can be sure are present.
    assert 'test' in index


def test_get_logging_levels():
    logging.config.dictConfig(SIMPLE_LOGGING_CONFIG)
    levels = get_log_levels(None)
    assert 'test' in levels
    logger = levels['test']
    assert logger['level'] == 'WARNING'
    assert logger['effective'] == 'WARNING'


def test_get_logging_level():
    logging.config.dictConfig(SIMPLE_LOGGING_CONFIG)
    levels = get_log_levels('test')
    assert len(levels) == 1
    assert 'test' in levels
    logger = levels['test']
    assert logger['level'] == 'WARNING'
    assert logger['effective'] == 'WARNING'


def test_set_level():
    logging.config.dictConfig(SIMPLE_LOGGING_CONFIG)
    names = get_logger_names()
    assert 'test' in names
    levels = get_log_levels('test')
    assert 'test' in levels
    assert len(levels) == 1
    logger = levels['test']
    assert logger['level'] == 'WARNING'
    set_log_levels('test', 'DEBUG')
    assert get_log_levels('test')['test']['level'] == 'DEBUG'


def test_set_levels():
    import logging
    logging.config.dictConfig(SIMPLE_LOGGING_CONFIG)

    a = logging.getLogger('a')
    ab = logging.getLogger('a.b')
    abc = logging.getLogger('a.b.c')

    assert a.getEffectiveLevel() == logging.DEBUG
    assert ab.getEffectiveLevel() == logging.DEBUG
    assert abc.getEffectiveLevel() == logging.DEBUG

    set_log_levels('a.*', 'INFO')
    assert a.getEffectiveLevel() == logging.INFO
    assert ab.getEffectiveLevel() == logging.INFO
    assert abc.getEffectiveLevel() == logging.INFO

    set_log_levels('a.b.*', logging.WARNING)
    assert a.getEffectiveLevel() == logging.INFO
    assert ab.getEffectiveLevel() == logging.WARNING
    assert abc.getEffectiveLevel() == logging.WARNING

    set_log_levels('a.b.c.*', logging.ERROR)
    assert a.getEffectiveLevel() == logging.INFO
    assert ab.getEffectiveLevel() == logging.WARNING
    assert abc.getEffectiveLevel() == logging.ERROR

    set_log_levels('a.b.c', logging.CRITICAL)
    assert a.getEffectiveLevel() == logging.INFO
    assert ab.getEffectiveLevel() == logging.WARNING
    assert abc.getEffectiveLevel() == logging.CRITICAL

    set_log_levels('a.b', logging.DEBUG)
    assert a.getEffectiveLevel() == logging.INFO
    assert ab.getEffectiveLevel() == logging.DEBUG
    assert abc.getEffectiveLevel() == logging.CRITICAL

    set_log_levels('a', logging.TRACE)
    assert a.getEffectiveLevel() == logging.TRACE
    assert ab.getEffectiveLevel() == logging.DEBUG
    assert abc.getEffectiveLevel() == logging.CRITICAL

