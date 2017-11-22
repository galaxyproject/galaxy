"""The module describes the ``cpuinfo`` job metrics plugin."""
import logging
import re

from galaxy import util
from ..instrumenters import InstrumentPlugin
from ...metrics import formatting

log = logging.getLogger(__name__)

PROCESSOR_LINE = re.compile(r"processor\s*\:\s*(\d+)")


class CpuInfoFormatter(formatting.JobMetricFormatter):

    def format(self, key, value):
        if key == "processor_count":
            return "Processor Count", "%s" % int(value)
        else:
            return key, value


class CpuInfoPlugin(InstrumentPlugin):
    """ Gather information about processor configuration from /proc/cpuinfo.
    Linux only.
    """
    plugin_type = "cpuinfo"
    formatter = CpuInfoFormatter()

    def __init__(self, **kwargs):
        self.verbose = util.asbool(kwargs.get("verbose", False))

    def pre_execute_instrument(self, job_directory):
        return "cat /proc/cpuinfo > '%s'" % self.__instrument_cpuinfo_path(job_directory)

    def job_properties(self, job_id, job_directory):
        properties = {}
        processor_count = 0
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
                    key, value = line.split(":", 1)
                    key = "processor_%s_%s" % (current_processor, key.strip())
                    value = value
        properties["processor_count"] = processor_count
        return properties

    def __instrument_cpuinfo_path(self, job_directory):
        return self._instrument_file_path(job_directory, "cpuinfo")


__all__ = ('CpuInfoPlugin', )
