try:
    from fs_gcsfs import GCSFS
    from google.cloud.storage import Client
    from google.oauth2.credentials import Credentials
except ImportError:
    GCSFS = None

from ._pyfilesystem2 import PyFilesystem2FilesSource


class GoogleCloudStorageFilesSource(PyFilesystem2FilesSource):
    plugin_type = "googlecloudstorage"
    required_module = GCSFS
    required_package = "fs-gcsfs"

    def _open_fs(self, user_context):
        props = self._serialization_props(user_context)
        bucket_name = props.pop("bucket_name", None)
        root_path = props.pop("root_path", None)
        project = props.pop("project", None)
        args = {}
        if props.get("anonymous"):
            args["client"] = Client.create_anonymous_client()
        elif props.get("token"):
            args["client"] = Client(project=project, credentials=Credentials(**props))
        handle = GCSFS(bucket_name, root_path=root_path, retry=0, **args)
        return handle


__all__ = ("GoogleCloudStorageFilesSource",)
