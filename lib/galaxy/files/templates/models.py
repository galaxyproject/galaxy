from typing import (
    Any,
    Dict,
    List,
    Literal,
    Optional,
    Type,
    Union,
)

from pydantic import RootModel

from galaxy.util.config_templates import (
    EnvironmentDict,
    expand_raw_config,
    MarkdownContent,
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

FileSourceTemplateType = Literal["ftp", "posix", "s3fs", "azure", "onedata", "webdav"]


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


FileSourceTemplateConfiguration = Union[
    PosixFileSourceTemplateConfiguration,
    S3FSFileSourceTemplateConfiguration,
    FtpFileSourceTemplateConfiguration,
    AzureFileSourceTemplateConfiguration,
    OnedataFileSourceTemplateConfiguration,
    WebdavFileSourceTemplateConfiguration,
]
FileSourceConfiguration = Union[
    PosixFileSourceConfiguration,
    S3FSFileSourceConfiguration,
    FtpFileSourceConfiguration,
    AzureFileSourceConfiguration,
    OnedataFileSourceConfiguration,
    WebdavFileSourceConfiguration,
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


FileSourceTemplateCatalog = RootModel[List[FileSourceTemplate]]


class FileSourceTemplateSummaries(RootModel):
    root: List[FileSourceTemplateSummary]


def template_to_configuration(
    template: FileSourceTemplate,
    variables: Dict[str, TemplateVariableValueType],
    secrets: SecretsDict,
    user_details: UserDetailsDict,
    environment: EnvironmentDict,
) -> FileSourceConfiguration:
    configuration_template = template.configuration
    populate_default_variables(template.variables, variables)
    raw_config = expand_raw_config(configuration_template, variables, secrets, user_details, environment)
    return to_configuration_object(raw_config)


TypesToConfigurationClasses: Dict[FileSourceTemplateType, Type[FileSourceConfiguration]] = {
    "ftp": FtpFileSourceConfiguration,
    "posix": PosixFileSourceConfiguration,
    "s3fs": S3FSFileSourceConfiguration,
    "azure": AzureFileSourceConfiguration,
    "onedata": OnedataFileSourceConfiguration,
    "webdav": WebdavFileSourceConfiguration,
}


def to_configuration_object(configuration_dict: Dict[str, Any]) -> FileSourceConfiguration:
    if "type" not in configuration_dict:
        raise KeyError("Configuration objects require a file source 'type' key, none found.")
    object_store_type = configuration_dict["type"]
    if object_store_type not in TypesToConfigurationClasses:
        raise ValueError(f"Unknown file source type found in raw configuration dictionary ({object_store_type}).")
    return TypesToConfigurationClasses[object_store_type](**configuration_dict)
