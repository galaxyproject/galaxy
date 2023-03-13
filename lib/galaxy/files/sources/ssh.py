try:
    from fs.sshfs import SSHFS
except ImportError:
    SSHFS = None

from typing import (
    Optional,
    Union,
)

from . import (
    FilesSourceOptions,
    FilesSourceProperties,
)
from ._pyfilesystem2 import PyFilesystem2FilesSource


class SshFilesSource(PyFilesystem2FilesSource):
    plugin_type = "ssh"
    required_module = SSHFS
    required_package = "fs.sshfs"

    def _open_fs(self, user_context=None, opts: Optional[FilesSourceOptions] = None):
        props = self._serialization_props(user_context)
        extra_props: Union[FilesSourceProperties, dict] = opts.extra_props or {} if opts else {}
        path = props.pop("path")
        handle = SSHFS(**{**props, **extra_props})
        if path:
            handle = handle.opendir(path)
        return handle


__all__ = ("SshFilesSource",)
