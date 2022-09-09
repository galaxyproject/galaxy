"""
This script is intended to be invoked by the db.sh script.
"""

import logging
import os
import sys
from argparse import (
    ArgumentParser,
    Namespace,
)

sys.path.insert(1, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, "lib")))

from galaxy.model.migrations import verify_databases_via_script
from galaxy.model.migrations.dbscript import DbScript
from galaxy.model.migrations.scripts import get_configuration

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)


def exec_upgrade(args: Namespace) -> None:
    _exec_command("upgrade", args)


def exec_downgrade(args: Namespace) -> None:
    _exec_command("downgrade", args)


def exec_revision(args: Namespace) -> None:
    _exec_command("revision", args)


def exec_version(args: Namespace) -> None:
    _exec_command("version", args)


def exec_dbversion(args: Namespace) -> None:
    _exec_command("dbversion", args)


def exec_history(args: Namespace) -> None:
    _exec_command("history", args)


def exec_show(args: Namespace) -> None:
    _exec_command("show", args)


def exec_init(args: Namespace) -> None:
    gxy_config, tsi_config, is_auto_migrate = get_configuration(sys.argv, os.getcwd())
    verify_databases_via_script(gxy_config, tsi_config, is_auto_migrate)


def _exec_command(command, args):
    dbscript = DbScript(args.config)
    getattr(dbscript, command)(args)


def main() -> None:
    def add_parser(command, func, help, aliases=None, parents=None):
        aliases = aliases or []
        parents = parents or []
        parser = subparsers.add_parser(command, aliases=aliases, help=help, parents=parents)
        parser.set_defaults(func=func)
        return parser

    config_arg_parser = ArgumentParser(add_help=False)
    config_arg_parser.add_argument("-c", "--galaxy-config", help="Alternate Galaxy configuration file", dest="config")

    verbose_arg_parser = ArgumentParser(add_help=False)
    verbose_arg_parser.add_argument("-v", "--verbose", action="store_true", help="Display more detailed output")

    sql_arg_parser = ArgumentParser(add_help=False)
    sql_arg_parser.add_argument(
        "--sql",
        action="store_true",
        help="Don't emit SQL to database - dump to standard output/file instead. See Alembic docs on offline mode.",
    )

    parser = ArgumentParser(
        description="Common database schema migration operations",
        epilog="Note: these operations are applied to the Galaxy model only (stored in the `gxy` branch)."
        " For migrating the `tsi` branch, use the `run_alembic.sh` script.",
        parents=[config_arg_parser],
    )

    subparsers = parser.add_subparsers(required=True)

    upgrade_cmd_parser = add_parser(
        "upgrade",
        exec_upgrade,
        "Upgrade to a later version",
        aliases=["u"],
        parents=[sql_arg_parser],
    )
    upgrade_cmd_parser.add_argument("revision", help="Revision identifier", nargs="?")

    downgrade_cmd_parser = add_parser(
        "downgrade",
        exec_downgrade,
        "Revert to a previous version",
        aliases=["d"],
        parents=[sql_arg_parser],
    )
    downgrade_cmd_parser.add_argument("revision", help="Revision identifier")

    add_parser(
        "version",
        exec_version,
        "Show the head revision in the migrations script directory",
        aliases=["v"],
        parents=[verbose_arg_parser],
    )

    add_parser(
        "dbversion",
        exec_dbversion,
        "Show the current revision for Galaxy's database",
        aliases=["dbv"],
        parents=[verbose_arg_parser],
    )

    history_cmd_parser = add_parser(
        "history",
        exec_history,
        "List revision scripts in chronological order",
        parents=[verbose_arg_parser],
    )
    history_cmd_parser.add_argument("-i", "--indicate-current", help="Indicate current revision", action="store_true")

    show_cmd_parser = add_parser(
        "show",
        exec_show,
        "Show the revision(s) denoted by the given symbol",
    )
    show_cmd_parser.add_argument("revision", help="Revision identifier")

    revision_cmd_parser = add_parser("revision", aliases=["r"], help="Create a new revision file", func=exec_revision)
    revision_cmd_parser.add_argument("-m", "--message", help="Message string to use with 'revision'", required=True)
    revision_cmd_parser.add_argument("--rev-id", help="Specify a revision id instead of generating one")

    add_parser(
        "init",
        exec_init,
        "Initialize empty database(s) for both branches (create database objects for gxy and tsi branch)",
    )

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
