from galaxy.tool_util.verify.wait import (
    TimeoutAssertionError,
    wait_on,
)


class Sleeper:
    def __init__(self):
        self.sleeps = []

    def sleep(self, delta):
        self.sleeps.append(delta)


class WaitCondition:
    def __init__(self, after_call_count=0, return_value=True):
        self.after_call_count = after_call_count
        self.call_count = 0
        self.return_value = return_value

    def __call__(self):
        self.call_count += 1
        if self.call_count > self.after_call_count:
            return self.return_value
        else:
            return None


def test_immediate_return():
    condition = WaitCondition(return_value="first")
    sleeper = Sleeper()

    assert "first" == wait_on(condition, "condition", 100, sleep_=sleeper.sleep)
    assert len(sleeper.sleeps) == 0


def test_timeout_first_call():
    condition = WaitCondition(after_call_count=1, return_value="second")
    sleeper = Sleeper()

    exception_called = False
    try:
        wait_on(condition, "never met condition", 1, delta=2, sleep_=sleeper.sleep)
    except TimeoutAssertionError as e:
        assert "never met condition" in str(e)
        assert "after 2.0 seconds" in str(e)
        exception_called = True
    assert len(sleeper.sleeps) == 1
    assert sleeper.sleeps[0] == 2  # delta of 2
    assert exception_called


def test_timeout_third_call():
    condition = WaitCondition(after_call_count=4, return_value="second")
    sleeper = Sleeper()

    exception_called = False
    try:
        wait_on(condition, "condition", 5, delta=2, sleep_=sleeper.sleep)
    except TimeoutAssertionError:
        exception_called = True
    assert len(sleeper.sleeps) == 3
    assert sleeper.sleeps[0] == 2  # delta of 2
    assert sleeper.sleeps[1] == 2  # delta of 2
    assert sleeper.sleeps[2] == 2  # delta of 2
    assert exception_called


def test_return_on_third_call():
    condition = WaitCondition(after_call_count=2, return_value="second")
    sleeper = Sleeper()

    assert "second" == wait_on(condition, "condition", 5, delta=2, sleep_=sleeper.sleep)
    assert len(sleeper.sleeps) == 2
    assert sleeper.sleeps[0] == 2  # delta of 2
    assert sleeper.sleeps[1] == 2  # delta of 2


def test_timeout_backoff():
    condition = WaitCondition(after_call_count=4, return_value="second")
    sleeper = Sleeper()

    exception_called = False
    try:
        wait_on(condition, "condition", 8, delta=2, polling_backoff=1, sleep_=sleeper.sleep)
    except TimeoutAssertionError:
        exception_called = True
    assert len(sleeper.sleeps) == 3
    assert sleeper.sleeps[0] == 2  # delta of 2
    assert sleeper.sleeps[1] == 3  # delta of 2 + 1 backoff
    assert sleeper.sleeps[2] == 4  # delta of 2 + 2 backoff
    assert exception_called
