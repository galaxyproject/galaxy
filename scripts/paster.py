"""
Bootstrap the Galaxy framework.

This should not be called directly!  Use the run.sh script in Galaxy's
top level directly.
"""

import os, sys

try:
    import configparser
except:
    import ConfigParser as configparser

# ensure supported version
from check_python import check_python
try:
    check_python()
except:
    sys.exit( 1 )

new_path = [ os.path.join( os.getcwd(), "lib" ) ]
new_path.extend( sys.path[1:] ) # remove scripts/ from the path
sys.path = new_path

from galaxy import eggs

if 'LOG_TEMPFILES' in os.environ:
    from log_tempfile import TempFile
    _log_tempfile = TempFile()
    import tempfile

try:
    serve = sys.argv.index('serve')
except:
    print >>sys.stderr, "Galaxy does not use the real Paste Script, the only supported command is 'serve'"
    sys.exit(1)

# eggs.require() can be called inside the app without access to the Galaxy
# config, so we need to push the egg options into the environment so they are
# available to Crate instantiated in require()

# locate the arg containing the path to the config file
config = None
p = configparser.ConfigParser()
for arg in sys.argv:
    try:
        p.read(arg)
        assert 'app:main' in p.sections()
        config = arg
        break
    except (configparser.Error, AssertionError):
        pass

# find any egg options set in the config
crate = eggs.Crate(config)
for opt in ('enable_eggs', 'enable_egg_fetch', 'try_dependencies_from_env'):
    env = 'GALAXY_CONFIG_' + opt.upper()
    # don't overwrite existing env vars configured by the user
    if env not in os.environ:
        os.environ[env] = str(getattr(crate.galaxy_config, opt))

eggs.require( "Paste" )
eggs.require( "PasteDeploy" )

from galaxy.util.pastescript import serve
serve.run()
