#!/usr/bin/env python
import os
import sys
sys.path.insert(1, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, 'lib')))

import logging
logging.basicConfig()
log = logging.getLogger(__name__)


from galaxy.model.orm.scripts import get_config
from galaxy.model import mapping
from galaxy.util.properties import load_app_properties
from galaxy.web.security import SecurityHelper

# Get config file and load up SA session
config = get_config( sys.argv )
model = mapping.init( '/tmp/', config['db_url'] )
sa_session = model.context.current

# With the config file we can load the full app properties
app_properties = load_app_properties(ini_file=config['config_file'])

# We need the ID secret for configuring the security helper to decrypt
# galaxysession cookies.
if "id_secret" not in app_properties:
    log.warn('No ID_SECRET specified. Please set the "id_secret" in your galaxy.ini.')

id_secret = app_properties.get('id_secret', 'dangerous_default')

security_helper = SecurityHelper(id_secret=id_secret)
# And get access to the models
# Login manager to manage current_user functionality

if len(sys.argv) != 3:
    sys.stdout.write("python %s (encode|decode) value\n" % sys.argv[0])

if sys.argv[1] == 'decode':
    sys.stdout.write(security_helper.decode_guid(sys.argv[2]))
elif sys.argv[1] == 'encode':
    sys.stdout.write(security_helper.encode_guid(sys.argv[2]))
else:
    sys.stdout.write("Unknown argument")
sys.stdout.write('\n')
