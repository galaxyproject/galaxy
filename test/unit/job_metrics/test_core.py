import subprocess

from galaxy.job_metrics.instrumenters.core import (
    CorePlugin,
    GALAXY_MEMORY_MB_KEY,
    GALAXY_SLOTS_KEY,
)
from galaxy.util import listify


def test_core_instrumentation(tmpdir):
    core_plugin = CorePlugin()
    env = {"GALAXY_SLOTS": "4", "GALAXY_MEMORY_MB": "1024"}
    _run_plugin(core_plugin, tmpdir, env)
    properties = core_plugin.job_properties(1, tmpdir)
    assert properties[GALAXY_SLOTS_KEY] == 4
    assert properties[GALAXY_MEMORY_MB_KEY] == 1024


def _run_plugin(plugin, work_dir, env=None):
    setup_commands = plugin.pre_execute_instrument(work_dir)
    teardown_commands = plugin.post_execute_instrument(work_dir)
    if setup_commands is not None:
        _run(setup_commands, work_dir, env)
    if teardown_commands is not None:
        _run(teardown_commands, work_dir, env)


def _run(commands, work_dir, env):
    command_str = "\n".join(listify(commands))
    return subprocess.run(command_str, shell=True, cwd=work_dir, env=env)
