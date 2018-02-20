#!/usr/bin/env python
import argparse
import sys

from galaxy.tools.verify.interactor import GalaxyInteractorApi, verify_tool

DESCRIPTION = "Script to quickly run a tool test against a running Galaxy instance."


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]

    args = _arg_parser().parse_args(argv)
    galaxy_interactor_kwds = {
        "galaxy_url": args.galaxy_url,
        "master_api_key": args.admin_key,
        "api_key": args.key,
        "keep_outputs_dir": args.output,
    }
    tool_id = args.tool_id
    test_index = int(args.test_index)
    tool_version = args.tool_version

    galaxy_interactor = GalaxyInteractorApi(**galaxy_interactor_kwds)
    verify_tool(tool_id, galaxy_interactor, test_index=test_index, tool_version=tool_version)


def _arg_parser():
    parser = argparse.ArgumentParser(description=DESCRIPTION)
    parser.add_argument('-u', '--galaxy-url', default="http://localhost:8080", help='Galaxy URL')
    parser.add_argument('-k', '--key', default=None, help='Galaxy User API Key')
    parser.add_argument('-a', '--admin-key', default=None, help='Galaxy Admin API Key')
    parser.add_argument('-t', '--tool-id', default=None, help='Tool ID')
    parser.add_argument('--tool-version', default=None, help='Tool Version')
    parser.add_argument('-i', '--test-index', default=0, help='Tool Test Index (starting at 0)')
    parser.add_argument('-o', '--output', default=None, help='directory to dump outputs to')
    return parser


if __name__ == "__main__":
    main()
