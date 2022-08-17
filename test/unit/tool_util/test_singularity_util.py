from galaxy.tool_util.deps.singularity_util import build_singularity_run_command


def test_build_singularity_run_command_defaults():
    cmd = build_singularity_run_command(
        container_command="echo hi",
        image="busybox",
    )
    assert cmd == "singularity -s exec --cleanenv busybox echo hi"


def test_build_singularity_run_command_no_cleanenv():
    cmd = build_singularity_run_command(
        container_command="echo hi",
        image="busybox",
        cleanenv=False,
    )
    assert cmd == "singularity -s exec busybox echo hi"
