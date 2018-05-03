"""The module describes the ``cgroup`` job metrics plugin."""
import logging
from collections import namedtuple

from ..instrumenters import InstrumentPlugin
from ...metrics import formatting

log = logging.getLogger(__name__)


COLLECT_SCRIPT = """#!/bin/sh

interval="${1:-30}"

if [ ! -e /proc/$PPID/cgroup ]; then
    echo 'No /proc/$PPID/cgroup, are cgroups available on this system?' 1>&2
    exit 1
fi

cpuacct_mount=$(mount -t cgroup | awk '$NF ~ /,cpuacct/ {print $3}')
memory_mount=$(mount -t cgroup | awk '$NF ~ /,memory/ {print $3}')
cpuacct_dir=$(awk -F':' ' $2 ~ /^(cpu,cpuacct|cpuacct,cpu)$/ {print $3}' /proc/$PPID/cgroup)
memory_dir=$(awk -F':' ' $2 == "memory" {print $3}' /proc/$PPID/cgroup)
cpu_usage_path="$cpuacct_mount$cpuacct_dir/cpuacct.usage"
mem_usage_path="$memory_mount$memory_dir/memory.memsw.usage_in_bytes"

paths=''
[ -n "$cpuacct_mount" -a -n "$cpuacct_dir" -a -f "$cpu_usage_path" ] && paths="$paths $cpu_usage_path"
[ -n "$memory_mount" -a -n "$memory_dir" -a -f "$mem_usage_path" ] && paths="$paths $mem_usage_path"
paths="$(echo $paths | sed 's/^ //')"

if [ -z "$paths" ]; then
    echo 'Could not determine paths for any cgroup params to read' 2>&1
    exit 1
fi

header="#time"
for path in $paths; do
    header="$header $(basename $path)"
done
echo "$header"

while : ; do
    echo "$(date --utc +%s) $(cat $paths | xargs echo)"
    sleep $interval
done
"""

Metric = namedtuple("Metric", ("key", "subkey", "value"))


class CgroupTimeSeriesPluginFormatter(formatting.JobMetricFormatter):

    def format(self, key, value):
        assert key == 'data_file'
        return "Has time series data?", "Yes"


class CgroupTimeSeriesPlugin(InstrumentPlugin):
    """ Plugin that collects memory and cpu utilization from within a cgroup.
    """
    plugin_type = "cgroup_time_series"
    formatter = CgroupTimeSeriesPluginFormatter()

    def __init__(self, **kwargs):
        self.interval = int(kwargs.get("interval", 30))

    def pre_execute_instrument(self, job_directory):
        self.__write_script(job_directory)
        return [
            """sh {script} {interval} > {data} 2> {log} & __GALAXY_CGROUP_TIME_SERIES_PID=$!""".format(
                script=self._instrument_file_path(job_directory, "script"),
                data=self._instrument_file_path(job_directory, "data"),
                log=self._instrument_file_path(job_directory, "log"),
                interval=self.interval,
            )
        ]

    def post_execute_instrument(self, job_directory):
        return [
            """kill $__GALAXY_CGROUP_TIME_SERIES_PID 2>> {log}""".format(log=self._instrument_file_path(job_directory, "log")),
        ]

    def job_properties(self, job_id, job_directory):
        metrics = {}
        with open(self._instrument_file_path(job_directory, "data")) as fh:
            head = fh.next()
            assert head.startswith("#time "), "Invalid header: %s" % head
        metrics['data_file'] = open(self._instrument_file_path(job_directory, "data"))
        return metrics

    def __write_script(self, job_directory):
        with open(self._instrument_file_path(job_directory, "script"), 'w') as fh:
            fh.write(COLLECT_SCRIPT)


__all__ = ('CgroupTimeSeriesPlugin', )
