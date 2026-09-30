import json
import logging
from types import SimpleNamespace

import pytest

from galaxy.job_metrics import (
    JobInstrumenter,
    JobMetrics,
)
from galaxy.job_metrics.instrumenters.pulsar import (
    POSTPROCESS,
    PREPROCESS,
    PulsarPlugin,
    read_target_version,
    write_version_status,
    write_version_target,
)
from galaxy.job_metrics.safety import Safety

PREPROCESS_FILE = "__instrument_pulsar_transfer_preprocess"
POSTPROCESS_FILE = "__instrument_pulsar_transfer_postprocess"


def _record(job_directory, phase, **recorded):
    name = PREPROCESS_FILE if phase == PREPROCESS else POSTPROCESS_FILE
    job_directory.join(name).write(json.dumps(recorded))


def test_no_properties_without_files(tmpdir):
    assert PulsarPlugin().job_properties(1, str(tmpdir)) == {}


def test_reads_both_phases(tmpdir):
    _record(tmpdir, PREPROCESS, files=3, bytes=1024, seconds=2.5)
    _record(tmpdir, POSTPROCESS, files=1, bytes=17, seconds=0.5)
    properties = PulsarPlugin().job_properties(1, str(tmpdir))
    assert properties == {
        "preprocess_files": 3,
        "preprocess_bytes": 1024,
        "preprocess_seconds": 2.5,
        "postprocess_files": 1,
        "postprocess_bytes": 17,
        "postprocess_seconds": 0.5,
    }


def test_one_phase_missing_is_not_an_error(tmpdir):
    _record(tmpdir, PREPROCESS, files=2, bytes=8, seconds=1.0)
    properties = PulsarPlugin().job_properties(1, str(tmpdir))
    assert properties["preprocess_files"] == 2
    assert "postprocess_files" not in properties


def test_unexpected_keys_are_ignored(tmpdir):
    _record(tmpdir, PREPROCESS, files=1, bytes=2, seconds=3.0, retries=9)
    assert "preprocess_retries" not in PulsarPlugin().job_properties(1, str(tmpdir))


def test_corrupt_file_raises(tmpdir):
    tmpdir.join(PREPROCESS_FILE).write("not json")
    with pytest.raises(json.JSONDecodeError):
        PulsarPlugin().job_properties(1, str(tmpdir))


@pytest.mark.parametrize("recorded", [[], [1, 2, 3], "files", None, 3, True])
def test_non_object_file_raises(tmpdir, recorded):
    tmpdir.join(PREPROCESS_FILE).write(json.dumps(recorded))
    with pytest.raises(AttributeError):
        PulsarPlugin().job_properties(1, str(tmpdir))


@pytest.mark.parametrize("contents", ["not json", "[]"])
def test_collection_logs_invalid_metrics_without_raising(tmpdir, caplog, contents):
    tmpdir.join(PREPROCESS_FILE).write(contents)
    instrumenter = JobMetrics(conf_dict=[{"type": "pulsar"}]).default_job_instrumenter
    with caplog.at_level(logging.ERROR, logger="galaxy.job_metrics"):
        assert instrumenter.collect_properties(SimpleNamespace(id=1), str(tmpdir)) == {}
    assert len(caplog.records) == 1
    record = caplog.records[0]
    assert record.levelno == logging.ERROR
    assert "Failed to collect job properties for plugin" in record.message
    assert record.exc_info is not None


def test_plugin_is_configurable_by_type():
    instrumenter = JobMetrics(conf_dict=[{"type": "pulsar"}]).default_job_instrumenter
    assert isinstance(instrumenter, JobInstrumenter)
    assert [type(p) for p in instrumenter.plugins] == [PulsarPlugin]


def test_instruments_nothing_in_the_job_script(tmpdir):
    plugin = PulsarPlugin()
    assert plugin.pre_execute_instrument(str(tmpdir)) is None
    assert plugin.post_execute_instrument(str(tmpdir)) is None


def test_formatting():
    formatter = PulsarPlugin.formatter
    assert formatter.format("preprocess_seconds", 2.5) == ("Pulsar Input Staging (Wall Clock)", "2.5 seconds")
    assert formatter.format("postprocess_seconds", 125.0) == ("Pulsar Output Staging (Wall Clock)", "2 minutes")
    assert formatter.format("postprocess_bytes", 1024) == ("Pulsar Output Staging Size", "1.0 KB")
    assert formatter.format("postprocess_files", 3) == ("Pulsar Outputs Staged", "3")
    assert formatter.format("something_else", 3) == ("something_else", "3")


def test_reads_versions_galaxy_recorded(tmpdir):
    write_version_target(str(tmpdir), client_version="0.15.16", target_version="0.15.0.dev1", source="container_image")
    write_version_status(str(tmpdir), "0.15.0.dev1")
    properties = PulsarPlugin().job_properties(1, str(tmpdir))
    assert properties == {
        "client_version": "0.15.16",
        "target_version": "0.15.0.dev1",
        "target_version_source": "container_image",
        "server_version": "0.15.0.dev1",
        "server_version_source": "status",
    }


def test_server_version_from_the_file_pulsar_staged_back(tmpdir):
    tmpdir.join("__instrument_pulsar_version").write(json.dumps({"version": "0.15.16"}))
    properties = PulsarPlugin().job_properties(1, str(tmpdir))
    assert properties == {"server_version": "0.15.16", "server_version_source": "job_files"}


def test_status_version_wins_over_the_staged_back_file(tmpdir):
    tmpdir.join("__instrument_pulsar_version").write(json.dumps({"version": "0.15.15"}))
    write_version_status(str(tmpdir), "0.15.16")
    properties = PulsarPlugin().job_properties(1, str(tmpdir))
    assert properties["server_version"] == "0.15.16"
    assert properties["server_version_source"] == "status"


def test_read_target_version(tmpdir):
    assert read_target_version(str(tmpdir)) is None
    write_version_target(str(tmpdir), client_version="0.15.16", target_version="0.14.0", source="destination")
    assert read_target_version(str(tmpdir)) == "0.14.0"


def test_version_metrics_are_only_for_admins():
    plugin = PulsarPlugin()
    assert plugin.safety("preprocess_seconds") == Safety.SAFE
    assert plugin.safety("server_version") == Safety.POTENTIALLY_SENSITVE
    assert PulsarPlugin.default_safety == Safety.POTENTIALLY_SENSITVE


def test_version_formatting():
    formatter = PulsarPlugin.formatter
    assert formatter.format("client_version", "0.15.16") == ("Pulsar Client Version", "0.15.16")
    assert formatter.format("server_version_source", "status") == ("Pulsar Server Version Source", "status")
