#!/usr/bin/env python

import argparse
import datetime as dt
import json
import os
import sys
from collections import namedtuple
from concurrent.futures import thread, ThreadPoolExecutor

import yaml

from galaxy.tool_util.verify.interactor import (
    DictClientTestConfig,
    GalaxyInteractorApi,
    verify_tool,
)

DESCRIPTION = """Script to quickly run a tool test against a running Galaxy instance."""
DEFAULT_SUITE_NAME = "Galaxy Tool Tests"
ALL_TESTS = -1
ALL_TOOLS = "*"
ALL_VERSION = "*"
LATEST_VERSION = None


TestReference = namedtuple("TestReference", ["tool_id", "tool_version", "test_index"])
TestException = namedtuple("TestException", ["tool_id", "exception", "was_recorded"])


class Results:

    def __init__(self, default_suitename, test_json, append=False):
        self.test_json = test_json or "-"
        test_results = []
        test_exceptions = []
        suitename = default_suitename
        if append:
            assert test_json != "-"
            with open(test_json) as f:
                previous_results = json.load(f)
                test_results = previous_results["tests"]
                if "suitename" in previous_results:
                    suitename = previous_results["suitename"]
        self.test_results = test_results
        self.test_exceptions = test_exceptions
        self.suitename = suitename

    def register_result(self, result):
        self.test_results.append(result)

    def register_exception(self, test_exception):
        self.test_exceptions.append(test_exception)

    def write(self):
        tests = sorted(self.test_results, key=lambda el: el['id'])
        n_passed, n_failures, n_skips = 0, 0, 0
        n_errors = len([e for e in self.test_exceptions if not e.was_recorded])
        for test in tests:
            status = test['status']
            if status == "success":
                n_passed += 1
            elif status == "error":
                n_errors += 1
            elif status == "skip":
                n_skips += 1
            elif status == "failure":
                n_failures += 1
        report_obj = {
            'version': '0.1',
            'suitename': self.suitename,
            'results': {
                'total': n_passed + n_failures + n_skips + n_errors,
                'errors': n_errors,
                'failures': n_failures,
                'skips': n_skips,
            },
            'tests': tests,
        }
        if self.test_json == "-":
            print(json.dumps(report_obj))
        else:
            with open(self.test_json, "w") as f:
                json.dump(report_obj, f)

    def info_message(self):
        messages = []
        passed_tests = self._tests_with_status('success')
        messages.append("Passed tool tests ({0}): {1}".format(
            len(passed_tests),
            [t["id"] for t in passed_tests]
        ))
        failed_tests = self._tests_with_status('failure')
        messages.append("Failed tool tests ({0}): {1}".format(
            len(failed_tests),
            [t["id"] for t in failed_tests]
        ))
        skiped_tests = self._tests_with_status('skip')
        messages.append("Skipped tool tests ({0}): {1}".format(
            len(skiped_tests),
            [t["id"] for t in skiped_tests]
        ))
        errored_tests = self._tests_with_status('error')
        messages.append("Errored tool tests ({0}): {1}".format(
            len(errored_tests),
            [t["id"] for t in errored_tests]
        ))
        return "\n".join(messages)

    @property
    def success_count(self):
        self._tests_with_status('success')

    @property
    def skip_count(self):
        self._tests_with_status('skip')

    @property
    def error_count(self):
        return self._tests_with_status('error') + len(self.test_exceptions)

    @property
    def failure_count(self):
        return self._tests_with_status('failure')

    def _tests_with_status(self, status):
        return [t for t in self.test_results if t.get("status") == status]


def test_tools(
    galaxy_interactor,
    test_references,
    results,
    log=None,
    parallel_tests=1,
    history_per_test_case=False,
    no_history_cleanup=False,
    retries=0,
    verify_kwds=None,
):
    """Run through tool tests and write report.

    Refactor this into Galaxy in 21.01.
    """
    verify_kwds = (verify_kwds or {}).copy()
    tool_test_start = dt.datetime.now()
    history_created = False
    if history_per_test_case:
        test_history = None
    else:
        history_created = True
        test_history = galaxy_interactor.new_history(history_name=f"History for {results.suitename}")
    verify_kwds.update({
        "no_history_cleanup": no_history_cleanup,
        "test_history": test_history,
    })
    with ThreadPoolExecutor(max_workers=parallel_tests) as executor:
        try:
            for test_reference in test_references:
                _test_tool(
                    executor=executor,
                    test_reference=test_reference,
                    results=results,
                    galaxy_interactor=galaxy_interactor,
                    log=log,
                    retries=retries,
                    verify_kwds=verify_kwds,
                )
        finally:
            # Always write report, even if test was cancelled.
            try:
                executor.shutdown(wait=True)
            except KeyboardInterrupt:
                executor._threads.clear()
                thread._threads_queues.clear()
            results.write()
            if log:
                log.info("Report written to '%s'", os.path.abspath(results.test_json))
                log.info(results.info_message())
                log.info("Total tool test time: {0}".format(dt.datetime.now() - tool_test_start))
            if history_created and not no_history_cleanup:
                galaxy_interactor.delete_history(test_history)


def _test_tool(
    executor,
    test_reference,
    results,
    galaxy_interactor,
    log,
    retries,
    verify_kwds,
):
    tool_id = test_reference.tool_id
    tool_version = test_reference.tool_version
    test_index = test_reference.test_index
    # If given a tool_id with a version suffix, strip it off so we can treat tool_version
    # correctly at least in client_test_config.
    if tool_version and tool_id.endswith("/" + tool_version):
        tool_id = tool_id[:-len("/" + tool_version)]

    label_base = tool_id
    if tool_version:
        label_base += "/" + str(tool_version)

    test_id = label_base + "-" + str(test_index)

    def run_test():
        run_retries = retries
        job_data = None
        job_exception = None

        def register(job_data_):
            nonlocal job_data
            job_data = job_data_

        try:
            while run_retries >= 0:
                job_exception = None
                try:
                    if log:
                        log.info("Executing test '%s'", test_id)
                    verify_tool(
                        tool_id, galaxy_interactor, test_index=test_index, tool_version=tool_version,
                        register_job_data=register, **verify_kwds
                    )
                    if log:
                        log.info("Test '%s' passed", test_id)
                    break
                except Exception as e:
                    if log:
                        log.warning("Test '%s' failed", test_id, exc_info=True)

                    job_exception = e
                    run_retries -= 1
        finally:
            if job_data is not None:
                results.register_result({
                    "id": test_id,
                    "has_data": True,
                    "data": job_data,
                })
            if job_exception is not None:
                was_recorded = job_data is not None
                test_exception = TestException(tool_id, job_exception, was_recorded)
                results.register_exception(test_exception)

    executor.submit(run_test)


def build_case_references(galaxy_interactor, tool_id=ALL_TOOLS, tool_version=LATEST_VERSION, test_index=ALL_TESTS):
    test_references = []
    if tool_id == ALL_TOOLS:
        tests_summary = galaxy_interactor.get_tests_summary()
        for tool_id, tool_versions_dict in tests_summary.items():
            for tool_version, summary in tool_versions_dict.items():
                for test_index in range(summary["count"]):
                    test_reference = TestReference(tool_id, tool_version, test_index)
                    test_references.append(test_reference)
    else:
        assert tool_id
        tool_test_dicts = galaxy_interactor.get_tool_tests(tool_id, tool_version=tool_version) or {}
        for i, tool_test_dict in enumerate(tool_test_dicts):
            this_tool_version = tool_test_dict.get("tool_version", tool_version)
            this_test_index = i
            if test_index == ALL_TESTS or i == test_index:
                test_reference = TestReference(tool_id, this_tool_version, this_test_index)
                test_references.append(test_reference)
    return test_references


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
    verbose = args.verbose

    galaxy_interactor = GalaxyInteractorApi(**galaxy_interactor_kwds)
    test_references = build_case_references(
        galaxy_interactor,
        tool_id=tool_id,
        tool_version=tool_version,
        test_index=args.test_index,
    )
    results = Results(args.suite_name, output_json_path, append=args.append)
    verify_kwds = dict(
        client_test_config=tools_client_test_config,
        force_path_paste=args.force_path_paste,
        skip_with_reference_data=not args.with_reference_data,
        quiet=not verbose,
    )
    test_tools(
        galaxy_interactor,
        test_references,
        results,
        log=None,
        verify_kwds=verify_kwds,
    )
    exceptions = results.test_exceptions
    if exceptions:
        raise exceptions[0]


def _arg_parser():
    parser = argparse.ArgumentParser(description=DESCRIPTION)
    parser.add_argument('-u', '--galaxy-url', default="http://localhost:8080", help='Galaxy URL')
    parser.add_argument('-k', '--key', default=None, help='Galaxy User API Key')
    parser.add_argument('-a', '--admin-key', default=None, help='Galaxy Admin API Key')
    parser.add_argument('--force_path_paste', default=False, action="store_true", help='This requires Galaxy-side config option "allow_path_paste" enabled. Allows for fetching test data locally. Only for admins.')
    parser.add_argument('-t', '--tool-id', default=ALL_TOOLS, help='Tool ID')
    parser.add_argument('--tool-version', default=None, help='Tool Version (if tool id supplied). Defaults to just latest version, use * to test all versions')
    parser.add_argument('-i', '--test-index', default=ALL_TESTS, type=int, help='Tool Test Index (starting at 0) - by default all tests will run.')
    parser.add_argument('-o', '--output', default=None, help='directory to dump outputs to')
    parser.add_argument('--append', default=False, action="store_true", help="Extend a test record json (created with --output-json) with additional tests.")
    parser.add_argument('-j', '--output-json', default=None, help='output metadata json')
    parser.add_argument('--verbose', default=False, action="store_true", help="Verbose logging.")
    parser.add_argument('-c', '--client-test-config', default=None, help="Test config YAML to help with client testing")
    parser.add_argument('--suite-name', default=DEFAULT_SUITE_NAME, help="Suite name for tool test output")
    parser.add_argument('--with-reference-data', dest="with_reference_data", default=False, action="store_true")
    parser.add_argument('--skip-with-reference-data', dest="with_reference_data", action="store_false", help="Skip tests the Galaxy server believes use data tables or loc files.")
    parser.add_argument('--history-per-suite', dest="history_per_test_case", default=False, action="store_false", help="Create new history per test suite (all tests in same history).")
    parser.add_argument('--history-per-test-case', dest="history_per_test_case", action="store_true", help="Create new history per test case.")
    parser.add_argument('--no-history-cleanup', default=False, action="store_true", help="Perserve histories created for testing.")
    parser.add_argument('--retries', default=0, type=int, help="Retry failed tests.")
    return parser


if __name__ == "__main__":
    main()
