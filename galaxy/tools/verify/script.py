#!/usr/bin/env python
from __future__ import print_function

import argparse
import json
import sys

from galaxy.tools.verify.interactor import GalaxyInteractorApi, verify_tool

DESCRIPTION = """Script to quickly run a tool test against a running Galaxy instance."""
ALL_TESTS = "*all_tests*"


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
    tool_version = args.tool_version

    galaxy_interactor = GalaxyInteractorApi(**galaxy_interactor_kwds)
    raw_test_index = args.test_index
    if raw_test_index == ALL_TESTS:
        tool_test_dicts = galaxy_interactor.get_tool_tests(tool_id, tool_version=tool_version)
        test_indices = list(range(len(tool_test_dicts)))
    else:
        test_indices = [int(raw_test_index)]

    test_results = []

    if args.append:
        with open(args.output_json, "r") as f:
            previous_results = json.load(f)
            test_results = previous_results["tests"]

    exceptions = []
    verbose = args.verbose
    for test_index in test_indices:
        if tool_version:
            tool_id_and_version = "%s/%s" % (tool_id, tool_version)
        else:
            tool_id_and_version = tool_id

        test_identifier = "tool %s test # %d" % (tool_id_and_version, test_index)

        def register(job_data):
            test_results.append({
                'id': tool_id + "-" + str(test_index),
                'has_data': True,
                'data': job_data,
            })

        try:
            verify_tool(
                tool_id, galaxy_interactor, test_index=test_index, tool_version=tool_version,
                register_job_data=register, quiet=not verbose, force_path_paste=args.force_path_paste
            )

            if verbose:
                print("%s passed" % test_identifier)

        except Exception as e:
            if verbose:
                print("%s failed, %s" % (test_identifier, e))
            exceptions.append(e)

    report_obj = {
        'version': '0.1',
        'tests': test_results,
    }
    output_json = args.output_json
    if output_json:
        if args.output_json == "-":
            assert not args.append
            print(json.dumps(report_obj))
        else:
            with open(args.output_json, "w") as f:
                json.dump(report_obj, f)

    if exceptions:
        raise exceptions[0]


def _arg_parser():
    parser = argparse.ArgumentParser(description=DESCRIPTION)
    parser.add_argument('-u', '--galaxy-url', default="http://localhost:8080", help='Galaxy URL')
    parser.add_argument('-k', '--key', default=None, help='Galaxy User API Key')
    parser.add_argument('-a', '--admin-key', default=None, help='Galaxy Admin API Key')
    parser.add_argument('--force_path_paste', default=False, action="store_true", help='This requires Galaxy-side config option "allow_path_paste" enabled. Allows for fetching test data locally. Only for admins.')
    parser.add_argument('-t', '--tool-id', default=None, help='Tool ID')
    parser.add_argument('--tool-version', default=None, help='Tool Version')
    parser.add_argument('-i', '--test-index', default=ALL_TESTS, help='Tool Test Index (starting at 0) - by default all tests will run.')
    parser.add_argument('-o', '--output', default=None, help='directory to dump outputs to')
    parser.add_argument('--append', default=False, action="store_true", help="Extend a test record json (created with --output-json) with additional tests.")
    parser.add_argument('-j', '--output-json', default=None, help='output metadata json')
    parser.add_argument('--verbose', default=False, action="store_true", help="Verbose logging.")
    return parser


if __name__ == "__main__":
    main()
