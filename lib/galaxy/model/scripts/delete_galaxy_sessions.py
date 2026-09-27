import argparse
import datetime
import os
import sys

from sqlalchemy import (
    create_engine,
    text,
)

sys.path.insert(
    1, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, os.pardir, os.pardir, "lib"))
)

from galaxy.model.orm.scripts import get_config

DESCRIPTION = """Remove old galaxy_session records from database."""


def main():
    args = _get_parser().parse_args()
    config = get_config(sys.argv, use_argparse=False, cwd=os.getcwd())
    engine = create_engine(config["db_url"])
    run(engine=engine, max_update_time=args.updated)


def _get_parser():
    parser = argparse.ArgumentParser(description=DESCRIPTION)
    parser.add_argument(
        "--updated",
        type=datetime.datetime.fromisoformat,
        help="most recent `updated` date/time in ISO format  (for example, March 11, 1952 is represented as '1952-03-11')",
    )
    return parser


# Each user's newest session is kept regardless of age: it holds the browser cookie
# and the history reopened on the next login. The ranking must match the ordering
# of `User.current_galaxy_session`.
DELETE_STMT = text("""
    DELETE FROM galaxy_session
    WHERE update_time < :update_time
    AND id NOT IN (
        SELECT id FROM (
            SELECT id, row_number() OVER (PARTITION BY user_id ORDER BY update_time DESC, id DESC) AS rn
            FROM galaxy_session
            WHERE user_id IS NOT NULL
        ) AS ranked
        WHERE rn = 1
    )
    """)


def run(engine, max_update_time=None):
    """Delete galaxy_session records updated prior to `max_update_time`, except each user's newest session."""
    max_update_time = max_update_time or _get_default_max_update_time()
    with engine.begin() as conn:
        conn.execute(DELETE_STMT, {"update_time": max_update_time})


def _get_default_max_update_time():
    """By default, do not delete galaxy_sessions updated less than a month ago."""
    today = datetime.date.today()
    return today.replace(month=today.month - 1)


if __name__ == "__main__":
    main()
