"""Abstraction for waiting on API conditions to become true."""
from time import (
    sleep,
    time,
)
from typing import (
    Callable,
    Optional,
    Union,
)

DEFAULT_POLLING_BACKOFF = 0
DEFAULT_POLLING_DELTA = 0.25

TIMEOUT_MESSAGE_TEMPLATE = "Timed out after {} seconds waiting on {}."
timeout_type = Union[int, float]


def wait_on(
    function: Callable,
    desc: str,
    timeout: timeout_type,
    delta: timeout_type = DEFAULT_POLLING_DELTA,
    polling_backoff: timeout_type = DEFAULT_POLLING_BACKOFF,
    sleep_: Optional[Callable] = None,  # only used in tests
):
    """Wait for function to return non-None value.

    Grow the polling interval (initially ``delta`` defaulting to 0.25 seconds)
    incrementally by the supplied ``polling_backoff`` (defaulting to 0).

    Throw a TimeoutAssertionError if the supplied timeout is reached without
    supplied function ever returning a non-None value.

    The sleep_ parameter is used by the unit tests to "mock" out sleeping
    """
    sleep_foo = sleep_ or sleep
    start = time()
    while True:
        total_wait = time() - start
        if total_wait > timeout:
            raise TimeoutAssertionError(TIMEOUT_MESSAGE_TEMPLATE.format(int(total_wait), desc))
        value = function()
        if value is not None:
            return value
        sleep_foo(delta)
        delta += polling_backoff


class TimeoutAssertionError(AssertionError):
    """Derivative of AssertionError indicating wait_on exceeded max time."""

    def __init__(self, message):
        super().__init__(message)
