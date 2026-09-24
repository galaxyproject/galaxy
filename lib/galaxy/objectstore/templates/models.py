from typing import (
    Annotated,
    Any,
    Literal,
    TypeAlias,
)

from pydantic import (
    Field,
    RootModel,
)

from galaxy.objectstore.badges import (
    BadgeDict,
    StoredBadgeDict,
)
from galaxy.util.config_templates import (
    EnvironmentDict,
    expand_raw_config,
    ImplicitConfigurationParameters,
    MarkdownContent,
    merge_implicit_parameters,
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
ObjectStoreTemplateVariableValueType: TypeAlias = TemplateVariableValueType
ObjectStoreTemplateType = Literal["aws_s3", "azure_blob", "boto3", "disk", "generic_s3", "onedata", "rucio", "irods"]


class S3AuthTemplate(StrictModel):
    access_key: str | TemplateExpansion
    secret_key: str | TemplateExpansion


class S3Auth(StrictModel):
    access_key: str
    secret_key: str


class S3BucketTemplate(StrictModel):
    name: str | TemplateExpansion
    use_reduced_redundancy: bool | TemplateExpansion | None = None


class S3Bucket(StrictModel):
    name: str
    use_reduced_redundancy: bool | None = None


BadgeList = list[StoredBadgeDict] | None


class AwsS3ObjectStoreTemplateConfiguration(StrictModel):
    type: Literal["aws_s3"]
    auth: S3AuthTemplate
    bucket: S3BucketTemplate
    badges: BadgeList = None
    template_start: str | None = None
    template_end: str | None = None


class AwsS3ObjectStoreConfiguration(StrictModel):
    type: Literal["aws_s3"]
    auth: S3Auth
    bucket: S3Bucket
    badges: BadgeList = None


class AzureAuthTemplate(StrictModel):
    account_name: str | TemplateExpansion
    account_key: str | TemplateExpansion


class AzureAuth(StrictModel):
    account_name: str
    account_key: str


class AzureContainerTemplate(StrictModel):
    name: str | TemplateExpansion


class AzureContainer(StrictModel):
    name: str


class AzureTransferTemplate(StrictModel):
    max_concurrency: int | TemplateExpansion | None = None
    download_max_concurrency: int | TemplateExpansion | None = None
    upload_max_concurrency: int | TemplateExpansion | None = None
    max_single_put_size: int | TemplateExpansion | None = None
    max_single_get_size: int | TemplateExpansion | None = None
    max_block_size: int | TemplateExpansion | None = None


class AzureObjectStoreTemplateConfiguration(StrictModel):
    type: Literal["azure_blob"]
    auth: AzureAuthTemplate
    container: AzureContainerTemplate
    transfer: AzureTransferTemplate | None = None
    badges: BadgeList = None
    template_start: str | None = None
    template_end: str | None = None


class AzureTransfer(StrictModel):
    max_concurrency: int | None = None
    download_max_concurrency: int | None = None
    upload_max_concurrency: int | None = None
    max_single_put_size: int | None = None
    max_single_get_size: int | None = None
    max_block_size: int | None = None


class AzureObjectStoreConfiguration(StrictModel):
    type: Literal["azure_blob"]
    auth: AzureAuth
    container: AzureContainer
    transfer: AzureTransfer | None = None
    badges: BadgeList = None


class Boto3BucketTemplate(StrictModel):
    name: str | TemplateExpansion


class Boto3ConnectionTemplate(StrictModel):
    endpoint_url: str | TemplateExpansion
    region: str | TemplateExpansion | None = None


class Boto3TransferTemplate(StrictModel):
    use_threads: bool | TemplateExpansion | None = None
    multipart_threshold: int | TemplateExpansion | None = None
    max_concurrency: int | TemplateExpansion | None = None
    multipart_chunksize: int | TemplateExpansion | None = None
    num_download_attempts: int | TemplateExpansion | None = None
    max_io_queue: int | TemplateExpansion | None = None
    io_chunksize: int | TemplateExpansion | None = None
    max_bandwidth: int | TemplateExpansion | None = None
    download_use_threads: bool | TemplateExpansion | None = None
    download_multipart_threshold: int | TemplateExpansion | None = None
    download_max_concurrency: int | TemplateExpansion | None = None
    download_multipart_chunksize: int | TemplateExpansion | None = None
    download_num_download_attempts: int | TemplateExpansion | None = None
    download_max_io_queue: int | TemplateExpansion | None = None
    download_io_chunksize: int | TemplateExpansion | None = None
    download_max_bandwidth: int | TemplateExpansion | None = None
    upload_use_threads: bool | TemplateExpansion | None = None
    upload_multipart_threshold: int | TemplateExpansion | None = None
    upload_max_concurrency: int | TemplateExpansion | None = None
    upload_multipart_chunksize: int | TemplateExpansion | None = None
    upload_num_download_attempts: int | TemplateExpansion | None = None
    upload_max_io_queue: int | TemplateExpansion | None = None
    upload_io_chunksize: int | TemplateExpansion | None = None
    upload_max_bandwidth: int | TemplateExpansion | None = None


class Boto3ObjectStoreTemplateConfiguration(StrictModel):
    type: Literal["boto3"]
    auth: S3AuthTemplate
    bucket: Boto3BucketTemplate
    connection: Boto3ConnectionTemplate | None = None
    transfer: Boto3TransferTemplate | None = None
    badges: BadgeList = None
    template_start: str | None = None
    template_end: str | None = None


class Boto3Bucket(StrictModel):
    name: str


class Boto3Connection(StrictModel):
    endpoint_url: str
    region: str | None = None


class Boto3Transfer(StrictModel):
    use_threads: bool | None = None
    multipart_threshold: int | None = None
    max_concurrency: int | None = None
    multipart_chunksize: int | None = None
    num_download_attempts: int | None = None
    max_io_queue: int | None = None
    io_chunksize: int | None = None
    max_bandwidth: int | None = None
    download_use_threads: bool | None = None
    download_multipart_threshold: int | None = None
    download_max_concurrency: int | None = None
    download_multipart_chunksize: int | None = None
    download_num_download_attempts: int | None = None
    download_max_io_queue: int | None = None
    download_io_chunksize: int | None = None
    download_max_bandwidth: int | None = None
    upload_use_threads: bool | None = None
    upload_multipart_threshold: int | None = None
    upload_max_concurrency: int | None = None
    upload_multipart_chunksize: int | None = None
    upload_num_download_attempts: int | None = None
    upload_max_io_queue: int | None = None
    upload_io_chunksize: int | None = None
    upload_max_bandwidth: int | None = None


class Boto3ObjectStoreConfiguration(StrictModel):
    type: Literal["boto3"]
    auth: S3Auth
    bucket: Boto3Bucket
    connection: Boto3Connection | None = None
    transfer: Boto3Transfer | None = None
    badges: BadgeList = None


class DiskObjectStoreTemplateConfiguration(StrictModel):
    type: Literal["disk"]
    files_dir: str | TemplateExpansion
    badges: BadgeList = None
    template_start: str | None = None
    template_end: str | None = None


class DiskObjectStoreConfiguration(StrictModel):
    type: Literal["disk"]
    files_dir: str
    badges: BadgeList = None


class S3ConnectionTemplate(StrictModel):
    host: str | TemplateExpansion
    port: int | TemplateExpansion
    is_secure: bool | TemplateExpansion | None = True
    conn_path: str | TemplateExpansion | None = ""


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
    template_start: str | None = None
    template_end: str | None = None


class GenericS3ObjectStoreConfiguration(StrictModel):
    type: Literal["generic_s3"]
    auth: S3Auth
    bucket: S3Bucket
    connection: S3Connection
    badges: BadgeList = None


class OnedataAuthTemplate(StrictModel):
    access_token: str | TemplateExpansion


class OnedataAuth(StrictModel):
    access_token: str


class OnedataConnectionTemplate(StrictModel):
    onezone_domain: str | TemplateExpansion
    disable_tls_certificate_validation: bool | TemplateExpansion = False


class OnedataConnection(StrictModel):
    onezone_domain: str
    disable_tls_certificate_validation: bool = False


class OnedataSpaceTemplate(StrictModel):
    name: str | TemplateExpansion
    galaxy_root_dir: str | TemplateExpansion | None = ""


class OnedataSpace(StrictModel):
    name: str
    galaxy_root_dir: str


class OnedataObjectStoreTemplateConfiguration(StrictModel):
    type: Literal["onedata"]
    auth: OnedataAuthTemplate
    connection: OnedataConnectionTemplate
    space: OnedataSpaceTemplate
    badges: BadgeList = None
    template_start: str | None = None
    template_end: str | None = None


class OnedataObjectStoreConfiguration(StrictModel):
    type: Literal["onedata"]
    auth: OnedataAuth
    connection: OnedataConnection
    space: OnedataSpace
    badges: BadgeList = None


class RucioObjectStoreTemplateConfiguration(StrictModel):
    type: Literal["rucio"]
    scope: str
    upload_rse_name: str
    upload_scheme: Any | None = None
    download_schemes: Any | None = None
    auth_host: str
    host: str
    auth_type: str
    account: str | TemplateExpansion
    username: str | TemplateExpansion
    password: str | TemplateExpansion
    badges: BadgeList = None
    register_only: bool | None = False
    template_start: str | None = None
    template_end: str | None = None


class RucioObjectStoreConfiguration(StrictModel):
    type: Literal["rucio"]
    scope: str
    upload_rse_name: str
    upload_scheme: Any | None = None
    download_schemes: Any | None = None
    register_only: bool | None = False
    auth_host: str
    host: str
    auth_type: str
    account: str
    username: str
    password: str
    badges: BadgeList = None


# iRODS


class IrodsAuthTemplate(StrictModel):
    username: str | TemplateExpansion
    password: str | TemplateExpansion


class IrodsAuth(StrictModel):
    username: str
    password: str


class IrodsConnectionTemplate(StrictModel):
    host: str | TemplateExpansion
    port: int | TemplateExpansion
    timeout: int | TemplateExpansion | None
    refresh_time: int | TemplateExpansion | None
    connection_pool_monitor_interval: int | TemplateExpansion | None


class IrodsConnection(StrictModel):
    host: str
    port: int | None
    timeout: int | None = None
    refresh_time: int | None = None
    connection_pool_monitor_interval: int | None = None


class IrodsPathTemplate(StrictModel):
    path: str | TemplateExpansion | None = ""


class IrodsPath(StrictModel):
    path: str | None = ""


class IrodsResourceTemplate(StrictModel):
    name: str | TemplateExpansion


class IrodsResource(StrictModel):
    name: str


class IrodsZoneTemplate(StrictModel):
    name: str | TemplateExpansion


class IrodsZone(StrictModel):
    name: str


class IrodsSslTemplate(StrictModel):
    client_server_negotiation: str | TemplateExpansion | None = ""
    client_server_policy: str | TemplateExpansion | None = ""
    encryption_algorithm: str | TemplateExpansion | None = ""
    encryption_key_size: int | TemplateExpansion | None = None
    encryption_num_hash_rounds: int | TemplateExpansion | None = None
    encryption_salt_size: int | TemplateExpansion | None = None
    ssl_verify_server: str | TemplateExpansion | None = ""
    ssl_ca_certificate_file: str | TemplateExpansion | None = ""


class IrodsSsl(StrictModel):
    client_server_negotiation: str | None = ""
    client_server_policy: str | None = ""
    encryption_algorithm: str | None = ""
    encryption_key_size: int | None = None
    encryption_num_hash_rounds: int | None = None
    encryption_salt_size: int | None = None
    ssl_verify_server: str | None = ""
    ssl_ca_certificate_file: str | None = ""


class IrodsObjectStoreTemplateConfiguration(StrictModel):
    type: Literal["irods"]
    auth: IrodsAuthTemplate
    connection: IrodsConnectionTemplate
    zone: IrodsZoneTemplate
    resource: IrodsResourceTemplate
    ssl: IrodsSslTemplate | None = None
    logical: IrodsPathTemplate | None = None
    badges: BadgeList = None
    template_start: str | None = None
    template_end: str | None = None


class IrodsObjectStoreConfiguration(StrictModel):
    type: Literal["irods"]
    auth: IrodsAuth
    connection: IrodsConnection
    zone: IrodsZone
    resource: IrodsResource
    ssl: IrodsSsl | None = None
    logical: IrodsPath | None = None
    badges: BadgeList = None


ObjectStoreTemplateConfiguration = Annotated[
    AwsS3ObjectStoreTemplateConfiguration
    | Boto3ObjectStoreTemplateConfiguration
    | GenericS3ObjectStoreTemplateConfiguration
    | DiskObjectStoreTemplateConfiguration
    | AzureObjectStoreTemplateConfiguration
    | OnedataObjectStoreTemplateConfiguration
    | RucioObjectStoreTemplateConfiguration
    | IrodsObjectStoreTemplateConfiguration,
    Field(discriminator="type"),
]

ObjectStoreConfiguration = Annotated[
    AwsS3ObjectStoreConfiguration
    | Boto3ObjectStoreConfiguration
    | DiskObjectStoreConfiguration
    | AzureObjectStoreConfiguration
    | GenericS3ObjectStoreConfiguration
    | OnedataObjectStoreConfiguration
    | RucioObjectStoreConfiguration
    | IrodsObjectStoreConfiguration,
    Field(discriminator="type"),
]

ObjectStoreTemplateVariable = TemplateVariable
ObjectStoreTemplateSecret = TemplateSecret


class ObjectStoreTemplateBase(StrictModel):
    """Version of ObjectStoreTemplate we can send to the UI/API.

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


class ObjectStoreTemplateSummary(ObjectStoreTemplateBase):
    badges: list[BadgeDict]
    type: ObjectStoreTemplateType


class ObjectStoreTemplate(ObjectStoreTemplateBase):
    configuration: ObjectStoreTemplateConfiguration
    environment: list[TemplateEnvironmentEntry] | None = None

    @property
    def type(self):
        return self.configuration.type


ObjectStoreTemplateCatalog = RootModel[list[ObjectStoreTemplate]]


class ObjectStoreTemplateSummaries(RootModel):
    root: list[ObjectStoreTemplateSummary]


def template_to_configuration(
    template: ObjectStoreTemplate,
    variables: dict[str, ObjectStoreTemplateVariableValueType],
    secrets: SecretsDict,
    user_details: UserDetailsDict,
    environment: EnvironmentDict,
    implicit: ImplicitConfigurationParameters | None = None,
) -> ObjectStoreConfiguration:
    configuration_template = template.configuration
    populate_default_variables(template.variables, variables)
    raw_config = expand_raw_config(configuration_template, variables, secrets, user_details, environment)
    merge_implicit_parameters(raw_config, implicit)
    return to_configuration_object(raw_config)


TypesToConfigurationClasses: dict[ObjectStoreTemplateType, type[ObjectStoreConfiguration]] = {
    "aws_s3": AwsS3ObjectStoreConfiguration,
    "boto3": Boto3ObjectStoreConfiguration,
    "generic_s3": GenericS3ObjectStoreConfiguration,
    "azure_blob": AzureObjectStoreConfiguration,
    "disk": DiskObjectStoreConfiguration,
    "onedata": OnedataObjectStoreConfiguration,
    "rucio": RucioObjectStoreConfiguration,
    "irods": IrodsObjectStoreConfiguration,
}


def to_configuration_object(configuration_dict: dict[str, Any]) -> ObjectStoreConfiguration:
    if "type" not in configuration_dict:
        raise KeyError("Configuration objects require an object store 'type' key, none found.")
    object_store_type = configuration_dict["type"]
    if object_store_type not in TypesToConfigurationClasses:
        raise ValueError(f"Unknown object store type found in raw configuration dictionary ({object_store_type}).")
    return TypesToConfigurationClasses[object_store_type](**configuration_dict)
