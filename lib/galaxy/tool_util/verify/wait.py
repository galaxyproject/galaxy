"""Abstraction for waiting on API conditions to become true."""

import time


def wait_on(function, desc, timeout):
    """Wait for function to return non-None value."""
    delta = .25
    iteration = 0
    while True:
        total_wait = delta * iteration
        if total_wait > timeout:
            timeout_message = "Timed out after %s seconds waiting on %s." % (
                total_wait, desc
            )
            raise TimeoutAssertionError(timeout_message)
        iteration += 1
        value = function()
        if value is not None:
            return value
        time.sleep(delta)


class TimeoutAssertionError(AssertionError):
    """Derivative of AssertionError indicating wait_on exceeded max time."""

    def __init__(self, message):
        super(TimeoutAssertionError, self).__init__(message)
