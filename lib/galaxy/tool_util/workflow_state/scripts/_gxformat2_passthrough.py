"""In-process dispatch helpers for gxformat2 commands under the gxwf umbrella."""

import argparse
import importlib


def _make_handler(target: str):
    module_name, _, attr = target.partition(":")

    def handler(args: argparse.Namespace) -> int:
        func = getattr(importlib.import_module(module_name), attr)
        return func(args.passthrough_args) or 0

    return handler


def register_passthrough(subparsers, subcommand: str, target: str, help_text: str):
    p = subparsers.add_parser(subcommand, help=help_text, add_help=False)
    p.add_argument("passthrough_args", nargs=argparse.REMAINDER)
    p.set_defaults(func=_make_handler(target))
