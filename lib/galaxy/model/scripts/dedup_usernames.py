import os
import sys

from sqlalchemy import create_engine

sys.path.insert(
    1, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, os.pardir, os.pardir, "lib"))
)

from galaxy.model.orm.scripts import get_config
from galaxy.model.scripts.user_deduplicator import UserDeduplicator

DESCRIPTION = "Deduplicate usernames in galaxy_user table"


def main():
    config = get_config(sys.argv, use_argparse=False, cwd=os.getcwd())
    engine = create_engine(config["db_url"])
    ud = UserDeduplicator(engine=engine)
    ud.deduplicate_usernames()


if __name__ == "__main__":
    main()
