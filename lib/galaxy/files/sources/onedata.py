try:
    from fs.onedatarestfs import OnedataRESTFS
except ImportError:
    OnedataRESTFS = None

from typing import Optional
from . import FilesSourceOptions
from ._pyfilesystem2 import PyFilesystem2FilesSource


class OnedataFilesSource(PyFilesystem2FilesSource):
    plugin_type = "onedata"
    required_module = OnedataRESTFS
    required_package = "fs.onedatarestfs"

    def _open_fs(self, user_context=None, opts: Optional[FilesSourceOptions] = None):
        props = self._serialization_props(user_context)
        onezone_domain = props.pop("onezoneDomain", {}) or ""
        onezone_domain = onezone_domain.lstrip("https://").lstrip("http://")
        access_token = props.pop("accessToken", {}) or ""
        handle = OnedataRESTFS(onezone_domain, access_token)
        return handle


__all__ = ("OnedataFilesSource",)
