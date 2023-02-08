try:
    from fs_gcsfs import GCSFS
    from google.cloud.storage import Client
    from google.oauth2.credentials import Credentials
except ImportError:
    GCSFS = None

from typing import (
    cast,
)

from typing_extensions import Unpack

from . import (
    FilesSourceOptions,
    FilesSourceProperties,
)
from ._pyfilesystem2 import PyFilesystem2FilesSource


class GoogleCloudStorageFilesSourceProperties(FilesSourceProperties, total=False):
    bucket_name: str
    root_path: str
    project: str
    anonymous: bool


class GoogleCloudStorageFilesSource(PyFilesystem2FilesSource):
    plugin_type = "googlecloudstorage"
    required_module = GCSFS
    required_package = "fs-gcsfs"

    def _open_fs(self, user_context=None, **kwargs: Unpack[FilesSourceOptions]):
        props = self._serialization_props(user_context)
        extra_props: GoogleCloudStorageFilesSourceProperties = cast(
            GoogleCloudStorageFilesSourceProperties, kwargs.get("extra_props") or {}
        )
        bucket_name = props.pop("bucket_name", None)
        root_path = props.pop("root_path", None)
        project = props.pop("project", None)
        args = {}
        if props.get("anonymous"):
            args["client"] = Client.create_anonymous_client()
        elif props.get("token"):
            args["client"] = Client(project=project, credentials=Credentials(**props))
        handle = GCSFS(bucket_name, root_path=root_path, retry=0, **{**args, **extra_props})
        return handle


__all__ = ("GoogleCloudStorageFilesSource",)
