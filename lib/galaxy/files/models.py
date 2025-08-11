"""Template-aware configuration models for file sources."""

from typing import (
    Annotated,
    Any,
    Generic,
    Literal,
    Optional,
    TYPE_CHECKING,
    TypeVar,
    Union,
)

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)

from galaxy.files.sources._defaults import (
    DEFAULT_SCHEME,
    DEFAULT_WRITABLE,
)
from galaxy.util.config_parsers import (
    IpAllowedListEntryT,
    parse_allowlist_ips,
)
from galaxy.util.config_templates import (
    EnvironmentDict,
    partial_model,
)
from galaxy.util.template import fill_template

if TYPE_CHECKING:
    from galaxy.files import OptionalUserContext


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class FlexibleModel(BaseModel):
    model_config = ConfigDict(extra="allow")


class FileSourcePluginsConfig(BaseModel):
    symlink_allowlist: list[str] = []
    fetch_url_allowlist: list[IpAllowedListEntryT] = []
    library_import_dir: Optional[str] = None
    user_library_import_dir: Optional[str] = None
    ftp_upload_dir: Optional[str] = None
    ftp_upload_purge: bool = True
    tmp_dir: Optional[str] = None
    webdav_use_temp_files: Optional[bool] = None
    listings_expiry_time: Optional[int] = None

    @staticmethod
    def from_app_config(config):
        # Formalize what we read in from config to create a more clear interface
        # for this component.
        kwds = {}
        kwds["symlink_allowlist"] = config.user_library_import_symlink_allowlist
        kwds["fetch_url_allowlist"] = config.fetch_url_allowlist_ips
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
            "fetch_url_allowlist": [str(ip) for ip in self.fetch_url_allowlist],
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


class UserData:
    """User data exposed to file sources."""

    def __init__(self, context: "OptionalUserContext" = None):
        self.context = context

    @property
    def email(self) -> Optional[str]:
        return self.context.email if self.context else None

    @property
    def username(self) -> Optional[str]:
        return self.context.username if self.context else None

    @property
    def is_admin(self) -> bool:
        return self.context.is_admin if self.context else False

    @property
    def is_anonymous(self) -> bool:
        return self.context.anonymous if self.context else True


class FileSourceSupports(StrictModel):
    """Feature support flags for a file source plugin"""

    pagination: Annotated[bool, Field(description="Whether this file source supports server-side pagination.")] = False
    search: Annotated[bool, Field(description="Whether this file source supports server-side search.")] = False
    sorting: Annotated[bool, Field(description="Whether this file source supports server-side sorting.")] = False


class FilesSourceProperties(StrictModel):
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
    ] = None
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


@partial_model()
class PartialFilesSourceProperties(FilesSourceProperties):
    """Partial model for FilesSourceProperties to allow partial updates."""

    # We allow extra properties to be set in the model because each file source may have its own specific properties.
    model_config = ConfigDict(extra="allow")


class FilesSourceOptions(StrictModel):
    """Options to control behavior of file source operations, such as realize_to, write_from and list."""

    write_intent: Annotated[
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
        Optional[PartialFilesSourceProperties],
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


# Fields to skip during template expansion
COMMON_FILE_SOURCE_PROP_NAMES = set(FilesSourceProperties.model_fields.keys())


class BaseFileSourceTemplateConfiguration(FilesSourceProperties):
    """Base class for template-aware file source configurations.

    Subclasses should override fields that support templating to use
    Union[ActualType, TemplateExpansion] for those fields.
    """


class BaseFileSourceConfiguration(FilesSourceProperties):
    """Base class for resolved file source configurations.

    This contains the actual resolved values after template evaluation.
    """


class FilesSourceTemplateContext:
    """Context for filling templates in file source configurations.

    This is used to provide additional context to file sources during operations.
    It can include user data, environment variables, and other relevant information.
    """

    def __init__(
        self,
        user_data: Optional[UserData] = None,
        environment: Optional[EnvironmentDict] = None,
        file_sources_config: Optional[FileSourcePluginsConfig] = None,
    ):
        self.user_data = user_data or UserData()
        self.environment = environment or {}
        self.file_sources_config = file_sources_config or FileSourcePluginsConfig()

    def to_dict(self) -> dict[str, Any]:
        return {
            "user": self.user_data.context if self.user_data.context else None,
            "environ": self.environment,
            "config": self.file_sources_config.to_dict(),
        }


TTemplateConfig = TypeVar("TTemplateConfig", bound=BaseFileSourceTemplateConfiguration)
TResolvedConfig = TypeVar("TResolvedConfig", bound=BaseFileSourceConfiguration)


def resolve_file_source_template(
    template_config: BaseFileSourceTemplateConfiguration,
    resolved_config_class: type[TResolvedConfig],
    context: FilesSourceTemplateContext,
) -> TResolvedConfig:
    """Resolve templated file source configuration to actual values.

    Args:
        template_config: Configuration that may contain templated values
        resolved_config_class: The target configuration class to instantiate
        file_sources_config: File sources configuration
        environment: Environment variables for template resolution
        user_data: Current user context for template variable resolution

    Returns:
        Resolved configuration with all templates evaluated
    """
    template_variables = context.to_dict()

    def expand_template_value(value: Any) -> Any:
        """Recursively expand templated values."""
        if isinstance(value, str) and "$" in value:
            template_context = {
                "user": template_variables.get("user"),
                "environ": template_variables.get("environ", {}),
                "config": template_variables.get("config"),
            }
            return fill_template(value, context=template_context, futurized=True)
        elif isinstance(value, dict):
            return {k: expand_template_value(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [expand_template_value(item) for item in value]
        else:
            return value

    # Convert to dict, expand templates, then convert back to the specific resolved config class
    config_dict = template_config.model_dump(
        exclude_unset=True, exclude_none=True, exclude=COMMON_FILE_SOURCE_PROP_NAMES
    )
    expanded_dict = {k: expand_template_value(v) for k, v in config_dict.items()}

    # Add back the skipped fields that are still needed in the resolved config
    for skip_field in COMMON_FILE_SOURCE_PROP_NAMES:
        if hasattr(template_config, skip_field):
            expanded_dict[skip_field] = getattr(template_config, skip_field)

    return resolved_config_class(**expanded_dict)


class FilesSourceRuntimeContext(Generic[TResolvedConfig]):
    """Context for file source operations, providing user data and resolved configuration."""

    def __init__(self, user_data: UserData, config: TResolvedConfig):
        self._user_data = user_data
        self._config = config

    @property
    def user_data(self) -> UserData:
        """User data for the current context."""
        return self._user_data

    @property
    def config(self) -> TResolvedConfig:
        """Resolved configuration for the file source with all templates expanded."""
        return self._config
