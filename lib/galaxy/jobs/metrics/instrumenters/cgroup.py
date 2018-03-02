"""The module describes the ``cgroup`` job metrics plugin."""
import logging

from galaxy.util import asbool, nice_size
from ..instrumenters import InstrumentPlugin
from ...metrics import formatting

log = logging.getLogger(__name__)

TITLES = {
    "memory.memsw.max_usage_in_bytes": "Max memory usage (MEM+SWP)",
    "memory.max_usage_in_bytes": "Max memory usage (MEM)",
    "memory.limit_in_bytes": "Memory limit on cgroup (MEM)",
    "memory.memsw.limit_in_bytes": "Memory limit on cgroup (MEM+SWP)",
    "memory.soft_limit_in_bytes": "Memory softlimit on cgroup",
    "memory.failcnt": "Failed to allocate memory count",
    "memory.oom_control": "OOM Control enabled",
    "under_oom": "Was OOM Killer active?",
    "cpuacct.usage": "CPU Time"
}
CONVERSION = {
    "memory.memsw.max_usage_in_bytes": nice_size,
    "memory.max_usage_in_bytes": nice_size,
    "memory.limit_in_bytes": nice_size,
    "memory.memsw.limit_in_bytes": nice_size,
    "memory.soft_limit_in_bytes": nice_size,
    "under_oom": lambda x: "Yes" if x == "1" else "No",
    "cpuacct.usage": lambda x: formatting.seconds_to_str(int(x) / 10**9)  # convert nanoseconds
}


class CgroupPluginFormatter(formatting.JobMetricFormatter):

    def format(self, key, value):
        title = TITLES.get(key, key)
        if key in CONVERSION:
            return title, CONVERSION[key](value)
        elif key.endswith("_bytes"):
            try:
                return title, nice_size(key)
            except ValueError:
                pass
        return title, value


class CgroupPlugin(InstrumentPlugin):
    """ Plugin that collects memory and cpu utilization from within a cgroup.
    """
    plugin_type = "cgroup"
    formatter = CgroupPluginFormatter()

    def __init__(self, **kwargs):
        self.verbose = asbool(kwargs.get("verbose", False))

    def post_execute_instrument(self, job_directory):
        commands = []
        commands.append(self.__record_cgroup_cpu_usage(job_directory))
        commands.append(self.__record_cgroup_memory_usage(job_directory))
        return commands

    def job_properties(self, job_id, job_directory):
        metrics = self.__read_metrics(self.__cgroup_metrics_file(job_directory))
        return metrics

    def __record_cgroup_cpu_usage(self, job_directory):
        return """if [ `command -v cgget` ] && [ -e /proc/$$/cgroup ]; then cat /proc/$$/cgroup | awk -F':' '$2=="cpuacct,cpu"{print $2":"$3}' | xargs -I{} cgget -g {} > %(metrics)s ; else echo "" > %(metrics)s; fi""" % {"metrics": self.__cgroup_metrics_file(job_directory)}

    def __record_cgroup_memory_usage(self, job_directory):
        return """if [ `command -v cgget` ] && [ -e /proc/$$/cgroup ]; then cat /proc/$$/cgroup | awk -F':' '$2=="memory"{print $2":"$3}' | xargs -I{} cgget -g {} >> %(metrics)s ; else echo "" > %(metrics)s; fi""" % {"metrics": self.__cgroup_metrics_file(job_directory)}

    def __cgroup_metrics_file(self, job_directory):
        return self._instrument_file_path(job_directory, "_metrics")

    def __read_metrics(self, path):
        metrics = {}
        with open(path, "r") as infile:
            for line in infile:
                line = line.strip()
                try:
                    key, value = line.split(": ")
                    if key in TITLES or self.verbose:
                        metrics[key] = value
                except ValueError:
                    if line.startswith("under_oom"):
                        metrics["under_oom"] = line.split(" ")[1]
        return metrics


__all__ = ('CgroupPlugin', )
