from typing import Union

try:
    from fs.azblob import (
        BlobFS,
        BlobFSV2,
    )
except ImportError:
    BlobFS = None

from typing import Optional

from . import (
    FilesSourceOptions,
    FilesSourceProperties,
)
from ._pyfilesystem2 import PyFilesystem2FilesSource


class AzureFileSource(PyFilesystem2FilesSource):
    plugin_type = "azure"
    required_module = BlobFS
    required_package = "fs-azureblob"

    def _open_fs(self, user_context=None, opts: Optional[FilesSourceOptions] = None):
        props = self._serialization_props(user_context)
        extra_props: Union[FilesSourceProperties, dict] = opts.extra_props or {} if opts else {}
        all_props = {**props, **extra_props}
        namespace_type = all_props.get("namespace_type", "hierarchical")
        if namespace_type not in ["hierarchical", "flat"]:
            raise Exception("Misconfigured azure file source")
        account_name = all_props["account_name"]
        account_key = all_props["account_key"]
        container = all_props["container_name"]
        handle: Union[BlobFSV2, BlobFS]
        if namespace_type == "flat":
            handle = BlobFS(account_name, container, account_key)
        else:
            handle = BlobFSV2(account_name, container, account_key)

        return handle


__all__ = ("AzureFileSource",)
