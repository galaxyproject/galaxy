#!/usr/bin/env python

"""
Populates blank uuid fields in datasets with randomly generated values

Going forward, these ids will be generated for all new datasets. This
script fixes datasets that were generated before the change.
"""
from __future__ import print_function

import argparse
import os
import sys
import uuid

sys.path.insert(1, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, 'lib')))

import galaxy.config
from galaxy.util.script import app_properties_from_args, populate_config_args

DESCRIPTION = """
Populates blank uuid fields in datasets with randomly generated values.

Going forward, these ids will be generated for all new datasets. This
script fixes datasets that were generated before the change.
"""


def main():
    parser = argparse.ArgumentParser(DESCRIPTION)
    populate_config_args(parser)
    args = parser.parse_args()

    app_properties = app_properties_from_args(args)
    config = galaxy.config.Configuration(**app_properties)
    model = galaxy.config.init_models_from_config(config)

    for row in model.context.query(model.Dataset):
        if row.uuid is None:
            row.uuid = uuid.uuid4()
            print("Setting dataset:", row.id, " UUID to ", row.uuid)
    model.context.flush()

    for row in model.context.query(model.Workflow):
        if row.uuid is None:
            row.uuid = uuid.uuid4()
            print("Setting Workflow:", row.id, " UUID to ", row.uuid)
    model.context.flush()
    print("Complete")


if __name__ == "__main__":
    main()
