"""The module describes the ``hostname`` job metrics plugin."""

import logging

from . import InstrumentPlugin

log = logging.getLogger(__name__)


class HostnamePlugin(InstrumentPlugin):
    """Gather hostname"""

    plugin_type = "hostname"

    def __init__(self, **kwargs):
        pass

    def pre_execute_instrument(self, job_directory):
        return f"hostname -f > '{self.__instrument_hostname_path(job_directory)}'"

    def job_properties(self, job_id, job_directory):
        with open(self.__instrument_hostname_path(job_directory)) as f:
            return {"hostname": f.read().strip()}

    def __instrument_hostname_path(self, job_directory):
        return self._instrument_file_path(job_directory, "hostname")


__all__ = ("HostnamePlugin",)
