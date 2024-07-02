from typing import (
    Any,
    Dict,
    List,
    Optional,
    Type,
    Union,
)

from pydantic import RootModel
from typing_extensions import Literal

from galaxy.objectstore.badges import (
    BadgeDict,
    StoredBadgeDict,
)
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
    TemplateVariableType,
    TemplateVariableValueType,
    UserDetailsDict,
)

ObjectStoreTemplateVariableType = TemplateVariableType
ObjectStoreTemplateVariableValueType = TemplateVariableValueType
ObjectStoreTemplateType = Literal["aws_s3", "azure_blob", "boto3", "disk", "generic_s3", "onedata"]


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


class AwsS3ObjectStoreTemplateConfiguration(StrictModel):
    type: Literal["aws_s3"]
    auth: S3AuthTemplate
    bucket: S3BucketTemplate
    badges: BadgeList = None
    template_start: Optional[str] = None
    template_end: Optional[str] = None


class AwsS3ObjectStoreConfiguration(StrictModel):
    type: Literal["aws_s3"]
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


class AzureTransferTemplate(StrictModel):
    max_concurrency: Optional[Union[int, TemplateExpansion]] = None
    download_max_concurrency: Optional[Union[int, TemplateExpansion]] = None
    upload_max_concurrency: Optional[Union[int, TemplateExpansion]] = None
    max_single_put_size: Optional[Union[int, TemplateExpansion]] = None
    max_single_get_size: Optional[Union[int, TemplateExpansion]] = None
    max_block_size: Optional[Union[int, TemplateExpansion]] = None


class AzureObjectStoreTemplateConfiguration(StrictModel):
    type: Literal["azure_blob"]
    auth: AzureAuthTemplate
    container: AzureContainerTemplate
    transfer: Optional[AzureTransferTemplate] = None
    badges: BadgeList = None
    template_start: Optional[str] = None
    template_end: Optional[str] = None


class AzureTransfer(StrictModel):
    max_concurrency: Optional[int] = None
    download_max_concurrency: Optional[int] = None
    upload_max_concurrency: Optional[int] = None
    max_single_put_size: Optional[int] = None
    max_single_get_size: Optional[int] = None
    max_block_size: Optional[int] = None


class AzureObjectStoreConfiguration(StrictModel):
    type: Literal["azure_blob"]
    auth: AzureAuth
    container: AzureContainer
    transfer: Optional[AzureTransfer] = None
    badges: BadgeList = None


class Boto3BucketTemplate(StrictModel):
    name: Union[str, TemplateExpansion]


class Boto3ConnectionTemplate(StrictModel):
    endpoint_url: Union[str, TemplateExpansion]
    region: Optional[Union[str, TemplateExpansion]] = None


class Boto3TransferTemplate(StrictModel):
    use_threads: Optional[Union[bool, TemplateExpansion]] = None
    multipart_threshold: Optional[Union[int, TemplateExpansion]] = None
    max_concurrency: Optional[Union[int, TemplateExpansion]] = None
    multipart_chunksize: Optional[Union[int, TemplateExpansion]] = None
    num_download_attempts: Optional[Union[int, TemplateExpansion]] = None
    max_io_queue: Optional[Union[int, TemplateExpansion]] = None
    io_chunksize: Optional[Union[int, TemplateExpansion]] = None
    max_bandwidth: Optional[Union[int, TemplateExpansion]] = None
    download_use_threads: Optional[Union[bool, TemplateExpansion]] = None
    download_multipart_threshold: Optional[Union[int, TemplateExpansion]] = None
    download_max_concurrency: Optional[Union[int, TemplateExpansion]] = None
    download_multipart_chunksize: Optional[Union[int, TemplateExpansion]] = None
    download_num_download_attempts: Optional[Union[int, TemplateExpansion]] = None
    download_max_io_queue: Optional[Union[int, TemplateExpansion]] = None
    download_io_chunksize: Optional[Union[int, TemplateExpansion]] = None
    download_max_bandwidth: Optional[Union[int, TemplateExpansion]] = None
    upload_use_threads: Optional[Union[bool, TemplateExpansion]] = None
    upload_multipart_threshold: Optional[Union[int, TemplateExpansion]] = None
    upload_max_concurrency: Optional[Union[int, TemplateExpansion]] = None
    upload_multipart_chunksize: Optional[Union[int, TemplateExpansion]] = None
    upload_num_download_attempts: Optional[Union[int, TemplateExpansion]] = None
    upload_max_io_queue: Optional[Union[int, TemplateExpansion]] = None
    upload_io_chunksize: Optional[Union[int, TemplateExpansion]] = None
    upload_max_bandwidth: Optional[Union[int, TemplateExpansion]] = None


class Boto3ObjectStoreTemplateConfiguration(StrictModel):
    type: Literal["boto3"]
    auth: S3AuthTemplate
    bucket: Boto3BucketTemplate
    connection: Optional[Boto3ConnectionTemplate] = None
    transfer: Optional[Boto3TransferTemplate] = None
    badges: BadgeList = None
    template_start: Optional[str] = None
    template_end: Optional[str] = None


class Boto3Bucket(StrictModel):
    name: str


class Boto3Connection(StrictModel):
    endpoint_url: str
    region: Optional[str] = None


class Boto3Transfer(StrictModel):
    use_threads: Optional[bool] = None
    multipart_threshold: Optional[int] = None
    max_concurrency: Optional[int] = None
    multipart_chunksize: Optional[int] = None
    num_download_attempts: Optional[int] = None
    max_io_queue: Optional[int] = None
    io_chunksize: Optional[int] = None
    max_bandwidth: Optional[int] = None
    download_use_threads: Optional[bool] = None
    download_multipart_threshold: Optional[int] = None
    download_max_concurrency: Optional[int] = None
    download_multipart_chunksize: Optional[int] = None
    download_num_download_attempts: Optional[int] = None
    download_max_io_queue: Optional[int] = None
    download_io_chunksize: Optional[int] = None
    download_max_bandwidth: Optional[int] = None
    upload_use_threads: Optional[bool] = None
    upload_multipart_threshold: Optional[int] = None
    upload_max_concurrency: Optional[int] = None
    upload_multipart_chunksize: Optional[int] = None
    upload_num_download_attempts: Optional[int] = None
    upload_max_io_queue: Optional[int] = None
    upload_io_chunksize: Optional[int] = None
    upload_max_bandwidth: Optional[int] = None


class Boto3ObjectStoreConfiguration(StrictModel):
    type: Literal["boto3"]
    auth: S3Auth
    bucket: Boto3Bucket
    connection: Optional[Boto3Connection] = None
    transfer: Optional[Boto3Transfer] = None
    badges: BadgeList = None


class DiskObjectStoreTemplateConfiguration(StrictModel):
    type: Literal["disk"]
    files_dir: Union[str, TemplateExpansion]
    badges: BadgeList = None
    template_start: Optional[str] = None
    template_end: Optional[str] = None


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
    template_start: Optional[str] = None
    template_end: Optional[str] = None


class GenericS3ObjectStoreConfiguration(StrictModel):
    type: Literal["generic_s3"]
    auth: S3Auth
    bucket: S3Bucket
    connection: S3Connection
    badges: BadgeList = None


class OnedataAuthTemplate(StrictModel):
    access_token: Union[str, TemplateExpansion]


class OnedataAuth(StrictModel):
    access_token: str


class OnedataConnectionTemplate(StrictModel):
    onezone_domain: Union[str, TemplateExpansion]
    disable_tls_certificate_validation: Union[bool, TemplateExpansion] = False


class OnedataConnection(StrictModel):
    onezone_domain: str
    disable_tls_certificate_validation: bool = False


class OnedataSpaceTemplate(StrictModel):
    name: Union[str, TemplateExpansion]
    galaxy_root_dir: Optional[Union[str, TemplateExpansion]] = ""


class OnedataSpace(StrictModel):
    name: str
    galaxy_root_dir: str


class OnedataObjectStoreTemplateConfiguration(StrictModel):
    type: Literal["onedata"]
    auth: OnedataAuthTemplate
    connection: OnedataConnectionTemplate
    space: OnedataSpaceTemplate
    badges: BadgeList = None
    template_start: Optional[str] = None
    template_end: Optional[str] = None


class OnedataObjectStoreConfiguration(StrictModel):
    type: Literal["onedata"]
    auth: OnedataAuth
    connection: OnedataConnection
    space: OnedataSpace
    badges: BadgeList = None


ObjectStoreTemplateConfiguration = Union[
    AwsS3ObjectStoreTemplateConfiguration,
    Boto3ObjectStoreTemplateConfiguration,
    GenericS3ObjectStoreTemplateConfiguration,
    DiskObjectStoreTemplateConfiguration,
    AzureObjectStoreTemplateConfiguration,
    OnedataObjectStoreTemplateConfiguration,
]
ObjectStoreConfiguration = Union[
    AwsS3ObjectStoreConfiguration,
    Boto3ObjectStoreConfiguration,
    DiskObjectStoreConfiguration,
    AzureObjectStoreConfiguration,
    GenericS3ObjectStoreConfiguration,
    OnedataObjectStoreConfiguration,
]


ObjectStoreTemplateVariable = TemplateVariable
ObjectStoreTemplateSecret = TemplateSecret


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
    variables: Optional[List[TemplateVariable]] = None
    secrets: Optional[List[TemplateSecret]] = None


class ObjectStoreTemplateSummary(ObjectStoreTemplateBase):
    badges: List[BadgeDict]
    type: ObjectStoreTemplateType


class ObjectStoreTemplate(ObjectStoreTemplateBase):
    configuration: ObjectStoreTemplateConfiguration
    environment: Optional[List[TemplateEnvironmentEntry]] = None


ObjectStoreTemplateCatalog = RootModel[List[ObjectStoreTemplate]]


class ObjectStoreTemplateSummaries(RootModel):
    root: List[ObjectStoreTemplateSummary]


def template_to_configuration(
    template: ObjectStoreTemplate,
    variables: Dict[str, ObjectStoreTemplateVariableValueType],
    secrets: SecretsDict,
    user_details: UserDetailsDict,
    environment: EnvironmentDict,
) -> ObjectStoreConfiguration:
    configuration_template = template.configuration
    populate_default_variables(template.variables, variables)
    raw_config = expand_raw_config(configuration_template, variables, secrets, user_details, environment)
    return to_configuration_object(raw_config)


TypesToConfigurationClasses: Dict[ObjectStoreTemplateType, Type[ObjectStoreConfiguration]] = {
    "aws_s3": AwsS3ObjectStoreConfiguration,
    "boto3": Boto3ObjectStoreConfiguration,
    "generic_s3": GenericS3ObjectStoreConfiguration,
    "azure_blob": AzureObjectStoreConfiguration,
    "disk": DiskObjectStoreConfiguration,
    "onedata": OnedataObjectStoreConfiguration,
}


def to_configuration_object(configuration_dict: Dict[str, Any]) -> ObjectStoreConfiguration:
    if "type" not in configuration_dict:
        raise KeyError("Configuration objects require an object store 'type' key, none found.")
    object_store_type = configuration_dict["type"]
    if object_store_type not in TypesToConfigurationClasses:
        raise ValueError(f"Unknown object store type found in raw configuration dictionary ({object_store_type}).")
    return TypesToConfigurationClasses[object_store_type](**configuration_dict)
