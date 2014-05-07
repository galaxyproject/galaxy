from .local import LocalShell

from logging import getLogger
log = getLogger(__name__)

__all__ = ('RemoteShell', 'SecureShell', 'GlobusSecureShell')


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

    def __init__(self, rsh='ssh', rcp='scp', **kwargs):
        rsh += ' -oStrictHostKeyChecking=yes -oConnectTimeout=60'
        rcp += ' -oStrictHostKeyChecking=yes -oConnectTimeout=60'
        super(SecureShell, self).__init__(rsh=rsh, rcp=rcp, **kwargs)


class GlobusSecureShell(SecureShell):

    def __init__(self, rsh='gsissh', rcp='gsiscp', **kwargs):
        super(GlobusSecureShell, self).__init__(rsh=rsh, rcp=rcp, **kwargs)
