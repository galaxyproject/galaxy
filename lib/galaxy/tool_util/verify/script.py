#!/usr/bin/env python

import argparse
import json
import sys

import yaml

from galaxy.tool_util.verify.interactor import (
    DictClientTestConfig,
    GalaxyInteractorApi,
    verify_tool,
)

DESCRIPTION = """Script to quickly run a tool test against a running Galaxy instance."""
ALL_TESTS = "*all_tests*"


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]

    args = _arg_parser().parse_args(argv)
    client_test_config_path = args.client_test_config
    if client_test_config_path is not None:
        with open(client_test_config_path, "r") as f:
            client_test_config = yaml.full_load(f)
    else:
        client_test_config = {}

    def get_option(key):
        arg_val = getattr(args, key, None)
        if arg_val is None and key in client_test_config:
            val = client_test_config.get(key)
        else:
            val = arg_val
        return val

    output_json_path = get_option("output_json")
    galaxy_interactor_kwds = {
        "galaxy_url": get_option("galaxy_url"),
        "master_api_key": get_option("admin_key"),
        "api_key": get_option("key"),
        "keep_outputs_dir": args.output,
    }
    tool_id = args.tool_id
    tool_version = args.tool_version
    tools_client_test_config = DictClientTestConfig(client_test_config.get("tools"))

    galaxy_interactor = GalaxyInteractorApi(**galaxy_interactor_kwds)
    raw_test_index = args.test_index
    if raw_test_index == ALL_TESTS:
        tool_test_dicts = galaxy_interactor.get_tool_tests(tool_id, tool_version=tool_version)
        test_indices = list(range(len(tool_test_dicts)))
    else:
        test_indices = [int(raw_test_index)]

    test_results = []

    if args.append:
        assert output_json_path != "-"
        with open(output_json_path) as f:
            previous_results = json.load(f)
            test_results = previous_results["tests"]

    exceptions = []
    verbose = args.verbose
    for test_index in test_indices:
        if tool_version:
            tool_id_and_version = "{}/{}".format(tool_id, tool_version)
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
                register_job_data=register, quiet=not verbose, force_path_paste=args.force_path_paste,
                client_test_config=tools_client_test_config,
            )

            if verbose:
                print("%s passed" % test_identifier)

        except Exception as e:
            if verbose:
                print("{} failed, {}".format(test_identifier, e))
            exceptions.append(e)

    report_obj = {
        'version': '0.1',
        'tests': test_results,
    }
    if output_json_path:
        if output_json_path == "-":
            print(json.dumps(report_obj))
        else:
            with open(output_json_path, "w") as f:
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
    parser.add_argument('-c', '--client-test-config', default=None, help="Test config YAML to help with client testing")
    return parser


if __name__ == "__main__":
    main()
