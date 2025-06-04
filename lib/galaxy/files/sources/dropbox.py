try:
    from fs.dropboxfs import DropboxFS
except ImportError:
    DropboxFS = None

from typing import (
    cast,
    Optional,
    Union,
)

from galaxy.exceptions import (
    AuthenticationRequired,
    MessageException,
)
from . import (
    AnyRemoteEntry,
    DatasetHash,
    FilesSourceOptions,
    FilesSourceProperties,
    RemoteFile,
)
from ._pyfilesystem2 import PyFilesystem2FilesSource


class DropboxFilesSource(PyFilesystem2FilesSource):
    plugin_type = "dropbox"
    required_module = DropboxFS
    required_package = "fs.dropboxfs"

    def _open_fs(self, user_context=None, opts: Optional[FilesSourceOptions] = None):
        props = self._serialization_props(user_context)
        extra_props: Union[FilesSourceProperties, dict] = opts.extra_props or {} if opts else {}
        # accessToken has been renamed to access_token in fs.dropboxfs 1.0
        if "accessToken" in props:
            props["access_token"] = props.pop("accessToken")
        if "oauth2_access_token" in props:
            props["access_token"] = props.pop("oauth2_access_token")

        try:
            handle = DropboxFS(**{**props, **extra_props})
            return handle
        except Exception as e:
            # This plugin might raise dropbox.dropbox_client.BadInputException
            # which is not a subclass of fs.errors.FSError
            if "OAuth2" in str(e):
                raise AuthenticationRequired(
                    f"Permission Denied. Reason: {e}. Please check your credentials in your preferences for {self.label}."
                )
            raise MessageException(f"Error connecting to Dropbox. Reason: {e}")

    def _get_content_hash(self, path) -> Optional[DatasetHash]:
        """
        Return the hash source for this file source.
        """
        with self._open_fs() as fs:
            info = fs.getinfo(path)
            if info.is_file and "dropbox" in info.raw:
                hash_value = info.raw["dropbox"].get("content_hash")
                if hash_value:
                    return {"hash_value": str(hash_value), "hash_function": "DROPBOX"}
        return None

    def _resource_info_to_dict(self, dir_path, resource_info) -> AnyRemoteEntry:
        rval = super()._resource_info_to_dict(dir_path, resource_info)
        if resource_info.is_file:
            rval = cast(RemoteFile, rval)
            # dropbox returns a content_hash we can use to potentially avoid downloading the file if we already have it
            rval["content_hash"] = resource_info.raw["dropbox"]["content_hash"]
            rval["content_hash_algorithm"] = "dropbox_content_hash"
        return rval


__all__ = ("DropboxFilesSource",)
