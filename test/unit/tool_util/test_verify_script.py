import json
import os
from tempfile import NamedTemporaryFile
from typing import (
    cast,
    NoReturn,
)
from unittest import mock

from galaxy.tool_util.unittest_utils.interactor import (
    EXISTING_HISTORY,
    EXISTING_HISTORY_NAME,
    EXISTING_SUITE_NAME,
    MockGalaxyInteractor,
    NEW_HISTORY_ID,
)
from galaxy.tool_util.verify.interactor import GalaxyInteractorApi
from galaxy.tool_util.verify.script import (
    arg_parser,
    build_case_references,
    Results,
    test_tools as run,
    TestReference,
)

VT_PATH = "galaxy.tool_util.verify.script.verify_tool"


def test_arg_parse() -> None:
    parser = arg_parser()

    # defaults
    args = parser.parse_args([])
    assert not args.with_reference_data
    assert not args.history_per_test_case
    assert args.page_size == 0
    assert args.page_number == 0
    assert args.parallel_tests == 1

    # skip flags
    args = parser.parse_args(["--skip-with-reference-data", "--history-per-test-case"])
    assert not args.with_reference_data
    assert args.history_per_test_case

    # enable flags
    args = parser.parse_args(["--with-reference-data", "--history-per-suite"])
    assert args.with_reference_data
    assert not args.history_per_test_case

    # pagination
    args = parser.parse_args(["--page-size", "5", "--page-number", "40", "--parallel-tests", "3"])
    assert args.page_size == 5
    assert args.page_number == 40
    assert args.parallel_tests == 3
    assert args.test_data is None

    args = parser.parse_args(["--test-data", "/foo/bar", "--test-data", "cow"])
    assert len(args.test_data) == 2
    assert args.test_data[0] == "/foo/bar"
    assert args.test_data[1] == "cow"

    args = parser.parse_args(["--skip-previously-successful"])
    assert args.skip == "successful"

    args = parser.parse_args(["--skip-previously-executed"])
    assert args.skip == "executed"


def test_test_tools() -> None:
    interactor = MockGalaxyInteractor()
    f = NamedTemporaryFile()
    results = Results("my suite", f.name)
    test_references = [
        TestReference("cat", "0.1.0", 0),
        TestReference("cat", "0.1.0", 1),
        TestReference("cat", "0.2.0", 0),
    ]
    with mock.patch(VT_PATH) as mock_verify:
        assert_results_not_written(results)
        run(
            cast(GalaxyInteractorApi, interactor),
            test_references,
            results,
        )
        calls = mock_verify.call_args_list
        assert len(calls) == 3
        assert len(results.test_exceptions) == 0
        assert_results_written(results)
        assert interactor.history_created
        assert interactor.history_deleted


def test_test_tools_no_history_cleanup() -> None:
    interactor = MockGalaxyInteractor()
    f = NamedTemporaryFile()
    results = Results("my suite", f.name)
    test_references = [
        TestReference("cat", "0.1.0", 0),
    ]
    with mock.patch(VT_PATH) as mock_verify:
        assert_results_not_written(results)
        run(
            cast(GalaxyInteractorApi, interactor),
            test_references,
            results,
            no_history_cleanup=True,
        )
        calls = mock_verify.call_args_list
        assert len(calls) == 1
        assert len(results.test_exceptions) == 0
        assert_results_written(results)
        assert interactor.history_created
        assert not interactor.history_deleted


def test_test_tools_history_reuse() -> None:
    interactor = MockGalaxyInteractor()
    f = NamedTemporaryFile()
    results = Results(EXISTING_SUITE_NAME, f.name)
    test_references = [
        TestReference("cat", "0.1.0", 0),
    ]
    with mock.patch(VT_PATH) as mock_verify:
        assert_results_not_written(results)
        run(
            cast(GalaxyInteractorApi, interactor),
            test_references,
            results,
            no_history_reuse=False,
        )
        calls = mock_verify.call_args_list
        assert len(calls) == 1
        assert len(results.test_exceptions) == 0
        assert_results_written(results)
        assert interactor.history_id == EXISTING_HISTORY["id"]
        assert interactor.history_name == EXISTING_HISTORY_NAME
        assert not interactor.history_created
        assert not interactor.history_deleted


def test_test_tools_no_history_reuse() -> None:
    interactor = MockGalaxyInteractor()
    f = NamedTemporaryFile()
    results = Results("existing suite", f.name)
    test_references = [
        TestReference("cat", "0.1.0", 0),
    ]
    with mock.patch(VT_PATH) as mock_verify:
        assert_results_not_written(results)
        run(
            cast(GalaxyInteractorApi, interactor),
            test_references,
            results,
            no_history_reuse=True,
        )
        calls = mock_verify.call_args_list
        assert len(calls) == 1
        assert len(results.test_exceptions) == 0
        assert_results_written(results)
        assert interactor.history_id == NEW_HISTORY_ID
        assert interactor.history_name == EXISTING_HISTORY_NAME
        assert interactor.history_created
        assert interactor.history_deleted


def test_test_tools_history_name() -> None:
    interactor = MockGalaxyInteractor()
    f = NamedTemporaryFile()
    results = Results("my suite", f.name)
    test_references = [
        TestReference("cat", "0.1.0", 0),
    ]
    with mock.patch(VT_PATH) as mock_verify:
        assert_results_not_written(results)
        run(
            cast(GalaxyInteractorApi, interactor),
            test_references,
            results,
            history_name="testfoo",
        )
        calls = mock_verify.call_args_list
        assert len(calls) == 1
        assert len(results.test_exceptions) == 0
        assert_results_written(results)
        assert interactor.history_id == NEW_HISTORY_ID
        assert interactor.history_name == "testfoo"
        assert interactor.history_created
        assert interactor.history_deleted


def test_test_tool_per_test_history() -> None:
    interactor = MockGalaxyInteractor()
    f = NamedTemporaryFile()
    results = Results("my suite", f.name)
    test_references = [
        TestReference("cat", "0.1.0", 0),
        TestReference("cat", "0.1.0", 1),
    ]
    with mock.patch(VT_PATH) as mock_verify:
        assert_results_not_written(results)
        run(
            cast(GalaxyInteractorApi, interactor),
            test_references,
            results,
            history_per_test_case=True,
        )
        calls = mock_verify.call_args_list
        assert len(calls) == 2
        assert len(results.test_exceptions) == 0
        assert_results_written(results)
        assert not interactor.history_created
        assert not interactor.history_deleted


def test_test_tools_records_exception() -> None:
    interactor = MockGalaxyInteractor()
    f = NamedTemporaryFile()
    results = Results("my suite", f.name)
    test_references = [
        TestReference("bad", "0.1.0", 0),
    ]
    with mock.patch(VT_PATH) as mock_verify:
        assert_results_not_written(results)

        def side_effect(*args, **kwd) -> NoReturn:
            raise Exception("Cow")

        mock_verify.side_effect = side_effect
        run(
            cast(GalaxyInteractorApi, interactor),
            test_references,
            results,
        )
        calls = mock_verify.call_args_list
        assert len(calls) == 1
        assert len(results.test_exceptions) == 1
        assert_results_written(results)


def test_test_tools_records_retry_exception() -> None:
    interactor = MockGalaxyInteractor()
    f = NamedTemporaryFile()
    results = Results("my suite", f.name)
    test_references = [
        TestReference("bad", "0.1.0", 0),
    ]
    with mock.patch(VT_PATH) as mock_verify:
        assert_results_not_written(results)

        count = 0

        def side_effect(*args, **kwd):
            nonlocal count
            raise_exception = count == 0
            count += 1
            if raise_exception:
                raise Exception("Cow")

        mock_verify.side_effect = side_effect
        run(
            cast(GalaxyInteractorApi, interactor),
            test_references,
            results,
            retries=1,
        )
        calls = mock_verify.call_args_list
        assert len(calls) == 2
        assert len(results.test_exceptions) == 0
        assert_results_written(results)


def test_append_results() -> None:
    tf = NamedTemporaryFile()
    tf.close()
    assert not os.path.exists(tf.name)
    # Now try to append to the non-existent file.
    results = Results("my suite", tf.name, True)
    results.register_result({"id": "foo", "has_data": True, "data": {"status": "success"}})
    try:
        results.write()
        assert os.path.exists(tf.name)
        with open(tf.name) as f:
            report_obj = json.load(f)
        assert "tests" in report_obj
        assert len(report_obj["tests"]) == 1
        assert report_obj["results"]["total"] == 1, report_obj["results"]
        assert report_obj["results"]["errors"] == 0
        assert report_obj["results"]["skips"] == 0
    finally:
        os.remove(tf.name)
    assert not os.path.exists(tf.name)


def test_results():
    tf = NamedTemporaryFile()
    results = Results("my suite", tf.name)
    results.register_result({"id": "foo", "has_data": True, "data": {"status": "success"}})
    results.write()
    message = results.info_message()

    with open(tf.name) as f:
        report_obj = json.load(f)
    assert "tests" in report_obj
    assert len(report_obj["tests"]) == 1
    assert report_obj["results"]["total"] == 1, report_obj["results"]
    assert report_obj["results"]["errors"] == 0
    assert report_obj["results"]["skips"] == 0

    assert "Passed tool tests (1)" in message
    assert "Skipped tool tests (0)" in message

    results.register_result({"id": "bar", "has_data": True, "data": {"status": "skip"}})
    results.write()
    message = results.info_message()

    with open(tf.name) as f:
        report_obj = json.load(f)
    assert len(report_obj["tests"]) == 2
    assert report_obj["results"]["skips"] == 1
    assert "Passed tool tests (1)" in message
    assert "Skipped tool tests (1)" in message


def test_build_references() -> None:
    interactor = cast(GalaxyInteractorApi, MockGalaxyInteractor())
    test_references = build_case_references(interactor)
    assert len(test_references) == 6

    test_references = build_case_references(interactor, "cat1", tool_version="*")
    assert len(test_references) == 6

    test_references = build_case_references(interactor, "cat1", tool_version="*", page_size=3, page_number=1)
    assert len(test_references) == 3

    test_references = build_case_references(interactor, "cat1", tool_version="*", page_size=3, page_number=2)
    assert len(test_references) == 0

    test_references = build_case_references(interactor, "cat1", tool_version="*", page_size=3, page_number=3)
    assert len(test_references) == 0

    test_references = build_case_references(interactor, "cat1", tool_version=None)
    assert len(test_references) == 4

    test_references = build_case_references(interactor, "cat1", tool_version="0.2.0")
    assert len(test_references) == 4

    test_references = build_case_references(interactor, "cat1", tool_version="0.1.0")
    assert len(test_references) == 2

    test_references = build_case_references(interactor, "cat1", tool_version="0.1.0", test_index=1)
    assert len(test_references) == 1

    # Specifying an index but not a version, grabs latest version and fills it in.
    test_references = build_case_references(interactor, "cat1", test_index=2)
    assert len(test_references) == 1
    test_reference = test_references[0]
    assert test_reference.tool_id == "cat1"
    assert test_reference.tool_version == "0.2.0"
    assert test_reference.test_index == 2


def assert_results_not_written(results: Results) -> None:
    assert os.stat(results.test_json).st_size == 0


def assert_results_written(results: Results) -> None:
    assert os.stat(results.test_json).st_size > 0
    with open(results.test_json) as f:
        json.load(f)
