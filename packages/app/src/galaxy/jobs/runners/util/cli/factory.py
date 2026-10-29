try:
    from galaxy.jobs.runners.util.cli import (
        CliInterface,
        split_params,
    )
except ImportError:
    from pulsar.managers.util.cli import (  # type: ignore[no-redef]
        CliInterface,
        split_params,
    )


def build_cli_interface():
    return CliInterface()


def get_shell(params):
    cli_interface = build_cli_interface()
    shell_params, _ = split_params(params)
    return cli_interface.get_shell_plugin(shell_params)
