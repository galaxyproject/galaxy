from galaxy.job_metrics import formatting
from galaxy.job_metrics import JobMetrics


def test_job_metrics_load():
    # Just construct the manager to make sure all the plugin classes load fine
    # and package is configured properly.
    JobMetrics()


def test_job_metric_formatting():
    assert formatting.seconds_to_str(0) == "0 seconds"
    assert formatting.seconds_to_str(59) == "59 seconds"
    assert formatting.seconds_to_str(60) == "1 minutes"
    assert formatting.seconds_to_str(61) == "1 minutes"
    assert formatting.seconds_to_str(119) == "1 minutes"
    assert formatting.seconds_to_str(120) == "2 minutes"
    assert formatting.seconds_to_str(121) == "2 minutes"
    assert formatting.seconds_to_str(600) == "10 minutes"
    assert formatting.seconds_to_str(601) == "10 minutes"
    assert formatting.seconds_to_str(660) == "11 minutes"
    assert formatting.seconds_to_str(661) == "11 minutes"
    assert formatting.seconds_to_str(3600) == "1 hours and 0 minutes"
    assert formatting.seconds_to_str(3601) == "1 hours and 0 minutes"
    assert formatting.seconds_to_str(3660) == "1 hours and 1 minutes"
    assert formatting.seconds_to_str(3661) == "1 hours and 1 minutes"
    assert formatting.seconds_to_str(36181) == "10 hours and 3 minutes"
