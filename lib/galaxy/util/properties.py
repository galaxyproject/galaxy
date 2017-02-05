""" Module used to blend ini, environment, and explicit dictionary properties
to determine application configuration. Some hard coded defaults for Galaxy but
this should be reusable by tool shed and pulsar as well.
"""
import os
import os.path
import sys

from six import iteritems
from six.moves.configparser import ConfigParser


def find_config_file(default, old_default, explicit, cwd=None):
    if cwd is not None:
        default = os.path.join(cwd, default)
        old_default = os.path.join(cwd, old_default)
        if explicit is not None:
            explicit = os.path.join(cwd, explicit)

    if explicit:
        if os.path.exists(explicit):
            config_file = explicit
        else:
            raise Exception("Problem determining Galaxy's configuration - the specified configuration file cannot be found.")
    else:
        if not os.path.exists( default ) and os.path.exists( old_default ):
            config_file = old_default
        elif os.path.exists( default ):
            config_file = default
        else:
            config_file = default + ".sample"
    return config_file


def load_app_properties(
    kwds={},
    ini_file=None,
    ini_section="app:main",
    config_prefix="GALAXY_CONFIG_"
):
    properties = kwds.copy() if kwds else {}
    if ini_file:
        defaults = {
            'here': os.path.dirname(os.path.abspath(ini_file)),
            '__file__': os.path.abspath(ini_file)
        }
        parser = NicerConfigParser(ini_file, defaults=defaults)
        parser.optionxform = str  # Don't lower-case keys
        with open(ini_file) as f:
            parser.read_file(f)

        properties.update( dict( parser.items( ini_section ) ) )

    override_prefix = "%sOVERRIDE_" % config_prefix
    for key in os.environ:
        if key.startswith( override_prefix ):
            config_key = key[ len( override_prefix ): ].lower()
            properties[ config_key ] = os.environ[ key ]
        elif key.startswith( config_prefix ):
            config_key = key[ len( config_prefix ): ].lower()
            if config_key not in properties:
                properties[ config_key ] = os.environ[ key ]

    return properties


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
