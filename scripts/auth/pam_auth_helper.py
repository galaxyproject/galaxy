#!/usr/bin/env python

import logging
import signal
import sys

log = logging.getLogger(__name__)

TIMEOUT = 5

try:
    import pam
except ImportError:
    log.debug('PAM auth helper: Could not import pam module')
    sys.exit(1)


def handle_timeout(signum, stack):
    raise IOError("Timed out reading input")


# set timeout so we don't block on reading stdin
signal.alarm(TIMEOUT)

pam_service = sys.stdin.readline().strip()
pam_username = sys.stdin.readline().strip()
pam_password = sys.stdin.readline().strip()

# cancel the alarm
signal.alarm(0)

p_auth = pam.pam()
authenticated = p_auth.authenticate(pam_username, pam_password, service=pam_service)
if authenticated:
    log.debug('PAM auth helper: authentication successful for {}'.format(pam_username))
    sys.stdout.write('True\n')
    sys.exit(0)
else:
    log.debug('PAM auth helper: authentication failed for {}'.format(pam_username))
    sys.stdout.write('False\n')
    sys.exit(1)
