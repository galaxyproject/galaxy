import sys

from galaxy.jobs.runners.util.cli.shell.local import LocalShell


def test_local_shell_preserves_nonzero_exit_status():
    result = LocalShell().execute(
        [sys.executable, "-c", "import sys; print('result'); sys.stderr.write('diagnostic'); sys.exit(3)"],
        timeout_check_interval=0.01,
    )
    assert result.returncode == 3
    assert result.stdout == "result\n"
    assert result.stderr == "diagnostic"
