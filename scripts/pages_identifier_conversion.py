import argparse
import difflib
import logging
import os
import sys

sys.path.insert(1, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, "lib")))

import galaxy
import galaxy.app
import galaxy.config
from galaxy.managers.pages import (
    PageContentProcessor,
    placeholderRenderForSave,
)
from galaxy.model.base import transaction
from galaxy.model.mapping import init_models_from_config
from galaxy.objectstore import build_object_store_from_config
from galaxy.security.idencoding import IdEncodingHelper
from galaxy.util import unicodify
from galaxy.util.bunch import Bunch
from galaxy.util.script import (
    app_properties_from_args,
    populate_config_args,
)


def main(argv):
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("-k", "--secret-key", help="Key to convert pages with", default="")
    parser.add_argument("-d", "--dry-run", help="No changes, just test it.", action="store_true")
    populate_config_args(parser)
    args = parser.parse_args()
    properties = app_properties_from_args(args)
    config = galaxy.config.Configuration(**properties)
    secret = args.secret_key or config.id_secret
    security_helper = IdEncodingHelper(id_secret=secret)
    object_store = build_object_store_from_config(config)
    if not config.database_connection:
        print(
            "The database connection is empty. If you are using the default value, please uncomment that in your galaxy.yml"
        )

    model = init_models_from_config(config, object_store=object_store)
    session = model.context.current
    pagerevs = session.query(model.PageRevision).all()
    mock_trans = Bunch(app=Bunch(security=security_helper), model=model, user_is_admin=lambda: True, sa_session=session)
    for p in pagerevs:
        try:
            processor = PageContentProcessor(mock_trans, placeholderRenderForSave)
            processor.feed(p.content)
            newcontent = unicodify(processor.output(), "utf-8")
            if p.content != newcontent:
                if not args.dry_run:
                    p.content = unicodify(processor.output(), "utf-8")
                    session.add(p)
                    session = session()
                    with transaction(session):
                        session.commit()
                else:
                    print(f"Modifying revision {p.id}.")
                    print(difflib.unified_diff(p.content, newcontent))
        except Exception:
            logging.exception(
                "Error parsing page, rolling changes back and skipping revision %s.  Please report this error.", p.id
            )
            session.rollback()


if __name__ == "__main__":
    main(sys.argv)
