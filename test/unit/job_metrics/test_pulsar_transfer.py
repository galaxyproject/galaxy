import json

from galaxy.job_metrics import (
    JobInstrumenter,
    JobMetrics,
)
from galaxy.job_metrics.instrumenters.pulsar_transfer import (
    POSTPROCESS,
    PREPROCESS,
    PulsarTransferPlugin,
)

PREPROCESS_FILE = "__instrument_pulsar_transfer_preprocess"
POSTPROCESS_FILE = "__instrument_pulsar_transfer_postprocess"


def _record(job_directory, phase, **recorded):
    name = PREPROCESS_FILE if phase == PREPROCESS else POSTPROCESS_FILE
    job_directory.join(name).write(json.dumps(recorded))


def test_no_properties_without_files(tmpdir):
    assert PulsarTransferPlugin().job_properties(1, str(tmpdir)) == {}


def test_reads_both_phases(tmpdir):
    _record(tmpdir, PREPROCESS, files=3, bytes=1024, seconds=2.5)
    _record(tmpdir, POSTPROCESS, files=1, bytes=17, seconds=0.5)
    properties = PulsarTransferPlugin().job_properties(1, str(tmpdir))
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
    properties = PulsarTransferPlugin().job_properties(1, str(tmpdir))
    assert properties["preprocess_files"] == 2
    assert "postprocess_files" not in properties


def test_unexpected_keys_are_ignored(tmpdir):
    _record(tmpdir, PREPROCESS, files=1, bytes=2, seconds=3.0, retries=9)
    assert "preprocess_retries" not in PulsarTransferPlugin().job_properties(1, str(tmpdir))


def test_corrupt_file_is_skipped(tmpdir):
    tmpdir.join(PREPROCESS_FILE).write("not json")
    assert PulsarTransferPlugin().job_properties(1, str(tmpdir)) == {}


def test_non_object_file_is_skipped(tmpdir):
    tmpdir.join(PREPROCESS_FILE).write("[1, 2, 3]")
    assert PulsarTransferPlugin().job_properties(1, str(tmpdir)) == {}


def test_plugin_is_configurable_by_type():
    instrumenter = JobMetrics(conf_dict=[{"type": "pulsar_transfer"}]).default_job_instrumenter
    assert isinstance(instrumenter, JobInstrumenter)
    assert [type(p) for p in instrumenter.plugins] == [PulsarTransferPlugin]


def test_instruments_nothing_in_the_job_script(tmpdir):
    plugin = PulsarTransferPlugin()
    assert plugin.pre_execute_instrument(str(tmpdir)) is None
    assert plugin.post_execute_instrument(str(tmpdir)) is None


def test_formatting():
    formatter = PulsarTransferPlugin.formatter
    assert formatter.format("preprocess_seconds", 2.5) == ("Pulsar Input Staging (Wall Clock)", "2.5 seconds")
    assert formatter.format("postprocess_seconds", 125.0) == ("Pulsar Output Staging (Wall Clock)", "2 minutes")
    assert formatter.format("postprocess_bytes", 1024) == ("Pulsar Output Staging Size", "1.0 KB")
    assert formatter.format("postprocess_files", 3) == ("Pulsar Outputs Staged", "3")
    assert formatter.format("something_else", 3) == ("something_else", "3")
