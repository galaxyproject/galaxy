"""Abstraction for waiting on API conditions to become true."""

import time

DEFAULT_POLLING_BACKOFF = 0
DEFAULT_POLLING_DELTA = 0.25

TIMEOUT_MESSAGE_TEMPLATE = "Timed out after {} seconds waiting on {}."


def wait_on(function, desc, timeout, delta=DEFAULT_POLLING_DELTA, polling_backoff=DEFAULT_POLLING_BACKOFF, sleep_=None):
    """Wait for function to return non-None value.

    Grow the polling interval (initially ``delta`` defaulting to 0.25 seconds)
    incrementally by the supplied ``polling_backoff`` (defaulting to 0).

    Throw a TimeoutAssertionError if the supplied timeout is reached without
    supplied function ever returning a non-None value.
    """
    sleep = sleep_ or time.sleep
    total_wait = 0
    while True:
        if total_wait > timeout:
            raise TimeoutAssertionError(TIMEOUT_MESSAGE_TEMPLATE.format(total_wait, desc))
        value = function()
        if value is not None:
            return value
        total_wait += delta
        sleep(delta)
        delta += polling_backoff


class TimeoutAssertionError(AssertionError):
    """Derivative of AssertionError indicating wait_on exceeded max time."""

    def __init__(self, message):
        super(TimeoutAssertionError, self).__init__(message)
