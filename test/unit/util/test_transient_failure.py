from unittest import SkipTest

import pytest

from galaxy.util import unittest_utils
from galaxy.util.unittest_utils import transient_failure


@transient_failure(issue=12345)
def _failing_test():
    raise AssertionError("boom")


@transient_failure(issue=12345)
def _skipping_test():
    raise SkipTest("remote site down")


@transient_failure(issue=12345)
def _passing_test():
    return "ok"


def test_transient_failure_marks_failure(monkeypatch):
    monkeypatch.setattr(unittest_utils, "SKIP_FLAKEY_TESTS_ON_ERROR", None)
    with pytest.raises(AssertionError, match=r"^KNOWN TRANSIENT FAILURE \[Issue #12345\]"):
        _failing_test()


def test_transient_failure_skips_when_skipping_flakey_fails(monkeypatch):
    monkeypatch.setattr(unittest_utils, "SKIP_FLAKEY_TESTS_ON_ERROR", "1")
    with pytest.raises(SkipTest, match=r"^Skipping known transient failure \[Issue #12345\]$"):
        _failing_test()


def test_transient_failure_keeps_test_skip_reason(monkeypatch):
    monkeypatch.setattr(unittest_utils, "SKIP_FLAKEY_TESTS_ON_ERROR", "1")
    with pytest.raises(SkipTest, match=r"remote site down$"):
        _skipping_test()


def test_transient_failure_passing_test_not_skipped(monkeypatch):
    monkeypatch.setattr(unittest_utils, "SKIP_FLAKEY_TESTS_ON_ERROR", "1")
    assert _passing_test() == "ok"
