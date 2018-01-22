"""The module describes the ``meminfo`` job metrics plugin."""
import re
import sys

from galaxy import util
from ..instrumenters import InstrumentPlugin
from ...metrics import formatting

if sys.version_info > (3,):
    long = int


MEMINFO_LINE = re.compile(r"(\w+)\s*\:\s*(\d+) kB")

# Important (non-verbose) meminfo property titles.
MEMINFO_TITLES = {
    "memtotal": "Total System Memory",
    "swaptotal": "Total System Swap"
}


class MemInfoFormatter(formatting.JobMetricFormatter):

    def format(self, key, value):
        title = MEMINFO_TITLES.get(key, key)
        return title, util.nice_size(value * 1000)  # kB = *1000, KB = *1024 - wikipedia


class MemInfoPlugin(InstrumentPlugin):
    """ Gather information about processor configuration from /proc/cpuinfo.
    Linux only.
    """
    plugin_type = "meminfo"
    formatter = MemInfoFormatter()

    def __init__(self, **kwargs):
        self.verbose = util.asbool(kwargs.get("verbose", False))

    def pre_execute_instrument(self, job_directory):
        return "cat /proc/meminfo > '%s'" % self.__instrument_meminfo_path(job_directory)

    def job_properties(self, job_id, job_directory):
        properties = {}
        with open(self.__instrument_meminfo_path(job_directory)) as f:
            for line in f:
                line = line.strip()
                if not line:  # Skip empty lines
                    continue
                line_match = MEMINFO_LINE.match(line)
                if not line_match:
                    continue
                key = line_match.group(1).lower()
                # By default just grab important meminfo properties with titles
                # defined for formatter. Grab everything in verbose mode for
                # an arbitrary snapshot of memory at beginning of run.
                if key in MEMINFO_TITLES or self.verbose:
                    value = long(line_match.group(2))
                    properties[key] = value
        return properties

    def __instrument_meminfo_path(self, job_directory):
        return self._instrument_file_path(job_directory, "meminfo")


__all__ = ('MemInfoPlugin', )
