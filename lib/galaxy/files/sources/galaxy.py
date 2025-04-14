"""Static Galaxy file sources - ftp and libraries."""

from typing import (
    Optional,
)

from typing_extensions import Unpack

from galaxy.files.sources import PluginKind
from .posix import (
    PosixFilesSource,
    PosixFilesSourceProperties,
)


class UserFtpFilesSource(PosixFilesSource):
    plugin_type = "gxftp"
    plugin_kind = PluginKind.stock

    def __init__(self, **kwd: Unpack[PosixFilesSourceProperties]):
        posix_kwds: PosixFilesSourceProperties = dict(
            id="_ftp",
            root="${user.ftp_dir}",
            label="FTP Directory",
            doc="Galaxy User's FTP Directory",
            writable=True,
        )
        posix_kwds.update(kwd)
        if "delete_on_realize" not in posix_kwds:
            file_sources_config = kwd["file_sources_config"]
            posix_kwds["delete_on_realize"] = file_sources_config.ftp_upload_purge
        super().__init__(**posix_kwds)

    def get_prefix(self) -> Optional[str]:
        return None

    def get_scheme(self) -> str:
        return "gxftp"


class LibraryImportFilesSource(PosixFilesSource):
    plugin_type = "gximport"
    plugin_kind = PluginKind.stock

    def __init__(self, **kwd: Unpack[PosixFilesSourceProperties]):
        posix_kwds: PosixFilesSourceProperties = dict(
            id="_import",
            root="${config.library_import_dir}",
            label="Library Import Directory",
            doc="Galaxy's library import directory",
        )
        posix_kwds.update(kwd)
        super().__init__(**posix_kwds)

    def get_prefix(self) -> Optional[str]:
        return None

    def get_scheme(self) -> str:
        return "gximport"


class UserLibraryImportFilesSource(PosixFilesSource):
    plugin_type = "gxuserimport"
    plugin_kind = PluginKind.stock

    def __init__(self, **kwd: Unpack[PosixFilesSourceProperties]):
        posix_kwds: PosixFilesSourceProperties = dict(
            id="_userimport",
            root="${config.user_library_import_dir}/${user.email}",
            label="Library User Import Directory",
            doc="Galaxy's user library import directory",
        )
        posix_kwds.update(kwd)
        super().__init__(**posix_kwds)

    def get_prefix(self) -> Optional[str]:
        return None

    def get_scheme(self) -> str:
        return "gxuserimport"


__all__ = ("UserFtpFilesSource", "LibraryImportFilesSource", "UserLibraryImportFilesSource")
