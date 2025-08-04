"""
Galaxy FilesSource implementation for RSpace.

This module implements a FilesSource that interacts with an RSpace [1] instance. RSpace is an electronic lab notebook
(ELN) designed for documenting, managing and sharing scientific data. The central concepts in RSpace are the Workspace,
the Inventory and the Gallery.

The Workspace's role is organizing and managing research activities. It allows creating documents, folders and research
notebooks [2]. The Inventory is a tool to keep track of laboratory resources, such as reagents, samples and equipment
[3]. The Gallery is where any research data represented as files is stored [4].

The FilesSource implemented by this module accesses the Gallery of an RSpace instance. The Gallery is organized in
categories (e.g. Images, Audio, Documents, Chemistry), where each category is itself a tree structure with folders and
files just like a regular filesystem, although there is a key difference: categories and their subfolders can only
contain files of certain types (e.g. jpeg, bmp, png, etc. for the Images category).

This implementation is based on the ``rspace-client-python`` library [5], which provides a PyFilesystem2 [6] interface
to interact with RSpace's Gallery (available as ``GalleryFilesystem`` in the ``rspace_client.eln.fs`` module). It
consists just of a minimal wrapper (based on the base ``PyFilesystem2FilesSource`` provided by Galaxy) around the
``GalleryFilesystem`` class.

References:

- [1] https://www.researchspace.com/
- [2] https://documentation.researchspace.com/article/bzgr8ea9e3-the-workspace
- [3] https://documentation.researchspace.com/category/zpizk20kgx-inventory
- [4] https://documentation.researchspace.com/article/sl6mo1i9do-the-gallery
- [5] https://github.com/rspace-os/rspace-client-python
- [6] https://docs.pyfilesystem.org/
"""

import datetime
import os.path
from types import MethodType
from typing import (
    Any,
    BinaryIO,
    cast,
    ClassVar,
    IO,
    Optional,
)

from . import (
    AnyRemoteEntry,
    FilesSourceProperties,
    RemoteDirectory,
    RemoteFile,
)
from ._pyfilesystem2 import PyFilesystem2FilesSource

try:
    from rspace_client.eln.fs import GalleryFilesystem as RSpaceGalleryFilesystem
except ImportError:
    RSpaceGalleryFilesystem = None

__all__ = ("RSpaceFilesSource",)


class FakedNameIO:
    """
    A wrapper around a file-like object that fakes the name attribute.

    The name attribute is used by `requests` (that `rspace-client-python` depends on) to determine the mime type. RSpace
    will reject uploads to the Gallery that do not match the file types accepted by the target folder (e.g. no `.dat`
    files allowed in the "Images" folder).

    Galaxy datasets are stored in the filesystem with the `.dat` extension. Therefore, the ability to fake the name (and
    thus the extension) is essential to be able to upload files to any RSpace folder other than "Miscellaneous" without
    having to alter the `rspace-client-python` library itself.
    """

    def __init__(self, handle: IO, name: Optional[str] = None):
        """Initialize the wrapper from an existing file-like object."""
        self._handle = handle
        self._name = name

    @property
    def name(self) -> str:
        """Retrieve the faked name if it was provided, otherwise retrieve the original file name."""
        return self._name or self._handle.name

    def __getattr__(self, name):
        """Retrieve any other attribute."""
        return getattr(self._handle, name)


if RSpaceGalleryFilesystem is not None:

    class PatchedRSpaceGalleryFilesystem(RSpaceGalleryFilesystem):
        """
        Patch RSpaceGalleryFilesystem to keep a record of the RSpace global id of the most recently uploaded file.
        """

        upload_global_id: str
        # The RSpace global id of the most recently uploaded file.

        _upload_response: dict
        # The response from the RSpace's API (in JSON format) after uploading a file.

        def __init__(self, *args, **kwargs):
            """
            Initialize the RSpaceGalleryFilesystem and patch the `upload_file()` method to save the upload response.
            """
            super().__init__(*args, **kwargs)

            # patch the `upload_file()` method to save the upload response
            eln_client_upload_file_method = self.eln_client.upload_file

            def upload_file(self_, file, folder_id=None, caption=None):
                self._upload_response = eln_client_upload_file_method(file, folder_id=folder_id, caption=caption)

            self.eln_client.upload_file = MethodType(upload_file, self.eln_client)

        def upload(self, path: str, file: BinaryIO, chunk_size: Optional[int] = None, **options: Any) -> None:
            """
            Patch the `upload()` method to retrieve the global id from the saved upload response.
            """
            super().upload(path, file, chunk_size, **options)
            self.upload_global_id = self._upload_response["globalId"]


class RSpaceFileSourceConfiguration(FilesSourceProperties):
    endpoint: str
    api_key: str


class RSpaceFilesSource(PyFilesystem2FilesSource):
    plugin_type = "rspace"
    required_module = RSpaceGalleryFilesystem
    required_package = "rspace_client.eln.fs"
    config_class: ClassVar[type[RSpaceFileSourceConfiguration]] = RSpaceFileSourceConfiguration
    config: RSpaceFileSourceConfiguration

    _upload_global_id: str
    # The RSpace global id of the most recently uploaded file.

    def __init__(self, config: RSpaceFileSourceConfiguration):
        super().__init__(config)

    def _open_fs(self):
        """
        Instantiate a PyFilesystem2 FS object for RSpace's Gallery.
        """
        if RSpaceGalleryFilesystem is None:
            raise self.required_package_exception

        # patch the `upload()` method to keep track of the global id of the most recently uploaded file, change the
        # target path and fake the name of the file
        gallery_fs = PatchedRSpaceGalleryFilesystem(self.config.endpoint, self.config.api_key)
        gallery_fs_upload_method = gallery_fs.upload

        def upload(self_, path: str, file: BinaryIO, chunk_size: Optional[int] = None, **options: Any) -> None:
            gallery_fs_upload_method(
                os.path.dirname(path),
                cast(BinaryIO, FakedNameIO(file, name=os.path.basename(path))),
                chunk_size,
                **options,
            )
            self._upload_global_id = gallery_fs.upload_global_id

        gallery_fs.upload = MethodType(upload, gallery_fs)  # type: ignore[method-assign]

        return gallery_fs

    def _write_from(self, target_path: str, native_path: str) -> str:
        """
        Save a file to the RSpace Gallery.
        """
        target_directory = os.path.dirname(target_path)
        super()._write_from(target_path, native_path)
        return os.path.join(target_directory, self._upload_global_id)

    def _resource_info_to_dict(self, dir_path, resource_info) -> AnyRemoteEntry:
        """
        Convert PyFilesystem2 resource information objects to dictionaries representing directories and files.

        Display names for categories, directories and files in the RSpace Gallery are made available within the custom
        namespace "rspace" (as well as creation dates). Names are available in the "basic" namespace are the internal
        RSpace names, which are unique. Thus, those names from the "basic" namespace are used to generate the URIs for
        the directories and files (remote entries).
        """
        basename = resource_info.get("basic", "name")
        dirname = dir_path
        path = os.path.join(dirname, basename)

        dict_ = {
            "name": resource_info.get("rspace", "name"),
            "uri": self.uri_from_path(path),
            "path": path,
        }

        entry: AnyRemoteEntry
        if resource_info.is_dir:
            entry = RemoteDirectory(name=dict_["name"], uri=dict_["uri"], path=dict_["path"])
        else:
            dict_.update(
                {
                    "size": resource_info.size,
                    "ctime": self.to_dict_time(
                        datetime.datetime.fromisoformat(resource_info.get("rspace", "created")).astimezone(
                            datetime.timezone.utc
                        )
                    ),
                }
            )
            entry = RemoteFile(
                name=dict_["name"],
                size=dict_["size"],
                ctime=dict_["ctime"],
                uri=dict_["uri"],
                path=dict_["path"],
            )

        return entry
