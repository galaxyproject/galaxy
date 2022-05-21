"""Static Galaxy file sources - ftp and libraries."""

from .posix import PosixFilesSource


class UserFtpFilesSource(PosixFilesSource):
    plugin_type = "gxftp"

    def __init__(self, label="FTP Directory", doc="Galaxy User's FTP Directory", root="${user.ftp_dir}", **kwd):
        posix_kwds = dict(
            id="_ftp",
            root=root,
            label=label,
            doc=doc,
            writable=True,
        )
        posix_kwds.update(kwd)
        if "delete_on_realize" not in posix_kwds:
            file_sources_config = kwd["file_sources_config"]
            posix_kwds["delete_on_realize"] = file_sources_config.ftp_upload_purge
        super().__init__(**posix_kwds)

    def get_prefix(self):
        return None

    def get_scheme(self):
        return "gxftp"


class LibraryImportFilesSource(PosixFilesSource):
    plugin_type = "gximport"

    def __init__(
        self,
        label="Library Import Directory",
        doc="Galaxy's library import directory",
        root="${config.library_import_dir}",
        **kwd,
    ):
        posix_kwds = dict(
            id="_import",
            root=root,
            label=label,
            doc=doc,
        )
        posix_kwds.update(kwd)
        super().__init__(**posix_kwds)

    def get_prefix(self):
        return None

    def get_scheme(self):
        return "gximport"


class UserLibraryImportFilesSource(PosixFilesSource):
    plugin_type = "gxuserimport"

    def __init__(
        self,
        label="Library User Import Directory",
        doc="Galaxy's user library import directory",
        root="${config.user_library_import_dir}/${user.email}",
        **kwd,
    ):
        posix_kwds = dict(
            id="_userimport",
            root=root,
            label=label,
            doc=doc,
        )
        posix_kwds.update(kwd)
        super().__init__(**posix_kwds)

    def get_prefix(self):
        return None

    def get_scheme(self):
        return "gxuserimport"


__all__ = ("UserFtpFilesSource", "LibraryImportFilesSource", "UserLibraryImportFilesSource")
