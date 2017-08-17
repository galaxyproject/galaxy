""" Module used to blend ini, environment, and explicit dictionary properties
to determine application configuration. Some hard coded defaults for Galaxy but
this should be reusable by tool shed and pulsar as well.
"""
import os
import os.path
import sys

import yaml

from six import iteritems
from six.moves.configparser import ConfigParser

from galaxy.util import listify


def find_config_file(default, old_defaults, explicit, cwd=None):
    old_defaults = listify(old_defaults)
    if cwd is not None:
        default = os.path.join(cwd, default)
        for i in range(len(old_defaults)):
            old_defaults[i] = os.path.join(cwd, old_defaults[i])
        if explicit is not None:
            explicit = os.path.join(cwd, explicit)

    if explicit:
        if os.path.exists(explicit):
            config_file = explicit
        else:
            raise Exception("Problem determining Galaxy's configuration - the specified configuration file cannot be found.")
    else:
        config_file = None
        if os.path.exists(default):
            config_file = default
        if config_file is None:
            for old_default in old_defaults:
                if os.path.exists(old_default):
                    config_file = old_default

        if config_file is None:
            config_file = default + ".sample"

    return config_file


def load_app_properties(
    kwds={},
    ini_file=None,
    ini_section=None,
    config_file=None,
    config_section=None,
    config_prefix="GALAXY_CONFIG_"
):
    properties = kwds.copy() if kwds else {}
    if config_file is None:
        config_file = ini_file
        config_section = ini_section

    if config_file:
        if not config_file.endswith(".yml") and not config_file.endswith(".yml.sample"):
            if config_section is None:
                config_section = "app:main"
            parser = nice_config_parser(config_file)
            properties.update(dict(parser.items(config_section)))
        else:
            if config_section is None:
                config_section = "galaxy"

            with open(config_file, "r") as f:
                raw_properties = yaml.load(f)
            properties = raw_properties[config_section] or {}

    override_prefix = "%sOVERRIDE_" % config_prefix
    for key in os.environ:
        if key.startswith(override_prefix):
            config_key = key[len(override_prefix):].lower()
            properties[config_key] = os.environ[key]
        elif key.startswith(config_prefix):
            config_key = key[len(config_prefix):].lower()
            if config_key not in properties:
                properties[config_key] = os.environ[key]

    return properties


def nice_config_parser(path):
    defaults = {
        'here': os.path.dirname(os.path.abspath(path)),
        '__file__': os.path.abspath(path)
    }
    parser = NicerConfigParser(path, defaults=defaults)
    parser.optionxform = str  # Don't lower-case keys
    with open(path) as f:
        parser.read_file(f)
    return parser


class NicerConfigParser(ConfigParser):

    def __init__(self, filename, *args, **kw):
        ConfigParser.__init__(self, *args, **kw)
        self.filename = filename
        if hasattr(self, '_interpolation'):
            self._interpolation = self.InterpolateWrapper(self._interpolation)

    read_file = getattr(ConfigParser, 'read_file', ConfigParser.readfp)

    def defaults(self):
        """Return the defaults, with their values interpolated (with the
        defaults dict itself)

        Mainly to support defaults using values such as %(here)s
        """
        defaults = ConfigParser.defaults(self).copy()
        for key, val in iteritems(defaults):
            defaults[key] = self.get('DEFAULT', key) or val
        return defaults

    def _interpolate(self, section, option, rawval, vars):
        # Python < 3.2
        try:
            return ConfigParser._interpolate(
                self, section, option, rawval, vars)
        except Exception:
            e = sys.exc_info()[1]
            args = list(e.args)
            args[0] = 'Error in file %s: %s' % (self.filename, e)
            e.args = tuple(args)
            e.message = args[0]
            raise

    class InterpolateWrapper(object):
        # Python >= 3.2
        def __init__(self, original):
            self._original = original

        def __getattr__(self, name):
            return getattr(self._original, name)

        def before_get(self, parser, section, option, value, defaults):
            try:
                return self._original.before_get(parser, section, option,
                                                 value, defaults)
            except Exception:
                e = sys.exc_info()[1]
                args = list(e.args)
                args[0] = 'Error in file %s: %s' % (parser.filename, e)
                e.args = tuple(args)
                e.message = args[0]
                raise


__all__ = ('find_config_file', 'load_app_properties', 'NicerConfigParser')
