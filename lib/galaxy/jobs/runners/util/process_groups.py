import errno
import logging
import os
import signal
from time import (
    monotonic,
    sleep,
)

log = logging.getLogger(__name__)


def check_pg(pgid):
    """Check whether processes in process group pgid are still alive."""
    try:
        pid, exit_status = os.waitpid(-pgid, os.WNOHANG)
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


def kill_pgs(pgids, grace_period=1.0):
    """Kill all processes in each of the process groups pgids.

    Unlike calling kill_pg() for each group, every group gets SIGTERM before
    waiting, and the groups still alive after grace_period seconds all get
    SIGKILL, so the wait does not grow with the number of groups.

    Liveness is tested by sending signal 0 instead of with check_pg(), so this
    does not reap the processes and whoever waits on them still gets their
    exit status.
    """
    pgids = list(pgids)
    alive = pgids
    for sig in [signal.SIGTERM, signal.SIGKILL]:
        alive = [pgid for pgid in alive if _signal_pg(pgid, sig)]
        deadline = monotonic() + grace_period
        while alive and monotonic() < deadline:
            sleep(0.1)
            alive = [pgid for pgid in alive if _signal_pg(pgid, 0)]
        if not alive:
            log.debug("Processes in process groups %s successfully killed with signal %d", pgids, sig)
            return
    log.warning("Some process in process groups %s refuses to die after signaling TERM/KILL", alive)


def _signal_pg(pgid, sig):
    """Send sig to process group pgid, return False if the group no longer exists."""
    try:
        os.killpg(pgid, sig)
    except OSError as e:
        if e.errno == errno.ESRCH:
            return False
        if sig:
            log.warning(
                "Got errno %s when sending signal %d to process group %d: %s",
                errno.errorcode[e.errno] if e.errno is not None else None,
                sig,
                pgid,
                e.strerror,
            )
    return True
