"""Common Crawl file source plugin using fsspec.

This plugin wraps the ``commoncrawl-fsspec`` library's
:class:`~commoncrawl_fsspec.filesystem.CommonCrawlFileSystem` to provide
read-only access to the `Common Crawl <https://commoncrawl.org/>`_ archive
through Galaxy's file source framework.

Users can browse crawl releases, navigate segments, and download individual
WARC, WET, or WAT files that can be imported into Galaxy histories.
"""

import logging

from fsspec import AbstractFileSystem

from galaxy.files.models import (
    FilesSourceRuntimeContext,
)
from galaxy.files.sources._fsspec import (
    CacheOptionsDictType,
    FsspecBaseFileSourceConfiguration,
    FsspecBaseFileSourceTemplateConfiguration,
    FsspecFilesSource,
)

try:
    from commoncrawl_fsspec import CommonCrawlFileSystem
except ImportError:
    CommonCrawlFileSystem = None  # type: ignore[assignment, misc, unused-ignore]


REQUIRED_PACKAGE = "commoncrawl-fsspec"
FS_PLUGIN_TYPE = "commoncrawl"

log = logging.getLogger(__name__)


class CommonCrawlFileSourceTemplateConfiguration(FsspecBaseFileSourceTemplateConfiguration):
    """Template configuration for the Common Crawl file source."""


class CommonCrawlFileSourceConfiguration(FsspecBaseFileSourceConfiguration):
    """Resolved configuration for the Common Crawl file source."""


class CommonCrawlFilesSource(
    FsspecFilesSource[CommonCrawlFileSourceTemplateConfiguration, CommonCrawlFileSourceConfiguration]
):
    """File source plugin for browsing Common Crawl data.

    The plugin is strictly read-only. It delegates to
    :class:`~commoncrawl_fsspec.filesystem.CommonCrawlFileSystem` for all
    filesystem operations (listing, file retrieval).
    """

    plugin_type = FS_PLUGIN_TYPE
    required_module = CommonCrawlFileSystem
    required_package = REQUIRED_PACKAGE

    template_config_class = CommonCrawlFileSourceTemplateConfiguration
    resolved_config_class = CommonCrawlFileSourceConfiguration

    def get_writable(self) -> bool:
        """Common Crawl is a public read-only dataset."""
        return False

    def _open_fs(
        self,
        context: FilesSourceRuntimeContext[CommonCrawlFileSourceConfiguration],
        cache_options: CacheOptionsDictType,
    ) -> AbstractFileSystem:
        if CommonCrawlFileSystem is None:
            raise self.required_package_exception

        return CommonCrawlFileSystem(**cache_options)


__all__ = ("CommonCrawlFilesSource",)
