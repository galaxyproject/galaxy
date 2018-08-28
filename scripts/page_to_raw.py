import argparse
import logging
import os
import sys

sys.path.insert(1, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, 'lib')))

try:
    from bs4 import BeautifulSoup
except ImportError:
    print("Please install the BeautifulSoup 4 Python module to use this script.")
    exit(4)

import galaxy
import galaxy.app
import galaxy.config
from galaxy.objectstore import build_object_store_from_config
from galaxy.util.script import app_properties_from_args, populate_config_args
from galaxy.web.security import SecurityHelper


def main(argv):
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('-k', '--secret-key', help='Key to convert pages with', default='')
    parser.add_argument('-e', '--encode', action="store_true", help='Switch to encode mode')
    populate_config_args(parser)
    args = parser.parse_args()
    properties = app_properties_from_args(args)
    config = galaxy.config.Configuration(**properties)
    secret = args.secret_key or config.id_secret
    security_helper = SecurityHelper(id_secret=secret)
    object_store = build_object_store_from_config(config)
    if not config.database_connection:
        logging.warning("The database connection is empty. If you are using the default value, please uncomment that in your galaxy.yml")

    model = galaxy.config.init_models_from_config(config, object_store=object_store)
    session = model.context.current
    pagerevs = session.query(model.PageRevision).all()
    for p in pagerevs:
        changed = False
        s = BeautifulSoup(p.content, features='lxml')
        divs = s.find_all("div", class_="embedded-item")
        for div in divs:
            # Each of these needs to have the id split, re-encoded, and saved.
            cls, hsh = div['id'].split('-')
            try:
                if args.encode:
                    # ENSURE THIS IS AN INTEGER BEFORE ENCODING
                    try:
                        int(hsh)
                    except ValueError:
                        print("SKIP: Encoding mode activated, but encountered id %s, skipping." % hsh)
                    new_id = security_helper.encode_id(hsh)
                else:
                    new_id = security_helper.decode_id(hsh)
                div['id'] = "%s-%s" % (cls, new_id)
                changed = True
            except UnicodeEncodeError:
                print("Encoding error translating identifiers -- are you sure the id_secret is correct?  Rolling back session so no changes are made.")
                session.rollback()
                exit(2)
            except ValueError:
                print("Decoding error -- it looks like the values are already encoded.  Rolling back session so no changes are made.")
                session.rollback()
                exit(3)
        if changed:
            p.content = str(s)
            session.add(p)
    session.flush()


if __name__ == '__main__':
    main(sys.argv)
