"""The module describes the ``cpuinfo`` job metrics plugin."""

import logging
import re
from typing import Any

from galaxy import util
from . import InstrumentPlugin
from ..formatting import (
    FormattedMetric,
    JobMetricFormatter,
)

log = logging.getLogger(__name__)

PROCESSOR_LINE = re.compile(r"processor\s*\:\s*(\d+)")


class CpuInfoFormatter(JobMetricFormatter):
    def format(self, key: str, value: Any) -> FormattedMetric | None:
        if key == "processor_count":
            return FormattedMetric("Processor Count", f"{int(value)}")
        else:
            return super().format(key, value)


class CpuInfoPlugin(InstrumentPlugin):
    """Gather information about processor configuration from /proc/cpuinfo.
    Linux only.
    """

    plugin_type = "cpuinfo"
    formatter = CpuInfoFormatter()
    fields: set[str] | None

    def __init__(self, **kwargs):
        self.verbose = util.asbool(kwargs.get("verbose", False))
        fields_str = kwargs.get("fields", None)
        if isinstance(fields_str, list):
            self.fields = {f.lower() for f in fields_str}
        elif fields_str:
            self.fields = {f.strip().lower() for f in fields_str.split(",")}
        else:
            self.fields = None
        # Collapse a field to a single key when its value is identical across
        # every processor, instead of one processor_N_<field> key per core.
        self.unique = util.asbool(kwargs.get("unique", False))

    def pre_execute_instrument(self, job_directory):
        return f"cat /proc/cpuinfo > '{self.__instrument_cpuinfo_path(job_directory)}'"

    def job_properties(self, job_id, job_directory):
        properties: dict[str, Any] = {}
        processor_count = 0
        per_field_values: dict[str, dict[str, str]] = {}
        with open(self.__instrument_cpuinfo_path(job_directory)) as f:
            current_processor = None
            for line in f:
                line = line.strip().lower()
                if not line:  # Skip empty lines
                    continue

                processor_line_match = PROCESSOR_LINE.match(line)
                if processor_line_match:
                    processor_count += 1
                    current_processor = processor_line_match.group(1)
                elif current_processor and self.verbose:
                    # If verbose, dump information about each processor
                    # into database...
                    field, value = line.split(":", 1)
                    field = field.strip()
                    if self.fields is not None and field not in self.fields:
                        continue
                    value = value.strip()
                    if self.unique:
                        per_field_values.setdefault(field, {})[current_processor] = value
                    else:
                        properties[f"processor_{current_processor}_{field}"] = value

        if self.unique:
            for field, by_processor in per_field_values.items():
                distinct_values = set(by_processor.values())
                reported_by_all = len(by_processor) == processor_count
                if len(distinct_values) == 1 and reported_by_all:
                    properties[field] = distinct_values.pop()
                else:
                    # Processors disagree, or some processors did not report this
                    # field at all: keep per-processor keys for it.
                    for processor_id, value in by_processor.items():
                        properties[f"processor_{processor_id}_{field}"] = value

        properties["processor_count"] = processor_count
        return properties

    def __instrument_cpuinfo_path(self, job_directory):
        return self._instrument_file_path(job_directory, "cpuinfo")


__all__ = ("CpuInfoPlugin",)
