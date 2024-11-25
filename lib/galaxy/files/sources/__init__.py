import abc
import os
import time
from dataclasses import (
    dataclass,
    field,
)
from enum import Enum
from typing import (
    Any,
    ClassVar,
    List,
    Optional,
    Set,
    Tuple,
    Type,
    TYPE_CHECKING,
    Union,
)

from typing_extensions import (
    Literal,
    NotRequired,
    TypedDict,
)

from galaxy.exceptions import (
    ConfigurationError,
    ItemAccessibilityException,
    RequestParameterInvalidException,
)
from galaxy.files.plugins import FileSourcePluginsConfig
from galaxy.util.bool_expressions import (
    BooleanExpressionEvaluator,
    TokenContainedEvaluator,
)
from galaxy.util.template import fill_template

DEFAULT_SCHEME = "gxfiles"
DEFAULT_WRITABLE = False
DEFAULT_PAGE_LIMIT = 25

if TYPE_CHECKING:
    from galaxy.files import (
        FileSourcesUserContext,
        OptionalUserContext,
    )


class PluginKind(str, Enum):
    """Enum to distinguish between different kinds or categories of plugins."""

    rfs = "rfs"
    """Remote File System

    A remote file system is a file source that is backed by a remote file system
    that is accessible via a URI. Examples include FTP, SFTP, S3, etc.
    """

    drs = "drs"
    """Data Repository Service

    A data repository service is a file source that is backed by a remote data
    repository service implementing the (DRS) API which provides a generic interface
    to data repositories so data consumers, including workflow systems,
    can access data in a single, standard way regardless of where it's stored and how it's managed.
    """

    rdm = "rdm"
    """Research Data Management

    A research data management file source is a file source that is backed by a remote
    research data management system that can provide DOIs. Examples include InvenioRDM, Zenodo, etc.
    """

    stock = "stock"
    """Stock Plugin

    A stock plugin is a file source that is shipped with Galaxy and covers common
    use cases. Examples include the UserFTP, LibraryImport, UserLibraryImport, etc.
    """


class FileSourceSupports(TypedDict):
    """Feature support flags for a file source plugin"""

    # Indicates whether the file source supports pagination for listing files
    pagination: NotRequired[bool]
    # Indicates whether the file source supports server-side search for listing files
    search: NotRequired[bool]
    # Indicates whether the file source supports server-side sorting for listing files
    sorting: NotRequired[bool]


class FilesSourceProperties(TypedDict):
    """Initial set of properties used to initialize a filesource.

    Filesources can extend this typed dict to define any additional
    filesource specific properties.
    """

    file_sources_config: NotRequired[FileSourcePluginsConfig]
    id: NotRequired[str]
    label: NotRequired[str]
    doc: NotRequired[Optional[str]]
    scheme: NotRequired[str]
    writable: NotRequired[bool]
    requires_roles: NotRequired[Optional[str]]
    requires_groups: NotRequired[Optional[str]]
    disable_templating: NotRequired[Optional[bool]]
    # API helper values
    uri_root: NotRequired[str]
    type: NotRequired[str]
    browsable: NotRequired[bool]
    url: NotRequired[Optional[str]]
    supports: NotRequired[FileSourceSupports]


@dataclass
class FilesSourceOptions:
    """Options to control behavior of file source operations, such as realize_to, write_from and list."""

    # Indicates access to the FS operation with intent to write.
    # Even if a file source is "writeable" some directories (or elements) may be restricted or read-only
    # so those should be skipped while browsing with writeable=True.
    writeable: Optional[bool] = False

    # Property overrides for values initially configured through the constructor. For example
    # the HTTPFilesSource passes in additional http_headers through these properties, which
    # are merged with constructor defined http_headers. The interpretation of these properties
    # are filesystem specific.
    extra_props: Optional[FilesSourceProperties] = field(default_factory=lambda: FilesSourceProperties())


class EntryData(TypedDict):
    """Provides data to create a new entry in a file source."""

    name: str
    # May contain additional properties depending on the file source


class Entry(TypedDict):
    """Represents the result of creating a new entry in a file source."""

    name: str
    uri: str
    # May contain additional properties depending on the file source
    external_link: NotRequired[str]


class RemoteEntry(TypedDict):
    name: str
    uri: str
    path: str


TDirectoryClass = TypedDict("TDirectoryClass", {"class": Literal["Directory"]})
TFileClass = TypedDict("TFileClass", {"class": Literal["File"]})


class RemoteDirectory(RemoteEntry, TDirectoryClass):
    pass


class RemoteFile(RemoteEntry, TFileClass):
    size: int
    ctime: str


AnyRemoteEntry = Union[RemoteDirectory, RemoteFile]


class SingleFileSource(metaclass=abc.ABCMeta):
    """
    Represents a protocol handler for a single remote file that can be read by or written to by Galaxy.
    A remote file source can typically handle a url like `https://galaxyproject.org/myfile.txt` or
    `drs://myserver/123456`. The filesource abstraction allows programmatic control over the specific source
    to access, injection of credentials and access control. Filesources are typically listed and configured
    through `file_sources_conf.yml` or programmatically, as required.

    Filesources can be contextualized with a `user_context`, which contains information related to the current
    user attempting to access that filesource such as the username, preferences, roles etc., which can then
    be used by the filesource to make authorization decisions or inject credentials.

    Filesources are loaded through Galaxy's plugin system in `galaxy.util.plugin_config`.
    """

    @abc.abstractmethod
    def get_writable(self) -> bool:
        """Return a boolean indicating whether this target is writable."""

    @abc.abstractmethod
    def user_has_access(self, user_context: "OptionalUserContext") -> bool:
        """Return a boolean indicating whether the user can access the FileSource."""

    @abc.abstractmethod
    def realize_to(
        self,
        source_path: str,
        native_path: str,
        user_context: "OptionalUserContext" = None,
        opts: Optional[FilesSourceOptions] = None,
    ):
        """Realize source path (relative to uri root) to local file system path.

        :param source_path: url of the source file to copy from. e.g. `https://galaxyproject.org/myfile.txt`
        :type source_path: str
        :param native_path: local path to write to. e.g. `/tmp/myfile.txt`
        :type native_path: str
        :param user_context: A user context , defaults to None
        :type user_context: OptionalUserContext, optional
        :param opts: A set of options to exercise additional control over the realize_to method. Filesource specific, defaults to None
        :type opts: Optional[FilesSourceOptions], optional
        """

    @abc.abstractmethod
    def write_from(
        self,
        target_path: str,
        native_path: str,
        user_context: "OptionalUserContext" = None,
        opts: Optional[FilesSourceOptions] = None,
    ) -> str:
        """Write file at native path to target_path (relative to uri root).

        :param target_path: url of the target file to write to within the filesource. e.g. `gxfiles://myftp1/myfile.txt`
        :type target_path: str
        :param native_path: The local file to read. e.g. `/tmp/myfile.txt`
        :type native_path: str
        :param user_context: A user context , defaults to None
        :type user_context: _type_, optional
        :param opts: A set of options to exercise additional control over the write_from method. Filesource specific, defaults to None
        :type opts: Optional[FilesSourceOptions], optional
        :return: Actual url of the written file, fixed by the service backing the FileSource. May differ from the target
            path.
        :rtype: str
        """

    @abc.abstractmethod
    def score_url_match(self, url: str) -> int:
        """Return how well a given url matches this filesource. A score greater than zero indicates that
        this filesource is capable of processing the given url.

        Scoring is based on the following rules:
        a. The maximum score will be the length of the url.
        b. The minimum score will be the length of the scheme if the filesource can handle the file.
        c. The score will be zero if the filesource cannot handle the file.

        For example, given the following file source config:
        - type: webdav
          id: cloudstor
          url: "https://cloudstor.aarnet.edu.au"
          root: "/plus/remote.php/webdav"
        - type: http
          id: generic_http

        the generic http handler may return a score of 8 for the url
        https://cloudstor.aarnet.edu.au/plus/remote.php/webdav/myfolder/myfile.txt,
        as it can handle only the scheme part of the url. A webdav handler may return a score of
        55 for the same url, as both the webdav url and root combined are a specific match.

        :param url: The url to score for a match against this filesource.
        :type url: str
        :return: A score based on the aforementioned rules.
        :rtype: int
        """

    @abc.abstractmethod
    def to_relative_path(self, url: str) -> str:
        """Convert this url to a filesource relative path. For example, given the url
        `gxfiles://mysource1/myfile.txt` it will return `/myfile.txt`. Protocols directly understood
        by the handler need not be relativized. For example, the url `s3://bucket/myfile.txt` can be
        returned unchanged."""

    @abc.abstractmethod
    def to_dict(self, for_serialization=False, user_context: "OptionalUserContext" = None) -> FilesSourceProperties:
        """Return a dictified representation of this FileSource instance.

        If ``user_context`` is supplied, properties should be written so user
        context doesn't need to be present after the plugin is re-hydrated.
        """


class SupportsBrowsing(metaclass=abc.ABCMeta):
    """An interface indicating that this filesource is browsable.

    Browsable filesources will typically have a root uri from which to start browsing.
    e.g. In an s3 bucket, the root uri may be gxfiles://bucket1/

    They will also have a list method to list files in a specific path within the filesource.
    """

    @abc.abstractmethod
    def get_uri_root(self) -> str:
        """Return a prefix for the root (e.g. gxfiles://prefix/)."""

    @abc.abstractmethod
    def list(
        self,
        path="/",
        recursive=False,
        user_context: "OptionalUserContext" = None,
        opts: Optional[FilesSourceOptions] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        query: Optional[str] = None,
        sort_by: Optional[str] = None,
    ) -> Tuple[List[AnyRemoteEntry], int]:
        """Return a list of 'Directory's and 'File's and the total count in a tuple."""


class FilesSource(SingleFileSource, SupportsBrowsing):
    """Represents a combined interface for single or browsable filesources.
    The `get_browsable` method can be used to determine whether the filesource is browsable and
    implements the `SupportsBrowsing` interface.
    """

    plugin_type: ClassVar[str]

    @abc.abstractmethod
    def get_browsable(self) -> bool:
        """Return true if the filesource implements the SupportsBrowsing interface."""


def file_source_type_is_browsable(target_type: Type["BaseFilesSource"]) -> bool:
    # Check whether the list method has been overridden
    return target_type.list != BaseFilesSource.list or target_type._list != BaseFilesSource._list


class BaseFilesSource(FilesSource):
    plugin_kind: ClassVar[PluginKind] = PluginKind.rfs  # Remote File Source by default, override in subclasses
    supports_pagination: ClassVar[bool] = False
    supports_search: ClassVar[bool] = False
    supports_sorting: ClassVar[bool] = False

    def get_browsable(self) -> bool:
        return file_source_type_is_browsable(type(self))

    def get_prefix(self) -> Optional[str]:
        return self.id

    def get_scheme(self) -> str:
        return self.scheme or "gxfiles"

    def get_writable(self) -> bool:
        return self.writable

    def user_has_access(self, user_context: "OptionalUserContext") -> bool:
        if user_context is None and self.user_context_required:
            return False
        return (
            user_context is None
            or user_context.is_admin
            or (self._user_has_required_roles(user_context) and self._user_has_required_groups(user_context))
        )

    @property
    def user_context_required(self) -> bool:
        return self.requires_roles is not None or self.requires_groups is not None

    def get_uri_root(self) -> str:
        prefix = self.get_prefix()
        scheme = self.get_scheme()
        root = f"{scheme}://"
        if prefix:
            root = uri_join(root, prefix)
        return root

    def get_url(self) -> Optional[str]:
        """Returns a URL that can be used to link to the remote source."""
        return None

    def to_relative_path(self, url: str) -> str:
        return url.replace(self.get_uri_root(), "") or "/"

    def score_url_match(self, url: str) -> int:
        root = self.get_uri_root()
        return len(root) if root in url else 0

    def uri_from_path(self, path: str) -> str:
        uri_root = self.get_uri_root()
        return uri_join(uri_root, path)

    def _parse_common_config_opts(self, kwd: FilesSourceProperties):
        self._file_sources_config = kwd.pop("file_sources_config")
        self.id = kwd.pop("id")
        self.label = kwd.pop("label", None) or self.id
        self.doc = kwd.pop("doc", None)
        self.scheme = kwd.pop("scheme", DEFAULT_SCHEME)
        self.writable = kwd.pop("writable", DEFAULT_WRITABLE)
        self.requires_roles = kwd.pop("requires_roles", None)
        self.requires_groups = kwd.pop("requires_groups", None)
        self.disable_templating = kwd.pop("disable_templating", False)
        self._validate_security_rules()
        # If coming from to_dict, strip API helper values
        kwd.pop("uri_root", None)
        kwd.pop("type", None)
        kwd.pop("browsable", None)
        kwd.pop("supports", None)
        return kwd

    def to_dict(self, for_serialization=False, user_context: "OptionalUserContext" = None) -> FilesSourceProperties:
        rval: FilesSourceProperties = {
            "id": self.id,
            "type": self.plugin_type,
            "label": self.label,
            "doc": self.doc,
            "writable": self.writable,
            "browsable": self.get_browsable(),
            "requires_roles": self.requires_roles,
            "requires_groups": self.requires_groups,
            "disable_templating": self.disable_templating,
            "scheme": self.get_scheme(),
            "supports": {
                "pagination": self.supports_pagination,
                "search": self.supports_search,
                "sorting": self.supports_sorting,
            },
        }
        if self.get_browsable():
            rval["uri_root"] = self.get_uri_root()
        if self.get_url() is not None:
            rval["url"] = self.get_url()
        if for_serialization:
            rval.update(self._serialization_props(user_context=user_context))
        return rval

    def to_dict_time(self, ctime):
        if ctime is None:
            return None
        elif isinstance(ctime, (int, float)):
            return time.strftime("%m/%d/%Y %I:%M:%S %p", time.localtime(ctime))
        else:
            return ctime.strftime("%m/%d/%Y %I:%M:%S %p")

    @abc.abstractmethod
    def _serialization_props(self, user_context: "OptionalUserContext" = None) -> FilesSourceProperties:
        """Serialize properties needed to recover plugin configuration.
        Used in to_dict method if for_serialization is True.
        """

    def list(
        self,
        path="/",
        recursive=False,
        user_context: "OptionalUserContext" = None,
        opts: Optional[FilesSourceOptions] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        query: Optional[str] = None,
        sort_by: Optional[str] = None,
    ) -> Tuple[List[AnyRemoteEntry], int]:
        self._check_user_access(user_context)
        if not self.supports_pagination and (limit is not None or offset is not None):
            raise RequestParameterInvalidException("Pagination is not supported by this file source.")
        if not self.supports_search and query:
            raise RequestParameterInvalidException("Server-side search is not supported by this file source.")
        if not self.supports_sorting and sort_by:
            raise RequestParameterInvalidException("Server-side sorting is not supported by this file source.")
        if self.supports_pagination:
            if limit is not None and limit < 1:
                raise RequestParameterInvalidException("Limit must be greater than 0.")
            if offset is not None and offset < 0:
                raise RequestParameterInvalidException("Offset must be greater than or equal to 0.")

        return self._list(path, recursive, user_context, opts, limit, offset, query)

    def _list(
        self,
        path="/",
        recursive=False,
        user_context: "OptionalUserContext" = None,
        opts: Optional[FilesSourceOptions] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        query: Optional[str] = None,
        sort_by: Optional[str] = None,
    ) -> Tuple[List[AnyRemoteEntry], int]:
        raise NotImplementedError()

    def create_entry(
        self,
        entry_data: EntryData,
        user_context: "OptionalUserContext" = None,
        opts: Optional[FilesSourceOptions] = None,
    ) -> Entry:
        self._ensure_writeable()
        self._check_user_access(user_context)
        return self._create_entry(entry_data, user_context, opts)

    def _create_entry(
        self,
        entry_data: EntryData,
        user_context: "OptionalUserContext" = None,
        opts: Optional[FilesSourceOptions] = None,
    ) -> Entry:
        """Create a new entry (directory) in the file source.

        The file source must be writeable.
        This function can be overridden by subclasses to provide a way of creating entries in the file source.
        """
        raise NotImplementedError()

    def write_from(
        self,
        target_path: str,
        native_path: str,
        user_context: "OptionalUserContext" = None,
        opts: Optional[FilesSourceOptions] = None,
    ) -> str:
        self._ensure_writeable()
        self._check_user_access(user_context)
        return self._write_from(target_path, native_path, user_context=user_context, opts=opts) or target_path

    @abc.abstractmethod
    def _write_from(
        self,
        target_path: str,
        native_path: str,
        user_context: "OptionalUserContext" = None,
        opts: Optional[FilesSourceOptions] = None,
    ) -> Optional[str]:
        pass

    def realize_to(
        self,
        source_path: str,
        native_path: str,
        user_context: "OptionalUserContext" = None,
        opts: Optional[FilesSourceOptions] = None,
    ):
        self._check_user_access(user_context)
        self._realize_to(source_path, native_path, user_context, opts=opts)

    @abc.abstractmethod
    def _realize_to(
        self,
        source_path: str,
        native_path: str,
        user_context: "OptionalUserContext" = None,
        opts: Optional[FilesSourceOptions] = None,
    ):
        pass

    def _ensure_writeable(self):
        if not self.get_writable():
            raise Exception("Cannot write to a non-writable file source.")

    def _check_user_access(self, user_context):
        """Raises an exception if the given user doesn't have the rights to access this file source.

        Warning: if the user_context is None, then the check is skipped. This is due to tool executions context
        not having access to the user_context. The validation will be done when checking the tool parameters.
        """
        if user_context is not None and not self.user_has_access(user_context):
            raise ItemAccessibilityException(f"User {user_context.username} has no access to file source.")

    def _evaluate_prop(self, prop_val: Any, user_context: "OptionalUserContext"):
        rval = prop_val

        # just return if we've disabled templating for this plugin
        if self.disable_templating:
            return rval

        if isinstance(prop_val, str) and "$" in prop_val:
            template_context = dict(
                user=user_context,
                environ=os.environ,
                config=self._file_sources_config,
            )
            rval = fill_template(prop_val, context=template_context, futurized=True)
        elif isinstance(prop_val, dict):
            rval = {key: self._evaluate_prop(childprop, user_context) for key, childprop in prop_val.items()}
        elif isinstance(prop_val, list):
            rval = [self._evaluate_prop(childprop, user_context) for childprop in prop_val]

        return rval

    def _user_has_required_roles(self, user_context: "FileSourcesUserContext") -> bool:
        if self.requires_roles:
            return self._evaluate_security_rules(self.requires_roles, user_context.role_names)
        return True

    def _user_has_required_groups(self, user_context: "FileSourcesUserContext") -> bool:
        if self.requires_groups:
            return self._evaluate_security_rules(self.requires_groups, user_context.group_names)
        return True

    def _evaluate_security_rules(self, rule_expression: str, user_credentials: Set[str]) -> bool:
        token_evaluator = TokenContainedEvaluator(user_credentials)
        evaluator = BooleanExpressionEvaluator(token_evaluator)
        return evaluator.evaluate_expression(rule_expression)

    def _validate_security_rules(self) -> None:
        """Checks if the security rules defined in the plugin configuration are valid boolean expressions or raises
        a ConfigurationError exception otherwise."""

        def _get_error_msg_for(rule_name: str) -> str:
            return f"Invalid boolean expression for '{rule_name}' in {self.label} file source plugin configuration."

        if self.requires_roles and not BooleanExpressionEvaluator.is_valid_expression(self.requires_roles):
            raise ConfigurationError(_get_error_msg_for("requires_roles"))
        if self.requires_groups and not BooleanExpressionEvaluator.is_valid_expression(self.requires_groups):
            raise ConfigurationError(_get_error_msg_for("requires_groups"))


def uri_join(*args: str) -> str:
    # url_join doesn't work with non-standard scheme
    if "://" in (arg0 := args[0]):
        scheme, path = arg0.split("://", 1)
        rval = f"{scheme}://{slash_join(path, *args[1:]) if path else slash_join(*args[1:])}"
    else:
        rval = slash_join(*args)
    return rval


def slash_join(*args: str) -> str:
    # https://codereview.stackexchange.com/questions/175421/joining-strings-to-form-a-url
    return "/".join(arg.strip("/") for arg in args)
