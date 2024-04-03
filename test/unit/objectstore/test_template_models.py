from yaml import safe_load

from galaxy.objectstore.templates.manager import raw_config_to_catalog
from galaxy.objectstore.templates.models import (
    AzureObjectStoreConfiguration,
    DiskObjectStoreConfiguration,
    GenericS3ObjectStoreConfiguration,
    ObjectStoreTemplateCatalog,
    S3ObjectStoreConfiguration,
    template_to_configuration,
)

LIBRARY_1 = """
- id: amazon_bucket
  name: Amazon Bucket
  description: An Amazon S3 Bucket
  variables:
    use_reduced_redundancy:
      type: boolean
      help: Reduce redundancy and save money.
  secrets:
    access_key:
      help: AWS access key to use when connecting to AWS resources.
    secret_key:
      help: AWS secret key to use when connecting to AWS resources.
    bucket_name:
      help: Name of bucket to use when connecting to AWS resources.
  configuration:
    type: s3
    auth:
        access_key: '{{ secrets.access_key}}'
        secret_key: '{{ secrets.secret_key}}'
    bucket:
        name: '{{ secrets.bucket_name}}'
        use_reduced_redundancy: '{{ variables.use_reduced_redundancy}}'
    badges:
      - type: less_stable
      - type: slower
      - type: not_backed_up
"""


def test_parsing_simple_s3():
    template_library = _parse_template_library(LIBRARY_1)
    assert len(template_library.root) == 1
    s3_template = template_library.root[0]
    assert s3_template.description == "An Amazon S3 Bucket"
    configuration_obj = template_to_configuration(
        s3_template,
        {"use_reduced_redundancy": False},
        {"access_key": "sec1", "secret_key": "sec2", "bucket_name": "sec3"},
        user_details={},
    )
    badges = s3_template.configuration.badges
    assert badges
    assert len(badges) == 3

    # expanded configuration should validate with template expansions...
    assert isinstance(configuration_obj, S3ObjectStoreConfiguration)
    configuration = configuration_obj.model_dump()

    assert configuration["type"] == "s3"
    assert configuration["auth"]["access_key"] == "sec1"
    assert configuration["auth"]["secret_key"] == "sec2"
    assert configuration["bucket"]["name"] == "sec3"
    assert configuration["bucket"]["use_reduced_redundancy"] is False
    assert len(configuration["badges"]) == 3


LIBRARY_GENERIC_S3 = """
- id: minio_bucket
  name: MinIO Bucket
  description: A MinIO bucket connected using a generic S3 object store.
  variables:
    use_reduced_redundancy:
      type: boolean
      help: Reduce redundancy and save money.
  secrets:
    access_key:
      help: AWS access key to use when connecting to AWS resources.
    secret_key:
      help: AWS secret key to use when connecting to AWS resources.
    bucket_name:
      help: Name of bucket to use when connecting to AWS resources.
  configuration:
    type: generic_s3
    auth:
        access_key: '{{ secrets.access_key}}'
        secret_key: '{{ secrets.secret_key}}'
    bucket:
        name: '{{ secrets.bucket_name}}'
        use_reduced_redundancy: '{{ variables.use_reduced_redundancy}}'
    connection:
        host: minio.galaxyproject.org
        port: 5679
    badges:
      - type: less_stable
      - type: slower
      - type: not_backed_up
"""


def test_parsing_generic_s3():
    template_library = _parse_template_library(LIBRARY_GENERIC_S3)
    assert len(template_library.root) == 1
    s3_template = template_library.root[0]
    assert s3_template.description == "A MinIO bucket connected using a generic S3 object store."
    configuration_obj = template_to_configuration(
        s3_template,
        {"use_reduced_redundancy": False},
        {"access_key": "sec1", "secret_key": "sec2", "bucket_name": "sec3"},
        user_details={},
    )
    badges = s3_template.configuration.badges
    assert badges
    assert len(badges) == 3

    # expanded configuration should validate with template expansions...
    assert isinstance(configuration_obj, GenericS3ObjectStoreConfiguration)
    configuration = configuration_obj.model_dump()

    assert configuration["type"] == "generic_s3"
    assert configuration["auth"]["access_key"] == "sec1"
    assert configuration["auth"]["secret_key"] == "sec2"
    assert configuration["bucket"]["name"] == "sec3"
    assert configuration["bucket"]["use_reduced_redundancy"] is False
    assert configuration["connection"]["host"] == "minio.galaxyproject.org"
    assert configuration["connection"]["port"] == 5679
    assert configuration["connection"]["conn_path"] == ""
    assert configuration["connection"]["is_secure"] is True
    assert len(configuration["badges"]) == 3


LIBRARY_2 = """
- id: general_disk
  name: General Disk
  description: General Disk Bound to You
  configuration:
    type: disk
    files_dir: '/data/general/{{ user.username }}'
- id: secure_disk
  name: Secure Disk
  description: Secure Disk Bound to You
  configuration:
    type: disk
    files_dir: '/data/secure/{{ user.username }}'
"""


def test_parsing_multiple_posix():
    template_library = _parse_template_library(LIBRARY_2)
    assert len(template_library.root) == 2
    general_template = template_library.root[0]
    secure_template = template_library.root[1]

    assert general_template.version == 0
    assert secure_template.version == 0
    assert secure_template.hidden is False

    general_configuration = template_to_configuration(general_template, {}, {}, user_details={"username": "jane"})
    assert isinstance(general_configuration, DiskObjectStoreConfiguration)
    assert general_configuration.files_dir == "/data/general/jane"

    secure_configuration = template_to_configuration(secure_template, {}, {}, user_details={"username": "jane"})
    assert isinstance(secure_configuration, DiskObjectStoreConfiguration)
    assert secure_configuration.files_dir == "/data/secure/jane"


LIBRARY_AZURE_CONTAINER = """
- id: amazon_bucket
  name: Azure Container
  description: An Azure Container
  variables:
    account_name:
      type: string
      help: Azure account name to use when connecting to Azure resources.
  secrets:
    account_key:
      help: Azure account key to use when connecting to Azure resources.
    container_name:
      help: Name of container to use when connecting to Azure cloud resources.
  configuration:
    type: azure_blob
    auth:
        account_name: '{{ variables.account_name}}'
        account_key: '{{ secrets.account_key}}'
    container:
        name: '{{ secrets.container_name}}'
"""


def test_parsing_azure():
    template_library = _parse_template_library(LIBRARY_AZURE_CONTAINER)
    assert len(template_library.root) == 1
    azure_template = template_library.root[0]
    assert azure_template.description == "An Azure Container"
    configuration_obj = template_to_configuration(
        azure_template,
        {"account_name": "galaxyproject"},
        {"account_key": "sec1", "container_name": "sec2"},
        user_details={},
    )
    assert isinstance(configuration_obj, AzureObjectStoreConfiguration)
    assert configuration_obj.auth.account_name == "galaxyproject"
    assert configuration_obj.auth.account_key == "sec1"
    assert configuration_obj.container.name == "sec2"


def _parse_template_library(contents: str) -> ObjectStoreTemplateCatalog:
    raw_contents = safe_load(contents)
    return raw_config_to_catalog(raw_contents)
