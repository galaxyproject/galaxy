from typing import (
    Any,
    Optional,
)

from galaxy.job_metrics import (
    formatting,
    JobMetrics,
    RawMetric,
)
from galaxy.job_metrics.safety import Safety

TEST_JOBS_METRICS = JobMetrics()
TEST_LINUX_OS = "Ubuntu Linux 21.10"


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


def test_job_metrics_format_cgroup():
    _assert_format(
        "cgroup",
        "cpuacct.usage",
        7265342042,
        assert_title="CPU Time",
        assert_value="7.265342042 seconds",
    )
    _assert_format(
        "cgroup",
        "memory.limit_in_bytes",
        9223372036854771712,
        assert_title="Memory limit on cgroup (MEM)",
        assert_value="8.0 EB",
    )


def test_job_metrics_uname():
    _assert_format(
        "uname",
        "moo",
        TEST_LINUX_OS,
        assert_title="Operating System",
        assert_value=TEST_LINUX_OS,
    )


def test_metrics_dictifiable():
    test_metrics = [
        RawMetric("galaxy_slots", "4", "core"),
        RawMetric("uname", TEST_LINUX_OS, "uname"),
        RawMetric("SSH_AUTH_SOCK", "/private/tmp/com.apple.launchd.Nw6gC2VOCr/Listeners", "env"),
    ]
    dictifiable_metrics = TEST_JOBS_METRICS.dictifiable_metrics(test_metrics, Safety.POTENTIALLY_SENSITVE)
    _assert_metrics_of_type(dictifiable_metrics, ["core", "uname"])

    dictifiable_metrics = TEST_JOBS_METRICS.dictifiable_metrics(test_metrics, Safety.SAFE)
    _assert_metrics_of_type(dictifiable_metrics, ["core"])

    dictifiable_metrics = TEST_JOBS_METRICS.dictifiable_metrics(test_metrics, Safety.UNSAFE)
    _assert_metrics_of_type(dictifiable_metrics, ["core", "uname", "env"])


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


def _assert_metrics_of_type(metric_list, expected_types):
    assert len(metric_list) == len(expected_types)
    for dictifiable_metric, expected_type in zip(metric_list, expected_types):
        assert dictifiable_metric.plugin == expected_type


def _assert_format(
    plugin: str, key: str, value: Any, assert_title: Optional[str] = None, assert_value: Optional[str] = None
):
    result = TEST_JOBS_METRICS.format(plugin, key, value)
    if assert_title is not None:
        assert result[0] == assert_title
    if assert_value is not None:
        assert result[1] == assert_value
