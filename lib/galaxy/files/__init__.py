import logging
import os
from collections import defaultdict
from typing import (
    Any,
    Callable,
    Dict,
    List,
    NamedTuple,
    Optional,
    Protocol,
    Set,
)

from galaxy import exceptions
from galaxy.files.sources import (
    BaseFilesSource,
    FilesSourceProperties,
    PluginKind,
)
from galaxy.util.dictifiable import Dictifiable
from galaxy.util.plugin_config import (
    plugin_source_from_dict,
    plugin_source_from_path,
    PluginConfigSource,
    PluginConfigsT,
)
from .plugins import (
    FileSourcePluginLoader,
    FileSourcePluginsConfig,
)

log = logging.getLogger(__name__)


class FileSourcePath(NamedTuple):
    file_source: BaseFilesSource
    path: str


class FileSourceScore(NamedTuple):
    file_source: BaseFilesSource
    score: int


class NoMatchingFileSource(Exception):
    pass


class UserDefinedFileSources(Protocol):
    """Entry-point for Galaxy to inject user-defined object stores.

    Supplied object of this class is used to write out concrete
    description of file sources when serializing all file sources
    available to a user.
    """

    def validate_uri_root(self, uri: str, user_context: "FileSourcesUserContext") -> None:
        pass

    def find_best_match(self, url: str) -> Optional[FileSourceScore]:
        pass

    def user_file_sources_to_dicts(
        self,
        for_serialization: bool,
        user_context: "FileSourcesUserContext",
        browsable_only: Optional[bool] = False,
        include_kind: Optional[Set[PluginKind]] = None,
        exclude_kind: Optional[Set[PluginKind]] = None,
    ) -> List[FilesSourceProperties]:
        """Write out user file sources as list of config dictionaries."""
        # config_dicts: List[FilesSourceProperties] = []
        # for file_source in self.user_file_sources():
        #     as_dict = file_source.to_dict(for_serialization=for_serialization, user_context=user_context)
        #     config_dicts.append(as_dict)
        # return config_dicts


class NullUserDefinedFileSources(UserDefinedFileSources):

    def validate_uri_root(self, uri: str, user_context: "FileSourcesUserContext") -> None:
        return None

    def find_best_match(self, url: str) -> Optional[FileSourceScore]:
        return None

    def user_file_sources_to_dicts(
        self,
        for_serialization: bool,
        user_context: "FileSourcesUserContext",
        browsable_only: Optional[bool] = False,
        include_kind: Optional[Set[PluginKind]] = None,
        exclude_kind: Optional[Set[PluginKind]] = None,
    ) -> List[FilesSourceProperties]:
        return []


def _ensure_user_defined_file_sources(
    user_defined_file_sources: Optional[UserDefinedFileSources] = None,
) -> UserDefinedFileSources:
    if user_defined_file_sources is not None:
        return user_defined_file_sources
    else:
        return NullUserDefinedFileSources()


class ConfiguredFileSourcesConf:
    conf_dict: Optional[PluginConfigsT]
    conf_file: Optional[str]

    def __init__(self, conf_dict: Optional[PluginConfigsT] = None, conf_file: Optional[str] = None):
        self.conf_dict = conf_dict
        self.conf_file = conf_file

    @staticmethod
    def from_app_config(config):
        config_file = config.file_sources_config_file
        config_dict = None
        if not config_file or not os.path.exists(config_file):
            config_file = None
            config_dict = config.file_sources
        return ConfiguredFileSourcesConf(config_dict, config_file)


class ConfiguredFileSources:
    """Load plugins and resolve Galaxy URIs to FileSource objects."""

    _file_sources: List[BaseFilesSource]
    _plugin_loader: FileSourcePluginLoader
    _user_defined_file_sources: UserDefinedFileSources

    def __init__(
        self,
        file_sources_config: FileSourcePluginsConfig,
        configured_file_source_conf: Optional[ConfiguredFileSourcesConf] = None,
        load_stock_plugins: bool = False,
        plugin_loader: Optional[FileSourcePluginLoader] = None,
        user_defined_file_sources: Optional[UserDefinedFileSources] = None,
    ):
        self._file_sources_config = file_sources_config
        self._plugin_loader = plugin_loader or FileSourcePluginLoader()
        self._user_defined_file_sources = _ensure_user_defined_file_sources(user_defined_file_sources)
        file_sources: List[BaseFilesSource] = []
        if configured_file_source_conf is None:
            configured_file_source_conf = ConfiguredFileSourcesConf(conf_dict=[])
        if configured_file_source_conf.conf_file is not None:
            file_sources = self._load_plugins_from_file(configured_file_source_conf.conf_file)
        elif configured_file_source_conf.conf_dict is not None:
            plugin_source = plugin_source_from_dict(configured_file_source_conf.conf_dict)
            file_sources = self._parse_plugin_source(plugin_source)
        else:
            file_sources = []
        custom_sources_configured = len(file_sources) > 0 or (user_defined_file_sources is not None)
        if load_stock_plugins:
            stock_file_source_conf_dict = []

            def _ensure_loaded(plugin_type):
                for file_source in file_sources:
                    if file_source.plugin_type == plugin_type:
                        return
                stock_file_source_conf_dict.append({"type": plugin_type})

            _ensure_loaded("http")
            _ensure_loaded("base64")
            _ensure_loaded("drs")

            if file_sources_config.ftp_upload_dir is not None:
                _ensure_loaded("gxftp")
            if file_sources_config.library_import_dir is not None:
                _ensure_loaded("gximport")
            if file_sources_config.user_library_import_dir is not None:
                _ensure_loaded("gxuserimport")

            if stock_file_source_conf_dict:
                stock_plugin_source = plugin_source_from_dict(stock_file_source_conf_dict)
                # insert at beginning instead of append so FTP and library import appear
                # at the top of the list (presumably the most common options). Admins can insert
                # these explicitly for greater control.
                file_sources = self._parse_plugin_source(stock_plugin_source) + file_sources

        self._file_sources = file_sources
        self.custom_sources_configured = custom_sources_configured

    def _load_plugins_from_file(self, conf_file: str):
        plugin_source = plugin_source_from_path(conf_file)
        return self._parse_plugin_source(plugin_source)

    def _parse_plugin_source(self, plugin_source: PluginConfigSource):
        return self._plugin_loader.load_plugins(plugin_source, self._file_sources_config)

    def find_best_match(self, url: str) -> Optional[BaseFilesSource]:
        """Returns the best matching file source for handling a particular url. Each filesource scores its own
        ability to match a particular url, and the highest scorer with a score > 0 is selected."""
        scores = [FileSourceScore(file_source, file_source.score_url_match(url)) for file_source in self._file_sources]
        user_best_score = self._user_defined_file_sources.find_best_match(url)
        if user_best_score is not None:
            scores.append(user_best_score)
        scores.sort(key=lambda f: f.score, reverse=True)
        return next((fsscore.file_source for fsscore in scores if fsscore.score > 0), None)

    def get_file_source_path(self, uri):
        """Parse uri into a FileSource object and a path relative to its base."""
        if "://" not in uri:
            raise exceptions.RequestParameterInvalidException(f"Invalid uri [{uri}]")
        file_source = self.find_best_match(uri)
        if not file_source:
            raise exceptions.RequestParameterInvalidException(f"Could not find handler for URI [{uri}]")
        path = file_source.to_relative_path(uri)
        return FileSourcePath(file_source, path)

    def validate_uri_root(self, uri: str, user_context: "FileSourcesUserContext"):
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
            if user_login is None:
                raise exceptions.AuthenticationRequired("Must be logged in to use this feature.")
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
        self._user_defined_file_sources.validate_uri_root(uri, user_context)

    def looks_like_uri(self, path_or_uri):
        # is this string a URI this object understands how to realize
        file_source = self.find_best_match(path_or_uri)
        if file_source:
            return True
        else:
            return False

    def plugins_to_dict(
        self,
        for_serialization: bool = False,
        user_context: "OptionalUserContext" = None,
        browsable_only: Optional[bool] = False,
        include_kind: Optional[Set[PluginKind]] = None,
        exclude_kind: Optional[Set[PluginKind]] = None,
    ) -> List[FilesSourceProperties]:
        rval: List[FilesSourceProperties] = []
        for file_source in self._file_sources:
            if not file_source.user_has_access(user_context):
                continue
            if include_kind and file_source.plugin_kind not in include_kind:
                continue
            if exclude_kind and file_source.plugin_kind in exclude_kind:
                continue
            if browsable_only and not file_source.get_browsable():
                continue
            el = file_source.to_dict(for_serialization=for_serialization, user_context=user_context)
            rval.append(el)
        if user_context:
            rval.extend(
                self._user_defined_file_sources.user_file_sources_to_dicts(
                    for_serialization,
                    user_context,
                    browsable_only=browsable_only,
                    include_kind=include_kind,
                    exclude_kind=exclude_kind,
                )
            )
        return rval

    def to_dict(self, for_serialization: bool = False, user_context: "OptionalUserContext" = None) -> Dict[str, Any]:
        return {
            "file_sources": self.plugins_to_dict(for_serialization=for_serialization, user_context=user_context),
            "config": self._file_sources_config.to_dict(),
        }

    @staticmethod
    def from_dict(as_dict, load_stock_plugins=False):
        if as_dict is not None:
            sources_as_dict = as_dict["file_sources"]
            config_as_dict = as_dict["config"]
            file_sources_config = FileSourcePluginsConfig.from_dict(config_as_dict)
        else:
            sources_as_dict = []
            file_sources_config = FileSourcePluginsConfig()
        configured_file_sources_conf = ConfiguredFileSourcesConf(conf_dict=sources_as_dict)
        return ConfiguredFileSources(
            file_sources_config, configured_file_sources_conf, load_stock_plugins=load_stock_plugins
        )


class NullConfiguredFileSources(ConfiguredFileSources):
    def __init__(
        self,
    ):
        super().__init__(FileSourcePluginsConfig(), ConfiguredFileSourcesConf(conf_dict=[]))


class DictifiableFilesSourceContext(Protocol):
    @property
    def role_names(self) -> Set[str]: ...

    @property
    def group_names(self) -> Set[str]: ...

    @property
    def file_sources(self) -> ConfiguredFileSources: ...

    def to_dict(
        self, view: str = "collection", value_mapper: Optional[Dict[str, Callable]] = None
    ) -> Dict[str, Any]: ...


class FileSourceDictifiable(Dictifiable, DictifiableFilesSourceContext):
    dict_collection_visible_keys = ("email", "username", "ftp_dir", "preferences", "is_admin")

    def to_dict(self, view="collection", value_mapper: Optional[Dict[str, Callable]] = None) -> Dict[str, Any]:
        rval = super().to_dict(view=view, value_mapper=value_mapper)
        rval["role_names"] = list(self.role_names)
        rval["group_names"] = list(self.group_names)
        return rval


class FileSourcesUserContext(DictifiableFilesSourceContext, Protocol):

    @property
    def email(self) -> Optional[str]: ...

    @property
    def username(self) -> Optional[str]: ...

    @property
    def ftp_dir(self) -> Optional[str]: ...

    @property
    def preferences(self) -> Dict[str, Any]: ...

    @property
    def is_admin(self) -> bool: ...

    @property
    def user_vault(self) -> Dict[str, Any]: ...

    @property
    def app_vault(self) -> Dict[str, Any]: ...

    @property
    def anonymous(self) -> bool: ...


OptionalUserContext = Optional[FileSourcesUserContext]


class ProvidesFileSourcesUserContext(FileSourcesUserContext, FileSourceDictifiable):
    """Implement a FileSourcesUserContext from a Galaxy ProvidesUserContext (e.g. trans)."""

    def __init__(self, trans, **kwargs):
        self.trans = trans

    @property
    def email(self) -> Optional[str]:
        user = self.trans.user
        return user and user.email

    @property
    def username(self) -> Optional[str]:
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
        role_names = set()
        if user:
            role_names = {ura.role.name for ura in user.roles}
            role_names.add(user.email)  # User's private role may have a generic name, so add user's email explicitly.
        return role_names

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

    @property
    def file_sources(self):
        return self.trans.app.file_sources

    @property
    def anonymous(self) -> bool:
        return self.trans.anonymous


class DictFileSourcesUserContext(FileSourcesUserContext, FileSourceDictifiable):
    def __init__(self, **kwd):
        self._kwd = kwd

    @property
    def email(self):
        return self._kwd.get("email")

    @property
    def username(self) -> Optional[str]:
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

    @property
    def file_sources(self):
        return self._kwd.get("file_sources")

    @property
    def anonymous(self) -> bool:
        return not bool(self._kwd.get("username"))
