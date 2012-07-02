"""
Base class for runners which execute commands via a shell
"""

class BaseShellExec(object):
    def __init__(self, *args, **kwargs):
        raise NotImplementedError()
    def copy(self, rcp_cmd, files, dest):
        raise NotImplementedError()
    def execute(self, cmd, persist=False, timeout=60):
        raise NotImplementedError()
