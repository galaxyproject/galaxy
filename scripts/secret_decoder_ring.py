#!/usr/bin/env python
"""
Script to encode/decode the IDs that galaxy exposes to users and admins.
"""
import argparse
import logging
import os
import sys

sys.path.insert(1, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, "lib")))

from galaxy.security.idencoding import IdEncodingHelper
from galaxy.util import unicodify
from galaxy.util.script import (
    app_properties_from_args,
    populate_config_args,
)

logging.basicConfig()
log = logging.getLogger(__name__)

parser = argparse.ArgumentParser()
parser.add_argument("action", metavar="ACTION", type=str, default=None, choices=("decode", "encode"))
parser.add_argument("value", metavar="VALUE", nargs="+", type=str, default=None, help="value to encode or decode")
populate_config_args(parser)
args = parser.parse_args()

app_properties = app_properties_from_args(args)

# We need the ID secret for configuring the security helper to decrypt
# galaxysession cookies.
if "id_secret" not in app_properties:
    log.warning('No ID_SECRET specified. Please set the "id_secret" in your galaxy.yml.')

id_secret = app_properties.get("id_secret", "dangerous_default")

security_helper = IdEncodingHelper(id_secret=id_secret)
# And get access to the models
# Login manager to manage current_user functionality

if args.action == "decode":
    for value in args.value:
        sys.stdout.write(security_helper.decode_guid(value.lstrip("F")))
        sys.stdout.write("\n")
elif args.action == "encode":
    for value in args.value:
        sys.stdout.write(unicodify(security_helper.encode_guid(value)))
        sys.stdout.write("\n")
