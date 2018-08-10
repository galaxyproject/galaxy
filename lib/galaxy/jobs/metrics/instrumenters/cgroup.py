"""The module describes the ``cgroup`` job metrics plugin."""
import logging
import numbers
from collections import namedtuple

from galaxy.util import asbool, nice_size
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
    "cpuacct.usage": "CPU Time"
}
CONVERSION = {
    "memory.oom_control.oom_kill_disable": lambda x: "No" if x == 1 else "Yes",
    "memory.oom_control.under_oom": lambda x: "Yes" if x == 1 else "No",
    "cpuacct.usage": lambda x: formatting.seconds_to_str(x / 10**9)  # convert nanoseconds
}


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
        elif isinstance(value, numbers.Number) and value == int(value):
            value = int(value)
        return title, value


class CgroupPlugin(InstrumentPlugin):
    """ Plugin that collects memory and cpu utilization from within a cgroup.
    """
    plugin_type = "cgroup"
    formatter = CgroupPluginFormatter()

    def __init__(self, **kwargs):
        self.verbose = asbool(kwargs.get("verbose", False))
        params_str = kwargs.get("params", None)
        if params_str:
            params = [v.strip() for v in params_str.split(",")]
        else:
            params = TITLES.keys()
        self.params = params

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
        prev_metric = None
        with open(path, "r") as infile:
            for line in infile:
                try:
                    metric, prev_metric = self.__read_key_value(line, prev_metric)
                except Exception:
                    log.exception("Caught exception attempting to read metric from cgroup line: %s", line)
                    metric = None
                if not metric:
                    continue
                self.__add_metric(metrics, prev_metric)
                prev_metric = metric
        self.__add_metric(metrics, prev_metric)
        return metrics

    def __add_metric(self, metrics, metric):
        if metric and (metric.subkey in self.params or self.verbose):
            metrics[metric.subkey] = metric.value

    def __read_key_value(self, line, prev_metric):
        if not line.startswith('\t'):
            # line is a single-line param or the first line of a multi-line param
            try:
                subkey, value = line.strip().split(": ", 1)
                key = subkey
            except ValueError:
                # or not a param line at all, ignore
                return None, prev_metric
        else:
            # line is a subsequent line of a multi-line param
            subkey, value = line.strip().split(" ", 1)
            key = prev_metric.key
            subkey = ".".join((key, subkey))
            prev_metric = self.__fix_prev_metric(prev_metric)
        value = self.__type_value(value)
        return (Metric(key, subkey, value), prev_metric)

    def __fix_prev_metric(self, metric):
        # we can't determine whether a param is single-line or multi-line until we read the second line, after which, we
        # must go back and fix the first param to be subkeyed
        if metric.key == metric.subkey:
            try:
                subkey, value = metric.value.split(" ", 1)
                subkey = ".".join((metric.key, subkey))
                metric = Metric(metric.key, subkey, self.__type_value(value))
            except ValueError:
                pass
        return metric

    def __type_value(self, value):
        try:
            try:
                return int(value)
            except ValueError:
                return float(value)
        except ValueError:
            return value


__all__ = ('CgroupPlugin', )
