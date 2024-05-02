from typing import (
    Any,
    Dict,
    List,
    Optional,
    Type,
    Union,
)

from boltons.iterutils import remap
from jinja2.nativetypes import NativeEnvironment
from pydantic import (
    BaseModel,
    ConfigDict,
    RootModel,
)
from typing_extensions import Literal

from galaxy.objectstore.badges import (
    BadgeDict,
    StoredBadgeDict,
)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


ObjectStoreTemplateVariableType = Literal["string", "boolean", "integer"]
ObjectStoreTemplateVariableValueType = Union[str, bool, int]
TemplateExpansion = str
ObjectStoreTemplateType = Literal["s3", "azure_blob", "disk", "generic_s3"]


class S3AuthTemplate(StrictModel):
    access_key: Union[str, TemplateExpansion]
    secret_key: Union[str, TemplateExpansion]


class S3Auth(StrictModel):
    access_key: str
    secret_key: str


class S3BucketTemplate(StrictModel):
    name: Union[str, TemplateExpansion]
    use_reduced_redundancy: Optional[Union[bool, TemplateExpansion]] = None


class S3Bucket(StrictModel):
    name: str
    use_reduced_redundancy: Optional[bool] = None


BadgeList = Optional[List[StoredBadgeDict]]


class S3ObjectStoreTemplateConfiguration(StrictModel):
    type: Literal["s3"]
    auth: S3AuthTemplate
    bucket: S3BucketTemplate
    badges: BadgeList = None


class S3ObjectStoreConfiguration(StrictModel):
    type: Literal["s3"]
    auth: S3Auth
    bucket: S3Bucket
    badges: BadgeList = None


class AzureAuthTemplate(StrictModel):
    account_name: Union[str, TemplateExpansion]
    account_key: Union[str, TemplateExpansion]


class AzureAuth(StrictModel):
    account_name: str
    account_key: str


class AzureContainerTemplate(StrictModel):
    name: Union[str, TemplateExpansion]


class AzureContainer(StrictModel):
    name: str


class AzureObjectStoreTemplateConfiguration(StrictModel):
    type: Literal["azure_blob"]
    auth: AzureAuthTemplate
    container: AzureContainerTemplate
    badges: BadgeList = None


class AzureObjectStoreConfiguration(StrictModel):
    type: Literal["azure_blob"]
    auth: AzureAuth
    container: AzureContainer
    badges: BadgeList = None


class DiskObjectStoreTemplateConfiguration(StrictModel):
    type: Literal["disk"]
    files_dir: Union[str, TemplateExpansion]
    badges: BadgeList = None


class DiskObjectStoreConfiguration(StrictModel):
    type: Literal["disk"]
    files_dir: str
    badges: BadgeList = None


class S3ConnectionTemplate(StrictModel):
    host: Union[str, TemplateExpansion]
    port: Union[int, TemplateExpansion]
    is_secure: Optional[Union[bool, TemplateExpansion]] = True
    conn_path: Optional[Union[str, TemplateExpansion]] = ""


class S3Connection(StrictModel):
    host: str
    port: int
    is_secure: bool = True
    conn_path: str = ""


class GenericS3ObjectStoreTemplateConfiguration(StrictModel):
    type: Literal["generic_s3"]
    auth: S3AuthTemplate
    bucket: S3BucketTemplate
    connection: S3ConnectionTemplate
    badges: BadgeList = None


class GenericS3ObjectStoreConfiguration(StrictModel):
    type: Literal["generic_s3"]
    auth: S3Auth
    bucket: S3Bucket
    connection: S3Connection
    badges: BadgeList = None


ObjectStoreTemplateConfiguration = Union[
    S3ObjectStoreTemplateConfiguration,
    GenericS3ObjectStoreTemplateConfiguration,
    DiskObjectStoreTemplateConfiguration,
    AzureObjectStoreTemplateConfiguration,
]
ObjectStoreConfiguration = Union[
    S3ObjectStoreConfiguration,
    DiskObjectStoreConfiguration,
    AzureObjectStoreConfiguration,
    GenericS3ObjectStoreConfiguration,
]
MarkdownContent = str


class ObjectStoreTemplateVariable(StrictModel):
    name: str
    help: Optional[MarkdownContent]
    type: ObjectStoreTemplateVariableType


class ObjectStoreTemplateSecret(StrictModel):
    name: str
    help: Optional[MarkdownContent]


class ObjectStoreTemplateBase(StrictModel):
    """Version of ObjectStoreTemplate we can send to the UI/API.

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
    variables: Optional[List[ObjectStoreTemplateVariable]] = None
    secrets: Optional[List[ObjectStoreTemplateSecret]] = None


class ObjectStoreTemplateSummary(ObjectStoreTemplateBase):
    badges: List[BadgeDict]
    type: ObjectStoreTemplateType


class ObjectStoreTemplate(ObjectStoreTemplateBase):
    configuration: ObjectStoreTemplateConfiguration


ObjectStoreTemplateCatalog = RootModel[List[ObjectStoreTemplate]]


class ObjectStoreTemplateSummaries(RootModel):
    root: List[ObjectStoreTemplateSummary]


def template_to_configuration(
    template: ObjectStoreTemplate,
    variables: Dict[str, ObjectStoreTemplateVariableValueType],
    secrets: Dict[str, str],
    user_details: Dict[str, Any],
) -> ObjectStoreConfiguration:
    configuration_template = template.configuration
    template_variables = {
        "variables": variables,
        "secrets": secrets,
        "user": user_details,
    }

    def expand_template(_, key, value):
        if isinstance(value, str) and "{{" in value and "}}" in value:
            # NativeEnvironment preserves Python types
            template = NativeEnvironment().from_string(value)
            return key, template.render(**template_variables)
        return key, value

    raw_config = remap(configuration_template.model_dump(), visit=expand_template)
    return to_configuration_object(raw_config)


TypesToConfigurationClasses: Dict[ObjectStoreTemplateType, Type[ObjectStoreConfiguration]] = {
    "s3": S3ObjectStoreConfiguration,
    "generic_s3": GenericS3ObjectStoreConfiguration,
    "azure_blob": AzureObjectStoreConfiguration,
    "disk": DiskObjectStoreConfiguration,
}


def to_configuration_object(configuration_dict: Dict[str, Any]) -> ObjectStoreConfiguration:
    if "type" not in configuration_dict:
        raise KeyError("Configuration objects require an object store 'type' key, none found.")
    object_store_type = configuration_dict["type"]
    if object_store_type not in TypesToConfigurationClasses:
        raise ValueError(f"Unknown object store type found in raw configuration dictionary ({object_store_type}).")
    return TypesToConfigurationClasses[object_store_type](**configuration_dict)
