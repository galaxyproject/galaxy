import errno
import logging
import os
import signal
from time import sleep

log = logging.getLogger(__name__)


def check_pg(pgid):
    """Check whether processes in process group pgid are still alive."""
    try:
        (pid, exit_status) = os.waitpid(-pgid, os.WNOHANG)
    except OSError as e:
        if e.errno == errno.ECHILD:
            log.debug("check_pg(): No process found in process group %d", pgid)
        else:
            log.warning(
                "check_pg(): Got errno %s when checking process group %d: %s",
                errno.errorcode[e.errno] if e.errno is not None else None,
                pgid,
                e.strerror,
            )
        return False
    # Since we are passing os.WNOHANG to os.waitpid(), pid is 0 if no process
    # status is available immediately.
    return pid == 0


def kill_pg(pgid):
    """Kill all processes in process group pgid."""
    for sig in [signal.SIGTERM, signal.SIGKILL]:
        try:
            os.killpg(pgid, sig)
        except OSError as e:
            if e.errno == errno.ESRCH:
                return
            log.warning(
                "Got errno %s when sending signal %d to process group %d: %s",
                errno.errorcode[e.errno] if e.errno is not None else None,
                sig,
                pgid,
                e.strerror,
            )
        sleep(1)
        if not check_pg(pgid):
            log.debug("Processes in process group %d successfully killed with signal %d", pgid, sig)
            return
    else:
        log.warning("Some process in process group %d refuses to die after signaling TERM/KILL", pgid)
