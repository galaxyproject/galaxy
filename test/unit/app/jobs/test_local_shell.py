import sys

import pytest

from galaxy.jobs.runners.util.cli.shell.local import (
    LocalShell,
    TIMEOUT_RETURN_CODE,
)


@pytest.mark.parametrize("returncode", [0, 3])
def test_local_shell_preserves_owned_process_exit_status(returncode):
    result = LocalShell().execute(
        [sys.executable, "-c", f"import sys; print('result'); sys.stderr.write('diagnostic'); sys.exit({returncode})"],
        timeout_check_interval=0.01,
    )
    assert result.returncode == returncode
    assert result.stdout == "result\n"
    assert result.stderr == "diagnostic"


def test_local_shell_preserves_timeout_group_termination():
    result = LocalShell().execute(
        [sys.executable, "-c", "import time; time.sleep(10)"], timeout=0.1, timeout_check_interval=0.01
    )
    assert result.returncode == TIMEOUT_RETURN_CODE
    assert result.stderr == "Execution timed out"
