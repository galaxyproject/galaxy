""" Module used to blend ini, environment, and explicit dictionary properties
to determine application configuration. Some hard coded defaults for Galaxy but
this should be reusable by tool shed and pulsar as well.
"""
import os
import os.path


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
        # Mimic the way loadwsgi loads configuration files - needed for
        # correctness given the very specific ways interpolation is handled.
        from galaxy.util.pastescript.loadwsgi import NicerConfigParser
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
