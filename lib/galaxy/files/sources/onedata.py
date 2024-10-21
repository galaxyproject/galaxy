try:
    from fs.onedatarestfs import OnedataRESTFS
except ImportError:
    OnedataRESTFS = None

from typing import Optional

from galaxy.util import mapped_chars
from . import FilesSourceOptions
from ._pyfilesystem2 import PyFilesystem2FilesSource


def remove_prefix(prefix, string):
    if string.startswith(prefix):
        string = string[len(prefix) :]
    return string


class OnedataFilesSource(PyFilesystem2FilesSource):
    plugin_type = "onedata"
    required_module = OnedataRESTFS
    required_package = "fs.onedatarestfs"

    def _open_fs(self, user_context=None, opts: Optional[FilesSourceOptions] = None):
        props = self._serialization_props(user_context)

        access_token = props.pop("access_token", "") or ""
        onezone_domain = props.pop("onezone_domain", "") or ""
        onezone_domain = remove_prefix("http://", remove_prefix("https://", onezone_domain))
        disable_tls_certificate_validation = props.pop("disable_tls_certificate_validation", False) or False

        alt_space_fqn_separators = [mapped_chars["@"]] if "@" in mapped_chars else None

        handle = OnedataRESTFS(
            onezone_domain,
            access_token,
            alt_space_fqn_separators=alt_space_fqn_separators,
            verify_ssl=not disable_tls_certificate_validation,
        )
        return handle


__all__ = ("OnedataFilesSource",)
