import abc
import builtins
import os
import time
from enum import Enum
from typing import (
    Annotated,
    Any,
    ClassVar,
    Optional,
    Type,
    TYPE_CHECKING,
    Union,
)

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)
from typing_extensions import Literal

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


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class FlexibleModel(BaseModel):
    model_config = ConfigDict(extra="allow")


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


class FileSourceSupports(StrictModel):
    """Feature support flags for a file source plugin"""

    pagination: Annotated[bool, Field(description="Whether this file source supports server-side pagination.")] = False
    search: Annotated[bool, Field(description="Whether this file source supports server-side search.")] = False
    sorting: Annotated[bool, Field(description="Whether this file source supports server-side sorting.")] = False


class FileSourceConfiguration(StrictModel):
    """Initial set of properties used to initialize a file source.

    File sources can extend this model to define any additional
    filesource specific properties.
    """

    id: Annotated[
        str,
        Field(
            ...,
            description="The `FilesSource` plugin identifier",
        ),
    ]
    type: Annotated[
        str,
        Field(
            ...,
            description="The type of the plugin.",
        ),
    ]
    label: Annotated[
        Optional[str],
        Field(
            ...,
            description="The display label for this plugin.",
        ),
    ] = "Unlabeled File Source"
    doc: Annotated[
        Optional[str],
        Field(
            None,
            title="Documentation",
            description="Documentation or extended description for this plugin.",
        ),
    ] = None
    browsable: Annotated[
        bool,
        Field(
            ...,
            title="Browsable",
            description="Whether this file source plugin can list items.",
        ),
    ] = False
    writable: Annotated[
        bool,
        Field(
            ...,
            title="Writeable",
            description="Whether this files source plugin allows write access.",
        ),
    ] = DEFAULT_WRITABLE
    requires_roles: Annotated[
        Optional[str],
        Field(
            None,
            title="Requires roles",
            description=(
                "Only users with the roles specified here can access this source."
                " This is a boolean expression that can be evaluated by the server."
                " It can be a simple role name or a complex expression."
                " For example, 'role1 and (role2 or role3)' will allow access if the user has role1 and either role2 or role3."
            ),
        ),
    ] = None
    requires_groups: Annotated[
        Optional[str],
        Field(
            None,
            title="Requires groups",
            description=(
                "Only users belonging to the groups specified here can access this source."
                " This is a boolean expression that can be evaluated by the server."
                " It can be a simple group name or a complex expression."
                " For example, 'group1 and (group2 or group3)' will allow access if the user belongs to group1 and either group2 or group3."
            ),
        ),
    ] = None
    disable_templating: Annotated[
        Optional[bool],
        Field(
            False,
            title="Disable Templating",
            description=(
                "Whether to disable templating for this file source. If set to True, "
                "the file source will not support templating in paths or other properties."
            ),
        ),
    ] = False
    scheme: Annotated[
        Optional[str],
        Field(
            DEFAULT_SCHEME,
            title="Scheme",
            description="The URI scheme used by this file source plugin.",
        ),
    ] = DEFAULT_SCHEME
    uri_root: Annotated[
        Optional[str],
        Field(
            None,
            title="URI root",
            description=(
                "The URI root used by this type of plugin. This is used to identify the file source and "
                "should be unique across all file sources."
            ),
        ),
    ] = None
    url: Annotated[
        Optional[str],
        Field(
            None,
            title="URL",
            description="Optional URL that might be provided by some plugins to link to the remote source.",
        ),
    ] = None
    supports: Annotated[
        FileSourceSupports,
        Field(
            default_factory=FileSourceSupports,
            description="Features supported by this file source.",
        ),
    ] = FileSourceSupports()
    file_sources_config: Annotated[
        FileSourcePluginsConfig,
        Field(
            ...,
            description="Configuration for the file sources, used to validate and initialize the file source.",
        ),
    ]


class FilesSourceOptions(StrictModel):
    """Options to control behavior of file source operations, such as realize_to, write_from and list."""

    writeable: Annotated[
        bool,
        Field(
            False,
            description=(
                "Whether the query is made with the intention of writing to the source."
                " If set to True, only entries (directories) that can be written to will be returned."
                " This is used to filter out read-only locations within the file source when listing entries."
            ),
        ),
    ] = False

    # Property overrides for values initially configured through the constructor. For example
    # the HTTPFilesSource passes in additional http_headers through these properties, which
    # are merged with constructor defined http_headers. The interpretation of these properties
    # are filesystem specific.
    extra_props: Annotated[
        Optional[FileSourceConfiguration],
        Field(
            description="Additional properties to override the initial properties defined in the constructor.",
        ),
    ] = None


class EntryData(FlexibleModel):
    """Provides data to create a new entry in a file source."""

    name: str
    # May contain additional properties depending on the file source


class Entry(FlexibleModel):
    """Represents the result of creating a new entry in a file source."""

    name: str
    uri: str
    # May contain additional properties depending on the file source
    external_link: Optional[str]


class RemoteEntry(StrictModel):
    """Represents a remote entry in a file source, either a directory or a file."""

    name: str
    uri: str
    path: str


class RemoteDirectory(RemoteEntry):
    class_: Annotated[Literal["Directory"], Field(..., serialization_alias="class")] = "Directory"


class RemoteFile(RemoteEntry):
    class_: Annotated[Literal["File"], Field(..., serialization_alias="class")] = "File"
    size: Annotated[int, Field(..., title="Size", description="The size of the file in bytes.")] = 0
    ctime: Annotated[
        Optional[str], Field(default="Unknown", title="Creation time", description="The creation time of the file.")
    ]


AnyRemoteEntry = Union[RemoteDirectory, RemoteFile]


class SingleFileSource(metaclass=abc.ABCMeta):
    """
    Represents a protocol handler for a single remote file that can be read by or written to by Galaxy.
    A remote file source can typically handle a url like `https://galaxyproject.org/myfile.txt` or
    `drs://myserver/123456`. The filesource abstraction allows programmatic control over the specific source
    to access, injection of credentials and access control. File sources are typically listed and configured
    through `file_sources_conf.yml` or programmatically, as required.

    File sources can be contextualized with a `user_context`, which contains information related to the current
    user attempting to access that filesource such as the username, preferences, roles etc., which can then
    be used by the filesource to make authorization decisions or inject credentials.

    File sources are loaded through Galaxy's plugin system in `galaxy.util.plugin_config`.
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
    def to_dict(self, for_serialization=False, user_context: "OptionalUserContext" = None) -> dict[str, Any]:
        """Return a dictified representation of this FileSource instance.

        If ``user_context`` is supplied, properties should be written so user
        context doesn't need to be present after the plugin is re-hydrated.
        """

    @abc.abstractmethod
    def prefer_links(self) -> bool:
        """Prefer linking to files."""


class SupportsBrowsing(metaclass=abc.ABCMeta):
    """An interface indicating that this filesource is browsable.

    Browsable file sources will typically have a root uri from which to start browsing.
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
    ) -> tuple[list[AnyRemoteEntry], int]:
        """Return a list of 'Directory's and 'File's and the total count in a tuple."""


class FilesSource(SingleFileSource, SupportsBrowsing):
    """Represents a combined interface for single or browsable file sources.
    The `get_browsable` method can be used to determine whether the filesource is browsable and
    implements the `SupportsBrowsing` interface.
    """

    plugin_type: ClassVar[str]

    @abc.abstractmethod
    def get_browsable(self) -> bool:
        """Return true if the filesource implements the SupportsBrowsing interface."""


def file_source_type_is_browsable(target_type: type["BaseFilesSource"]) -> bool:
    # Check whether the list method has been overridden
    return target_type.list != BaseFilesSource.list or target_type._list != BaseFilesSource._list


class BaseFilesSource(FilesSource):
    plugin_kind: ClassVar[PluginKind] = PluginKind.rfs  # Remote File Source by default, override in subclasses
    supports_pagination: ClassVar[bool] = False
    supports_search: ClassVar[bool] = False
    supports_sorting: ClassVar[bool] = False
    config_class: ClassVar[Type[FileSourceConfiguration]]

    def __init__(self, config: FileSourceConfiguration):
        self._parse_common_config_opts(config)
        self.config = config

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

    def prefer_links(self) -> bool:
        return False

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

    def _parse_common_config_opts(self, config: FileSourceConfiguration):
        """Initialize common configuration from a Pydantic model.

        This method extracts common file source properties from a Pydantic model
        and returns the remaining properties for plugin-specific use.
        """
        self._file_sources_config = config.file_sources_config
        self.id = config.id
        self.label = config.label
        self.doc = config.doc
        self.scheme = config.scheme
        self.writable = config.writable
        self.requires_roles = config.requires_roles
        self.requires_groups = config.requires_groups
        self.disable_templating = config.disable_templating
        self._validate_security_rules()

    def to_dict(self, for_serialization=False, user_context: "OptionalUserContext" = None) -> dict[str, Any]:
        rval: dict[str, Any] = {
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

    def to_dict_time(self, ctime) -> Optional[str]:
        if ctime is None:
            return None
        elif isinstance(ctime, (int, float)):
            return time.strftime("%m/%d/%Y %I:%M:%S %p", time.localtime(ctime))
        else:
            return ctime.strftime("%m/%d/%Y %I:%M:%S %p")

    def _evaluate_config_props(self, user_context: "OptionalUserContext") -> dict[str, Any]:
        """Evaluate properties that may contain templated values."""
        effective_props = {}
        for key, val in self.config.model_dump(exclude_unset=True, exclude_none=True).items():
            effective_props[key] = self._evaluate_prop(val, user_context=user_context)
        return effective_props

    def _serialization_props(self, user_context: "OptionalUserContext") -> dict[str, Any]:
        """Serialize properties needed to recover plugin configuration.
        Used in to_dict method if for_serialization is True.
        """
        return self._evaluate_config_props(user_context)

    def update_config_from_options(
        self,
        opts: Optional[FilesSourceOptions] = None,
        user_context: "OptionalUserContext" = None,
    ):
        """
        Ensures that the configuration is updated with any extra properties provided in the options and
        evaluates any properties that need to be computed based on the user context from template variables.
        """
        if opts and opts.extra_props:
            extra_props = opts.extra_props
            self.config = self.config.model_copy(update=extra_props.model_dump(exclude_unset=True), deep=True)
        evaluated_props = self._evaluate_config_props(user_context)
        self.config = self.config.model_copy(update=evaluated_props, deep=True)

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
    ) -> tuple[list[AnyRemoteEntry], int]:
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
    ) -> tuple[builtins.list[AnyRemoteEntry], int]:
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

    def _evaluate_security_rules(self, rule_expression: str, user_credentials: set[str]) -> bool:
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
