"""
"""
import importlib
import json
import pkgutil
from glob import glob
from os import getcwd
from os.path import (
    basename,
    join
)

DEFAULT_SHELL_PLUGIN = 'LocalShell'

ERROR_MESSAGE_NO_JOB_PLUGIN = "No job plugin parameter found, cannot create CLI job interface"
ERROR_MESSAGE_NO_SUCH_JOB_PLUGIN = "Failed to find job_plugin of type %s, available types include %s"


class CliInterface:
    """
    High-level interface for loading shell and job plugins and matching
    them to specified parameters.
    """

    def __init__(self, code_dir='lib'):
        """
        """
        def __load_from_code_dir(module_path):
            module_pattern = join(join(getcwd(), code_dir, *module_path.split('.')), '*.py')
            for file in glob(module_pattern):
                if basename(file).startswith('_'):
                    continue
                module_name = '{}.{}'.format(module_path, basename(file).rsplit('.py', 1)[0])
                module = __import__(module_name)
                for comp in module_name.split(".")[1:]:
                    module = getattr(module, comp)
                yield module

        def __load_from_path(module_path):
            base_module = importlib.import_module(module_path)
            for module_info in pkgutil.iter_modules(base_module.__path__):
                module = importlib.import_module('{}.{}'.format(module_path, module_info.name))
                yield module

        def __load(module_path, d):
            if code_dir is not None:
                module_generator = __load_from_code_dir
            else:
                module_generator = __load_from_path
            for module in module_generator(module_path):
                for name in module.__all__:
                    try:
                        d[name] = getattr(module, name)
                    except TypeError:
                        raise TypeError("Invalid type for name %s" % name)

        self.cli_shells = {}
        self.cli_job_interfaces = {}
        self.active_cli_shells = {}

        module_prefix = self.__module__
        __load('%s.shell' % module_prefix, self.cli_shells)
        __load('%s.job' % module_prefix, self.cli_job_interfaces)

    def get_plugins(self, shell_params, job_params):
        """
        Return shell and job interface defined by and configured via
        specified params.
        """
        shell = self.get_shell_plugin(shell_params)
        job_interface = self.get_job_interface(job_params)
        return shell, job_interface

    def get_shell_plugin(self, shell_params):
        shell_plugin = shell_params.get('plugin', DEFAULT_SHELL_PLUGIN)
        requested_shell_settings = json.dumps(shell_params, sort_keys=True)
        if requested_shell_settings not in self.active_cli_shells:
            self.active_cli_shells[requested_shell_settings] = self.cli_shells[shell_plugin](**shell_params)
        return self.active_cli_shells[requested_shell_settings]

    def get_job_interface(self, job_params):
        job_plugin = job_params.get('plugin', None)
        if not job_plugin:
            raise ValueError(ERROR_MESSAGE_NO_JOB_PLUGIN)
        job_plugin_class = self.cli_job_interfaces.get(job_plugin, None)
        if not job_plugin_class:
            raise ValueError(ERROR_MESSAGE_NO_SUCH_JOB_PLUGIN % (job_plugin, list(self.cli_job_interfaces.keys())))
        job_interface = job_plugin_class(**job_params)

        return job_interface


def split_params(params):
    shell_params = {k.replace('shell_', '', 1): v for k, v in params.items() if k.startswith('shell_')}
    job_params = {k.replace('job_', '', 1): v for k, v in params.items() if k.startswith('job_')}
    return shell_params, job_params
