"""The core plugin's resubmission_count metric."""

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


def test_a_job_that_was_never_resubmitted_records_no_metric():
    plugin = CorePlugin()

    properties = plugin.collect(FakeJob(42, resubmission_count=0), "/job-directory")

    assert RESUBMISSION_COUNT_KEY not in properties


def test_resubmission_metric_formatting_and_safety():
    plugin = CorePlugin()

    assert plugin.formatter is not None
    assert plugin.formatter.format(RESUBMISSION_COUNT_KEY, 1) == ("Resubmission Count", "1")
    assert plugin.safety(RESUBMISSION_COUNT_KEY) == Safety.SAFE
