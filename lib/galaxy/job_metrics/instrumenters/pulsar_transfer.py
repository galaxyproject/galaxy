"""The module describes the ``pulsar_transfer`` job metrics plugin.

Unlike every other plugin here, this one injects nothing into the job script. The work it
measures -- Pulsar staging a job's inputs in and its outputs back out -- happens either side
of the job script, in the Pulsar application, so Pulsar writes the metrics files itself and
this plugin only reads them.

The file is named by the usual instrumentation convention
(``__instrument_pulsar_transfer_<phase>``), which is also what gets Pulsar to stage it back
into Galaxy's metrics directory. Its contents are a JSON object of the keys below. Pulsar
writes that file in ``pulsar/managers/staging/metrics.py``; the two ends have to keep
agreeing on this shape.
"""

import json
from typing import Any

from galaxy.util import nice_size
from . import InstrumentPlugin
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


class PulsarTransferPluginFormatter(JobMetricFormatter):
    def format(self, key: str, value: Any) -> FormattedMetric | None:
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


class PulsarTransferPlugin(InstrumentPlugin):
    """Report how long Pulsar spent staging a job's files, and how much it moved."""

    plugin_type = "pulsar_transfer"
    formatter = PulsarTransferPluginFormatter()
    default_safety = Safety.SAFE

    def __init__(self, **kwargs: Any) -> None:
        pass

    def job_properties(self, job_id: int, job_directory: str) -> dict[str, Any]:
        properties: dict[str, Any] = {}
        for phase in PHASES:
            recorded = self.__read_phase(job_directory, phase)
            for key, value in recorded.items():
                if key in KEYS:
                    properties[f"{phase}_{key}"] = value
        return properties

    def __read_phase(self, job_directory: str, phase: str) -> dict[str, Any]:
        path = self._instrument_file_path(job_directory, phase)
        try:
            with open(path) as fh:
                return json.load(fh)
        except FileNotFoundError:
            # Pulsar did not report this phase - an older Pulsar, a job that ran somewhere
            # else entirely, or outputs that never made it back.
            return {}


# Only the plugin class - plugin discovery walks __all__ looking for one.
__all__ = ("PulsarTransferPlugin",)
