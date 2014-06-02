from tempfile import TemporaryFile
from time import sleep
from subprocess import Popen, PIPE

from ..shell import BaseShellExec
from ....util import Bunch, kill_pid

from logging import getLogger
log = getLogger(__name__)

TIMEOUT_ERROR_MESSAGE = u'Execution timed out'
TIMEOUT_RETURN_CODE = -1
DEFAULT_TIMEOUT = 60
DEFAULT_TIMEOUT_CHECK_INTERVAL = 3


class LocalShell(BaseShellExec):
    """

    >>> shell = LocalShell()
    >>> def exec_python(script, **kwds): return shell.execute('python -c "%s"' % script, **kwds)
    >>> exec_result = exec_python("from __future__ import print_function; print('Hello World')")
    >>> exec_result.stderr == u''
    True
    >>> exec_result.stdout.strip() == u'Hello World'
    True
    >>> exec_result = exec_python("import time; time.sleep(90)", timeout=3, timeout_check_interval=1)
    >>> exec_result.stdout == u''
    True
    >>> exec_result.stderr == 'Execution timed out'
    True
    >>> exec_result.returncode == TIMEOUT_RETURN_CODE
    True
    """

    def __init__(self, **kwds):
        pass

    def execute(self, cmd, persist=False, timeout=DEFAULT_TIMEOUT, timeout_check_interval=DEFAULT_TIMEOUT_CHECK_INTERVAL, **kwds):
        outf = TemporaryFile()
        p = Popen(cmd, shell=True, stdin=None, stdout=outf, stderr=PIPE)
        # poll until timeout

        for i in range(int(timeout / timeout_check_interval)):
            r = p.poll()
            if r is not None:
                break
            sleep(timeout_check_interval)
        else:
            kill_pid(p.pid)
            return Bunch(stdout=u'', stderr=TIMEOUT_ERROR_MESSAGE, returncode=TIMEOUT_RETURN_CODE)
        outf.seek(0)
        return Bunch(stdout=_read_str(outf), stderr=_read_str(p.stderr), returncode=p.returncode)


def _read_str(stream):
    contents = stream.read()
    return contents.decode('UTF-8') if isinstance(contents, bytes) else contents


__all__ = ('LocalShell',)
