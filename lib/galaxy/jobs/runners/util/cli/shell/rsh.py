import logging
import time

import paramiko
from pulsar.managers.util.retry import RetryActionExecutor

from galaxy.util import (
    smart_str,
    unicodify
)
from galaxy.util.bunch import Bunch
from .local import LocalShell

log = logging.getLogger(__name__)
logging.getLogger("paramiko").setLevel(logging.WARNING)  # paramiko logging is very verbose

__all__ = ('RemoteShell', 'SecureShell', 'GlobusSecureShell', 'ParamikoShell')


class RemoteShell(LocalShell):

    def __init__(self, rsh='rsh', rcp='rcp', hostname='localhost', username=None, options=None, **kwargs):
        super(RemoteShell, self).__init__(**kwargs)
        self.rsh = rsh
        self.rcp = rcp
        self.hostname = hostname
        self.username = username
        self.options = options
        self.sessions = {}

    def execute(self, cmd, persist=False, timeout=60):
        # TODO: implement persistence
        fullcmd = [self.rsh]
        if self.options:
            fullcmd.extend(self.options)
        if self.username:
            fullcmd.extend(["-l", self.username])
        fullcmd.extend([self.hostname, cmd])
        return super(RemoteShell, self).execute(fullcmd, persist, timeout)


class SecureShell(RemoteShell):
    SSH_NEW_KEY_STRING = 'Are you sure you want to continue connecting'

    def __init__(self, rsh='ssh', rcp='scp', private_key=None, port=None, strict_host_key_checking=True, **kwargs):
        strict_host_key_checking = "yes" if strict_host_key_checking else "no"
        options = ["-o", "StrictHostKeyChecking=%s" % strict_host_key_checking]
        options.extend(["-o", "ConnectTimeout=60"])
        if private_key:
            options.extend(['-i', private_key])
        if port:
            options.extend(['-p', str(port)])
        super(SecureShell, self).__init__(rsh=rsh, rcp=rcp, options=options, **kwargs)


class ParamikoShell(object):

    def __init__(self, username, hostname, password=None, private_key=None, port=22, timeout=60, **kwargs):
        self.username = username
        self.hostname = hostname
        self.password = password
        self.private_key = private_key
        self.port = int(port) if port else port
        self.timeout = int(timeout) if timeout else timeout
        self.ssh = None
        self.retry_action_executor = RetryActionExecutor(max_retries=100, interval_max=300)
        self.connect()

    def connect(self):
        log.info("Attempting establishment of new paramiko SSH channel")
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.ssh.connect(hostname=self.hostname,
                         port=self.port,
                         username=self.username,
                         password=self.password,
                         key_filename=self.private_key,
                         timeout=self.timeout)

    def execute(self, cmd, timeout=60):

        def retry():
            try:
                _, stdout, stderr = self._execute(cmd, timeout)
            except paramiko.SSHException as e:
                log.error(e)
                time.sleep(10)
                self.connect()
                _, stdout, stderr = self._execute(cmd, timeout)
            return stdout, stderr

        stdout, stderr = self.retry_action_executor.execute(retry)
        return_code = stdout.channel.recv_exit_status()
        return Bunch(stdout=unicodify(stdout.read()), stderr=unicodify(stderr.read()), returncode=return_code)

    def _execute(self, cmd, timeout):
        return self.ssh.exec_command(smart_str(cmd), timeout=timeout)


class GlobusSecureShell(SecureShell):

    def __init__(self, rsh='gsissh', rcp='gsiscp', **kwargs):
        super(GlobusSecureShell, self).__init__(rsh=rsh, rcp=rcp, **kwargs)
