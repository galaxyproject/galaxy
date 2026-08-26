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


def test_the_class_fallback_formatter_is_stable_and_unconfigured():
    """The class formatter renders metrics from a core plugin no longer in the configuration.

    It must not inherit display options from whichever instance happened to be constructed
    first: with destination-only configurations that would let destination ordering decide
    how historical metrics render.
    """
    plugin = CorePlugin(show_zero_resubmissions="true")

    assert plugin.formatter is not None
    assert plugin.formatter.format(RESUBMISSION_COUNT_KEY, 0) == ("Resubmission Count", "0")
    assert CorePlugin.formatter is not plugin.formatter
    assert CorePlugin.formatter is not None
    assert CorePlugin.formatter.format(RESUBMISSION_COUNT_KEY, 0) is None


def test_a_core_metric_still_formats_when_core_is_not_configured():
    """An admin who drops core from the configuration should not turn old metrics into raw keys."""
    job_metrics = JobMetrics(conf_dict=[{"type": "env"}])

    assert job_metrics.format("core", RESUBMISSION_COUNT_KEY, 3) == ("Resubmission Count", "3")
