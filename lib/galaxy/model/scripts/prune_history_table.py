import argparse
import datetime
import os
import sys

from sqlalchemy import create_engine

sys.path.insert(
    1, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, os.pardir, os.pardir, "lib"))
)

from galaxy.model.orm.scripts import get_config
from galaxy.model.scripts.history_table_pruner import HistoryTablePruner

DESCRIPTION = """Remove unused histories from database.

A history is considered unused if it doesn't have a user and its hid counter has not been incremented.
"""


def main():
    args = _get_parser().parse_args()
    config = get_config(sys.argv, use_argparse=False, cwd=os.getcwd())
    engine = create_engine(config["db_url"])
    htp = HistoryTablePruner(engine=engine, batch_size=args.batch, max_create_time=args.created)
    htp.run()


def _get_parser():
    parser = argparse.ArgumentParser(description=DESCRIPTION)
    parser.add_argument("--batch", type=int, help="batch size")
    parser.add_argument(
        "--created",
        type=datetime.datetime.fromisoformat,
        help="most recent created date/time in ISO format  (for example, March 11, 1952 is represented as '1952-03-11')",
    )
    return parser


if __name__ == "__main__":
    main()
