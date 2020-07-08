from galaxy.job_metrics import JobMetrics


def test_job_metrics_load():
    # Just construct the manager to make sure all the plugin classes load fine
    # and package is configured properly.
    JobMetrics()
