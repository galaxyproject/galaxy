import logging
import subprocess
from types import SimpleNamespace

import pytest

from galaxy.job_metrics.instrumenters.core import (
    CorePlugin,
    GALAXY_MEMORY_MB_KEY,
    GALAXY_SLOTS_KEY,
    PLATFORM_KEY,
)
from galaxy.jobs import MinimalJobWrapper
from galaxy.util import listify


def test_core_instrumentation(tmpdir):
    core_plugin = CorePlugin()
    env = {"GALAXY_SLOTS": "4", "GALAXY_MEMORY_MB": "1024"}
    _run_plugin(core_plugin, tmpdir, env)
    properties = core_plugin.job_properties(1, tmpdir)
    assert properties[GALAXY_SLOTS_KEY] == 4
    assert properties[GALAXY_MEMORY_MB_KEY] == 1024


def test_platform_recorded_on_this_node(tmpdir):
    core_plugin = CorePlugin()
    _run_plugin(core_plugin, tmpdir, {"GALAXY_SLOTS": "1", "GALAXY_MEMORY_MB": "1", "PATH": "/usr/bin:/bin"})
    platform = core_plugin.job_properties(1, tmpdir)[PLATFORM_KEY]
    assert platform.split("-")[0] in ("linux", "osx", "freebsd")


@pytest.mark.parametrize(
    "uname,expected",
    [
        ("Linux x86_64", "linux-64"),
        ("Linux aarch64", "linux-aarch64"),
        ("Linux arm64", "linux-aarch64"),
        ("Linux ppc64le", "linux-ppc64le"),
        ("Linux riscv64", "linux-riscv64"),
        ("Linux s390x", "linux-s390x"),
        ("Darwin x86_64", "osx-64"),
        ("Darwin arm64", "osx-arm64"),
        ("FreeBSD amd64", "freebsd-64"),
        ("SunOS i86pc", "sunos-i86pc"),
    ],
)
def test_platform_mapping(tmpdir, uname, expected):
    core_plugin = CorePlugin()
    (tmpdir / "__instrument_core_platform").write(uname + "\n")
    assert core_plugin.job_properties(1, str(tmpdir))[PLATFORM_KEY] == expected


def test_platform_missing_file(tmpdir):
    assert PLATFORM_KEY not in CorePlugin().job_properties(1, str(tmpdir))


def _collect(metrics, requested, caplog):
    wrapper = SimpleNamespace(
        job_id=7,
        platform=requested,
        working_directory="/nonexistent",
        app=SimpleNamespace(job_metrics=SimpleNamespace(collect_properties=lambda *a: metrics)),
    )
    has_metrics = SimpleNamespace(
        get_job=lambda: SimpleNamespace(destination_id="aarch64_dest"), add_metric=lambda *a: None
    )
    with caplog.at_level(logging.WARNING, logger="galaxy.jobs"):
        MinimalJobWrapper._collect_metrics(wrapper, has_metrics)


def test_platform_mismatch_warns(caplog):
    _collect({"core": {"platform": "linux-64"}}, "linux-aarch64", caplog)
    assert "Job 7 ran on platform linux-64" in caplog.text
    assert "aarch64_dest" in caplog.text and "linux-aarch64" in caplog.text


def test_platform_match_or_unset_is_quiet(caplog):
    _collect({"core": {"platform": "linux-64"}}, "linux-64", caplog)
    _collect({"core": {"platform": "linux-64"}}, None, caplog)
    _collect({"core": {}}, "linux-64", caplog)
    assert caplog.text == ""


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
