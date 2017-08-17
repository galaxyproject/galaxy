"""Generic config parsing into dictionary.
"""
import errno
import logging

try:
    import yaml
except ImportError:
    yaml = None


log = logging.getLogger(__name__)


def parse_config(config_file, root, default=None):
    if default:
        conf = default.copy()
    else:
        conf = {}
    try:
        load_func = __load_func(config_file)
        with open(config_file) as fh:
            c = load_func(fh)
            if not c:
                c = {}
            conf.update(c.get(root, {}))
    except (OSError, IOError) as exc:
        if exc.errno == errno.ENOENT:
            log.warning("config file '%s' does not exist, running with default config", config_file)
        else:
            raise
    return conf


def __load_func(path):
    if path.endswith('yaml') or path.endswith('.yml'):
        if not yaml:
            raise RuntimeError("The 'yaml' module could not be imported, please install PyYAML to read '%s'" % path)
        return yaml.load
