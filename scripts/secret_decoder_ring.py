#!/usr/bin/env python
"""
Script to encode/decode the IDs that galaxy exposes to users and admins.
"""
import logging
import os
import sys

sys.path.insert(1, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, 'lib')))

from galaxy.model import mapping
from galaxy.model.orm.scripts import get_config
from galaxy.util.properties import load_app_properties
from galaxy.web.security import SecurityHelper

logging.basicConfig()
log = logging.getLogger(__name__)

# Get config file and load up SA session
config = get_config(sys.argv)
model = mapping.init('/tmp/', config['db_url'])
sa_session = model.context.current

# With the config file we can load the full app properties
app_properties = load_app_properties(ini_file=config['config_file'])

# We need the ID secret for configuring the security helper to decrypt
# galaxysession cookies.
if "id_secret" not in app_properties:
    log.warning('No ID_SECRET specified. Please set the "id_secret" in your galaxy.ini.')

id_secret = app_properties.get('id_secret', 'dangerous_default')

security_helper = SecurityHelper(id_secret=id_secret)
# And get access to the models
# Login manager to manage current_user functionality

if len(sys.argv) != 3:
    sys.stdout.write("python %s (encode|decode) value\n" % sys.argv[0])
    sys.exit(1)

action = sys.argv[1]
value = sys.argv[2]

if action == 'decode':
    sys.stdout.write(security_helper.decode_guid(value.lstrip('F')))
elif action == 'encode':
    sys.stdout.write(security_helper.encode_guid(value))
else:
    sys.stdout.write("Unknown argument")
sys.stdout.write('\n')
