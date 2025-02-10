#!/usr/bin/env python

import argparse
import os
import sys

sys.path.insert(1, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, "lib")))

import galaxy.config
from galaxy.model.mapping import init_models_from_config
from galaxy.objectstore import build_object_store_from_config
from galaxy.util import nice_size
from galaxy.util.script import (
    app_properties_from_args,
    populate_config_args,
)

default_config = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, "config/galaxy.ini"))

parser = argparse.ArgumentParser()
parser.add_argument("-u", "--username", dest="username", help="Username of user to update", default="all")
parser.add_argument("-e", "--email", dest="email", help="Email address of user to update", default="all")
parser.add_argument(
    "--dry-run",
    dest="dryrun",
    help="Dry run (show changes but do not save to database)",
    action="store_true",
    default=False,
)
populate_config_args(parser)
args = parser.parse_args()


def init():
    if args.username == "all":
        args.username = None
    if args.email == "all":
        args.email = None

    app_properties = app_properties_from_args(args)
    config = galaxy.config.Configuration(**app_properties)
    object_store = build_object_store_from_config(config)
    engine = config.database_connection.split(":")[0]
    return init_models_from_config(config, object_store=object_store), object_store, engine


def quotacheck(sa_session, users, engine, object_store):
    sa_session.refresh(user)
    current = user.get_disk_usage()
    print(user.username, "<" + user.email + ">:", end=" ")

    if not args.dryrun:
        # Apply new disk usage
        user.calculate_and_set_disk_usage(object_store)
        # And fetch
        new = user.get_disk_usage()
    else:
        new = user.calculate_disk_usage_default_source(object_store)

    print("old usage:", nice_size(current), "change:", end=" ")
    if new in (current, None):
        print("none")
    else:
        if new > current:
            print(f"+{nice_size(new - current)}")
        else:
            print(f"-{nice_size(current - new)}")


if __name__ == "__main__":
    print("Loading Galaxy model...")
    model, object_store, engine = init()
    sa_session = model.context

    if not args.username and not args.email:
        user_count = sa_session.query(model.User).count()
        print(f"Processing {user_count} users...")
        for i, user in enumerate(sa_session.query(model.User).enable_eagerloads(False).yield_per(1000)):
            print(f"{int(float(i) / user_count * 100):3d}%", end=" ")
            quotacheck(sa_session, user, engine, object_store)
        print("100% complete")
        object_store.shutdown()
        sys.exit(0)
    elif args.username:
        user = sa_session.query(model.User).enable_eagerloads(False).filter_by(username=args.username).first()
    elif args.email:
        user = sa_session.query(model.User).enable_eagerloads(False).filter_by(email=args.email).first()
    if not user:
        print("User not found")
        sys.exit(1)
    quotacheck(sa_session, user, engine, object_store)
    object_store.shutdown()
