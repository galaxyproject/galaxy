from typing import (
    Any,
    Optional,
)

from galaxy.job_metrics import (
    formatting,
    JobMetrics,
)

TEST_JOBS_METRICS = JobMetrics()


def test_job_metrics_format_env():
    _assert_format(
        "env",
        "moo",
        "cow",
        assert_title="moo",
        assert_value="cow",
    )


def test_job_metrics_format_core():
    _assert_format(
        "core",
        "galaxy_slots",
        "4",
        assert_title="Cores Allocated",
        assert_value="4",
    )


def test_job_metrics_uname():
    _assert_format(
        "uname",
        "moo",
        "Ubuntu Linux 21.10",
        assert_title="Operating System",
        assert_value="Ubuntu Linux 21.10",
    )


def test_job_metric_formatting():
    assert formatting.seconds_to_str(0) == "0 seconds"
    assert formatting.seconds_to_str(1) == "1 second"
    assert formatting.seconds_to_str(59) == "59 seconds"
    assert formatting.seconds_to_str(60) == "1 minute"
    assert formatting.seconds_to_str(61) == "1 minute"
    assert formatting.seconds_to_str(119) == "1 minute"
    assert formatting.seconds_to_str(120) == "2 minutes"
    assert formatting.seconds_to_str(121) == "2 minutes"
    assert formatting.seconds_to_str(600) == "10 minutes"
    assert formatting.seconds_to_str(601) == "10 minutes"
    assert formatting.seconds_to_str(660) == "11 minutes"
    assert formatting.seconds_to_str(661) == "11 minutes"
    assert formatting.seconds_to_str(3600) == "1 hour and 0 minutes"
    assert formatting.seconds_to_str(3601) == "1 hour and 0 minutes"
    assert formatting.seconds_to_str(3660) == "1 hour and 1 minute"
    assert formatting.seconds_to_str(3661) == "1 hour and 1 minute"
    assert formatting.seconds_to_str(7260) == "2 hours and 1 minute"
    assert formatting.seconds_to_str(7320) == "2 hours and 2 minutes"
    assert formatting.seconds_to_str(36181) == "10 hours and 3 minutes"


def _assert_format(
    plugin: str, key: str, value: Any, assert_title: Optional[str] = None, assert_value: Optional[str] = None
):
    result = TEST_JOBS_METRICS.format(plugin, key, value)
    if assert_title is not None:
        assert result[0] == assert_title
    if assert_value is not None:
        assert result[1] == assert_value
