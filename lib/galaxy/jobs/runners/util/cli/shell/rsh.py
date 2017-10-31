import logging
import time

import paramiko

from .local import LocalShell
from ....util import Bunch

log = logging.getLogger(__name__)
logging.getLogger("paramiko").setLevel(logging.WARNING)  # paramiko logging is very verbose

__all__ = ('RemoteShell', 'SecureShell', 'GlobusSecureShell', 'ParamikoShell')


class RemoteShell(LocalShell):

    def __init__(self, rsh='rsh', rcp='rcp', hostname='localhost', username=None, **kwargs):
        super(RemoteShell, self).__init__(**kwargs)
        self.rsh = rsh
        self.rcp = rcp
        self.hostname = hostname
        self.username = username
        self.sessions = {}

    def execute(self, cmd, persist=False, timeout=60):
        # TODO: implement persistence
        if self.username is None:
            fullcmd = '%s %s %s' % (self.rsh, self.hostname, cmd)
        else:
            fullcmd = '%s -l %s %s %s' % (self.rsh, self.username, self.hostname, cmd)
        return super(RemoteShell, self).execute(fullcmd, persist, timeout)


class SecureShell(RemoteShell):
    SSH_NEW_KEY_STRING = 'Are you sure you want to continue connecting'

    def __init__(self, rsh='ssh', rcp='scp', private_key=None, port=None, strict_host_key_checking=True, **kwargs):
        strict_host_key_checking = "yes" if strict_host_key_checking else "no"
        rsh += " -oStrictHostKeyChecking=%s -oConnectTimeout=60" % strict_host_key_checking
        rcp += " -oStrictHostKeyChecking=%s -oConnectTimeout=60" % strict_host_key_checking
        if private_key:
            rsh += " -i %s" % private_key
            rcp += " -i %s" % private_key
        if port:
            rsh += " -p %s" % port
            rcp += " -p %s" % port
        super(SecureShell, self).__init__(rsh=rsh, rcp=rcp, **kwargs)


class ParamikoShell(object):

    def __init__(self, username, hostname, password=None, private_key=None, port=22, timeout=60, **kwargs):
        self.username = username
        self.hostname = hostname
        self.password = password
        self.private_key = private_key
        self.port = int(port) if port else port
        self.timeout = int(timeout) if timeout else timeout
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.connect()

    def connect(self):
        self.ssh.connect(hostname=self.hostname,
                         port=self.port,
                         username=self.username,
                         password=self.password,
                         key_filename=self.private_key,
                         timeout=self.timeout)

    def execute(self, cmd, timeout=60):
        try:
            _, stdout, stderr = self._execute(cmd, timeout)
        except paramiko.SSHException as e:
            log.error(e)
            time.sleep(10)
            self.connect()
            _, stdout, stderr = self._execute(cmd, timeout)
        return_code = stdout.channel.recv_exit_status()
        return Bunch(stdout=stdout.read(), stderr=stderr.read(), returncode=return_code)

    def _execute(self, cmd, timeout):
        return self.ssh.exec_command(cmd, timeout=timeout)


class GlobusSecureShell(SecureShell):

    def __init__(self, rsh='gsissh', rcp='gsiscp', **kwargs):
        super(GlobusSecureShell, self).__init__(rsh=rsh, rcp=rcp, **kwargs)
