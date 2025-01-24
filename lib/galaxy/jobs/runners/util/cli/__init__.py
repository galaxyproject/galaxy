"""
"""

import json

from galaxy.util.plugin_config import plugins_dict

DEFAULT_SHELL_PLUGIN = "LocalShell"

ERROR_MESSAGE_NO_JOB_PLUGIN = "No job plugin parameter found, cannot create CLI job interface"
ERROR_MESSAGE_NO_SUCH_JOB_PLUGIN = "Failed to find job_plugin of type %s, available types include %s"


class CliInterface:
    """
    High-level interface for loading shell and job plugins and matching
    them to specified parameters.
    """

    def __init__(self):
        """ """
        module_prefix = self.__module__
        self.cli_shells = plugins_dict(f"{module_prefix}.shell", "__name__")
        self.cli_job_interfaces = plugins_dict(f"{module_prefix}.job", "__name__")
        self.active_cli_shells = {}

    def get_plugins(self, shell_params, job_params):
        """
        Return shell and job interface defined by and configured via
        specified params.
        """
        shell = self.get_shell_plugin(shell_params)
        job_interface = self.get_job_interface(job_params)
        return shell, job_interface

    def get_shell_plugin(self, shell_params):
        shell_plugin = shell_params.get("plugin", DEFAULT_SHELL_PLUGIN)
        requested_shell_settings = json.dumps(shell_params, sort_keys=True)
        if requested_shell_settings not in self.active_cli_shells:
            shell_plugin_class = self.cli_shells.get(shell_plugin)
            if not shell_plugin_class:
                raise ValueError(
                    f"Unknown shell_plugin [{shell_plugin}], available plugins are {list(self.cli_shells.keys())}"
                )
            self.active_cli_shells[requested_shell_settings] = shell_plugin_class(**shell_params)
        return self.active_cli_shells[requested_shell_settings]

    def get_job_interface(self, job_params):
        job_plugin = job_params.get("plugin")
        if not job_plugin:
            raise ValueError(ERROR_MESSAGE_NO_JOB_PLUGIN)
        job_plugin_class = self.cli_job_interfaces.get(job_plugin)
        if not job_plugin_class:
            raise ValueError(ERROR_MESSAGE_NO_SUCH_JOB_PLUGIN % (job_plugin, list(self.cli_job_interfaces.keys())))
        return job_plugin_class(**job_params)


def split_params(params):
    shell_params = {k.replace("shell_", "", 1): v for k, v in params.items() if k.startswith("shell_")}
    job_params = {k.replace("job_", "", 1): v for k, v in params.items() if k.startswith("job_")}
    return shell_params, job_params
