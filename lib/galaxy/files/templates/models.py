from typing import (
    Any,
    Dict,
    List,
    Optional,
    Type,
    Union,
)

from pydantic import (
    Field,
    RootModel,
)
from typing_extensions import (
    Annotated,
    Literal,
)

from galaxy.util.config_templates import (
    ConfiguredOAuth2Sources,
    EnvironmentDict,
    expand_raw_config,
    get_oauth2_config_from,
    ImplicitConfigurationParameters,
    MarkdownContent,
    merge_implicit_parameters,
    OAuth2Configuration,
    populate_default_variables,
    SecretsDict,
    StrictModel,
    TemplateEnvironmentEntry,
    TemplateExpansion,
    TemplateSecret,
    TemplateVariable,
    TemplateVariableValueType,
    UserDetailsDict,
)

FileSourceTemplateType = Literal[
    "ftp", "posix", "s3fs", "azure", "onedata", "webdav", "dropbox", "googledrive", "elabftw"
]


class PosixFileSourceTemplateConfiguration(StrictModel):
    type: Literal["posix"]
    root: Union[str, TemplateExpansion]
    writable: Union[bool, TemplateExpansion] = False
    template_start: Optional[str] = None
    template_end: Optional[str] = None


class PosixFileSourceConfiguration(StrictModel):
    type: Literal["posix"]
    root: str
    writable: bool = False


class OAuth2TemplateConfiguration:
    oauth2_client_id: Union[str, TemplateExpansion]
    oauth2_client_secret: Union[str, TemplateExpansion]


class DropboxFileSourceTemplateConfiguration(OAuth2TemplateConfiguration, StrictModel):
    type: Literal["dropbox"]
    writable: Union[bool, TemplateExpansion] = False
    oauth2_client_id: Union[str, TemplateExpansion]
    oauth2_client_secret: Union[str, TemplateExpansion]
    template_start: Optional[str] = None
    template_end: Optional[str] = None


class OAuth2FileSourceConfiguration:
    oauth2_access_token: str


class DropboxFileSourceConfiguration(OAuth2FileSourceConfiguration, StrictModel):
    type: Literal["dropbox"]
    writable: bool = False
    oauth2_access_token: str


class GoogleDriveFileSourceTemplateConfiguration(OAuth2TemplateConfiguration, StrictModel):
    type: Literal["googledrive"]
    writable: Union[bool, TemplateExpansion] = False
    oauth2_client_id: Union[str, TemplateExpansion]
    oauth2_client_secret: Union[str, TemplateExpansion]
    # Will default to https://www.googleapis.com/auth/drive.file, which provides
    # access to a folder specific to your Galaxy instance. Ideally we would use
    # https://www.googleapis.com/auth/drive but that would require becoming
    # Google verified - https://support.google.com/cloud/answer/13464321#ss-rs-requirements.
    # That seems like a onerous process and I don't know how it would
    # work in the context of an open source project like Galaxy, I am
    # adding the extension point here for the brave individual that would like
    # to use it but I expect it isn't practical for the typical admin.
    oauth2_scope: Optional[Union[str, TemplateExpansion]] = None
    template_start: Optional[str] = None
    template_end: Optional[str] = None


class GoogleDriveFileSourceConfiguration(OAuth2FileSourceConfiguration, StrictModel):
    type: Literal["googledrive"]
    writable: bool = False
    oauth2_access_token: str


class S3FSFileSourceTemplateConfiguration(StrictModel):
    type: Literal["s3fs"]
    endpoint_url: Optional[Union[str, TemplateExpansion]] = None
    anon: Optional[Union[bool, TemplateExpansion]] = False
    secret: Optional[Union[str, TemplateExpansion]] = None
    key: Optional[Union[str, TemplateExpansion]] = None
    bucket: Optional[Union[str, TemplateExpansion]] = None
    writable: Union[bool, TemplateExpansion] = False
    template_start: Optional[str] = None
    template_end: Optional[str] = None


class S3FSFileSourceConfiguration(StrictModel):
    type: Literal["s3fs"]
    endpoint_url: Optional[str] = None
    anon: Optional[bool] = False
    secret: Optional[str] = None
    key: Optional[str] = None
    bucket: Optional[str] = None
    writable: bool = False


class FtpFileSourceTemplateConfiguration(StrictModel):
    type: Literal["ftp"]
    host: Union[str, TemplateExpansion]
    port: Union[int, TemplateExpansion] = 21
    user: Optional[Union[str, TemplateExpansion]] = None
    passwd: Optional[Union[str, TemplateExpansion]] = None
    writable: Union[bool, TemplateExpansion] = False
    template_start: Optional[str] = None
    template_end: Optional[str] = None


class FtpFileSourceConfiguration(StrictModel):
    type: Literal["ftp"]
    host: str
    port: int = 21
    user: Optional[str] = None
    passwd: Optional[str] = None
    writable: bool = False


class AzureFileSourceTemplateConfiguration(StrictModel):
    type: Literal["azure"]
    account_name: Union[str, TemplateExpansion]
    container_name: Union[str, TemplateExpansion]
    account_key: Union[str, TemplateExpansion]
    writable: Union[bool, TemplateExpansion] = False
    namespace_type: Union[str, TemplateExpansion] = "hierarchical"
    template_start: Optional[str] = None
    template_end: Optional[str] = None


class AzureFileSourceConfiguration(StrictModel):
    type: Literal["azure"]
    account_name: str
    container_name: str
    account_key: str
    namespace_type: str = "hierarchical"
    writable: bool = False


class OnedataFileSourceTemplateConfiguration(StrictModel):
    type: Literal["onedata"]
    access_token: Union[str, TemplateExpansion]
    onezone_domain: Union[str, TemplateExpansion]
    disable_tls_certificate_validation: Union[bool, TemplateExpansion] = False
    writable: Union[bool, TemplateExpansion] = False
    template_start: Optional[str] = None
    template_end: Optional[str] = None


class OnedataFileSourceConfiguration(StrictModel):
    type: Literal["onedata"]
    access_token: str
    onezone_domain: str
    disable_tls_certificate_validation: bool = False
    writable: bool = False


class WebdavFileSourceTemplateConfiguration(StrictModel):
    type: Literal["webdav"]
    url: Union[str, TemplateExpansion]
    root: Union[str, TemplateExpansion]
    login: Union[str, TemplateExpansion]
    password: Union[str, TemplateExpansion]
    writable: Union[bool, TemplateExpansion] = False
    template_start: Optional[str] = None
    template_end: Optional[str] = None


class WebdavFileSourceConfiguration(StrictModel):
    type: Literal["webdav"]
    url: str
    root: str
    login: str
    password: str
    writable: bool = False


class eLabFTWFileSourceTemplateConfiguration(StrictModel):  # noqa
    type: Literal["elabftw"]
    endpoint: Union[str, TemplateExpansion]
    api_key: Union[str, TemplateExpansion]
    writable: Union[bool, TemplateExpansion] = True
    template_start: Optional[str] = None
    template_end: Optional[str] = None


class eLabFTWFileSourceConfiguration(StrictModel):  # noqa
    type: Literal["elabftw"]
    endpoint: str
    api_key: str
    writable: bool = True


FileSourceTemplateConfiguration = Annotated[
    Union[
        PosixFileSourceTemplateConfiguration,
        S3FSFileSourceTemplateConfiguration,
        FtpFileSourceTemplateConfiguration,
        AzureFileSourceTemplateConfiguration,
        OnedataFileSourceTemplateConfiguration,
        WebdavFileSourceTemplateConfiguration,
        DropboxFileSourceTemplateConfiguration,
        GoogleDriveFileSourceTemplateConfiguration,
        eLabFTWFileSourceTemplateConfiguration,
    ],
    Field(discriminator="type"),
]

FileSourceConfiguration = Annotated[
    Union[
        PosixFileSourceConfiguration,
        S3FSFileSourceConfiguration,
        FtpFileSourceConfiguration,
        AzureFileSourceConfiguration,
        OnedataFileSourceConfiguration,
        WebdavFileSourceConfiguration,
        DropboxFileSourceConfiguration,
        GoogleDriveFileSourceConfiguration,
        eLabFTWFileSourceConfiguration,
    ],
    Field(discriminator="type"),
]


class FileSourceTemplateBase(StrictModel):
    """Version of FileSourceTemplate we can send to the UI/API.

    The configuration key in the child type may have secretes
    and shouldn't be exposed over the API - at least to non-admins.
    """

    id: str
    name: Optional[str]
    description: Optional[MarkdownContent]
    # The UI should just show the most recent version but allow
    # admins to define newer versions with new parameterizations
    # and keep old versions in template catalog for backward compatibility
    # for users with existing stores of that template.
    version: int = 0
    # Like with multiple versions, allow admins to deprecate a
    # template by hiding but keep it in the catalog for backward
    # compatibility for users with existing stores of that template.
    hidden: bool = False
    variables: Optional[List[TemplateVariable]] = None
    secrets: Optional[List[TemplateSecret]] = None


class FileSourceTemplateSummary(FileSourceTemplateBase):
    type: FileSourceTemplateType


class FileSourceTemplate(FileSourceTemplateBase):
    configuration: FileSourceTemplateConfiguration
    environment: Optional[List[TemplateEnvironmentEntry]] = None

    @property
    def type(self):
        return self.configuration.type


FileSourceTemplateCatalog = RootModel[List[FileSourceTemplate]]


class FileSourceTemplateSummaries(RootModel):
    root: List[FileSourceTemplateSummary]


def template_to_configuration(
    template: FileSourceTemplate,
    variables: Dict[str, TemplateVariableValueType],
    secrets: SecretsDict,
    user_details: UserDetailsDict,
    environment: EnvironmentDict,
    implicit: Optional[ImplicitConfigurationParameters] = None,
) -> FileSourceConfiguration:
    configuration_template = template.configuration
    populate_default_variables(template.variables, variables)
    raw_config = expand_raw_config(configuration_template, variables, secrets, user_details, environment)
    merge_implicit_parameters(raw_config, implicit)
    return to_configuration_object(raw_config)


TypesToConfigurationClasses: Dict[FileSourceTemplateType, Type[FileSourceConfiguration]] = {
    "ftp": FtpFileSourceConfiguration,
    "posix": PosixFileSourceConfiguration,
    "s3fs": S3FSFileSourceConfiguration,
    "azure": AzureFileSourceConfiguration,
    "onedata": OnedataFileSourceConfiguration,
    "webdav": WebdavFileSourceConfiguration,
    "dropbox": DropboxFileSourceConfiguration,
    "googledrive": GoogleDriveFileSourceConfiguration,
    "elabftw": eLabFTWFileSourceConfiguration,
}


OAUTH2_CONFIGURED_SOURCES: ConfiguredOAuth2Sources = {
    "dropbox": OAuth2Configuration(
        authorize_url="https://www.dropbox.com/oauth2/authorize",
        authorize_params={"token_access_type": "offline"},
        token_url="https://api.dropbox.com/oauth2/token",
    ),
    "googledrive": OAuth2Configuration(
        authorize_url="https://accounts.google.com/o/oauth2/v2/auth",
        authorize_params={"access_type": "offline", "prompt": "consent"},
        token_url="https://oauth2.googleapis.com/token",
        scope="https://www.googleapis.com/auth/drive.file",
    ),
}


def get_oauth2_config(template: FileSourceTemplate) -> OAuth2Configuration:
    return get_oauth2_config_from(template, OAUTH2_CONFIGURED_SOURCES)


def get_oauth2_config_or_none(template: FileSourceTemplate) -> Optional[OAuth2Configuration]:
    if template.configuration.type not in OAUTH2_CONFIGURED_SOURCES:
        return None
    return get_oauth2_config(template)


def to_configuration_object(configuration_dict: Dict[str, Any]) -> FileSourceConfiguration:
    if "type" not in configuration_dict:
        raise KeyError("Configuration objects require a file source 'type' key, none found.")
    object_store_type = configuration_dict["type"]
    if object_store_type not in TypesToConfigurationClasses:
        raise ValueError(f"Unknown file source type found in raw configuration dictionary ({object_store_type}).")
    return TypesToConfigurationClasses[object_store_type](**configuration_dict)
