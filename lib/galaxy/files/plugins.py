from typing import (
    cast,
    List,
    Optional,
    Type,
    TYPE_CHECKING,
)

from galaxy.util.config_parsers import parse_allowlist_ips
from galaxy.util.plugin_config import (
    load_plugins,
    PluginConfigSource,
    plugins_dict,
)

if TYPE_CHECKING:
    from galaxy.files.sources import BaseFilesSource


class FileSourcePluginsConfig:
    symlink_allowlist: List[str]
    fetch_url_allowlist: List[str]
    library_import_dir: Optional[str]
    user_library_import_dir: Optional[str]
    ftp_upload_dir: Optional[str]
    ftp_upload_purge: bool
    tmp_dir: Optional[str]
    webdav_use_temp_files: Optional[bool]
    listings_expiry_time: Optional[int]

    def __init__(
        self,
        symlink_allowlist=None,
        fetch_url_allowlist=None,
        library_import_dir=None,
        user_library_import_dir=None,
        ftp_upload_dir=None,
        ftp_upload_purge=True,
        tmp_dir=None,
        webdav_use_temp_files=None,
        listings_expiry_time=None,
    ):
        symlink_allowlist = symlink_allowlist or []
        fetch_url_allowlist = fetch_url_allowlist or []
        self.symlink_allowlist = symlink_allowlist
        self.fetch_url_allowlist = fetch_url_allowlist
        self.library_import_dir = library_import_dir
        self.user_library_import_dir = user_library_import_dir
        self.ftp_upload_dir = ftp_upload_dir
        self.ftp_upload_purge = ftp_upload_purge
        self.tmp_dir = tmp_dir
        self.webdav_use_temp_files = webdav_use_temp_files
        self.listings_expiry_time = listings_expiry_time

    @staticmethod
    def from_app_config(config):
        # Formalize what we read in from config to create a more clear interface
        # for this component.
        kwds = {}
        kwds["symlink_allowlist"] = config.user_library_import_symlink_allowlist
        kwds["fetch_url_allowlist"] = [str(ip) for ip in config.fetch_url_allowlist_ips]
        kwds["library_import_dir"] = config.library_import_dir
        kwds["user_library_import_dir"] = config.user_library_import_dir
        kwds["ftp_upload_dir"] = config.ftp_upload_dir
        kwds["ftp_upload_purge"] = config.ftp_upload_purge
        kwds["tmp_dir"] = config.file_source_temp_dir
        kwds["webdav_use_temp_files"] = config.file_source_webdav_use_temp_files
        kwds["listings_expiry_time"] = config.file_source_listings_expiry_time

        return FileSourcePluginsConfig(**kwds)

    def to_dict(self):
        return {
            "symlink_allowlist": self.symlink_allowlist,
            "fetch_url_allowlist": self.fetch_url_allowlist,
            "library_import_dir": self.library_import_dir,
            "user_library_import_dir": self.user_library_import_dir,
            "ftp_upload_dir": self.ftp_upload_dir,
            "ftp_upload_purge": self.ftp_upload_purge,
            "tmp_dir": self.tmp_dir,
            "webdav_use_temp_files": self.webdav_use_temp_files,
            "listings_expiry_time": self.listings_expiry_time,
        }

    @staticmethod
    def from_dict(as_dict):
        return FileSourcePluginsConfig(
            symlink_allowlist=as_dict["symlink_allowlist"],
            fetch_url_allowlist=parse_allowlist_ips(as_dict["fetch_url_allowlist"]),
            library_import_dir=as_dict["library_import_dir"],
            user_library_import_dir=as_dict["user_library_import_dir"],
            ftp_upload_dir=as_dict["ftp_upload_dir"],
            ftp_upload_purge=as_dict["ftp_upload_purge"],
            # Always provided for new jobs, remove in 25.0
            tmp_dir=as_dict.get("tmp_dir"),
            webdav_use_temp_files=as_dict.get("webdav_use_temp_files"),
            listings_expiry_time=as_dict.get("listings_expiry_time"),
        )


class FileSourcePluginLoader:

    def __init__(self):
        self._plugin_classes = self._file_source_plugins_dict()

    def _file_source_plugins_dict(self):
        import galaxy.files.sources

        return plugins_dict(galaxy.files.sources, "plugin_type")

    def get_plugin_type_class(self, plugin_type: str) -> Type["BaseFilesSource"]:
        return cast(Type["BaseFilesSource"], self._plugin_classes[plugin_type])

    def load_plugins(
        self, plugin_source: PluginConfigSource, file_source_plugin_config: FileSourcePluginsConfig
    ) -> List["BaseFilesSource"]:
        extra_kwds = {
            "file_sources_config": file_source_plugin_config,
        }
        return load_plugins(
            self._plugin_classes,
            plugin_source,
            extra_kwds,
            dict_to_list_key="id",
        )


__all__ = (
    "FileSourcePluginLoader",
    "FileSourcePluginsConfig",
)
