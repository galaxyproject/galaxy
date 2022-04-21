""" Module used to blend ini, environment, and explicit dictionary properties
to determine application configuration. Some hard coded defaults for Galaxy but
this should be reusable by tool shed and pulsar as well.
"""
import os
import os.path
import sys
from configparser import ConfigParser
from functools import partial
from itertools import (
    product,
    starmap,
)

import yaml

from galaxy.exceptions import InvalidFileFormatError
from galaxy.util.path import (
    extensions,
    has_ext,
    joinext,
)


def find_config_file(names, exts=None, dirs=None, include_samples=False):
    """Locate a config file in multiple directories, with multiple extensions.

    >>> from shutil import rmtree
    >>> from tempfile import mkdtemp
    >>> def touch(d, f):
    ...     open(os.path.join(d, f), 'w').close()
    >>> def _find_config_file(*args, **kwargs):
    ...     return find_config_file(*args, **kwargs).replace(d, '')
    >>> d = mkdtemp()
    >>> d1 = os.path.join(d, 'd1')
    >>> d2 = os.path.join(d, 'd2')
    >>> os.makedirs(d1)
    >>> os.makedirs(d2)
    >>> touch(d1, 'foo.ini')
    >>> touch(d1, 'foo.bar')
    >>> touch(d1, 'baz.ini.sample')
    >>> touch(d2, 'foo.yaml')
    >>> touch(d2, 'baz.yml')
    >>> _find_config_file('foo', dirs=(d1, d2))
    '/d1/foo.ini'
    >>> _find_config_file('baz', dirs=(d1, d2))
    '/d2/baz.yml'
    >>> _find_config_file('baz', dirs=(d1, d2), include_samples=True)
    '/d2/baz.yml'
    >>> _find_config_file('baz', dirs=(d1,), include_samples=True)
    '/d1/baz.ini.sample'
    >>> _find_config_file('foo', dirs=(d2, d1))
    '/d2/foo.yaml'
    >>> find_config_file('quux', dirs=(d,))
    >>> _find_config_file('foo', exts=('bar', 'ini'), dirs=(d1,))
    '/d1/foo.bar'
    >>> rmtree(d)
    """
    found = __find_config_files(
        names,
        exts=exts or extensions["yaml"] + extensions["ini"],
        dirs=dirs or [os.getcwd(), os.path.join(os.getcwd(), "config")],
        include_samples=include_samples,
    )
    if not found:
        return None
    # doesn't really make sense to log here but we should probably generate a warning of some kind if more than one
    # config is found.
    return found[0]


def load_app_properties(
    kwds=None, ini_file=None, ini_section=None, config_file=None, config_section=None, config_prefix="GALAXY_CONFIG_"
):
    if config_file is None:
        config_file = ini_file
        config_section = ini_section

    # read from file or init w/no file
    if config_file:
        properties = read_properties_from_file(config_file, config_section)
    else:
        properties = {"__file__": None}

    # update from kwds
    if kwds:
        properties.update(kwds)

    # update from env
    override_prefix = f"{config_prefix}OVERRIDE_"
    for key in os.environ:
        if key.startswith(override_prefix):
            config_key = key[len(override_prefix) :].lower()
            properties[config_key] = os.environ[key]
        elif key.startswith(config_prefix):
            config_key = key[len(config_prefix) :].lower()
            if config_key not in properties:
                properties[config_key] = os.environ[key]

    return properties


def read_properties_from_file(config_file, config_section=None):
    properties = {}
    if has_ext(config_file, "yaml", aliases=True, ignore="sample"):
        if config_section is None:
            config_section = "galaxy"
        properties.update(__default_properties(config_file))
        raw_properties = _read_from_yaml_file(config_file)
        if raw_properties:
            properties.update(raw_properties.get(config_section) or {})
    elif has_ext(config_file, "ini", aliases=True, ignore="sample"):
        if config_section is None:
            config_section = "app:main"
        parser = nice_config_parser(config_file)  # default properties loaded w/parser
        if parser.has_section(config_section):
            properties.update(dict(parser.items(config_section)))
        else:
            properties.update(parser.defaults())
    else:
        raise InvalidFileFormatError(f"File '{config_file}' doesn't have a supported extension")
    return properties


def _read_from_yaml_file(path):
    with open(path) as f:
        return yaml.safe_load(f)


def nice_config_parser(path):
    parser = NicerConfigParser(path, defaults=__default_properties(path))
    parser.optionxform = str  # Don't lower-case keys
    with open(path) as f:
        parser.read_file(f)
    return parser


class NicerConfigParser(ConfigParser):
    def __init__(self, filename, *args, **kw):
        ConfigParser.__init__(self, *args, **kw)
        self.filename = filename
        self._interpolation = self.InterpolateWrapper(self._interpolation)

    def defaults(self):
        """Return the defaults, with their values interpolated (with the
        defaults dict itself)

        Mainly to support defaults using values such as %(here)s
        """
        defaults = ConfigParser.defaults(self).copy()
        for key, val in defaults.items():
            defaults[key] = self.get("DEFAULT", key) or val
        return defaults

    class InterpolateWrapper:
        def __init__(self, original):
            self._original = original

        def __getattr__(self, name):
            return getattr(self._original, name)

        def before_get(self, parser, section, option, value, defaults):
            try:
                return self._original.before_get(parser, section, option, value, defaults)
            except Exception:
                e = sys.exc_info()[1]
                args = list(e.args)
                args[0] = f"Error in file {parser.filename}: {e}"
                e.args = tuple(args)
                e.message = args[0]
                raise


def _running_from_source():
    paths = ["run.sh", "lib/galaxy/__init__.py", "scripts/common_startup.sh"]
    return all(map(os.path.exists, paths))


running_from_source = _running_from_source()


def get_data_dir(properties):
    data_dir = properties.get("data_dir", None)
    if data_dir is None:
        if running_from_source:
            data_dir = "./database"
        else:
            config_dir = properties.get("config_dir", os.path.dirname(properties["__file__"]))
            data_dir = os.path.join(config_dir, "data")
    return data_dir


def __get_all_configs(dirs, names):
    return list(filter(os.path.exists, starmap(os.path.join, product(dirs, names))))


def __find_config_files(names, exts=None, dirs=None, include_samples=False):
    sample_names = []
    if isinstance(names, str):
        names = [names]
    if not dirs:
        dirs = [os.getcwd()]
    if exts:
        # add exts to names, converts back into a list because it's going to be small and we might consume names twice
        names = list(starmap(joinext, product(names, exts)))
    if include_samples:
        sample_names = map(partial(joinext, ext="sample"), names)
    # check for all names in each dir before moving to the next dir. could do it the other way around but that makes
    # less sense to me.
    return __get_all_configs(dirs, names) or __get_all_configs(dirs, sample_names)


def __default_properties(path):
    return {"here": os.path.dirname(os.path.abspath(path)), "__file__": os.path.abspath(path)}


__all__ = ("find_config_file", "get_data_dir", "load_app_properties", "NicerConfigParser", "running_from_source")
