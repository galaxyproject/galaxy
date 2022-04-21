"""The module describes the ``uname`` job metrics plugin."""
from . import InstrumentPlugin
from .. import formatting


class UnameFormatter(formatting.JobMetricFormatter):
    def format(self, key, value):
        return "Operating System", value


class UnamePlugin(InstrumentPlugin):
    """Use uname to gather operating system information about remote system
    job is running on. Linux only.
    """

    plugin_type = "uname"
    formatter = UnameFormatter()

    def __init__(self, **kwargs):
        self.uname_args = kwargs.get("args", "-a")

    def pre_execute_instrument(self, job_directory):
        return f"uname {self.uname_args} > '{self.__instrument_uname_path(job_directory)}'"

    def job_properties(self, job_id, job_directory):
        properties = {}
        with open(self.__instrument_uname_path(job_directory)) as f:
            properties["uname"] = f.read()
        return properties

    def __instrument_uname_path(self, job_directory):
        return self._instrument_file_path(job_directory, "uname")


__all__ = ("UnamePlugin",)
