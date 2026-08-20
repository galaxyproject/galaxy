"""The core plugin's resubmission_count metric."""

from galaxy.job_metrics import JobMetrics
from galaxy.job_metrics.instrumenters.core import (
    CorePlugin,
    RESUBMISSION_COUNT_KEY,
)
from galaxy.job_metrics.safety import Safety


class FakeJob:
    def __init__(self, id: int, resubmission_count: int) -> None:
        self.id = id
        self.resubmission_count = resubmission_count


def test_resubmission_count_comes_from_the_job_not_the_working_directory():
    plugin = CorePlugin()

    properties = plugin.collect(FakeJob(42, resubmission_count=2), "/cleared-and-recreated-working-directory")

    assert properties[RESUBMISSION_COUNT_KEY] == 2


def test_a_job_that_was_never_resubmitted_still_records_a_zero():
    plugin = CorePlugin()

    properties = plugin.collect(FakeJob(42, resubmission_count=0), "/job-directory")

    assert properties[RESUBMISSION_COUNT_KEY] == 0


def test_a_zero_count_is_recorded_but_not_displayed():
    plugin = CorePlugin()

    assert plugin.formatter is not None
    assert plugin.formatter.format(RESUBMISSION_COUNT_KEY, 0) is None


def test_show_zero_resubmissions_displays_the_zero():
    plugin = CorePlugin(show_zero_resubmissions="true")

    assert plugin.formatter is not None
    assert plugin.formatter.format(RESUBMISSION_COUNT_KEY, 0) == ("Resubmission Count", "0")


def test_show_zero_resubmissions_reaches_display_from_the_metrics_configuration():
    """An XML attribute arrives as a string, and has to travel to the formatter that renders."""
    job_metrics = JobMetrics(conf_dict=[{"type": "core", "show_zero_resubmissions": "true"}])

    assert job_metrics.format("core", RESUBMISSION_COUNT_KEY, 0) == ("Resubmission Count", "0")


def test_zero_resubmissions_stays_hidden_by_default_through_the_configuration():
    job_metrics = JobMetrics(conf_dict=[{"type": "core"}])

    assert job_metrics.format("core", RESUBMISSION_COUNT_KEY, 0) is None


def test_resubmission_metric_formatting_and_safety():
    plugin = CorePlugin()

    assert plugin.formatter is not None
    assert plugin.formatter.format(RESUBMISSION_COUNT_KEY, 1) == ("Resubmission Count", "1")
    assert plugin.safety(RESUBMISSION_COUNT_KEY) == Safety.SAFE
