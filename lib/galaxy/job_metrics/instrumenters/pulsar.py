"""The module describes the ``pulsar`` job metrics plugin.

Unlike every other plugin here, this one injects nothing into the job script. What it
reports happens either side of the job script, so its files are written by Pulsar and by
Galaxy's Pulsar runner, and this plugin only reads them. Each is a JSON object named by the
usual instrumentation convention (``__instrument_pulsar_<name>``):

- ``transfer_<phase>`` - Pulsar staging a job's inputs in and its outputs back out, keys
  below. The prefix is also what gets Pulsar to stage it back into Galaxy's metrics directory.
- ``version`` - the version of the Pulsar that staged the job, also written by Pulsar.
- ``version_target`` / ``version_status`` - written by the Pulsar runner: the version it made
  its decisions for at submission (and where that came from), and the version the remote
  reported when the job finished.

Pulsar writes its files in ``pulsar/managers/staging/metrics.py``; the two ends have to keep
agreeing on these shapes.
"""

import json
import logging
import os
from typing import Any

from galaxy.util import nice_size
from . import (
    INSTRUMENT_FILE_PREFIX,
    InstrumentPlugin,
)
from ..formatting import (
    FormattedMetric,
    JobMetricFormatter,
    seconds_to_str,
)
from ..safety import Safety

PREPROCESS = "preprocess"
POSTPROCESS = "postprocess"
PHASES = (PREPROCESS, POSTPROCESS)

# Keys in the JSON Pulsar writes, and - prefixed with the phase - the metric names recorded
# against the job.
FILES_KEY = "files"
BYTES_KEY = "bytes"
SECONDS_KEY = "seconds"
KEYS = (FILES_KEY, BYTES_KEY, SECONDS_KEY)

PLUGIN_TYPE = "pulsar"
VERSION = "version"
VERSION_TARGET = "version_target"
VERSION_STATUS = "version_status"

VERSION_LABELS = {
    "client_version": "Pulsar Client Version",
    "target_version": "Pulsar Target Version",
    "target_version_source": "Pulsar Target Version Source",
    "server_version": "Pulsar Server Version",
    "server_version_source": "Pulsar Server Version Source",
}

log = logging.getLogger(__name__)


class PulsarPluginFormatter(JobMetricFormatter):
    def format(self, key: str, value: Any) -> FormattedMetric | None:
        if key in VERSION_LABELS:
            return FormattedMetric(VERSION_LABELS[key], str(value))
        phase, _, metric = key.partition("_")
        if phase not in PHASES or metric not in KEYS:
            return super().format(key, value)
        direction = "Input" if phase == PREPROCESS else "Output"
        if metric == SECONDS_KEY:
            return FormattedMetric(f"Pulsar {direction} Staging (Wall Clock)", _format_seconds(float(value)))
        elif metric == BYTES_KEY:
            return FormattedMetric(f"Pulsar {direction} Staging Size", nice_size(value))
        else:
            return FormattedMetric(f"Pulsar {direction}s Staged", f"{int(value)}")


def _format_seconds(value: float) -> str:
    # Staging is frequently quicker than the minute resolution seconds_to_str settles for, and
    # "0 seconds" for a transfer that took a third of a second reads like a bug.
    if value < 60:
        return f"{value:.1f} seconds"
    return seconds_to_str(int(value))


class PulsarPlugin(InstrumentPlugin):
    """Report how long Pulsar spent staging a job's files and how much it moved, and which
    Pulsar versions were involved."""

    plugin_type = PLUGIN_TYPE
    formatter = PulsarPluginFormatter()
    # Server versions are only of interest to admins; transfer figures are fine to show.
    default_safety = Safety.POTENTIALLY_SENSITVE

    def __init__(self, **kwargs: Any) -> None:
        pass

    @classmethod
    def safety(cls, metric_name: str) -> Safety:
        if metric_name in VERSION_LABELS:
            return cls.default_safety
        return Safety.SAFE

    def job_properties(self, job_id: int, job_directory: str) -> dict[str, Any]:
        properties: dict[str, Any] = {}
        for phase in PHASES:
            recorded = _read(job_directory, f"transfer_{phase}")
            for key, value in recorded.items():
                if key in KEYS:
                    properties[f"{phase}_{key}"] = value
        target = _read(job_directory, VERSION_TARGET)
        for key in ("client_version", "target_version", "target_version_source"):
            if key in target:
                properties[key] = target[key]
        for name, source in ((VERSION_STATUS, "status"), (VERSION, "job_files")):
            server_version = _read(job_directory, name).get("version")
            if server_version:
                properties["server_version"] = server_version
                properties["server_version_source"] = source
                break
        return properties


def write_version_target(job_directory: str, client_version: str, target_version: str, source: str) -> None:
    """Record the Pulsar version a job was submitted for, and how it was determined."""
    _write(
        job_directory,
        VERSION_TARGET,
        {"client_version": client_version, "target_version": target_version, "target_version_source": source},
    )


def write_version_status(job_directory: str, server_version: str) -> None:
    """Record the version the remote Pulsar reported when the job finished."""
    _write(job_directory, VERSION_STATUS, {"version": server_version})


def read_target_version(job_directory: str) -> str | None:
    """The version recorded by write_version_target, if the job has one and it's readable."""
    try:
        return _read(job_directory, VERSION_TARGET).get("target_version")
    except ValueError:
        # _write is best effort, so this may be a partial write - finishing falls back instead.
        log.exception("Unreadable Pulsar target version in %s", job_directory)
        return None


def _path(job_directory: str, name: str) -> str:
    return os.path.join(job_directory, f"{INSTRUMENT_FILE_PREFIX}_{PLUGIN_TYPE}_{name}")


def _read(job_directory: str, name: str) -> dict[str, Any]:
    try:
        with open(_path(job_directory, name)) as fh:
            recorded: dict[str, Any] = json.load(fh)
            return recorded
    except FileNotFoundError:
        # Not reported - an older Pulsar or Galaxy, a job that ran somewhere else entirely,
        # or files that never made it back.
        return {}


def _write(job_directory: str, name: str, recorded: dict[str, Any]) -> None:
    # Best effort - a metric is never worth failing a job over.
    try:
        os.makedirs(job_directory, exist_ok=True)
        with open(_path(job_directory, name), "w") as fh:
            json.dump(recorded, fh)
    except Exception:
        log.exception("Failed to record Pulsar job metrics file %s", name)


# Only the plugin class - plugin discovery walks __all__ looking for one.
__all__ = ("PulsarPlugin",)
