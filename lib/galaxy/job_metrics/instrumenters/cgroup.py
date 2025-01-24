"""The module describes the ``cgroup`` job metrics plugin."""

import logging
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

VALID_VERSIONS = ("auto", "1", "2")
DEFAULT_PARAMS = (
    # cgroupsv1 - this is probably more params than are useful to collect, but don't remove any for legacy reasons
    "memory.memsw.max_usage_in_bytes",
    "memory.max_usage_in_bytes",
    "memory.limit_in_bytes",
    "memory.memsw.limit_in_bytes",
    "memory.soft_limit_in_bytes",
    "memory.failcnt",
    "memory.oom_control.oom_kill_disable",
    "memory.oom_control.under_oom",
    "cpuacct.usage",
    # cgroupsv2
    "memory.events.oom_kill",
    "memory.peak",
    "cpu.stat.system_usec",
    "cpu.stat.usage_usec",
    "cpu.stat.user_usec",
)
TITLES = {
    # cgroupsv1
    "memory.memsw.max_usage_in_bytes": "Max memory usage (MEM+SWP)",
    "memory.max_usage_in_bytes": "Max memory usage (MEM)",
    "memory.limit_in_bytes": "Memory limit on cgroup (MEM)",
    "memory.memsw.limit_in_bytes": "Memory limit on cgroup (MEM+SWP)",
    "memory.soft_limit_in_bytes": "Memory softlimit on cgroup",
    "memory.failcnt": "Failed to allocate memory count",
    "memory.oom_control.oom_kill_disable": "OOM Control enabled",
    "memory.oom_control.under_oom": "Was OOM Killer active?",
    "cpuacct.usage": "CPU Time",
    # cgroupsv2
    "memory.events.low": "Number of times the cgroup was reclaimed due to high memory pressure even though its usage is under the low "
    "boundary",
    "memory.events.high": "Number of times processes of the cgroup were throttled and routed to perform direct memory reclaim because "
    "the high memory boundary was exceeded",
    "memory.events.max": "Number of times the cgroup's memory usage was about to go over the max boundary",
    "memory.events.oom": "Number of time the cgroup's memory usage reached the limit and allocation was about to fail",
    "memory.events.oom_kill": "Number of processes belonging to this cgroup killed by any kind of OOM killer",
    "memory.events.oom_group_kill": "Number of times a group OOM has occurred",
    "memory.high": "Memory usage throttle limit",
    "memory.low": "Best-effort memory protection",
    "memory.max": "Memory usage hard limit",
    "memory.min": "Hard memory protection",
    "memory.peak": "Max memory usage recorded",
    "cpu.stat.system_usec": "CPU system time",
    "cpu.stat.usage_usec": "CPU usage time",
    "cpu.stat.user_usec": "CPU user time",
}
CONVERSION = {
    "memory.oom_control.oom_kill_disable": lambda x: "No" if x == 1 else "Yes",
    "memory.oom_control.under_oom": lambda x: "Yes" if x == 1 else "No",
    "memory.peak": lambda x: nice_size(x),
    "cpuacct.usage": lambda x: formatting.seconds_to_str(x / 10**9),  # convert nanoseconds
    "cpu.stat.system_usec": lambda x: formatting.seconds_to_str(x / 10**6),  # convert microseconds
    "cpu.stat.usage_usec": lambda x: formatting.seconds_to_str(x / 10**6),  # convert microseconds
    "cpu.stat.user_usec": lambda x: formatting.seconds_to_str(x / 10**6),  # convert microseconds
}
CGROUPSV1_TEMPLATE = r"""
if [ -e "/proc/$$/cgroup" -a -d "{cgroup_mount}" -a ! -f "{cgroup_mount}/cgroup.controllers" ]; then
    cgroup_path=$(cat "/proc/$$/cgroup" | awk -F':' '($2=="cpuacct,cpu") || ($2=="cpu,cpuacct") {{print $3}}');
    if [ ! -e "{cgroup_mount}/cpu$cgroup_path/cpuacct.usage" ]; then
        cgroup_path="";
    fi;
    for f in {cgroup_mount}/{{cpu\,cpuacct,cpuacct\,cpu}}$cgroup_path/{{cpu,cpuacct}}.*; do
        if [ -f "$f" ]; then
            echo "__$(basename $f)__" >> {metrics}; cat "$f" >> {metrics} 2>/dev/null;
        fi;
    done;
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
CGROUPSV2_TEMPLATE = r"""
if [ -e "/proc/$$/cgroup" -a -f "{cgroup_mount}/cgroup.controllers" ]; then
    cgroup_path=$(cat "/proc/$$/cgroup" | awk -F':' '($1=="0") {{print $3}}');
    for f in {cgroup_mount}/${{cgroup_path}}/{{cpu,memory}}.*; do
        echo "__$(basename $f)__" >> {metrics}; cat "$f" >> {metrics} 2>/dev/null;
    done;
fi
""".replace(
    "\n", " "
).strip()


Metric = namedtuple("Metric", ("key", "subkey", "value"))


class CgroupPluginFormatter(formatting.JobMetricFormatter):
    def format(self, key: str, value: Any) -> formatting.FormattedMetric:
        title = TITLES.get(key, key)
        if key in CONVERSION:
            return formatting.FormattedMetric(title, CONVERSION[key](value))
        elif key.endswith("_bytes"):
            try:
                return formatting.FormattedMetric(title, nice_size(value))
            except ValueError:
                pass
        else:
            try:
                int_value = int(value)
                if value == int_value:
                    value = int_value
            except TypeError:
                pass
        return formatting.FormattedMetric(title, str(value))


class CgroupPlugin(InstrumentPlugin):
    """Plugin that collects memory and cpu utilization from within a cgroup."""

    plugin_type = "cgroup"
    formatter = CgroupPluginFormatter()

    def __init__(self, **kwargs):
        self.verbose = asbool(kwargs.get("verbose", False))
        self.cgroup_mount = kwargs.get("cgroup_mount", "/sys/fs/cgroup")
        self.version = str(kwargs.get("version", "auto"))
        assert self.version in VALID_VERSIONS, f"cgroup metric version option must be one of {VALID_VERSIONS}"
        params_str = kwargs.get("params", None)
        if isinstance(params_str, list):
            params = params_str
        elif params_str:
            params = [v.strip() for v in params_str.split(",")]
        else:
            params = list(DEFAULT_PARAMS)
        self.params = params

    def post_execute_instrument(self, job_directory: str) -> List[str]:
        commands: List[str] = []
        if self.version in ("auto", "1"):
            commands.append(self.__record_cgroup_v1_usage(job_directory))
        if self.version in ("auto", "2"):
            commands.append(self.__record_cgroup_v2_usage(job_directory))
        return commands

    def job_properties(self, job_id, job_directory: str) -> Dict[str, Any]:
        metrics = self.__read_metrics(self.__cgroup_metrics_file(job_directory))
        return metrics

    def __record_cgroup_v1_usage(self, job_directory: str) -> str:
        return CGROUPSV1_TEMPLATE.format(
            metrics=self.__cgroup_metrics_file(job_directory), cgroup_mount=self.cgroup_mount
        )

    def __record_cgroup_v2_usage(self, job_directory: str) -> str:
        return CGROUPSV2_TEMPLATE.format(
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
