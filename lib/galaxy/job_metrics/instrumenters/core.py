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

log = logging.getLogger(__name__)

GALAXY_SLOTS_KEY = "galaxy_slots"
GALAXY_MEMORY_MB_KEY = "galaxy_memory_mb"
START_EPOCH_KEY = "start_epoch"
END_EPOCH_KEY = "end_epoch"
RUNTIME_SECONDS_KEY = "runtime_seconds"

ENERGY_NEEDED_MEMORY_KEY = "energy_needed_memory"
ENERGY_NEEDED_CPU_KEY = "energy_needed_cpu"


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
            return FormattedMetric(title, time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(value)))

    def __format_energy_needed_text(self, energy_needed_kwh: float) -> str:
        adjustedEnergyNeeded = energy_needed_kwh
        unit_magnitude = "kW⋅h"

        if energy_needed_kwh == 0:
            return "0 kW⋅h"

        if energy_needed_kwh >= 1e3:
            adjustedEnergyNeeded /= 1000
            unit_magnitude = "MW⋅h"
        elif energy_needed_kwh >= 1 and energy_needed_kwh <= 999:
            unit_magnitude = "W⋅h"
        elif energy_needed_kwh < 1 and energy_needed_kwh > 1e-4:
            adjustedEnergyNeeded *= 1000
            unit_magnitude = "mW⋅h"
        else:
            adjustedEnergyNeeded *= 1e6
            unit_magnitude = "µW⋅h"

        rounded_value = round(adjustedEnergyNeeded) == 0 and "< 1" or round(adjustedEnergyNeeded)
        return f"{rounded_value} {unit_magnitude}"


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
        galaxy_slots_file = self.__galaxy_slots_file(job_directory)
        galaxy_memory_mb_file = self.__galaxy_memory_mb_file(job_directory)

        properties: Dict[str, Any] = {}

        allocated_cpu_cores = self.__read_integer(galaxy_slots_file)
        properties[GALAXY_SLOTS_KEY] = allocated_cpu_cores

        allocated_memory_mebibyte = self.__read_integer(galaxy_memory_mb_file)
        properties[GALAXY_MEMORY_MB_KEY] = allocated_memory_mebibyte

        start_time_seconds = self.__read_seconds_since_epoch(job_directory, "start")
        end_time_seconds = self.__read_seconds_since_epoch(job_directory, "end")
        if start_time_seconds is not None and end_time_seconds is not None:
            properties[START_EPOCH_KEY] = start_time_seconds
            properties[END_EPOCH_KEY] = end_time_seconds

            runtime_seconds = end_time_seconds - start_time_seconds
            properties[RUNTIME_SECONDS_KEY] = end_time_seconds - start_time_seconds

            if allocated_cpu_cores is not None:
                tdp_per_ore = 115 / 10
                normalized_tdp_per_core = tdp_per_ore * allocated_cpu_cores

                memory_power_usage_constant = 0.3725
                memory_allocated_in_gibibyte = (allocated_memory_mebibyte or 0) / 1024  # Convert to gibibyte

                power_usage_effectiveness = 1.67

                runtime_hours = runtime_seconds / (60 * 60)  # Convert to hours

                power_needed_watts_cpu = power_usage_effectiveness * normalized_tdp_per_core
                power_needed_watts_memory = (
                    power_usage_effectiveness * memory_allocated_in_gibibyte * memory_power_usage_constant
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


__all__ = ("CorePlugin",)
