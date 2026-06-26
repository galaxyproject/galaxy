from typing import (
    Annotated,
    Any,
    Literal,
)

from pydantic import (
    Field,
    model_validator,
    RootModel,
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
    "ftp",
    "posix",
    "s3fs",
    "azure",
    "azureflat",
    "irods",
    "onedata",
    "webdav",
    "dropbox",
    "googledrive",
    "onedrive",
    "elabftw",
    "inveniordm",
    "zenodo",
    "rspace",
    "dataverse",
    "cbioportal",
    "huggingface",
    "iiif",
    "mavedb",
    "omero",
    "ssh",
]


class PosixFileSourceTemplateConfiguration(StrictModel):
    type: Literal["posix"]
    root: str | TemplateExpansion
    writable: bool | TemplateExpansion = False
    template_start: str | None = None
    template_end: str | None = None


class PosixFileSourceConfiguration(StrictModel):
    type: Literal["posix"]
    root: str
    writable: bool = False


class OAuth2TemplateConfiguration:
    oauth2_client_id: str | TemplateExpansion
    oauth2_client_secret: str | TemplateExpansion


class DropboxFileSourceTemplateConfiguration(OAuth2TemplateConfiguration, StrictModel):
    type: Literal["dropbox"]
    writable: bool | TemplateExpansion = False
    oauth2_client_id: str | TemplateExpansion
    oauth2_client_secret: str | TemplateExpansion
    template_start: str | None = None
    template_end: str | None = None


class OAuth2FileSourceConfiguration:
    oauth2_access_token: str


class DropboxFileSourceConfiguration(OAuth2FileSourceConfiguration, StrictModel):
    type: Literal["dropbox"]
    writable: bool = False
    oauth2_access_token: str


class GoogleDriveFileSourceTemplateConfiguration(OAuth2TemplateConfiguration, StrictModel):
    type: Literal["googledrive"]
    writable: bool | TemplateExpansion = False
    oauth2_client_id: str | TemplateExpansion
    oauth2_client_secret: str | TemplateExpansion
    # Will default to https://www.googleapis.com/auth/drive.file, which provides
    # access to a folder specific to your Galaxy instance. Ideally we would use
    # https://www.googleapis.com/auth/drive but that would require becoming
    # Google verified - https://support.google.com/cloud/answer/13464321#ss-rs-requirements.
    # That seems like a onerous process and I don't know how it would
    # work in the context of an open source project like Galaxy, I am
    # adding the extension point here for the brave individual that would like
    # to use it but I expect it isn't practical for the typical admin.
    oauth2_scope: str | TemplateExpansion | None = None
    template_start: str | None = None
    template_end: str | None = None


class GoogleDriveFileSourceConfiguration(OAuth2FileSourceConfiguration, StrictModel):
    type: Literal["googledrive"]
    writable: bool = False
    oauth2_access_token: str


class OneDriveFileSourceTemplateConfiguration(OAuth2TemplateConfiguration, StrictModel):
    type: Literal["onedrive"]
    writable: bool | TemplateExpansion = False
    oauth2_client_id: str | TemplateExpansion
    oauth2_client_secret: str | TemplateExpansion
    # Microsoft Graph app-folder scope keeps access limited to Apps/<Application Name>.
    oauth2_scope: str | TemplateExpansion | None = None
    drive_mode: Literal["appfolder", "full"] | TemplateExpansion = "appfolder"
    template_start: str | None = None
    template_end: str | None = None


class OneDriveFileSourceConfiguration(OAuth2FileSourceConfiguration, StrictModel):
    type: Literal["onedrive"]
    writable: bool = False
    oauth2_access_token: str
    drive_mode: Literal["appfolder", "full"] = "appfolder"


class S3FSFileSourceTemplateConfiguration(StrictModel):
    type: Literal["s3fs"]
    endpoint_url: str | TemplateExpansion | None = None
    anon: bool | TemplateExpansion | None = False
    secret: str | TemplateExpansion | None = None
    key: str | TemplateExpansion | None = None
    bucket: str | TemplateExpansion | None = None
    writable: bool | TemplateExpansion = False
    template_start: str | None = None
    template_end: str | None = None
    request_checksum_calculation: str | TemplateExpansion | None = None


class S3FSFileSourceConfiguration(StrictModel):
    type: Literal["s3fs"]
    endpoint_url: str | None = None
    anon: bool | None = False
    secret: str | None = None
    key: str | None = None
    bucket: str | None = None
    writable: bool = False
    request_checksum_calculation: str | None = None


class FtpFileSourceTemplateConfiguration(StrictModel):
    type: Literal["ftp"]
    host: str | TemplateExpansion
    port: int | TemplateExpansion = 21
    user: str | TemplateExpansion | None = None
    passwd: str | TemplateExpansion | None = None
    writable: bool | TemplateExpansion = False
    tls: bool | TemplateExpansion = False
    template_start: str | None = None
    template_end: str | None = None


class FtpFileSourceConfiguration(StrictModel):
    type: Literal["ftp"]
    host: str
    port: int = 21
    user: str | None = None
    passwd: str | None = None
    writable: bool = False
    tls: bool = False


class SshFileSourceTemplateConfiguration(StrictModel):
    type: Literal["ssh"]
    host: str | TemplateExpansion
    user: str | TemplateExpansion | None = None
    passwd: str | TemplateExpansion | None = None
    pkey: str | TemplateExpansion | None = None
    timeout: int | TemplateExpansion = 10
    port: int | TemplateExpansion = 22
    compress: bool | TemplateExpansion = False
    path: str | TemplateExpansion
    writable: bool | TemplateExpansion = False
    template_start: str | None = None
    template_end: str | None = None


class SshFileSourceConfiguration(StrictModel):
    type: Literal["ssh"]
    host: str
    user: str | None = None
    passwd: str | None = None
    pkey: str | None = None
    timeout: int = 10
    port: int = 22
    compress: bool = False
    path: str
    writable: bool = False


class AzureFileSourceTemplateConfiguration(StrictModel):
    type: Literal["azure"]
    account_name: str | TemplateExpansion
    container_name: str | TemplateExpansion
    account_key: str | TemplateExpansion
    writable: bool | TemplateExpansion = False
    namespace_type: str | TemplateExpansion = "hierarchical"
    template_start: str | None = None
    template_end: str | None = None


class AzureFileSourceConfiguration(StrictModel):
    type: Literal["azure"]
    account_name: str
    container_name: str
    account_key: str
    namespace_type: str = "hierarchical"
    writable: bool = False


class AzureFlatFileSourceTemplateConfiguration(StrictModel):
    type: Literal["azureflat"]
    account_name: str | TemplateExpansion
    container_name: str | TemplateExpansion | None = None
    account_key: str | TemplateExpansion
    writable: bool | TemplateExpansion = False
    template_start: str | None = None
    template_end: str | None = None


class AzureFlatFileSourceConfiguration(StrictModel):
    type: Literal["azureflat"]
    account_name: str
    container_name: str | None = None
    account_key: str
    writable: bool = False


class IrodsFileSourceTemplateConfiguration(StrictModel):
    type: Literal["irods"]
    host: str | TemplateExpansion
    port: int | TemplateExpansion = 1247
    username: str | TemplateExpansion
    password: str | TemplateExpansion
    zone: str | TemplateExpansion
    root: str | TemplateExpansion | None = None
    timeout: int | TemplateExpansion = 30
    refresh_time: int | TemplateExpansion = 300
    writable: bool | TemplateExpansion = False
    template_start: str | None = None
    template_end: str | None = None


class IrodsFileSourceConfiguration(StrictModel):
    type: Literal["irods"]
    host: str
    port: int = 1247
    username: str
    password: str
    zone: str
    root: str | None = None
    timeout: int = 30
    refresh_time: int = 300
    writable: bool = False


class OnedataFileSourceTemplateConfiguration(StrictModel):
    type: Literal["onedata"]
    access_token: str | TemplateExpansion
    onezone_domain: str | TemplateExpansion
    disable_tls_certificate_validation: bool | TemplateExpansion = False
    writable: bool | TemplateExpansion = False
    template_start: str | None = None
    template_end: str | None = None


class OnedataFileSourceConfiguration(StrictModel):
    type: Literal["onedata"]
    access_token: str
    onezone_domain: str
    disable_tls_certificate_validation: bool = False
    writable: bool = False


class WebdavConfigMixin:
    @model_validator(mode="before")
    @classmethod
    def ensure_base_url(cls, data: Any) -> Any:
        # Accept the version-0 WebDAV template's `url` field as an alias of
        # `base_url` so that v0 templates and any persisted v0 rendered configs
        # continue to validate after the rename.
        if isinstance(data, dict) and "base_url" not in data and "url" in data:
            data = dict(data)
            data["base_url"] = data.pop("url")
        return data


class WebdavFileSourceTemplateConfiguration(WebdavConfigMixin, StrictModel):
    type: Literal["webdav"]
    base_url: str | TemplateExpansion
    root: str | TemplateExpansion
    login: str | TemplateExpansion
    password: str | TemplateExpansion
    writable: bool | TemplateExpansion = False
    template_start: str | None = None
    template_end: str | None = None


class WebdavFileSourceConfiguration(WebdavConfigMixin, StrictModel):
    type: Literal["webdav"]
    base_url: str
    root: str
    login: str
    password: str
    writable: bool = False


class eLabFTWFileSourceTemplateConfiguration(StrictModel):  # noqa
    type: Literal["elabftw"]
    endpoint: str | TemplateExpansion
    api_key: str | TemplateExpansion
    writable: bool | TemplateExpansion = True
    template_start: str | None = None
    template_end: str | None = None


class eLabFTWFileSourceConfiguration(StrictModel):  # noqa
    type: Literal["elabftw"]
    endpoint: str
    api_key: str
    writable: bool = True


class InvenioFileSourceTemplateConfiguration(StrictModel):
    type: Literal["inveniordm"]
    url: str | TemplateExpansion
    public_name: str | TemplateExpansion
    token: str | TemplateExpansion
    writable: bool | TemplateExpansion = True
    template_start: str | None = None
    template_end: str | None = None


class InvenioFileSourceConfiguration(StrictModel):
    type: Literal["inveniordm"]
    url: str
    public_name: str
    token: str
    writable: bool = True


class ZenodoFileSourceTemplateConfiguration(StrictModel):
    type: Literal["zenodo"]
    url: str | TemplateExpansion
    public_name: str | TemplateExpansion
    token: str | TemplateExpansion
    writable: bool | TemplateExpansion = True
    template_start: str | None = None
    template_end: str | None = None


class ZenodoFileSourceConfiguration(StrictModel):
    type: Literal["zenodo"]
    url: str
    public_name: str
    token: str
    writable: bool = True


class RSpaceFileSourceTemplateConfiguration(StrictModel):
    type: Literal["rspace"]
    endpoint: str | TemplateExpansion
    api_key: str | TemplateExpansion
    writable: bool | TemplateExpansion = True
    template_start: str | None = None
    template_end: str | None = None


class RSpaceFileSourceConfiguration(StrictModel):
    type: Literal["rspace"]
    endpoint: str
    api_key: str
    writable: bool = True


class DataverseFileSourceTemplateConfiguration(StrictModel):
    type: Literal["dataverse"]
    url: str | TemplateExpansion
    public_name: str | TemplateExpansion
    token: str | TemplateExpansion
    writable: bool | TemplateExpansion = True
    template_start: str | None = None
    template_end: str | None = None


class DataverseFileSourceConfiguration(StrictModel):
    type: Literal["dataverse"]
    url: str
    public_name: str
    token: str
    writable: bool = True


class CBioPortalFileSourceTemplateConfiguration(StrictModel):
    type: Literal["cbioportal"]
    api_url: str | TemplateExpansion
    datahub_url: str | TemplateExpansion
    writable: bool | TemplateExpansion = False
    template_start: str | None = None
    template_end: str | None = None


class CBioPortalFileSourceConfiguration(StrictModel):
    type: Literal["cbioportal"]
    api_url: str
    datahub_url: str
    writable: bool = False


class HuggingFaceFileSourceTemplateConfiguration(StrictModel):
    type: Literal["huggingface"]
    token: str | TemplateExpansion | None = None
    endpoint: str | TemplateExpansion | None = None
    template_start: str | None = None
    template_end: str | None = None


class HuggingFaceFileSourceConfiguration(StrictModel):
    type: Literal["huggingface"]
    token: str | None = None
    endpoint: str | None = None


class IIIFFileSourceTemplateConfiguration(StrictModel):
    type: Literal["iiif"]
    manifest_url: str | TemplateExpansion
    template_start: str | None = None
    template_end: str | None = None


class IIIFFileSourceConfiguration(StrictModel):
    type: Literal["iiif"]
    manifest_url: str


class MaveDBFileSourceTemplateConfiguration(StrictModel):
    type: Literal["mavedb"]
    base_url: str | TemplateExpansion = "https://api.mavedb.org/api/v1"
    api_key: str | TemplateExpansion | None = None
    timeout: float | TemplateExpansion = 30.0
    template_start: str | None = None
    template_end: str | None = None


class MaveDBFileSourceConfiguration(StrictModel):
    type: Literal["mavedb"]
    base_url: str = "https://api.mavedb.org/api/v1"
    api_key: str | None = None
    timeout: float = 30.0


class OmeroFileSourceTemplateConfiguration(StrictModel):
    type: Literal["omero"]
    username: str | TemplateExpansion
    password: str | TemplateExpansion
    host: str | TemplateExpansion
    port: int | TemplateExpansion = 4064
    writable: bool | TemplateExpansion = False
    template_start: str | None = None
    template_end: str | None = None


class OmeroFileSourceConfiguration(StrictModel):
    type: Literal["omero"]
    username: str
    password: str
    host: str
    port: int = 4064
    writable: bool = False


FileSourceTemplateConfiguration = Annotated[
    PosixFileSourceTemplateConfiguration
    | S3FSFileSourceTemplateConfiguration
    | FtpFileSourceTemplateConfiguration
    | AzureFileSourceTemplateConfiguration
    | AzureFlatFileSourceTemplateConfiguration
    | IrodsFileSourceTemplateConfiguration
    | OnedataFileSourceTemplateConfiguration
    | WebdavFileSourceTemplateConfiguration
    | DropboxFileSourceTemplateConfiguration
    | GoogleDriveFileSourceTemplateConfiguration
    | OneDriveFileSourceTemplateConfiguration
    | eLabFTWFileSourceTemplateConfiguration
    | InvenioFileSourceTemplateConfiguration
    | ZenodoFileSourceTemplateConfiguration
    | RSpaceFileSourceTemplateConfiguration
    | DataverseFileSourceTemplateConfiguration
    | CBioPortalFileSourceTemplateConfiguration
    | HuggingFaceFileSourceTemplateConfiguration
    | IIIFFileSourceTemplateConfiguration
    | MaveDBFileSourceTemplateConfiguration
    | OmeroFileSourceTemplateConfiguration
    | SshFileSourceTemplateConfiguration,
    Field(discriminator="type"),
]

FileSourceConfiguration = Annotated[
    PosixFileSourceConfiguration
    | S3FSFileSourceConfiguration
    | FtpFileSourceConfiguration
    | AzureFileSourceConfiguration
    | AzureFlatFileSourceConfiguration
    | IrodsFileSourceConfiguration
    | OnedataFileSourceConfiguration
    | WebdavFileSourceConfiguration
    | DropboxFileSourceConfiguration
    | GoogleDriveFileSourceConfiguration
    | OneDriveFileSourceConfiguration
    | eLabFTWFileSourceConfiguration
    | InvenioFileSourceConfiguration
    | ZenodoFileSourceConfiguration
    | RSpaceFileSourceConfiguration
    | DataverseFileSourceConfiguration
    | CBioPortalFileSourceConfiguration
    | HuggingFaceFileSourceConfiguration
    | IIIFFileSourceConfiguration
    | MaveDBFileSourceConfiguration
    | OmeroFileSourceConfiguration
    | SshFileSourceConfiguration,
    Field(discriminator="type"),
]


class FileSourceTemplateBase(StrictModel):
    """Version of FileSourceTemplate we can send to the UI/API.

    The configuration key in the child type may have secretes
    and shouldn't be exposed over the API - at least to non-admins.
    """

    id: str
    name: str | None
    description: MarkdownContent | None
    # The UI should just show the most recent version but allow
    # admins to define newer versions with new parameterizations
    # and keep old versions in template catalog for backward compatibility
    # for users with existing stores of that template.
    version: int = 0
    # Like with multiple versions, allow admins to deprecate a
    # template by hiding but keep it in the catalog for backward
    # compatibility for users with existing stores of that template.
    hidden: bool = False
    variables: list[TemplateVariable] | None = None
    secrets: list[TemplateSecret] | None = None


class FileSourceTemplateSummary(FileSourceTemplateBase):
    type: FileSourceTemplateType


class FileSourceTemplate(FileSourceTemplateBase):
    configuration: FileSourceTemplateConfiguration
    environment: list[TemplateEnvironmentEntry] | None = None

    @property
    def type(self):
        return self.configuration.type


FileSourceTemplateCatalog = RootModel[list[FileSourceTemplate]]


class FileSourceTemplateSummaries(RootModel):
    root: list[FileSourceTemplateSummary]


def template_to_configuration(
    template: FileSourceTemplate,
    variables: dict[str, TemplateVariableValueType],
    secrets: SecretsDict,
    user_details: UserDetailsDict,
    environment: EnvironmentDict,
    implicit: ImplicitConfigurationParameters | None = None,
) -> FileSourceConfiguration:
    configuration_template = template.configuration
    populate_default_variables(template.variables, variables)
    raw_config = expand_raw_config(configuration_template, variables, secrets, user_details, environment)
    merge_implicit_parameters(raw_config, implicit)
    return to_configuration_object(raw_config)


TypesToConfigurationClasses: dict[FileSourceTemplateType, type[FileSourceConfiguration]] = {
    "ftp": FtpFileSourceConfiguration,
    "posix": PosixFileSourceConfiguration,
    "s3fs": S3FSFileSourceConfiguration,
    "azure": AzureFileSourceConfiguration,
    "azureflat": AzureFlatFileSourceConfiguration,
    "irods": IrodsFileSourceConfiguration,
    "onedata": OnedataFileSourceConfiguration,
    "webdav": WebdavFileSourceConfiguration,
    "dropbox": DropboxFileSourceConfiguration,
    "googledrive": GoogleDriveFileSourceConfiguration,
    "onedrive": OneDriveFileSourceConfiguration,
    "elabftw": eLabFTWFileSourceConfiguration,
    "inveniordm": InvenioFileSourceConfiguration,
    "zenodo": ZenodoFileSourceConfiguration,
    "rspace": RSpaceFileSourceConfiguration,
    "dataverse": DataverseFileSourceConfiguration,
    "cbioportal": CBioPortalFileSourceConfiguration,
    "huggingface": HuggingFaceFileSourceConfiguration,
    "iiif": IIIFFileSourceConfiguration,
    "mavedb": MaveDBFileSourceConfiguration,
    "omero": OmeroFileSourceConfiguration,
    "ssh": SshFileSourceConfiguration,
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
    "onedrive": OAuth2Configuration(
        authorize_url="https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
        token_url="https://login.microsoftonline.com/common/oauth2/v2.0/token",
        authorize_params={},
        scope="offline_access Files.ReadWrite.AppFolder",
    ),
}


def get_oauth2_config(template: FileSourceTemplate) -> OAuth2Configuration:
    return get_oauth2_config_from(template, OAUTH2_CONFIGURED_SOURCES)


def get_oauth2_config_or_none(template: FileSourceTemplate) -> OAuth2Configuration | None:
    if template.configuration.type not in OAUTH2_CONFIGURED_SOURCES:
        return None
    return get_oauth2_config(template)


def to_configuration_object(configuration_dict: dict[str, Any]) -> FileSourceConfiguration:
    if "type" not in configuration_dict:
        raise KeyError("Configuration objects require a file source 'type' key, none found.")
    object_store_type = configuration_dict["type"]
    if object_store_type not in TypesToConfigurationClasses:
        raise ValueError(f"Unknown file source type found in raw configuration dictionary ({object_store_type}).")
    return TypesToConfigurationClasses[object_store_type](**configuration_dict)
