import subprocess

from galaxy.job_metrics.instrumenters.core import (
    CorePlugin,
    GALAXY_MEMORY_MB_KEY,
    GALAXY_SLOTS_KEY,
)


def test_core_instrumentation(tmpdir):
    core_plugin = CorePlugin()
    setup_commands = core_plugin.pre_execute_instrument(tmpdir)
    teardown_commands = core_plugin.post_execute_instrument(tmpdir)
    env = {"GALAXY_SLOTS": "4", "GALAXY_MEMORY_MB": "1024"}
    _run(setup_commands, tmpdir, env)
    _run(teardown_commands, tmpdir, env)
    properties = core_plugin.job_properties(1, tmpdir)
    assert properties[GALAXY_SLOTS_KEY] == 4
    assert properties[GALAXY_MEMORY_MB_KEY] == 1024


def _run(commands, work_dir, env):
    return subprocess.run("\n".join(commands), shell=True, cwd=work_dir, env=env)
