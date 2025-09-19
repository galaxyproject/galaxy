"""Static Galaxy file sources - ftp and libraries."""

from typing import Optional

from galaxy.files.sources import PluginKind
from .posix import (
    PosixFilesSource,
    PosixTemplateConfiguration,
)


class UserFtpFilesSource(PosixFilesSource):
    plugin_type = "gxftp"
    plugin_kind = PluginKind.stock

    def __init__(self, template_config: PosixTemplateConfiguration):
        defaults = dict(
            id="_ftp",
            root="${user.ftp_dir}",
            label="FTP Directory",
            doc="Galaxy User's FTP Directory",
            writable=True,
        )
        template_config = self._apply_defaults_to_template(defaults, template_config)
        super().__init__(template_config)
        if not self.template_config.delete_on_realize:
            # If delete_on_realize is not set, use the default from the file sources config.
            self.template_config.delete_on_realize = self.template_config.file_sources_config.ftp_upload_purge

    def get_prefix(self) -> Optional[str]:
        return None

    def get_scheme(self) -> str:
        return "gxftp"


class LibraryImportFilesSource(PosixFilesSource):
    plugin_type = "gximport"
    plugin_kind = PluginKind.stock

    def __init__(self, template_config: PosixTemplateConfiguration):
        defaults = dict(
            id="_import",
            root="${config.library_import_dir}",
            label="Library Import Directory",
            doc="Galaxy's library import directory",
        )
        template_config = self._apply_defaults_to_template(defaults, template_config)
        super().__init__(template_config)

    def get_prefix(self) -> Optional[str]:
        return None

    def get_scheme(self) -> str:
        return "gximport"


class UserLibraryImportFilesSource(PosixFilesSource):
    plugin_type = "gxuserimport"
    plugin_kind = PluginKind.stock

    def __init__(self, template_config: PosixTemplateConfiguration):
        defaults = dict(
            id="_userimport",
            root="${config.user_library_import_dir}/${user.email}",
            label="Library User Import Directory",
            doc="Galaxy's user library import directory",
        )
        template_config = self._apply_defaults_to_template(defaults, template_config)
        super().__init__(template_config)

    def get_prefix(self) -> Optional[str]:
        return None

    def get_scheme(self) -> str:
        return "gxuserimport"


__all__ = ("UserFtpFilesSource", "LibraryImportFilesSource", "UserLibraryImportFilesSource")
