"""The job context the framework hands to instrument plugins at collection time."""

from typing import Any

from galaxy.job_metrics import JobInstrumenter
from galaxy.job_metrics.instrumenters import InstrumentPlugin
from galaxy.util.plugin_config import PluginConfigSource


class FakeJob:
    """Something Job-shaped, satisfying ProvidesJobMetricsContext structurally."""

    def __init__(self, id: int, resubmission_count: int = 0) -> None:
        self.id = id
        self.resubmission_count = resubmission_count


class DirectoryOnlyPlugin(InstrumentPlugin):
    """A plugin of the pre-existing kind: it knows a job id and a directory, nothing more."""

    plugin_type = "directory_only"

    def job_properties(self, job_id, job_directory: str) -> dict[str, Any]:
        return {"job_id": job_id, "job_directory": job_directory}


class JobReadingPlugin(InstrumentPlugin):
    """A plugin that overrides the new hook to read the job itself."""

    plugin_type = "job_reading"

    def job_properties(self, job_id, job_directory: str) -> dict[str, Any]:
        return {}

    def collect(self, job, job_directory: str) -> dict[str, Any]:
        return {"resubmission_count": job.resubmission_count}


def _instrumenter_for(*plugins) -> JobInstrumenter:
    instrumenter = JobInstrumenter({}, PluginConfigSource("dict", []))
    instrumenter.plugins = list(plugins)
    return instrumenter


def test_collect_defaults_to_job_properties_with_the_job_id():
    properties = DirectoryOnlyPlugin().collect(FakeJob(42), "/job/directory")

    assert properties == {"job_id": 42, "job_directory": "/job/directory"}


def test_collect_can_be_overridden_to_read_the_job():
    properties = JobReadingPlugin().collect(FakeJob(42, resubmission_count=3), "/job/directory")

    assert properties == {"resubmission_count": 3}


def test_instrumenter_routes_collection_through_collect():
    instrumenter = _instrumenter_for(DirectoryOnlyPlugin(), JobReadingPlugin())

    per_plugin = instrumenter.collect_properties(FakeJob(42, resubmission_count=1), "/job/directory")

    assert per_plugin["directory_only"] == {"job_id": 42, "job_directory": "/job/directory"}
    assert per_plugin["job_reading"] == {"resubmission_count": 1}
