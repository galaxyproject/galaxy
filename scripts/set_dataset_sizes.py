#!/usr/bin/env python

import argparse
import os
import sys

sys.path.insert(1, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, "lib")))

import galaxy.config
from galaxy.model.mapping import init_models_from_config
from galaxy.objectstore import build_object_store_from_config
from galaxy.util.script import (
    app_properties_from_args,
    populate_config_args,
)

parser = argparse.ArgumentParser()
populate_config_args(parser)
args = parser.parse_args()


def init():
    app_properties = app_properties_from_args(args)
    config = galaxy.config.Configuration(**app_properties)

    object_store = build_object_store_from_config(config)
    model = init_models_from_config(config, object_store=object_store)
    return model, object_store


if __name__ == "__main__":
    print("Loading Galaxy model...")
    model, object_store = init()
    sa_session = model.context.current

    set = 0
    dataset_count = sa_session.query(model.Dataset).count()
    print("Processing %i datasets..." % dataset_count)
    percent = 0
    print("Completed %i%%" % percent, end=" ")
    sys.stdout.flush()
    for i, dataset in enumerate(sa_session.query(model.Dataset).enable_eagerloads(False).yield_per(1000)):
        if dataset.total_size is None:
            dataset.set_total_size()
            set += 1
            if not set % 1000:
                sa_session.flush()
        new_percent = int(float(i) / dataset_count * 100)
        if new_percent != percent:
            percent = new_percent
            print("\rCompleted %i%%" % percent, end=" ")
            sys.stdout.flush()
    sa_session.flush()
    print("\rCompleted 100%")
    object_store.shutdown()
