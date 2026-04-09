"""Subprocess pass-through helpers for gxformat2 commands under the gxwf umbrella."""

import argparse
import shutil
import subprocess
import sys


def _make_passthrough_handler(cmd_name: str):
    def handler(args: argparse.Namespace) -> int:
        binary = shutil.which(cmd_name)
        if binary is None:
            print(
                f"error: '{cmd_name}' not found. Install gxformat2 to use this command.",
                file=sys.stderr,
            )
            return 1
        result = subprocess.run([binary] + args.passthrough_args)
        return result.returncode

    return handler


def register_passthrough(subparsers, subcommand: str, gxformat2_cmd: str, help_text: str):
    p = subparsers.add_parser(subcommand, help=help_text, add_help=False)
    p.add_argument("passthrough_args", nargs=argparse.REMAINDER)
    p.set_defaults(func=_make_passthrough_handler(gxformat2_cmd))
