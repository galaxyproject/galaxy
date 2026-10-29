"""retry_call_during_transitions: fast transition errors retry; Playwright timeouts already waited."""

import pytest
from selenium.common.exceptions import StaleElementReferenceException

from galaxy.selenium.has_playwright_driver import PlaywrightTimeoutException
from galaxy.selenium.navigates_galaxy import retry_call_during_transitions


def _always(exception):
    calls = []

    def f():
        calls.append(1)
        raise exception

    return f, calls


def test_stale_elements_retry_every_attempt():
    f, calls = _always(StaleElementReferenceException("stale"))
    with pytest.raises(StaleElementReferenceException):
        retry_call_during_transitions(f, attempts=10, sleep=0)
    # The first call, then attempts + 1 retries.
    assert len(calls) == 10 + 2


def test_a_playwright_timeout_is_retried_once():
    # Each Playwright timeout is a full action timeout of Playwright's own retrying; ten more of them
    # turned one covered click into minutes.
    f, calls = _always(PlaywrightTimeoutException("Locator.click: Timeout 30000ms exceeded."))
    with pytest.raises(PlaywrightTimeoutException):
        retry_call_during_transitions(f, attempts=10, sleep=0)
    assert len(calls) == 2
