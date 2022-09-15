"""
This script is intended to be invoked by the scripts/db_dev.sh script.
"""

import os
import sys
from argparse import ArgumentParser

sys.path.insert(1, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, "lib")))

from galaxy.model.migrations.dbscript import ParserBuilder


def main() -> None:
    parser = ArgumentParser(
        prog="db_dev.sh",
        description="Extended database schema migration operations",
        epilog="Note: these operations are applied to the Galaxy model only (stored in the `gxy` branch)."
        " For migrating the `tsi` branch, use the `run_alembic.sh` script.",
    )
    parser.add_argument("-c", "--galaxy-config", help="Alternate Galaxy configuration file", dest="config")
    parser.add_argument("--raiseerr", help="Raise a full stack trace on error", action="store_true")

    parser_builder = ParserBuilder(parser)

    parser_builder.add_upgrade_command()
    parser_builder.add_downgrade_command()
    parser_builder.add_version_command()
    parser_builder.add_dbversion_command()
    parser_builder.add_init_command()
    parser_builder.add_revision_command()
    parser_builder.add_history_command()
    parser_builder.add_show_command()

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
