from itertools import count
from time import sleep

import logging
log = logging.getLogger(__name__)

DEFAULT_MAX_RETRIES = -1  # By default don't retry.
DEFAULT_INTERVAL_START = 2.0
DEFAULT_INTERVAL_MAX = 30.0
DEFAULT_INTERVAL_STEP = 2.0
DEFAULT_CATCH = (Exception,)

DEFAULT_DESCRIPTION = "action"


class RetryActionExecutor(object):

    def __init__(self, **kwds):
        # Use variables that match kombu to keep things consistent across
        # Pulsar.
        # http://ask.github.io/kombu/reference/kombu.connection.html#kombu.connection.BrokerConnection.ensure_connection
        raw_max_retries = kwds.get("max_retries", DEFAULT_MAX_RETRIES)
        self.max_retries = None if not raw_max_retries else int(raw_max_retries)
        self.interval_start = float(kwds.get("interval_start", DEFAULT_INTERVAL_START))
        self.interval_step = float(kwds.get("interval_step", DEFAULT_INTERVAL_STEP))
        self.interval_max = float(kwds.get("interval_max", DEFAULT_INTERVAL_MAX))
        self.errback = kwds.get("errback", self.__default_errback)
        self.catch = kwds.get("catch", DEFAULT_CATCH)

        self.default_description = kwds.get("description", DEFAULT_DESCRIPTION)

    def execute(self, action, description=None):
        def on_error(exc, intervals, retries, interval=0):
            interval = next(intervals)
            if self.errback:
                errback_args = [exc, interval]
                if description is not None:
                    errback_args.append(description)
                self.errback(exc, interval, description)
            return interval

        return _retry_over_time(
            action,
            catch=self.catch,
            max_retries=self.max_retries,
            interval_start=self.interval_start,
            interval_step=self.interval_step,
            interval_max=self.interval_max,
            errback=on_error,
        )

    def __default_errback(self, exc, interval, description=None):
        description = description or self.default_description
        log.info(
            "Failed to execute %s, retrying in %s seconds.",
            description,
            interval,
            exc_info=True
        )


# Following functions are derived from Kombu versions @
# https://github.com/celery/kombu/blob/master/kombu/utils/__init__.py
# BSD License (https://github.com/celery/kombu/blob/master/LICENSE)
def _retry_over_time(fun, catch, args=[], kwargs={}, errback=None,
                     max_retries=None, interval_start=2, interval_step=2,
                     interval_max=30):
    """Retry the function over and over until max retries is exceeded.

    For each retry we sleep a for a while before we try again, this interval
    is increased for every retry until the max seconds is reached.

    :param fun: The function to try
    :param catch: Exceptions to catch, can be either tuple or a single
        exception class.
    :keyword args: Positional arguments passed on to the function.
    :keyword kwargs: Keyword arguments passed on to the function.
    :keyword max_retries: Maximum number of retries before we give up.
        If this is not set, we will retry forever.
    :keyword interval_start: How long (in seconds) we start sleeping between
        retries.
    :keyword interval_step: By how much the interval is increased for each
        retry.
    :keyword interval_max: Maximum number of seconds to sleep between retries.

    """
    retries = 0
    interval_range = __fxrange(interval_start,
                               interval_max + interval_start,
                               interval_step, repeatlast=True)
    for retries in count():
        try:
            return fun(*args, **kwargs)
        except catch as exc:
            if max_retries and retries >= max_retries:
                raise
            tts = float(errback(exc, interval_range, retries) if errback
                        else next(interval_range))
            if tts:
                sleep(tts)


def __fxrange(start=1.0, stop=None, step=1.0, repeatlast=False):
    cur = start * 1.0
    while 1:
        if not stop or cur <= stop:
            yield cur
            cur += step
        else:
            if not repeatlast:
                break
            yield cur - step
