"""
This script is intended to be invoked by the manage_toolshed_db.sh script.
"""

import os
import sys
from argparse import ArgumentParser

sys.path.insert(1, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, "lib")))

from tool_shed.webapp.model.migrations.dbscript import (
    CONFIG_FILE_ARG,
    ParserBuilder,
)


def main() -> None:
    parser = ArgumentParser(
        prog="manage_toolshed_db.sh",
        description="Common database schema migration operations",
    )
    parser.add_argument("-c", f"{CONFIG_FILE_ARG}", help="Alternate Tool Shed configuration file", dest="config")

    parser_builder = ParserBuilder(parser)

    parser_builder.add_upgrade_command()
    parser_builder.add_downgrade_command()
    parser_builder.add_version_command()
    parser_builder.add_dbversion_command()
    parser_builder.add_init_command()

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
