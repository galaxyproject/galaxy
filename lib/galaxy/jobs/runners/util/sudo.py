import logging
from subprocess import (
    PIPE,
    Popen,
)

SUDO_PATH = "/usr/bin/sudo"
SUDO_PRESERVE_ENVIRONMENT_ARG = "-E"
SUDO_USER_ARG = "-u"

log = logging.getLogger(__name__)


def sudo_popen(*args, **kwargs):
    """
    Helper method for building and executing Popen command. This is potentially
    sensetive code so should probably be centralized.
    """
    user = kwargs.get("user", None)
    full_command = [SUDO_PATH, SUDO_PRESERVE_ENVIRONMENT_ARG]
    if user:
        full_command.extend([SUDO_USER_ARG, user])
    full_command.extend(args)
    log.info(f"About to execute the following sudo command - [{' '.join(full_command)}]")
    p = Popen(full_command, shell=False, stdout=PIPE, stderr=PIPE)
    return p
