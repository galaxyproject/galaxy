import logging
import os
from collections import (
    defaultdict,
    namedtuple,
)
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Set,
)

from galaxy import exceptions
from galaxy.util import plugin_config
from galaxy.util.dictifiable import Dictifiable

log = logging.getLogger(__name__)

FileSourcePath = namedtuple("FileSourcePath", ["file_source", "path"])


class ConfiguredFileSources:
    """Load plugins and resolve Galaxy URIs to FileSource objects."""

    def __init__(
        self,
        file_sources_config: "ConfiguredFileSourcesConfig",
        conf_file=None,
        conf_dict=None,
        load_stock_plugins=False,
    ):
        self._file_sources_config = file_sources_config
        self._plugin_classes = self._file_source_plugins_dict()
        file_sources = []
        if conf_file is not None:
            file_sources = self._load_plugins_from_file(conf_file)
        elif conf_dict is not None:
            plugin_source = plugin_config.plugin_source_from_dict(conf_dict)
            file_sources = self._parse_plugin_source(plugin_source)
        else:
            file_sources = []
        custom_sources_configured = len(file_sources) > 0
        if load_stock_plugins:
            stock_file_source_conf_dict = []

            def _ensure_loaded(plugin_type):
                for file_source in file_sources:
                    if file_source.plugin_type == plugin_type:
                        return
                stock_file_source_conf_dict.append({"type": plugin_type})

            if file_sources_config.ftp_upload_dir is not None:
                _ensure_loaded("gxftp")
            if file_sources_config.library_import_dir is not None:
                _ensure_loaded("gximport")
            if file_sources_config.user_library_import_dir is not None:
                _ensure_loaded("gxuserimport")
            if stock_file_source_conf_dict:
                stock_plugin_source = plugin_config.plugin_source_from_dict(stock_file_source_conf_dict)
                # insert at begining instead of append so FTP and library import appear
                # at the top of the list (presumably the most common options). Admins can insert
                # these explicitly for greater control.
                file_sources = self._parse_plugin_source(stock_plugin_source) + file_sources

        self._file_sources = file_sources
        self.custom_sources_configured = custom_sources_configured

    def _load_plugins_from_file(self, conf_file):
        plugin_source = plugin_config.plugin_source_from_path(conf_file)
        return self._parse_plugin_source(plugin_source)

    def _file_source_plugins_dict(self):
        import galaxy.files.sources

        return plugin_config.plugins_dict(galaxy.files.sources, "plugin_type")

    def _parse_plugin_source(self, plugin_source):
        extra_kwds = {
            "file_sources_config": self._file_sources_config,
        }
        return plugin_config.load_plugins(
            self._plugin_classes,
            plugin_source,
            extra_kwds,
            dict_to_list_key="id",
        )

    def get_file_source_path(self, uri):
        """Parse uri into a FileSource object and a path relative to its base."""
        if "://" not in uri:
            raise exceptions.RequestParameterInvalidException(f"Invalid uri [{uri}]")
        scheme, rest = uri.split("://", 1)
        if scheme not in self.get_schemes():
            raise exceptions.RequestParameterInvalidException(f"Unsupported URI scheme [{scheme}]")

        if scheme != "gxfiles":
            # prefix unused
            id_prefix = None
            path = rest
        else:
            if "/" in rest:
                id_prefix, path = rest.split("/", 1)
            else:
                id_prefix, path = rest, "/"
        file_source = self.get_file_source(id_prefix, scheme)
        return FileSourcePath(file_source, path)

    def validate_uri_root(self, uri, user_context):
        # validate a URI against Galaxy's configuration, environment, and the current
        # user. Throw appropriate exception if there is a problem with the files source
        # referenced by the URI.
        if uri.startswith("gxuserimport://"):
            user_login = user_context.email
            user_base_dir = self._file_sources_config.user_library_import_dir
            if user_base_dir is None:
                raise exceptions.ConfigDoesNotAllowException(
                    "The configuration of this Galaxy instance does not allow upload from user directories."
                )
            full_import_dir = os.path.join(user_base_dir, user_login)
            if not os.path.exists(full_import_dir):
                raise exceptions.ObjectNotFound("Your user import directory does not exist.")
        elif uri.startswith("gximport://"):
            base_dir = self._file_sources_config.library_import_dir
            if base_dir is None:
                raise exceptions.ConfigDoesNotAllowException(
                    "The configuration of this Galaxy instance does not allow usage of import directory."
                )
        elif uri.startswith("gxftp://"):
            user_ftp_base_dir = self._file_sources_config.ftp_upload_dir
            if user_ftp_base_dir is None:
                raise exceptions.ConfigDoesNotAllowException(
                    "The configuration of this Galaxy instance does not allow upload from FTP directories."
                )
            user_ftp_dir = user_context.ftp_dir
            if not user_ftp_dir or not os.path.exists(user_ftp_dir):
                raise exceptions.ObjectNotFound(
                    "Your FTP directory does not exist, attempting to upload files to it may cause it to be created."
                )

    def get_file_source(self, id_prefix, scheme):
        for file_source in self._file_sources:
            # gxfiles uses prefix to find plugin, other scheme are assumed to have
            # at most one file_source.
            if scheme != file_source.get_scheme():
                continue
            prefix_match = scheme != "gxfiles" or file_source.get_prefix() == id_prefix
            if prefix_match:
                return file_source

    def looks_like_uri(self, path_or_uri):
        # is this string a URI this object understands how to realize
        if path_or_uri.startswith("gx") and "://" in path_or_uri:
            for scheme in self.get_schemes():
                if path_or_uri.startswith(f"{scheme}://"):
                    return True

        return False

    def get_schemes(self):
        schemes = set()
        for file_source in self._file_sources:
            schemes.add(file_source.get_scheme())
        return schemes

    def plugins_to_dict(
        self, for_serialization: bool = False, user_context: Optional["FileSourceDictifiable"] = None
    ) -> List[Dict[str, Any]]:
        rval = []
        for file_source in self._file_sources:
            if not file_source.user_has_access(user_context):
                continue
            el = file_source.to_dict(for_serialization=for_serialization, user_context=user_context)
            rval.append(el)
        return rval

    def to_dict(
        self, for_serialization: bool = False, user_context: Optional["FileSourceDictifiable"] = None
    ) -> Dict[str, Any]:
        return {
            "file_sources": self.plugins_to_dict(for_serialization=for_serialization, user_context=user_context),
            "config": self._file_sources_config.to_dict(),
        }

    @staticmethod
    def from_app_config(config):
        config_file = config.file_sources_config_file
        config_dict = None
        if not config_file or not os.path.exists(config_file):
            config_file = None
            config_dict = config.file_sources
        file_sources_config = ConfiguredFileSourcesConfig.from_app_config(config)
        return ConfiguredFileSources(
            file_sources_config, conf_file=config_file, conf_dict=config_dict, load_stock_plugins=True
        )

    @staticmethod
    def from_dict(as_dict):
        if as_dict is not None:
            sources_as_dict = as_dict["file_sources"]
            config_as_dict = as_dict["config"]
            file_sources_config = ConfiguredFileSourcesConfig.from_dict(config_as_dict)
        else:
            sources_as_dict = []
            file_sources_config = ConfiguredFileSourcesConfig()
        return ConfiguredFileSources(file_sources_config, conf_dict=sources_as_dict)


class ConfiguredFileSourcesConfig:
    def __init__(
        self,
        symlink_allowlist=None,
        library_import_dir=None,
        user_library_import_dir=None,
        ftp_upload_dir=None,
        ftp_upload_purge=True,
    ):
        symlink_allowlist = symlink_allowlist or []
        self.symlink_allowlist = symlink_allowlist
        self.library_import_dir = library_import_dir
        self.user_library_import_dir = user_library_import_dir
        self.ftp_upload_dir = ftp_upload_dir
        self.ftp_upload_purge = ftp_upload_purge

    @staticmethod
    def from_app_config(config):
        # Formalize what we read in from config to create a more clear interface
        # for this component.
        kwds = {}
        kwds["symlink_allowlist"] = getattr(config, "user_library_import_symlink_allowlist", [])
        kwds["library_import_dir"] = getattr(config, "library_import_dir", None)
        kwds["user_library_import_dir"] = getattr(config, "user_library_import_dir", None)
        kwds["ftp_upload_dir"] = getattr(config, "ftp_upload_dir", None)
        kwds["ftp_upload_purge"] = getattr(config, "ftp_upload_purge", True)
        return ConfiguredFileSourcesConfig(**kwds)

    def to_dict(self):
        return {
            "symlink_allowlist": self.symlink_allowlist,
            "library_import_dir": self.library_import_dir,
            "user_library_import_dir": self.user_library_import_dir,
            "ftp_upload_dir": self.ftp_upload_dir,
            "ftp_upload_purge": self.ftp_upload_purge,
        }

    @staticmethod
    def from_dict(as_dict):
        return ConfiguredFileSourcesConfig(
            symlink_allowlist=as_dict["symlink_allowlist"],
            library_import_dir=as_dict["library_import_dir"],
            user_library_import_dir=as_dict["user_library_import_dir"],
            ftp_upload_dir=as_dict["ftp_upload_dir"],
            ftp_upload_purge=as_dict["ftp_upload_purge"],
        )


class FileSourceDictifiable(Dictifiable):
    dict_collection_visible_keys = ("email", "username", "ftp_dir", "preferences", "is_admin")

    def to_dict(self, view="collection", value_mapper=None):
        rval = super().to_dict(view=view, value_mapper=value_mapper)
        rval["role_names"] = list(self.role_names)
        rval["group_names"] = list(self.group_names)
        return rval

    @property
    def role_names(self) -> Set[str]:
        raise NotImplementedError

    @property
    def group_names(sefl) -> Set[str]:
        raise NotImplementedError


class ProvidesUserFileSourcesUserContext(FileSourceDictifiable):
    """Implement a FileSourcesUserContext from a Galaxy ProvidesUserContext (e.g. trans)."""

    def __init__(self, trans):
        self.trans = trans

    @property
    def email(self):
        user = self.trans.user
        return user and user.email

    @property
    def username(self):
        user = self.trans.user
        return user and user.username

    @property
    def ftp_dir(self):
        return self.trans.user_ftp_dir

    @property
    def preferences(self):
        user = self.trans.user
        return user and user.extra_preferences or defaultdict(lambda: None)

    @property
    def role_names(self) -> Set[str]:
        """The set of role names of this user."""
        user = self.trans.user
        return {ura.role.name for ura in user.roles} if user else set()

    @property
    def group_names(self) -> Set[str]:
        """The set of group names to which this user belongs."""
        user = self.trans.user
        return {ugr.group.name for ugr in user.groups} if user else set()

    @property
    def is_admin(self):
        """Whether this user is an administrator."""
        return self.trans.user_is_admin

    @property
    def user_vault(self):
        """User vault namespace"""
        user_vault = self.trans.user_vault
        return user_vault or defaultdict(lambda: None)

    @property
    def app_vault(self):
        """App vault namespace"""
        vault = self.trans.app.vault
        return vault or defaultdict(lambda: None)


class DictFileSourcesUserContext(FileSourceDictifiable):
    def __init__(self, **kwd):
        self._kwd = kwd

    @property
    def email(self):
        return self._kwd.get("email")

    @property
    def username(self):
        return self._kwd.get("username")

    @property
    def ftp_dir(self):
        return self._kwd.get("user_ftp_dir")

    @property
    def preferences(self):
        return self._kwd.get("preferences")

    @property
    def role_names(self):
        return set(self._kwd.get("role_names", []))

    @property
    def group_names(self):
        return set(self._kwd.get("group_names", []))

    @property
    def is_admin(self):
        return self._kwd.get("is_admin")

    @property
    def user_vault(self):
        return self._kwd.get("user_vault")

    @property
    def app_vault(self):
        return self._kwd.get("app_vault")
