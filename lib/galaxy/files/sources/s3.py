try:
    from fs_s3fs import S3FS
except ImportError:
    S3FS = None

from ._pyfilesystem2 import PyFilesystem2FilesSource


class S3FilesSource(PyFilesystem2FilesSource):
    plugin_type = "s3"
    required_module = S3FS
    required_package = "fs-s3fs"

    def _open_fs(self, user_context):
        props = self._serialization_props(user_context)
        handle = S3FS(**props)
        return handle


__all__ = ("S3FilesSource",)
