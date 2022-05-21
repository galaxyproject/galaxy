#!/usr/bin/env python
"""
A command line helper for common operations performed by Galaxy maintainers.
Encodes and decodes IDs, returns Dataset IDs if provided an HDA or LDDA id,
returns the disk path of a dataset.
"""

import argparse
import os
import sys

sys.path.insert(1, os.path.join(os.path.dirname(__file__), os.pardir, "lib"))

import galaxy.config
from galaxy.model.mapping import init_models_from_config
from galaxy.security import idencoding
from galaxy.util.script import (
    app_properties_from_args,
    populate_config_args,
)

parser = argparse.ArgumentParser()
populate_config_args(parser)
parser.add_argument("-e", "--encode-id", dest="encode_id", help="Encode an ID")
parser.add_argument("-d", "--decode-id", dest="decode_id", help="Decode an ID")
parser.add_argument("--hda", dest="hda_id", help="Display HistoryDatasetAssociation info")
parser.add_argument("--ldda", dest="ldda_id", help="Display LibraryDatasetDatasetAssociation info")
args = parser.parse_args()

app_properties = app_properties_from_args(args)
config = galaxy.config.Configuration(**app_properties)
helper = idencoding.IdEncodingHelper(id_secret=app_properties.get("id_secret"))
model = init_models_from_config(config)

if args.encode_id:
    print(f'Encoded "{args.encode_id}": {helper.encode_id(args.encode_id)}')

if args.decode_id:
    print(f'Decoded "{args.decode_id}": {helper.decode_id(args.decode_id)}')

if args.hda_id:
    try:
        hda_id = int(args.hda_id)
    except Exception:
        hda_id = int(helper.decode_id(args.hda_id))
    hda = model.context.current.query(model.HistoryDatasetAssociation).get(hda_id)
    print(f'HDA "{hda.id}" is Dataset "{hda.dataset.id}" at: {hda.file_name}')

if args.ldda_id:
    try:
        ldda_id = int(args.ldda_id)
    except Exception:
        ldda_id = int(helper.decode_id(args.ldda_id))
    ldda = model.context.current.query(model.HistoryDatasetAssociation).get(ldda_id)
    print(f'LDDA "{ldda.id}" is Dataset "{ldda.dataset.id}" at: {ldda.file_name}')
