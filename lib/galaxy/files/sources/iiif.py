import os
from typing import Union

from fsspec import AbstractFileSystem

from galaxy.exceptions import MessageException
from galaxy.files.models import (
    FilesSourceRuntimeContext,
    RemoteDirectory,
    RemoteFile,
)
from galaxy.files.sources._defaults import DEFAULT_SCHEME
from galaxy.files.sources._fsspec import (
    CacheOptionsDictType,
    FsspecBaseFileSourceConfiguration,
    FsspecBaseFileSourceTemplateConfiguration,
    FsspecFilesSource,
)
from galaxy.util.config_templates import TemplateExpansion

try:
    from iiif_fsspec import IIIFFileSystem
except ImportError:
    IIIFFileSystem = None  # type: ignore[assignment,misc]


class IIIFFileSourceTemplateConfiguration(FsspecBaseFileSourceTemplateConfiguration):
    manifest_url: Union[str, TemplateExpansion]


class IIIFFileSourceConfiguration(FsspecBaseFileSourceConfiguration):
    manifest_url: str


class IIIFFilesSource(FsspecFilesSource[IIIFFileSourceTemplateConfiguration, IIIFFileSourceConfiguration]):
    plugin_type = "iiif"
    required_module = IIIFFileSystem
    required_package = "iiif-fsspec"

    template_config_class = IIIFFileSourceTemplateConfiguration
    resolved_config_class = IIIFFileSourceConfiguration

    def _open_fs(
        self,
        _context: FilesSourceRuntimeContext[IIIFFileSourceConfiguration],
        cache_options: CacheOptionsDictType,
    ) -> AbstractFileSystem:
        if IIIFFileSystem is None:
            raise self.required_package_exception

        return IIIFFileSystem(**cache_options)

    def _to_filesystem_path(self, path: str) -> str:
        if path in ("", "/"):
            return self.manifest_url
        return path.lstrip("/")

    def _info_to_entry(self, info: dict):
        filesystem_path = info["name"]
        entry_path = filesystem_path
        entry_name = self._entry_name_from_info(info, filesystem_path)
        uri = self.uri_from_path(entry_path)

        if info.get("type") == "directory":
            return RemoteDirectory(name=entry_name, uri=uri, path=entry_path)

        size = int(info.get("size", 0))
        ctime = self._get_formatted_timestamp(info)
        hashes = self._get_file_hashes(info)
        return RemoteFile(name=entry_name, size=size, ctime=ctime, uri=uri, path=entry_path, hashes=hashes)

    def _entry_name_from_info(self, info: dict, filesystem_path: str) -> str:
        iiif_label = info.get("iiif_label")
        if isinstance(iiif_label, str) and iiif_label:
            return iiif_label
        return os.path.basename(filesystem_path.rstrip("/"))

    @property
    def manifest_url(self) -> str:
        return self._normalize_manifest_url(self.template_config.manifest_url)

    @staticmethod
    def _normalize_manifest_url(manifest_url: str) -> str:
        return manifest_url.rstrip("/")

    def _write_from(
        self,
        _target_path: str,
        _native_path: str,
        _context: FilesSourceRuntimeContext[IIIFFileSourceConfiguration],
    ):
        raise MessageException("IIIF file sources are read-only and do not support exporting files.")

    def get_scheme(self) -> str:
        return self.scheme if self.scheme and self.scheme != DEFAULT_SCHEME else "iiif"


__all__ = ("IIIFFilesSource",)
