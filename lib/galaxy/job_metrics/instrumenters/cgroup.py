"""The module describes the ``cgroup`` job metrics plugin."""
import logging
import numbers
from collections import namedtuple
from typing import (
    Any,
    Dict,
    List,
)

from galaxy.util import (
    asbool,
    nice_size,
)
from . import InstrumentPlugin
from .. import formatting

log = logging.getLogger(__name__)

TITLES = {
    "memory.memsw.max_usage_in_bytes": "Max memory usage (MEM+SWP)",
    "memory.max_usage_in_bytes": "Max memory usage (MEM)",
    "memory.limit_in_bytes": "Memory limit on cgroup (MEM)",
    "memory.memsw.limit_in_bytes": "Memory limit on cgroup (MEM+SWP)",
    "memory.soft_limit_in_bytes": "Memory softlimit on cgroup",
    "memory.failcnt": "Failed to allocate memory count",
    "memory.oom_control.oom_kill_disable": "OOM Control enabled",
    "memory.oom_control.under_oom": "Was OOM Killer active?",
    "cpuacct.usage": "CPU Time",
}
CONVERSION = {
    "memory.oom_control.oom_kill_disable": lambda x: "No" if x == 1 else "Yes",
    "memory.oom_control.under_oom": lambda x: "Yes" if x == 1 else "No",
    "cpuacct.usage": lambda x: formatting.seconds_to_str(x / 10**9),  # convert nanoseconds
}
CPU_USAGE_TEMPLATE = r"""
if [ -e "/proc/$$/cgroup" -a -d "{cgroup_mount}" ]; then
    cgroup_path=$(cat "/proc/$$/cgroup" | awk -F':' '($2=="cpuacct,cpu") || ($2=="cpu,cpuacct") {{print $3}}');
    if [ ! -e "{cgroup_mount}/cpu$cgroup_path/cpuacct.usage" ]; then
        cgroup_path="";
    fi;
    for f in {cgroup_mount}/{{cpu\,cpuacct,cpuacct\,cpu}}$cgroup_path/{{cpu,cpuacct}}.*; do
        if [ -f "$f" ]; then
            echo "__$(basename $f)__" >> {metrics}; cat "$f" >> {metrics} 2>/dev/null;
        fi;
    done;
fi
""".replace(
    "\n", " "
).strip()
MEMORY_USAGE_TEMPLATE = """
if [ -e "/proc/$$/cgroup" -a -d "{cgroup_mount}" ]; then
    cgroup_path=$(cat "/proc/$$/cgroup" | awk -F':' '$2=="memory"{{print $3}}');
    if [ ! -e "{cgroup_mount}/memory$cgroup_path/memory.max_usage_in_bytes" ]; then
        cgroup_path="";
    fi;
    for f in {cgroup_mount}/memory$cgroup_path/memory.*; do
        echo "__$(basename $f)__" >> {metrics}; cat "$f" >> {metrics} 2>/dev/null;
    done;
fi
""".replace(
    "\n", " "
).strip()


Metric = namedtuple("Metric", ("key", "subkey", "value"))


class CgroupPluginFormatter(formatting.JobMetricFormatter):
    def format(self, key, value):
        title = TITLES.get(key, key)
        if key in CONVERSION:
            return title, CONVERSION[key](value)
        elif key.endswith("_bytes"):
            try:
                return title, nice_size(value)
            except ValueError:
                pass
        elif isinstance(value, (numbers.Integral, numbers.Real)) and value == int(value):
            value = int(value)
        return title, value


class CgroupPlugin(InstrumentPlugin):
    """Plugin that collects memory and cpu utilization from within a cgroup."""

    plugin_type = "cgroup"
    formatter = CgroupPluginFormatter()

    def __init__(self, **kwargs):
        self.verbose = asbool(kwargs.get("verbose", False))
        self.cgroup_mount = kwargs.get("cgroup_mount", "/sys/fs/cgroup")
        params_str = kwargs.get("params", None)
        if params_str:
            params = [v.strip() for v in params_str.split(",")]
        else:
            params = list(TITLES.keys())
        self.params = params

    def post_execute_instrument(self, job_directory: str) -> List[str]:
        commands: List[str] = []
        commands.append(self.__record_cgroup_cpu_usage(job_directory))
        commands.append(self.__record_cgroup_memory_usage(job_directory))
        return commands

    def job_properties(self, job_id, job_directory: str) -> Dict[str, Any]:
        metrics = self.__read_metrics(self.__cgroup_metrics_file(job_directory))
        return metrics

    def __record_cgroup_cpu_usage(self, job_directory: str) -> str:
        # comounted cgroups (which cpu and cpuacct are on the supported Linux distros) can appear in any order (cpu,cpuacct or cpuacct,cpu)
        return CPU_USAGE_TEMPLATE.format(
            metrics=self.__cgroup_metrics_file(job_directory), cgroup_mount=self.cgroup_mount
        )

    def __record_cgroup_memory_usage(self, job_directory: str) -> str:
        return MEMORY_USAGE_TEMPLATE.format(
            metrics=self.__cgroup_metrics_file(job_directory), cgroup_mount=self.cgroup_mount
        )

    def __cgroup_metrics_file(self, job_directory):
        return self._instrument_file_path(job_directory, "_metrics")

    def __read_metrics(self, path):
        metrics: Dict[str, str] = {}
        key = None
        with open(path) as infile:
            for line in infile:
                try:
                    metric, key = self.__read_key_value(line.strip(), key)
                except Exception:
                    log.exception("Caught exception attempting to read metric from cgroup line: %s", line)
                    metric = None
                if not metric:
                    continue
                self.__add_metric(metrics, metric)
        return metrics

    def __add_metric(self, metrics, metric):
        if metric and (metric.subkey in self.params or self.verbose):
            metrics[metric.subkey] = metric.value

    def __read_key_value(self, line, key):
        if line.startswith("__") and line.endswith("__"):
            # line is the beginning of a new param
            key = line[2:][:-2]
            return (None, key)
        elif line.count(" ") == 1:
            # line has a subkey
            subkey, value = line.split(" ", 1)
            subkey = ".".join((key, subkey))
        else:
            # line does not have a subkey
            subkey = key
            value = line
        value = self.__type_value(value)
        return (Metric(key, subkey, value), key)

    def __type_value(self, value):
        try:
            try:
                return int(value)
            except ValueError:
                return float(value)
        except ValueError:
            return value


__all__ = ("CgroupPlugin",)
