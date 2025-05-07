"""The module describes the ``core`` job metrics plugin."""

import datetime
import json
import logging
import zoneinfo
from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from . import InstrumentPlugin
from ..formatting import (
    FormattedMetric,
    JobMetricFormatter,
    seconds_to_str,
)
from ..safety import Safety

log = logging.getLogger(__name__)

GALAXY_SLOTS_KEY = "galaxy_slots"
GALAXY_MEMORY_MB_KEY = "galaxy_memory_mb"
START_EPOCH_KEY = "start_epoch"
END_EPOCH_KEY = "end_epoch"
RUNTIME_SECONDS_KEY = "runtime_seconds"
CONTAINER_ID = "container_id"
CONTAINER_TYPE = "container_type"


class CorePluginFormatter(JobMetricFormatter):
    def __init__(self, timezone: Optional[str]):
        self.tz: Optional[zoneinfo.ZoneInfo] = None
        self.strftime_format = "%Y-%m-%d %H:%M:%S"
        self.__init_tz(timezone)

    def __init_tz(self, timezone: Optional[str]):
        if timezone:
            self.tz = zoneinfo.ZoneInfo(timezone)
            self.strftime_format = "%Y-%m-%d %H:%M:%S %Z (%z)"

    def format(self, key: str, value: Any) -> FormattedMetric:
        if key == CONTAINER_ID:
            return FormattedMetric("Container ID", value)
        if key == CONTAINER_TYPE:
            return FormattedMetric("Container Type", value)
        value = int(value)
        if key == GALAXY_SLOTS_KEY:
            return FormattedMetric("Cores Allocated", f"{value}")
        elif key == GALAXY_MEMORY_MB_KEY:
            return FormattedMetric("Memory Allocated (MB)", f"{value}")
        elif key == RUNTIME_SECONDS_KEY:
            return FormattedMetric("Job Runtime (Wall Clock)", seconds_to_str(value))
        else:
            title = "Job Start Time" if key == START_EPOCH_KEY else "Job End Time"
            dt = datetime.datetime.fromtimestamp(value, tz=self.tz)
            return FormattedMetric(title, dt.strftime(self.strftime_format))


class CorePlugin(InstrumentPlugin):
    """Simple plugin that collects data without external dependencies. In
    particular it currently collects value set for Galaxy slots.
    """

    plugin_type = "core"
    formatter = None
    default_safety = Safety.SAFE

    def __init__(self, **kwargs):
        self.__init_formatter(kwargs.get("timezone"))

    def __init_formatter(self, timezone: Optional[str]):
        if CorePlugin.formatter is None:
            CorePlugin.formatter = CorePluginFormatter(timezone)

    def pre_execute_instrument(self, job_directory: str) -> List[str]:
        commands = []
        commands.append(self.__record_galaxy_slots_command(job_directory))
        commands.append(self.__record_galaxy_memory_mb_command(job_directory))
        commands.append(self.__record_seconds_since_epoch_to_file(job_directory, "start"))
        return commands

    def post_execute_instrument(self, job_directory: str) -> List[str]:
        commands = []
        commands.append(self.__record_seconds_since_epoch_to_file(job_directory, "end"))
        return commands

    def job_properties(self, job_id, job_directory: str) -> Dict[str, Any]:
        galaxy_slots_file = self.__galaxy_slots_file(job_directory)
        galaxy_memory_mb_file = self.__galaxy_memory_mb_file(job_directory)

        properties = {}
        properties[GALAXY_SLOTS_KEY] = self.__read_integer(galaxy_slots_file)
        properties[GALAXY_MEMORY_MB_KEY] = self.__read_integer(galaxy_memory_mb_file)
        start = self.__read_seconds_since_epoch(job_directory, "start")
        end = self.__read_seconds_since_epoch(job_directory, "end")
        properties.update(self.__read_container_details(job_directory))
        if start is not None and end is not None:
            properties[START_EPOCH_KEY] = start
            properties[END_EPOCH_KEY] = end
            properties[RUNTIME_SECONDS_KEY] = end - start
        return properties

    def get_container_file_path(self, job_directory):
        return self._instrument_file_path(job_directory, "container")

    def __read_container_details(self, job_directory) -> Dict[str, str]:
        try:
            with open(self.get_container_file_path(job_directory)) as fh:
                return json.load(fh)
        except FileNotFoundError:
            return {}

    def __record_galaxy_slots_command(self, job_directory):
        galaxy_slots_file = self.__galaxy_slots_file(job_directory)
        return f"""echo "$GALAXY_SLOTS" > '{galaxy_slots_file}' """

    def __record_galaxy_memory_mb_command(self, job_directory):
        galaxy_memory_mb_file = self.__galaxy_memory_mb_file(job_directory)
        return f"""echo "$GALAXY_MEMORY_MB" > '{galaxy_memory_mb_file}' """

    def __record_seconds_since_epoch_to_file(self, job_directory, name):
        path = self._instrument_file_path(job_directory, f"epoch_{name}")
        return f'date +"%s" > {path}'

    def __read_seconds_since_epoch(self, job_directory, name):
        path = self._instrument_file_path(job_directory, f"epoch_{name}")
        return self.__read_integer(path)

    def __galaxy_slots_file(self, job_directory):
        return self._instrument_file_path(job_directory, "galaxy_slots")

    def __galaxy_memory_mb_file(self, job_directory):
        return self._instrument_file_path(job_directory, "galaxy_memory_mb")

    def __read_integer(self, path):
        value = None
        try:
            value = int(open(path).read())
        except Exception:
            pass
        return value


__all__ = ("CorePlugin",)
