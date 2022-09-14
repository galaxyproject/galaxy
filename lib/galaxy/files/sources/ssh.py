try:
    from fs.sshfs import SSHFS
except ImportError:
    SSHFS = None

from ._pyfilesystem2 import PyFilesystem2FilesSource


class SshFilesSource(PyFilesystem2FilesSource):
    plugin_type = "ssh"
    required_module = SSHFS
    required_package = "fs.sshfs"

    def _open_fs(self, user_context):
        props = self._serialization_props(user_context)
        path = props.pop("path")
        handle = SSHFS(**props)
        if path:
            handle = handle.opendir(path)
        return handle


__all__ = ("SshFilesSource",)
