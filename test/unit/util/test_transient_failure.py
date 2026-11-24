from unittest import SkipTest

import pytest

from galaxy.util import unittest_utils
from galaxy.util.unittest_utils import transient_failure


@transient_failure(issue=12345)
def _failing_test():
    raise AssertionError("boom")


@transient_failure(issue=12345, potentially_fixed=True)
def _failing_potentially_fixed_test():
    raise AssertionError("boom")


@transient_failure(issue=12345, potentially_fixed=True)
def _skipping_test():
    raise SkipTest("remote site down")


def test_transient_failure_skips_when_skipping_flakey_fails(monkeypatch):
    monkeypatch.setattr(unittest_utils, "SKIP_FLAKEY_TESTS_ON_ERROR", "1")
    with pytest.raises(SkipTest, match=r"^Skipping known transient failure \[Issue #12345\]: boom$"):
        _failing_test()


def test_transient_failure_potentially_fixed_fails_when_skipping_flakey_fails(monkeypatch):
    monkeypatch.setattr(unittest_utils, "SKIP_FLAKEY_TESTS_ON_ERROR", "1")
    with pytest.raises(Exception, match=r"^KNOWN TRANSIENT FAILURE \[Issue #12345\] \[We have previously") as exc_info:
        _failing_potentially_fixed_test()
    assert exc_info.type is AssertionError


@pytest.mark.parametrize("skip_flakey", [None, "1"])
def test_transient_failure_keeps_test_skip_reason(monkeypatch, skip_flakey):
    monkeypatch.setattr(unittest_utils, "SKIP_FLAKEY_TESTS_ON_ERROR", skip_flakey)
    with pytest.raises(SkipTest, match=r"^remote site down$"):
        _skipping_test()
