#!/usr/bin/env python

import argparse
import concurrent.futures.thread
import datetime as dt
import json
import logging
import os
import sys
import tempfile
from concurrent.futures import (
    thread,
    ThreadPoolExecutor,
)
from typing import (
    Any,
    Callable,
    Dict,
    List,
    NamedTuple,
    Optional,
)

import yaml

from galaxy.tool_util.verify.interactor import (
    DictClientTestConfig,
    GalaxyInteractorApi,
    ToolTestDictsT,
    verify_tool,
)

DESCRIPTION = """Script to quickly run a tool test against a running Galaxy instance."""
DEFAULT_SUITE_NAME = "Galaxy Tool Tests"
ALL_TESTS = -1
ALL_TOOLS = "*"
ALL_VERSION = "*"
LATEST_VERSION = None


class TestReference(NamedTuple):
    tool_id: str
    tool_version: Optional[str]
    test_index: int


class TestException(NamedTuple):
    tool_id: str
    exception: Exception
    was_recorded: bool


class Results:
    test_exceptions: List[TestException]

    def __init__(
        self, default_suitename: str, test_json: str, append: bool = False, galaxy_url: Optional[str] = None
    ) -> None:
        self.test_json = test_json or "-"
        self.galaxy_url = galaxy_url
        test_results = []
        suitename = default_suitename
        if append:
            assert test_json != "-"
            with open(test_json) as f:
                previous_results = json.load(f)
                test_results = previous_results["tests"]
                if "suitename" in previous_results:
                    suitename = previous_results["suitename"]
        self.test_results = test_results
        self.test_exceptions = []
        self.suitename = suitename

    def register_result(self, result: Dict[str, Any]) -> None:
        self.test_results.append(result)

    def register_exception(self, test_exception: TestException) -> None:
        self.test_exceptions.append(test_exception)

    def already_successful(self, test_reference: TestReference) -> bool:
        test_data = self._previous_test_data(test_reference)
        if test_data:
            if "status" in test_data and test_data["status"] == "success":
                return True

        return False

    def already_executed(self, test_reference: TestReference) -> bool:
        test_data = self._previous_test_data(test_reference)
        if test_data:
            if "status" in test_data and test_data["status"] != "skipped":
                return True

        return False

    def _previous_test_data(self, test_reference: TestReference) -> Optional[Dict[str, Any]]:
        test_id = _test_id_for_reference(test_reference)
        for test_result in self.test_results:
            if test_result.get("id") != test_id:
                continue

            has_data = test_result.get("has_data", False)
            if has_data:
                test_data = test_result.get("data", {})
                return test_data

        return None

    def write(self) -> None:
        tests = sorted(self.test_results, key=lambda el: el["id"])
        n_passed, n_failures, n_skips = 0, 0, 0
        n_errors = len([e for e in self.test_exceptions if not e.was_recorded])
        for test in tests:
            has_data = test.get("has_data", False)
            if has_data:
                test_data = test.get("data", {})
                if "status" not in test_data:
                    raise Exception(f"Test result data {test_data} doesn't contain a status key.")
                status = test_data["status"]
                if status == "success":
                    n_passed += 1
                elif status == "error":
                    n_errors += 1
                elif status == "skip":
                    n_skips += 1
                elif status == "failure":
                    n_failures += 1
        report_obj = {
            "version": "0.1",
            "suitename": self.suitename,
            "results": {
                "total": n_passed + n_failures + n_skips + n_errors,
                "errors": n_errors,
                "failures": n_failures,
                "skips": n_skips,
            },
            "tests": tests,
        }
        if self.galaxy_url:
            report_obj["galaxy_url"] = self.galaxy_url
        if self.test_json == "-":
            print(json.dumps(report_obj))
        else:
            with open(self.test_json, "w") as f:
                json.dump(report_obj, f)

    def info_message(self) -> str:
        messages = []
        passed_tests = self._tests_with_status("success")
        messages.append("Passed tool tests ({}): {}".format(len(passed_tests), [t["id"] for t in passed_tests]))
        failed_tests = self._tests_with_status("failure")
        messages.append("Failed tool tests ({}): {}".format(len(failed_tests), [t["id"] for t in failed_tests]))
        skipped_tests = self._tests_with_status("skip")
        messages.append("Skipped tool tests ({}): {}".format(len(skipped_tests), [t["id"] for t in skipped_tests]))
        errored_tests = self._tests_with_status("error")
        messages.append("Errored tool tests ({}): {}".format(len(errored_tests), [t["id"] for t in errored_tests]))
        return "\n".join(messages)

    def _tests_with_status(self, status: str) -> List[Dict[str, Any]]:
        return [t for t in self.test_results if t.get("data", {}).get("status") == status]


def test_tools(
    galaxy_interactor: GalaxyInteractorApi,
    test_references: List[TestReference],
    results: Results,
    log: Optional[logging.Logger] = None,
    parallel_tests: int = 1,
    history_per_test_case: bool = False,
    history_name: Optional[str] = None,
    no_history_reuse: bool = False,
    no_history_cleanup: bool = False,
    publish_history: bool = False,
    retries: int = 0,
    verify_kwds: Optional[Dict[str, Any]] = None,
) -> None:
    """Run through tool tests and write report."""
    verify_kwds = (verify_kwds or {}).copy()
    tool_test_start = dt.datetime.now()
    history_created = False
    test_history = None
    if not history_per_test_case:
        if not history_name:
            history_name = f"History for {results.suitename}"
        if log:
            log.info(f"History name is '{history_name}'")
        if not no_history_reuse:
            history = galaxy_interactor.get_history(history_name=history_name)
            if history:
                test_history = history["id"]
                if log:
                    log.info(f"Using existing history with id '{test_history}', last updated: {history['update_time']}")
        if not test_history:
            history_created = True
            test_history = galaxy_interactor.new_history(history_name=history_name, publish_history=publish_history)
            if log:
                log.info(f"History created with id '{test_history}'")
    verify_kwds.update(
        {
            "no_history_cleanup": no_history_cleanup,
            "test_history": test_history,
        }
    )
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
                    publish_history=publish_history,
                )
        finally:
            # Always write report, even if test was cancelled.
            try:
                executor.shutdown(wait=True)
            except KeyboardInterrupt:
                executor._threads.clear()  # type: ignore[attr-defined]
                thread._threads_queues.clear()  # type: ignore[attr-defined]
            results.write()
            if log:
                if results.test_json == "-":
                    destination = "standard output"
                else:
                    destination = os.path.abspath(results.test_json)
                log.info(f"Report written to '{destination}'")
                log.info(results.info_message())
                log.info(f"Total tool test time: {dt.datetime.now() - tool_test_start}")
            if history_created and not no_history_cleanup:
                galaxy_interactor.delete_history(test_history)


def _test_id_for_reference(test_reference: "TestReference") -> str:
    tool_id = test_reference.tool_id
    tool_version = test_reference.tool_version
    test_index = test_reference.test_index

    if tool_version and tool_id.endswith(f"/{tool_version}"):
        tool_id = tool_id[: -len(f"/{tool_version}")]

    label_base = tool_id
    if tool_version:
        label_base += f"/{str(tool_version)}"

    test_id = f"{label_base}-{str(test_index)}"
    return test_id


def _test_tool(
    executor: concurrent.futures.thread.ThreadPoolExecutor,
    test_reference: "TestReference",
    results: Results,
    galaxy_interactor: GalaxyInteractorApi,
    log: Optional[logging.Logger],
    retries: int,
    publish_history: bool,
    verify_kwds: Dict[str, Any],
) -> None:
    tool_id = test_reference.tool_id
    tool_version = test_reference.tool_version
    test_index = test_reference.test_index
    # If given a tool_id with a version suffix, strip it off so we can treat tool_version
    # correctly at least in client_test_config.
    if tool_version and tool_id.endswith(f"/{tool_version}"):
        tool_id = tool_id[: -len(f"/{tool_version}")]

    test_id = _test_id_for_reference(test_reference)

    def run_test() -> None:
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
                        tool_id,
                        galaxy_interactor,
                        test_index=test_index,
                        tool_version=tool_version,
                        register_job_data=register,
                        publish_history=publish_history,
                        **verify_kwds,
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
                results.register_result(
                    {
                        "id": test_id,
                        "has_data": True,
                        "data": job_data,
                    }
                )
            if job_exception is not None:
                was_recorded = job_data is not None
                test_exception = TestException(tool_id, job_exception, was_recorded)
                results.register_exception(test_exception)

    executor.submit(run_test)


def build_case_references(
    galaxy_interactor: GalaxyInteractorApi,
    tool_id: str = ALL_TOOLS,
    tool_version: Optional[str] = LATEST_VERSION,
    test_index: int = ALL_TESTS,
    page_size: int = 0,
    page_number: int = 0,
    test_filters: Optional[List[Callable[[TestReference], bool]]] = None,
    log: Optional[logging.Logger] = None,
) -> List[TestReference]:
    test_references: List[TestReference] = []
    if tool_id == ALL_TOOLS:
        tests_summary = galaxy_interactor.get_tests_summary()
        for tool_id, tool_versions_dict in tests_summary.items():
            for tool_version, summary in tool_versions_dict.items():
                for test_index in range(summary["count"]):
                    test_reference = TestReference(tool_id, tool_version, test_index)
                    test_references.append(test_reference)
    else:
        assert tool_id
        tool_test_dicts: ToolTestDictsT = galaxy_interactor.get_tool_tests(tool_id, tool_version=tool_version)
        for i, tool_test_dict in enumerate(tool_test_dicts):
            this_tool_version = tool_test_dict.get("tool_version", tool_version)
            this_test_index = i
            if test_index == ALL_TESTS or i == test_index:
                test_reference = TestReference(tool_id, this_tool_version, this_test_index)
                test_references.append(test_reference)

    if test_filters is not None and len(test_filters) > 0:
        filtered_test_references: List[TestReference] = []
        for test_reference in test_references:
            skip_test = False
            for test_filter in test_filters:
                if test_filter(test_reference):
                    if log is not None:
                        log.debug(f"Filtering test for {test_reference}, skipping")
                    skip_test = True
            if not skip_test:
                filtered_test_references.append(test_reference)
        if log is not None:
            log.info(
                f"Skipping {len(test_references)-len(filtered_test_references)} out of {len(test_references)} tests."
            )
        test_references = filtered_test_references

    if page_size > 0:
        slice_start = page_size * page_number
        slice_end = page_size * (page_number + 1)
        test_references = test_references[slice_start:slice_end]

    return test_references


def main(argv=None) -> None:
    if argv is None:
        argv = sys.argv[1:]

    args = arg_parser().parse_args(argv)
    try:
        run_tests(args)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)


def run_tests(
    args: argparse.Namespace,
    test_filters: Optional[List[Callable[[TestReference], bool]]] = None,
    log: Optional[logging.Logger] = None,
) -> None:
    # Split out argument parsing so we can quickly build other scripts - such as a script
    # to run all tool tests for a workflow by just passing in a custom test_filters.
    test_filters = test_filters or []
    log = log or setup_global_logger(__name__, verbose=args.verbose)

    client_test_config_path = args.client_test_config
    if client_test_config_path is not None:
        log.debug(f"Reading client config path {client_test_config_path}")
        with open(client_test_config_path) as f:
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
    galaxy_url = get_option("galaxy_url")
    galaxy_interactor_kwds = {
        "galaxy_url": galaxy_url,
        "master_api_key": get_option("admin_key"),
        "api_key": get_option("key"),
        "keep_outputs_dir": args.output,
        "download_attempts": get_option("download_attempts"),
        "download_sleep": get_option("download_sleep"),
        "test_data": get_option("test_data"),
    }
    tool_id = args.tool_id
    tool_version = args.tool_version
    tools_client_test_config = DictClientTestConfig(client_test_config.get("tools"))
    verbose = args.verbose

    galaxy_interactor = GalaxyInteractorApi(**galaxy_interactor_kwds)
    results = Results(args.suite_name, output_json_path, append=args.append, galaxy_url=galaxy_url)

    skip = args.skip
    if skip == "executed":
        test_filters.append(results.already_executed)
    elif skip == "successful":
        test_filters.append(results.already_successful)

    test_references = build_case_references(
        galaxy_interactor,
        tool_id=tool_id,
        tool_version=tool_version,
        test_index=args.test_index,
        page_size=args.page_size,
        page_number=args.page_number,
        test_filters=test_filters,
        log=log,
    )
    log.debug(f"Built {len(test_references)} test references to executed.")
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
        log=log,
        parallel_tests=args.parallel_tests,
        history_per_test_case=args.history_per_test_case,
        history_name=args.history_name,
        no_history_reuse=args.no_history_reuse,
        no_history_cleanup=args.no_history_cleanup,
        publish_history=get_option("publish_history"),
        verify_kwds=verify_kwds,
    )
    exceptions = results.test_exceptions
    if exceptions:
        exception = exceptions[0]
        raise exception.exception


def setup_global_logger(name: str, log_file: Optional[str] = None, verbose: bool = False) -> logging.Logger:
    formatter = logging.Formatter("%(asctime)s %(levelname)-5s - %(message)s")
    console = logging.StreamHandler()
    console.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    logger.addHandler(console)

    if not log_file:
        # delete = false is chosen here because it is always nice to have a log file
        # ready if you need to debug. Not having the "if only I had set a log file"
        # moment after the fact.
        temp = tempfile.NamedTemporaryFile(prefix="ephemeris_", delete=False)
        log_file = temp.name
    file_handler = logging.FileHandler(log_file)
    logger.addHandler(file_handler)
    logger.info(f"Storing log file in: {log_file}")
    return logger


def arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=DESCRIPTION)
    parser.add_argument("-u", "--galaxy-url", default="http://localhost:8080", help="Galaxy URL")
    parser.add_argument("-k", "--key", default=None, help="Galaxy User API Key")
    parser.add_argument("-a", "--admin-key", default=None, help="Galaxy Admin API Key")
    parser.add_argument(
        "--force_path_paste",
        default=False,
        action="store_true",
        help='This requires Galaxy-side config option "allow_path_paste" enabled. Allows for fetching test data locally. Only for admins.',
    )
    parser.add_argument("-t", "--tool-id", default=ALL_TOOLS, help="Tool ID")
    parser.add_argument(
        "--tool-version",
        default=None,
        help="Tool Version (if tool id supplied). Defaults to just latest version, use * to test all versions",
    )
    parser.add_argument(
        "-i",
        "--test-index",
        default=ALL_TESTS,
        type=int,
        help="Tool Test Index (starting at 0) - by default all tests will run.",
    )
    parser.add_argument("-o", "--output", default=None, help="directory to dump outputs to")
    parser.add_argument(
        "--append",
        default=False,
        action="store_true",
        help="Extend a test record json (created with --output-json) with additional tests.",
    )
    skip_group = parser.add_mutually_exclusive_group()
    skip_group.add_argument(
        "--skip-previously-executed",
        dest="skip",
        default="no",
        action="store_const",
        const="executed",
        help="When used with --append, skip any test previously executed.",
    )
    skip_group.add_argument(
        "--skip-previously-successful",
        dest="skip",
        default="no",
        action="store_const",
        const="successful",
        help="When used with --append, skip any test previously executed successfully.",
    )
    parser.add_argument("-j", "--output-json", default=None, help="output metadata json")
    parser.add_argument("--verbose", default=False, action="store_true", help="Verbose logging.")
    parser.add_argument("-c", "--client-test-config", default=None, help="Test config YAML to help with client testing")
    parser.add_argument("--suite-name", default=DEFAULT_SUITE_NAME, help="Suite name for tool test output")
    parser.add_argument("--with-reference-data", dest="with_reference_data", default=False, action="store_true")
    parser.add_argument(
        "--skip-with-reference-data",
        dest="with_reference_data",
        action="store_false",
        help="Skip tests the Galaxy server believes use data tables or loc files.",
    )
    history_per_group = parser.add_mutually_exclusive_group()
    history_per_group.add_argument(
        "--history-per-suite",
        dest="history_per_test_case",
        default=False,
        action="store_false",
        help="Create new history per test suite (all tests in same history).",
    )
    history_per_group.add_argument(
        "--history-per-test-case",
        dest="history_per_test_case",
        action="store_true",
        help="Create new history per test case.",
    )
    history_per_group.add_argument("--history-name", default=None, help="Override default history name")
    parser.add_argument(
        "--no-history-reuse",
        default=False,
        action="store_true",
        help="Do not reuse histories if a matching one already exists.",
    )
    parser.add_argument(
        "--no-history-cleanup", default=False, action="store_true", help="Perserve histories created for testing."
    )
    parser.add_argument(
        "--publish-history", default=False, action="store_true", help="Publish test history. Useful for CI testing."
    )
    parser.add_argument("--parallel-tests", default=1, type=int, help="Parallel tests.")
    parser.add_argument("--retries", default=0, type=int, help="Retry failed tests.")
    parser.add_argument(
        "--page-size", default=0, type=int, help="If positive, use pagination and just run one 'page' to tool tests."
    )
    parser.add_argument(
        "--page-number", default=0, type=int, help="If page size is used, run this 'page' of tests - starts with 0."
    )
    parser.add_argument(
        "--download-attempts",
        default=1,
        type=int,
        help="Galaxy may return a transient 500 status code for download if test results are written but not yet accessible.",
    )
    parser.add_argument(
        "--download-sleep",
        default=1,
        type=int,
        help="If download attempts is greater than 1, the amount to sleep between download attempts.",
    )
    parser.add_argument("--test-data", action="append", help="Add local test data path to search for missing test data")
    return parser


if __name__ == "__main__":
    main()
