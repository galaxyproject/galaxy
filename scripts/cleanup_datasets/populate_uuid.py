#!/usr/bin/env python

"""
Populates blank uuid fields in datasets with randomly generated values

Going forward, these ids will be generated for all new datasets. This
script fixes datasets that were generated before the change.
"""

import argparse
import os
import sys
import uuid

sys.path.insert(1, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, "lib")))

import galaxy.config
from galaxy.model.mapping import init_models_from_config
from galaxy.util.script import (
    app_properties_from_args,
    populate_config_args,
)

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
    model = init_models_from_config(config)
    session = model.context()

    for row in session.query(model.Dataset):
        if row.uuid is None:
            row.uuid = uuid.uuid4()
            print("Setting dataset:", row.id, " UUID to ", row.uuid)
    session.commit()

    for row in session.query(model.Workflow):
        if row.uuid is None:
            row.uuid = uuid.uuid4()
            print("Setting Workflow:", row.id, " UUID to ", row.uuid)
    session.commit()
    print("Complete")


if __name__ == "__main__":
    main()
