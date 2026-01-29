from yaml import safe_load

from galaxy.files.templates.examples import get_example
from galaxy.files.templates.manager import raw_config_to_catalog
from galaxy.files.templates.models import (
    FileSourceTemplate,
    FileSourceTemplateCatalog,
    FtpFileSourceConfiguration,
    PosixFileSourceConfiguration,
    S3FSFileSourceConfiguration,
    template_to_configuration,
)

# API example server - all data is public and anyone can create keys and buckets
GALAXY_TEST_PLAY_MINIO_KEY = "LEHFJDNqSA4xcJmmezU7"
GALAXY_TEST_PLAY_MINIO_SECRET = "E3ycZrp2nV8WscER8HqgsPPL2aFc2uuTbRchelcX"
GALAXY_TEST_PLAY_MINIO_BUCKET = "gxtest1"

LIBRARY_AWS = """
- id: aws_bucket
  name: Amazon Bucket
  description: An Amazon S3 Bucket
  variables:
    bucket_name:
      type: string
      help: Name of bucket to use when connecting to AWS resources.
  secrets:
    access_key:
      help: AWS access key to use when connecting to AWS resources.
    secret_key:
      help: AWS secret key to use when connecting to AWS resources.
  configuration:
    type: s3fs
    key: '{{ secrets.access_key}}'
    secret: '{{ secrets.secret_key}}'
    bucket: '{{ variables.bucket_name}}'
"""


def test_aws_s3_config():
    template_library = _parse_template_library(LIBRARY_AWS)
    s3_template = _assert_has_one_template(template_library)
    assert s3_template.description == "An Amazon S3 Bucket"
    configuration_obj = template_to_configuration(
        s3_template,
        {"bucket_name": "sec3"},
        {"access_key": "sec1", "secret_key": "sec2"},
        user_details={},
        environment={},
    )

    # expanded configuration should validate with template expansions...
    assert isinstance(configuration_obj, S3FSFileSourceConfiguration)
    configuration = configuration_obj.model_dump()

    assert configuration["type"] == "s3fs"
    assert configuration["key"] == "sec1"
    assert configuration["secret"] == "sec2"
    assert configuration["bucket"] == "sec3"


LIBRARY_HOME_DIRECTORY = """
- id: home_directory
  name: Home Directory
  description: Your Home Directory on this System
  configuration:
    type: posix
    root: "/home/{{ user.username}}/"
"""


def test_a_posix_template():
    template_library = _parse_template_library(LIBRARY_HOME_DIRECTORY)
    posix_template = _assert_has_one_template(template_library)
    assert posix_template.description == "Your Home Directory on this System"
    configuration_obj = template_to_configuration(
        posix_template,
        {},
        {},
        user_details={"username": "foobar"},
        environment={},
    )

    # expanded configuration should validate with template expansions...
    assert isinstance(configuration_obj, PosixFileSourceConfiguration)
    configuration = configuration_obj.model_dump()

    assert configuration["type"] == "posix"
    assert configuration["root"] == "/home/foobar/"


LIBRARY_FTP = """
- id: ftp
  name: Generic FTP Server
  description: Generic FTP configuration with all configuration options exposed.
  configuration:
    type: ftp
    host: "{{ variables.host }}"
    user: "{{ variables.user }}"
    port: "{{ variables.port }}"
    passwd: "{{ secrets.password }}"
    writable: "{{ variables.writable }}"
  variables:
    host:
      type: string
      help: Host of FTP Server to Connect to.
    user:
      type: string
      help: Username to connect with.
    writable:
      type: boolean
      help: Is this an FTP server you have permission to write to?
      default: false
    port:
      type: integer
      help: Port used to connect to the FTP server.
      default: 21
  secrets:
    password:
      help: Password to connect to FTP server with.
"""


def test_ftp():
    template_library = _parse_template_library(LIBRARY_FTP)
    ftp_template = _assert_has_one_template(template_library)
    configuration_obj = template_to_configuration(
        ftp_template,
        {"host": "ftp.galaxyproject.org", "user": "john", "port": 22, "writable": True},
        {"password": "mycoolpassword123"},
        user_details={},
        environment={},
    )

    # expanded configuration should validate with template expansions...
    assert isinstance(configuration_obj, FtpFileSourceConfiguration)
    configuration = configuration_obj.model_dump()

    assert configuration["type"] == "ftp"
    assert configuration["host"] == "ftp.galaxyproject.org"
    # Not optional but it does specify a default so the configuration object does
    assert configuration["port"] == 22
    assert configuration["passwd"] == "mycoolpassword123"
    assert configuration["user"] == "john"


LIBRARY_FTP_NO_PORT = """
- id: ftp_no_port
  name: FTP (no port specified)
  description: Generic FTP configuration with no port specified.
  configuration:
    type: ftp
    host: "{{ variables.host }}"
    user: "{{ variables.user }}"
    passwd: "{{ secrets.password }}"
    writable: "{{ variables.writable }}"
  variables:
    host:
      type: string
      help: Host of FTP Server to Connect to.
    user:
      type: string
      help: Username to connect with.
    writable:
      type: boolean
      help: Is this an FTP server you have permission to write to?
  secrets:
    password:
      help: Password to connect to FTP server with.
"""


def test_ftp_no_port_template():
    template_library = _parse_template_library(LIBRARY_FTP_NO_PORT)
    ftp_template = _assert_has_one_template(template_library)
    configuration_obj = template_to_configuration(
        ftp_template,
        {"host": "ftp.galaxyproject.org", "user": "john", "writable": True},
        {"password": "mycoolpassword123"},
        user_details={},
        environment={},
    )

    # expanded configuration should validate with template expansions...
    assert isinstance(configuration_obj, FtpFileSourceConfiguration)
    configuration = configuration_obj.model_dump()

    assert configuration["type"] == "ftp"
    assert configuration["host"] == "ftp.galaxyproject.org"
    # Not optional but it does specify a default so the configuration object does
    assert configuration["port"] == 21
    assert configuration["passwd"] == "mycoolpassword123"
    assert configuration["user"] == "john"


LIBRARY_FTP_WITH_DEFAULT_SFTP_PORT = """
- id: ftp
  name: Generic SFTP Server
  description: Generic SFTP configuration with all configuration options exposed.
  configuration:
    type: ftp
    host: "{{ variables.host }}"
    user: "{{ variables.user }}"
    port: "{{ variables.port }}"
    passwd: "{{ secrets.password }}"
    writable: "{{ variables.writable }}"
  variables:
    host:
      type: string
      help: Host of SFTP Server to Connect to.
    user:
      type: string
      help: Username to connect with.
    writable:
      type: boolean
      help: Is this an SFTP server you have permission to write to?
    port:
      type: integer
      help: Port used to connect to the SFTP server.
      default: 22
  secrets:
    password:
      help: Password to connect to SFTP server with.
"""


def test_ftp_default_to_sftp_port():
    template_library = _parse_template_library(LIBRARY_FTP_WITH_DEFAULT_SFTP_PORT)
    ftp_template = _assert_has_one_template(template_library)
    configuration_obj = template_to_configuration(
        ftp_template,
        {"host": "ftp.galaxyproject.org", "user": "john", "writable": True},
        {"password": "mycoolpassword123"},
        user_details={},
        environment={},
    )

    # expanded configuration should validate with template expansions...
    assert isinstance(configuration_obj, FtpFileSourceConfiguration)
    configuration = configuration_obj.model_dump()

    assert configuration["type"] == "ftp"
    assert configuration["host"] == "ftp.galaxyproject.org"
    # Using the template default for not supplied values
    assert configuration["port"] == 22
    assert configuration["passwd"] == "mycoolpassword123"
    assert configuration["user"] == "john"


def test_s3fs_endpoint_building():
    s3fs_template = _get_example_template("s3fs_by_host_and_port.yml")
    configuration_obj = template_to_configuration(
        s3fs_template,
        {
            "host": "play.min.io",
            "access_key": GALAXY_TEST_PLAY_MINIO_KEY,
            "port": 9000,
            "connection_path": "",
            "secure": True,
            "bucket": GALAXY_TEST_PLAY_MINIO_BUCKET,
        },
        {"secret_key": GALAXY_TEST_PLAY_MINIO_SECRET},
        user_details={},
        environment={},
    )

    # expanded configuration should validate with template expansions...
    assert isinstance(configuration_obj, S3FSFileSourceConfiguration)
    assert configuration_obj.endpoint_url == "https://play.min.io:9000/"
    assert configuration_obj.key == GALAXY_TEST_PLAY_MINIO_KEY
    assert configuration_obj.secret == GALAXY_TEST_PLAY_MINIO_SECRET
    assert configuration_obj.anon is False
    assert configuration_obj.bucket == GALAXY_TEST_PLAY_MINIO_BUCKET


def test_production_aws_public_bucket():
    aws_public_bucket_template = _get_example_template("production_aws_public_bucket.yml")
    configuration_obj = template_to_configuration(
        aws_public_bucket_template,
        {
            "bucket": "encode-public",
        },
        {},
        user_details={},
        environment={},
    )
    assert isinstance(configuration_obj, S3FSFileSourceConfiguration)
    assert configuration_obj.anon is True
    assert configuration_obj.bucket == "encode-public"


def test_examples_parse():
    _assert_example_parses("production_ftp.yml")
    _assert_example_parses("production_azure.yml")
    _assert_example_parses("production_aws_private_bucket.yml")
    _assert_example_parses("production_aws_public_bucket.yml")
    _assert_example_parses("production_s3fs.yml")
    _assert_example_parses("production_dropbox.yml")
    _assert_example_parses("s3fs_by_host_and_port.yml")
    _assert_example_parses("templating_override.yml")
    _assert_example_parses("admin_secrets.yml")
    _assert_example_parses("admin_secrets_with_defaults.yml")
    _assert_example_parses("testing_multi_version_with_secrets.yml")
    _assert_example_parses("dropbox_client_secrets_in_vault.yml")
    _assert_example_parses("dropbox_client_secrets_explicit.yml")


def _assert_example_parses(filename: str):
    # just parsing it does the validation - using the assert function name for clarify
    # though.
    _get_example_library(filename)


def _get_example_template(filename: str) -> FileSourceTemplate:
    return _assert_has_one_template(_get_example_library(filename))


def _get_example_library(filename: str) -> FileSourceTemplateCatalog:
    as_str = get_example(filename)
    return _parse_template_library(as_str)


def _assert_has_one_template(catalog: FileSourceTemplateCatalog) -> FileSourceTemplate:
    assert len(catalog.root) == 1
    template = catalog.root[0]
    return template


def _parse_template_library(contents: str) -> FileSourceTemplateCatalog:
    raw_contents = safe_load(contents)
    return raw_config_to_catalog(raw_contents)
