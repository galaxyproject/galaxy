try:
    from galaxy.jobs.runners.util.cli import (
        CliInterface,
        split_params
    )
    code_dir = 'lib'
except ImportError:
    from pulsar.managers.util.cli import (
        CliInterface,
        split_params
    )
    code_dir = '.'


def get_shell(params):
    cli_interface = CliInterface(code_dir=code_dir)
    shell_params, _ = split_params(params)
    return cli_interface.get_shell_plugin(shell_params)
