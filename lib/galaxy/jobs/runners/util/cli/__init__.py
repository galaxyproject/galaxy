"""
"""
from glob import glob
from os.path import basename, join
from os import getcwd

DEFAULT_SHELL_PLUGIN = 'LocalShell'


class CliInterface(object):
    """
    High-level interface for loading shell and job plugins and matching
    them to specified parameters.
    """

    def __init__(self, code_dir='lib'):
        """
        """
        def __load(module_path, d):
            module_pattern = join(join(getcwd(), code_dir, *module_path.split('.')), '*.py')
            for file in glob(module_pattern):
                if basename(file).startswith('_'):
                    continue
                module_name = '%s.%s' % (module_path, basename(file).rsplit('.py', 1)[0])
                module = __import__(module_name)
                for comp in module_name.split(".")[1:]:
                    module = getattr(module, comp)
                for name in module.__all__:
                    try:
                        d[name] = getattr(module, name)
                    except TypeError:
                        raise TypeError("Invalid type for name %s" % name)

        self.cli_shells = {}
        self.cli_job_interfaces = {}

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
        shell = self.cli_shells[shell_plugin](**shell_params)
        return shell

    def get_job_interface(self, job_params):
        job_plugin = job_params['plugin']
        job_interface = self.cli_job_interfaces[job_plugin](**job_params)
        return job_interface


def split_params(params):
    shell_params = dict((k.replace('shell_', '', 1), v) for k, v in params.items() if k.startswith('shell_'))
    job_params = dict((k.replace('job_', '', 1), v) for k, v in params.items() if k.startswith('job_'))
    return shell_params, job_params
