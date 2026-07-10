import os

from yaml import safe_load

from galaxy.objectstore.templates.examples import get_example
from galaxy.objectstore.templates.manager import raw_config_to_catalog
from galaxy.objectstore.templates.models import (
    AwsS3ObjectStoreConfiguration,
    AzureObjectStoreConfiguration,
    CloudObjectStoreConfiguration,
    DiskObjectStoreConfiguration,
    GenericS3ObjectStoreConfiguration,
    ObjectStoreTemplateCatalog,
    template_to_configuration,
)
from galaxy.util.config_templates import VariablesDict

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
    type: aws_s3
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
        environment={},
    )
    badges = s3_template.configuration.badges
    assert badges
    assert len(badges) == 3

    # expanded configuration should validate with template expansions...
    assert isinstance(configuration_obj, AwsS3ObjectStoreConfiguration)
    configuration = configuration_obj.model_dump()

    assert configuration["type"] == "aws_s3"
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
        environment={},
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

    general_configuration = template_to_configuration(
        general_template, {}, {}, user_details={"username": "jane"}, environment={}
    )
    assert isinstance(general_configuration, DiskObjectStoreConfiguration)
    assert general_configuration.files_dir == "/data/general/jane"

    secure_configuration = template_to_configuration(
        secure_template, {}, {}, user_details={"username": "jane"}, environment={}
    )
    assert isinstance(secure_configuration, DiskObjectStoreConfiguration)
    assert secure_configuration.files_dir == "/data/secure/jane"


LIBRARY_WITH_PATH_PARAMETER = """
- id: path_disk
  name: General Disk
  description: General Disk Bound to You
  configuration:
    type: disk
    files_dir: '/data/general/{{ user.username | ensure_path_component }}//{{ variables.project_name | ensure_path_component }}'
  variables:
    project_name:
      type: string  # dont do this in practice - use path_component for more eager validation
      help: Project name used in path for this template library.
"""


def test_parsing_with_path_security():
    template_library = _parse_template_library(LIBRARY_WITH_PATH_PARAMETER)
    assert len(template_library.root) == 1
    path_template = template_library.root[0]

    assert path_template.version == 0

    user_details = {"username": "jane"}
    variables: VariablesDict = {"project_name": "moo"}

    general_configuration = template_to_configuration(
        path_template, variables, {}, user_details=user_details, environment={}
    )
    assert isinstance(general_configuration, DiskObjectStoreConfiguration)
    assert os.path.abspath(general_configuration.files_dir) == "/data/general/jane/moo"

    variables = {"project_name": "../moo"}
    exc = None
    try:
        template_to_configuration(path_template, variables, {}, user_details=user_details, environment={})
    except Exception as e:
        exc = e
    assert exc is not None


LIBRARY_WITH_CUSTOM_TEMPLATE_START_END = """
- id: path_disk
  name: General Disk
  description: General Disk Bound to You
  configuration:
    type: disk
    files_dir: '/data/general/@= user.username | ensure_path_component =@/@= variables.project_name | ensure_path_component =@'
    template_start: '@='
    template_end: '=@'
  variables:
    project_name:
      type: string  # dont do this in practice - use path_component for more eager validation
      help: Project name used in path for this template library.
"""


def test_custom_template_start_and_ends():
    template_library = _parse_template_library(LIBRARY_WITH_CUSTOM_TEMPLATE_START_END)
    assert len(template_library.root) == 1
    path_template = template_library.root[0]

    assert path_template.version == 0

    user_details = {"username": "jane"}
    variables: VariablesDict = {"project_name": "moo"}

    general_configuration = template_to_configuration(
        path_template, variables, {}, user_details=user_details, environment={}
    )
    assert isinstance(general_configuration, DiskObjectStoreConfiguration)
    assert os.path.abspath(general_configuration.files_dir) == "/data/general/jane/moo"


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
        environment={},
    )
    assert isinstance(configuration_obj, AzureObjectStoreConfiguration)
    assert configuration_obj.auth.account_name == "galaxyproject"
    assert configuration_obj.auth.account_key == "sec1"
    assert configuration_obj.container.name == "sec2"


def test_minio_example_boolean():
    template_library = _parse_template_library(get_example("minio_example.yml"))
    assert len(template_library.root) == 1
    minio_template = template_library.root[0]
    configuration_obj = template_to_configuration(
        minio_template,
        {"access_key": "galaxyproject", "bucket": "galaxy"},
        {"secret_key": "sec1"},
        user_details={},
        environment={"host": "localhost", "port": "9000", "secure": "1", "connection_path": "moo/cow"},
    )
    assert isinstance(configuration_obj, GenericS3ObjectStoreConfiguration)
    assert configuration_obj.connection.is_secure

    configuration_obj = template_to_configuration(
        minio_template,
        {"access_key": "galaxyproject", "bucket": "galaxy"},
        {"secret_key": "sec1"},
        user_details={},
        environment={"host": "localhost", "port": "9000", "secure": "no", "connection_path": "moo/cow"},
    )
    assert isinstance(configuration_obj, GenericS3ObjectStoreConfiguration)
    assert not configuration_obj.connection.is_secure


LIBRARY_CLOUD = """
- id: cloudbridge_bucket
  name: CloudBridge Bucket
  description: An S3 bucket connected through the provider-agnostic cloud object store.
  variables:
    bucket_name:
      type: string
      help: Name of the bucket.
    max_concurrency:
      type: integer
      help: Number of parts to transfer in parallel.
  secrets:
    access_key:
      help: AWS access key to use when connecting to AWS resources.
    secret_key:
      help: AWS secret key to use when connecting to AWS resources.
  configuration:
    type: cloud
    provider: aws
    auth:
        access_key: '{{ secrets.access_key}}'
        secret_key: '{{ secrets.secret_key}}'
    bucket:
        name: '{{ variables.bucket_name}}'
    transfer:
        max_concurrency: '{{ variables.max_concurrency}}'
    badges:
      - type: less_stable
- id: cloudbridge_swift_container
  name: Swift Container
  description: A native Swift container connected through the cloud object store.
  secrets:
    password:
      help: OpenStack password.
  configuration:
    type: cloud
    provider: openstack
    auth:
        username: an_os_user
        password: '{{ secrets.password}}'
        project_name: os_project
        auth_url: https://keystone.example.org:5000/v3
        region: RegionOne
    bucket:
        name: os_container
"""


def test_parsing_cloud():
    template_library = _parse_template_library(LIBRARY_CLOUD)
    assert len(template_library.root) == 2

    aws_template = template_library.root[0]
    assert aws_template.type == "cloud"
    configuration_obj = template_to_configuration(
        aws_template,
        {"bucket_name": "mybucket", "max_concurrency": 4},
        {"access_key": "sec1", "secret_key": "sec2"},
        user_details={},
        environment={},
    )
    assert isinstance(configuration_obj, CloudObjectStoreConfiguration)
    configuration = configuration_obj.model_dump()
    assert configuration["type"] == "cloud"
    assert configuration["provider"] == "aws"
    assert configuration["auth"]["access_key"] == "sec1"
    assert configuration["auth"]["secret_key"] == "sec2"
    assert configuration["bucket"]["name"] == "mybucket"
    assert configuration["transfer"]["max_concurrency"] == 4

    swift_template = template_library.root[1]
    configuration_obj = template_to_configuration(
        swift_template,
        {},
        {"password": "sec3"},
        user_details={},
        environment={},
    )
    assert isinstance(configuration_obj, CloudObjectStoreConfiguration)
    assert configuration_obj.provider == "openstack"
    assert configuration_obj.auth.username == "an_os_user"
    assert configuration_obj.auth.password == "sec3"
    assert configuration_obj.auth.auth_url == "https://keystone.example.org:5000/v3"
    assert configuration_obj.bucket.name == "os_container"


def test_examples_parse():
    assert_example_parses("simple_example.yml")
    assert_example_parses("minio_example.yml")
    assert_example_parses("production_generic_s3_legacy.yml")
    assert_example_parses("production_generic_s3.yml")
    assert_example_parses("production_aws_s3.yml")
    assert_example_parses("production_aws_s3_legacy.yml")
    assert_example_parses("production_azure_blob.yml")
    assert_example_parses("cloudflare.yml")
    assert_example_parses("cloudflare_legacy.yml")
    assert_example_parses("minio_just_buckets.yml")
    assert_example_parses("minio_just_buckets_legacy.yml")
    assert_example_parses("azure_just_container.yml")
    assert_example_parses("production_gcp_s3.yml")
    assert_example_parses("production_cloud_aws.yml")
    assert_example_parses("irods.yml")
    assert_example_parses("irods_ssl.yml")


def assert_example_parses(filename: str):
    as_str = get_example(filename)
    _parse_template_library(as_str)


def _parse_template_library(contents: str) -> ObjectStoreTemplateCatalog:
    raw_contents = safe_load(contents)
    return raw_config_to_catalog(raw_contents)
