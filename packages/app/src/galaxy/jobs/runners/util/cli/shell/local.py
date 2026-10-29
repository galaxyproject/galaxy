import os
from logging import getLogger
from subprocess import (
    PIPE,
    Popen,
)
from tempfile import TemporaryFile
from time import sleep

from galaxy.util.bunch import Bunch
from . import BaseShellExec
from ....util.process_groups import (
    check_pg,
    kill_pg,
)

log = getLogger(__name__)

TIMEOUT_ERROR_MESSAGE = "Execution timed out"
TIMEOUT_RETURN_CODE = -1
DEFAULT_TIMEOUT = 60
DEFAULT_TIMEOUT_CHECK_INTERVAL = 3


class LocalShell(BaseShellExec):
    """

    >>> shell = LocalShell()
    >>> def exec_python(script, **kwds): return shell.execute(['python', '-c', script], **kwds)
    >>> exec_result = exec_python("from __future__ import print_function; print('Hello World')")
    >>> exec_result.stderr == u''
    True
    >>> exec_result.stdout.strip() == u'Hello World'
    True
    >>> exec_result.returncode
    0
    >>> exec_result = exec_python("import time; time.sleep(10)", timeout=1, timeout_check_interval=.1)
    >>> exec_result.stdout == u''
    True
    >>> exec_result.stderr == 'Execution timed out'
    True
    >>> exec_result.returncode == TIMEOUT_RETURN_CODE
    True
    >>> shell.execute('echo hi').stdout == "hi\\n"
    True
    """

    def __init__(self, **kwds):
        pass

    def execute(
        self, cmd, persist=False, timeout=DEFAULT_TIMEOUT, timeout_check_interval=DEFAULT_TIMEOUT_CHECK_INTERVAL, **kwds
    ):
        is_cmd_string = isinstance(cmd, str)
        outf = TemporaryFile()
        p = Popen(cmd, stdin=None, stdout=outf, stderr=PIPE, shell=is_cmd_string, preexec_fn=os.setpgrp)
        # check process group until timeout

        for _ in range(int(timeout / timeout_check_interval)):
            sleep(0.1)  # For fast returning commands
            if not check_pg(p.pid):
                break
            sleep(timeout_check_interval)
        else:
            kill_pg(p.pid)
            return Bunch(stdout="", stderr=TIMEOUT_ERROR_MESSAGE, returncode=TIMEOUT_RETURN_CODE)
        outf.seek(0)
        # Need to poll once to establish return code
        p.poll()
        return Bunch(stdout=_read_str(outf), stderr=_read_str(p.stderr), returncode=p.returncode)


def _read_str(stream):
    contents = stream.read()
    return contents.decode("UTF-8") if isinstance(contents, bytes) else contents


__all__ = ("LocalShell",)
