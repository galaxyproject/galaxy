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

DESCRIPTION = """Remove old job metrics records from database."""


def main():
    args = _get_parser().parse_args()
    config = get_config(sys.argv, use_argparse=False, cwd=os.getcwd())
    engine = create_engine(config["db_url"])
    run(engine=engine, max_update_time=args.updated)


def _get_parser():
    parser = argparse.ArgumentParser(description=DESCRIPTION)
    parser.add_argument(
        "--updated",
        required=True,
        type=datetime.datetime.fromisoformat,
        help="most recent `updated` date/time in ISO format  (for example, March 11, 1952 is represented as '1952-03-11')",
    )
    return parser


def run(engine, max_update_time):
    """Delete galaxy_session records which were updated prior to `max_update_time`."""
    _delete_metrics(engine, max_update_time, "job_metric_text")
    _delete_metrics(engine, max_update_time, "job_metric_numeric")


def _delete_metrics(engine, max_update_time, metrics_table):
    stmt = text(f"DELETE FROM {metrics_table} USING job j WHERE m.job_id = j.id AND j.update_time < :update_time")
    params = {"update_time": max_update_time}
    with engine.begin() as conn:
        conn.execute(stmt, params)


if __name__ == "__main__":
    main()
