#!/usr/bin/env python
"""
A command line helper for common operations performed by Galaxy maintainers.
Encodes and decodes IDs, returns Dataset IDs if provided an HDA or LDDA id,
returns the disk path of a dataset.
"""
from __future__ import print_function

import argparse
import os
import sys

sys.path.insert(1, os.path.join(os.path.dirname(__file__), os.pardir, 'lib'))

import galaxy.config
from galaxy.util.script import app_properties_from_args, populate_config_args
from galaxy.web import security

parser = argparse.ArgumentParser()
populate_config_args(parser)
parser.add_argument('-e', '--encode-id', dest='encode_id', help='Encode an ID')
parser.add_argument('-d', '--decode-id', dest='decode_id', help='Decode an ID')
parser.add_argument('--hda', dest='hda_id', help='Display HistoryDatasetAssociation info')
parser.add_argument('--ldda', dest='ldda_id', help='Display LibraryDatasetDatasetAssociation info')
args = parser.parse_args()

app_properties = app_properties_from_args(args)
config = galaxy.config.Configuration(**app_properties)
helper = security.SecurityHelper(id_secret=app_properties.get('id_secret'))
model = galaxy.config.init_models_from_config(config)

if args.encode_id:
    print('Encoded "%s": %s' % (args.encode_id, helper.encode_id(args.encode_id)))

if args.decode_id:
    print('Decoded "%s": %s' % (args.decode_id, helper.decode_id(args.decode_id)))

if args.hda_id:
    try:
        hda_id = int(args.hda_id)
    except Exception:
        hda_id = int(helper.decode_id(args.hda_id))
    hda = model.context.current.query(model.HistoryDatasetAssociation).get(hda_id)
    print('HDA "%s" is Dataset "%s" at: %s' % (hda.id, hda.dataset.id, hda.file_name))

if args.ldda_id:
    try:
        ldda_id = int(args.ldda_id)
    except Exception:
        ldda_id = int(helper.decode_id(args.ldda_id))
    ldda = model.context.current.query(model.HistoryDatasetAssociation).get(ldda_id)
    print('LDDA "%s" is Dataset "%s" at: %s' % (ldda.id, ldda.dataset.id, ldda.file_name))
