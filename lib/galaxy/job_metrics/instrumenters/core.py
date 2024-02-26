"""The module describes the ``core`` job metrics plugin."""

import logging
import time
from typing import (
    Any,
    Dict,
    List,
)

from . import InstrumentPlugin
from ..formatting import (
    FormattedMetric,
    JobMetricFormatter,
    seconds_to_str,
)
from ..safety import Safety
from ...carbon_emissions import load_aws_ec2_reference_data_json

log = logging.getLogger(__name__)

GALAXY_SLOTS_KEY = "galaxy_slots"
GALAXY_MEMORY_MB_KEY = "galaxy_memory_mb"

START_EPOCH_KEY = "start_epoch"
END_EPOCH_KEY = "end_epoch"
RUNTIME_SECONDS_KEY = "runtime_seconds"

ENERGY_NEEDED_MEMORY_KEY = "energy_needed_memory"
ENERGY_NEEDED_CPU_KEY = "energy_needed_cpu"

# source: (in W/GB) http://dl.acm.org/citation.cfm?doid=3076113.3076117
# and https://www.tomshardware.com/uk/reviews/intel-core-i7-5960x-haswell-e-cpu,3918-13.html
MEMORY_POWER_USAGE_CONSTANT = 0.3725

# NOTE: Currently there is no way to get the PUE value from the galaxy config # so we use the
# global constant value # source: https://journal.uptimeinstitute.com/is-pue-actually-going-up/
POWER_USAGE_EFFECTIVENESS_CONSTANT = 1.67


class CorePluginFormatter(JobMetricFormatter):
    def format(self, key: str, value: Any) -> FormattedMetric:
        if key == GALAXY_SLOTS_KEY:
            return FormattedMetric("Cores Allocated", "%d" % int(value))
        elif key == GALAXY_MEMORY_MB_KEY:
            return FormattedMetric("Memory Allocated (MB)", "%d" % int(value))
        elif key == RUNTIME_SECONDS_KEY:
            return FormattedMetric("Job Runtime (Wall Clock)", seconds_to_str(int(value)))
        elif key == ENERGY_NEEDED_CPU_KEY:
            return FormattedMetric("CPU Energy Usage", self.__format_energy_needed_text(float(value)))
        elif key == ENERGY_NEEDED_MEMORY_KEY:
            return FormattedMetric("Memory Energy Usage", self.__format_energy_needed_text(float(value)))
        else:
            # TODO: Use localized version of this from galaxy.ini
            title = "Job Start Time" if key == START_EPOCH_KEY else "Job End Time"
            return FormattedMetric(title, time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(float(value))))

    def __format_energy_needed_text(self, energy_needed_kwh: float) -> str:
        adjusted_energy_needed = energy_needed_kwh
        unit_magnitude = "kW⋅h"

        if energy_needed_kwh == 0:
            return "0 kW⋅h"

        if energy_needed_kwh >= 1e3:
            adjusted_energy_needed /= 1000
            unit_magnitude = "MW⋅h"
        elif energy_needed_kwh >= 1 and energy_needed_kwh <= 999:
            unit_magnitude = "W⋅h"
        elif energy_needed_kwh < 1 and energy_needed_kwh > 1e-4:
            adjusted_energy_needed *= 1000
            unit_magnitude = "mW⋅h"
        else:
            adjusted_energy_needed *= 1e6
            unit_magnitude = "µW⋅h"

        rounded_value = round(adjusted_energy_needed)
        return f"{'< 1' if rounded_value == 0 else rounded_value} {unit_magnitude}"


class CorePlugin(InstrumentPlugin):
    """Simple plugin that collects data without external dependencies. In
    particular it currently collects value set for Galaxy slots.
    """

    plugin_type = "core"
    formatter = CorePluginFormatter()
    default_safety = Safety.SAFE

    def __init__(self, **kwargs):
        pass

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
        properties = {}

        galaxy_slots_file = self.__galaxy_slots_file(job_directory)
        galaxy_memory_mb_file = self.__galaxy_memory_mb_file(job_directory)

        allocated_cpu_cores = self.__read_integer(galaxy_slots_file)
        if allocated_cpu_cores is not None:
            properties[GALAXY_SLOTS_KEY] = allocated_cpu_cores

        allocated_memory_mebibyte = self.__read_integer(galaxy_memory_mb_file)
        if allocated_memory_mebibyte is not None:
            properties[GALAXY_MEMORY_MB_KEY] = allocated_memory_mebibyte

        start_time_seconds = self.__read_seconds_since_epoch(job_directory, "start")
        end_time_seconds = self.__read_seconds_since_epoch(job_directory, "end")
        if start_time_seconds is not None and end_time_seconds is not None:
            properties[START_EPOCH_KEY] = start_time_seconds
            properties[END_EPOCH_KEY] = end_time_seconds

            runtime_seconds = end_time_seconds - start_time_seconds
            properties[RUNTIME_SECONDS_KEY] = end_time_seconds - start_time_seconds

            if allocated_cpu_cores is not None:
                estimated_server_instance = self.__get_estimated_server_instance(
                    allocated_cpu_cores, allocated_memory_mebibyte or 0
                )
                if estimated_server_instance is not None:
                    cpu_info = estimated_server_instance["cpu"][0]
                    tdp_per_ore = cpu_info["tdp"] / cpu_info["core_count"]
                    normalized_tdp_per_core = tdp_per_ore * allocated_cpu_cores

                    memory_allocated_in_gibibyte = (allocated_memory_mebibyte or 0) / 1024  # Convert to gibibyte

                    runtime_hours = runtime_seconds / (60 * 60)  # Convert to hours

                    power_needed_watts_cpu = POWER_USAGE_EFFECTIVENESS_CONSTANT * normalized_tdp_per_core
                    power_needed_watts_memory = (
                        POWER_USAGE_EFFECTIVENESS_CONSTANT * memory_allocated_in_gibibyte * MEMORY_POWER_USAGE_CONSTANT
                    )

                    energy_needed_cpu_kwh = (runtime_hours * power_needed_watts_cpu) / 1000
                    energy_needed_memory_kwh = (runtime_hours * power_needed_watts_memory) / 1000

                    # Some jobs do not report memory usage, so a default value of 0 is used in this case
                    if energy_needed_memory_kwh != 0:
                        properties[ENERGY_NEEDED_MEMORY_KEY] = energy_needed_memory_kwh

                    properties[ENERGY_NEEDED_CPU_KEY] = energy_needed_cpu_kwh

        return properties

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

    def __get_estimated_server_instance(self, allocated_cpu_cores: int, allocated_memory_mebibyte=0):
        adjusted_memory = allocated_memory_mebibyte / 1024 if allocated_memory_mebibyte is not None else 0
        server_instance = None

        for aws_instance in load_aws_ec2_reference_data_json():
            # Use only core count in search criteria
            if adjusted_memory == 0 and aws_instance["v_cpu_count"] >= allocated_cpu_cores:
                server_instance = aws_instance
                break

            # Use both core count and allocated memory in search criteria
            if aws_instance["mem"] >= adjusted_memory and aws_instance["v_cpu_count"] >= allocated_cpu_cores:
                server_instance = aws_instance
                break

        if server_instance is None:
            return None

        return server_instance


__all__ = ("CorePlugin",)
