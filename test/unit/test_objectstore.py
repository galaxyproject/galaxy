import os
from contextlib import contextmanager
from shutil import rmtree
from string import Template
from tempfile import mkdtemp
from uuid import uuid4
from xml.etree import ElementTree

import yaml
from six import StringIO

from galaxy import objectstore
from galaxy.exceptions import ObjectInvalid
from galaxy.objectstore.azure_blob import AzureBlobObjectStore
from galaxy.objectstore.cloud import Cloud
from galaxy.objectstore.pithos import PithosObjectStore
from galaxy.objectstore.s3 import S3ObjectStore
from galaxy.util import directory_hash_id


DISK_TEST_CONFIG = """<?xml version="1.0"?>
<object_store type="disk">
    <files_dir path="${temp_directory}/files1"/>
    <extra_dir type="temp" path="${temp_directory}/tmp1"/>
    <extra_dir type="job_work" path="${temp_directory}/job_working_directory1"/>
</object_store>
"""


DISK_TEST_CONFIG_YAML = """
type: disk
files_dir: "${temp_directory}/files1"
extra_dirs:
  - type: temp
    path: "${temp_directory}/tmp1"
  - type: job_work
    path: "${temp_directory}/job_working_directory1"
"""


def test_disk_store():
    for config_str in [DISK_TEST_CONFIG, DISK_TEST_CONFIG_YAML]:
        with TestConfig(config_str) as (directory, object_store):
            # Test no dataset with id 1 exists.
            absent_dataset = MockDataset(1)
            assert not object_store.exists(absent_dataset)

            # Write empty dataset 2 in second backend, ensure it is empty and
            # exists.
            empty_dataset = MockDataset(2)
            directory.write("", "files1/000/dataset_2.dat")
            assert object_store.exists(empty_dataset)
            assert object_store.empty(empty_dataset)

            # Write non-empty dataset in backend 1, test it is not emtpy & exists.
            hello_world_dataset = MockDataset(3)
            directory.write("Hello World!", "files1/000/dataset_3.dat")
            assert object_store.exists(hello_world_dataset)
            assert not object_store.empty(hello_world_dataset)

            # Test get_data
            data = object_store.get_data(hello_world_dataset)
            assert data == "Hello World!"

            data = object_store.get_data(hello_world_dataset, start=1, count=6)
            assert data == "ello W"

            # Test Size

            # Test absent and empty datasets yield size of 0.
            assert object_store.size(absent_dataset) == 0
            assert object_store.size(empty_dataset) == 0
            # Elsewise
            assert object_store.size(hello_world_dataset) > 0  # Should this always be the number of bytes?

            # Test percent used (to some degree)
            percent_store_used = object_store.get_store_usage_percent()
            assert percent_store_used > 0.0
            assert percent_store_used < 100.0

            # Test update_from_file test
            output_dataset = MockDataset(4)
            output_real_path = os.path.join(directory.temp_directory, "files1", "000", "dataset_4.dat")
            assert not os.path.exists(output_real_path)
            output_working_path = directory.write("NEW CONTENTS", "job_working_directory1/example_output")
            object_store.update_from_file(output_dataset, file_name=output_working_path, create=True)
            assert os.path.exists(output_real_path)

            # Test delete
            to_delete_dataset = MockDataset(5)
            to_delete_real_path = directory.write("content to be deleted!", "files1/000/dataset_5.dat")
            assert object_store.exists(to_delete_dataset)
            assert object_store.delete(to_delete_dataset)
            assert not object_store.exists(to_delete_dataset)
            assert not os.path.exists(to_delete_real_path)


DISK_TEST_CONFIG_BY_UUID_YAML = """
type: disk
files_dir: "${temp_directory}/files1"
store_by: uuid
extra_dirs:
  - type: temp
    path: "${temp_directory}/tmp1"
  - type: job_work
    path: "${temp_directory}/job_working_directory1"
"""


def test_disk_store_by_uuid():
    for config_str in [DISK_TEST_CONFIG_BY_UUID_YAML]:
        with TestConfig(config_str) as (directory, object_store):
            # Test no dataset with id 1 exists.
            absent_dataset = MockDataset(1)
            assert not object_store.exists(absent_dataset)

            # Write empty dataset 2 in second backend, ensure it is empty and
            # exists.
            empty_dataset = MockDataset(2)
            directory.write("", "files1/%s/dataset_%s.dat" % (empty_dataset.rel_path_for_uuid_test(), empty_dataset.uuid))
            assert object_store.exists(empty_dataset)
            assert object_store.empty(empty_dataset)

            # Write non-empty dataset in backend 1, test it is not emtpy & exists.
            hello_world_dataset = MockDataset(3)
            directory.write("Hello World!", "files1/%s/dataset_%s.dat" % (hello_world_dataset.rel_path_for_uuid_test(), hello_world_dataset.uuid))
            assert object_store.exists(hello_world_dataset)
            assert not object_store.empty(hello_world_dataset)

            # Test get_data
            data = object_store.get_data(hello_world_dataset)
            assert data == "Hello World!"

            data = object_store.get_data(hello_world_dataset, start=1, count=6)
            assert data == "ello W"

            # Test Size

            # Test absent and empty datasets yield size of 0.
            assert object_store.size(absent_dataset) == 0
            assert object_store.size(empty_dataset) == 0
            # Elsewise
            assert object_store.size(hello_world_dataset) > 0  # Should this always be the number of bytes?

            # Test percent used (to some degree)
            percent_store_used = object_store.get_store_usage_percent()
            assert percent_store_used > 0.0
            assert percent_store_used < 100.0

            # Test update_from_file test
            output_dataset = MockDataset(4)
            output_real_path = os.path.join(directory.temp_directory, "files1", output_dataset.rel_path_for_uuid_test(), "dataset_%s.dat" % output_dataset.uuid)
            assert not os.path.exists(output_real_path)
            output_working_path = directory.write("NEW CONTENTS", "job_working_directory1/example_output")
            object_store.update_from_file(output_dataset, file_name=output_working_path, create=True)
            assert os.path.exists(output_real_path)

            # Test delete
            to_delete_dataset = MockDataset(5)
            to_delete_real_path = directory.write("content to be deleted!", "files1/%s/dataset_%s.dat" % (to_delete_dataset.rel_path_for_uuid_test(), to_delete_dataset.uuid))
            assert object_store.exists(to_delete_dataset)
            assert object_store.delete(to_delete_dataset)
            assert not object_store.exists(to_delete_dataset)
            assert not os.path.exists(to_delete_real_path)


def test_disk_store_alt_name_relpath():
    """ Test that alt_name cannot be used to access arbitrary paths using a
    relative path
    """
    with TestConfig(DISK_TEST_CONFIG) as (directory, object_store):
        empty_dataset = MockDataset(1)
        directory.write("", "files1/000/dataset_1.dat")
        directory.write("foo", "foo.txt")
        try:
            assert object_store.get_data(
                empty_dataset,
                extra_dir='dataset_1_files',
                alt_name='../../../foo.txt') != 'foo'
        except ObjectInvalid:
            pass


def test_disk_store_alt_name_abspath():
    """ Test that alt_name cannot be used to access arbitrary paths using a
    absolute path
    """
    with TestConfig(DISK_TEST_CONFIG) as (directory, object_store):
        empty_dataset = MockDataset(1)
        directory.write("", "files1/000/dataset_1.dat")
        absfoo = os.path.abspath(os.path.join(directory.temp_directory, "foo.txt"))
        with open(absfoo, 'w') as f:
            f.write("foo")
        try:
            assert object_store.get_data(
                empty_dataset,
                extra_dir='dataset_1_files',
                alt_name=absfoo) != 'foo'
        except ObjectInvalid:
            pass


HIERARCHICAL_TEST_CONFIG = """<?xml version="1.0"?>
<object_store type="hierarchical">
    <backends>
        <backend id="files1" type="disk" weight="1" order="0">
            <files_dir path="${temp_directory}/files1"/>
            <extra_dir type="temp" path="${temp_directory}/tmp1"/>
            <extra_dir type="job_work" path="${temp_directory}/job_working_directory1"/>
        </backend>
        <backend id="files2" type="disk" weight="1" order="1">
            <files_dir path="${temp_directory}/files2"/>
            <extra_dir type="temp" path="${temp_directory}/tmp2"/>
            <extra_dir type="job_work" path="${temp_directory}/job_working_directory2"/>
        </backend>
    </backends>
</object_store>
"""


HIERARCHICAL_TEST_CONFIG_YAML = """
type: hierarchical
backends:
   - id: files1
     type: disk
     weight: 1
     files_dir: "${temp_directory}/files1"
     extra_dirs:
     - type: temp
       path: "${temp_directory}/tmp1"
     - type: job_work
       path: "${temp_directory}/job_working_directory1"
   - id: files2
     type: disk
     weight: 1
     files_dir: "${temp_directory}/files2"
     extra_dirs:
     - type: temp
       path: "${temp_directory}/tmp2"
     - type: job_work
       path: "${temp_directory}/job_working_directory2"
"""


def test_hierarchical_store():
    for config_str in [HIERARCHICAL_TEST_CONFIG, HIERARCHICAL_TEST_CONFIG_YAML]:
        with TestConfig(config_str) as (directory, object_store):

            # Test no dataset with id 1 exists.
            assert not object_store.exists(MockDataset(1))

            # Write empty dataset 2 in second backend, ensure it is empty and
            # exists.
            directory.write("", "files2/000/dataset_2.dat")
            assert object_store.exists(MockDataset(2))
            assert object_store.empty(MockDataset(2))

            # Write non-empty dataset in backend 1, test it is not emtpy & exists.
            directory.write("Hello World!", "files1/000/dataset_3.dat")
            assert object_store.exists(MockDataset(3))
            assert not object_store.empty(MockDataset(3))

            # Assert creation always happens in first backend.
            for i in range(100):
                dataset = MockDataset(100 + i)
                object_store.create(dataset)
                assert object_store.get_filename(dataset).find("files1") > 0

            as_dict = object_store.to_dict()
            _assert_has_keys(as_dict, ["backends", "extra_dirs", "type"])
            _assert_key_has_value(as_dict, "type", "hierarchical")


DISTRIBUTED_TEST_CONFIG = """<?xml version="1.0"?>
<object_store type="distributed">
    <backends>
        <backend id="files1" type="disk" weight="2">
            <files_dir path="${temp_directory}/files1"/>
            <extra_dir type="temp" path="${temp_directory}/tmp1"/>
            <extra_dir type="job_work" path="${temp_directory}/job_working_directory1"/>
        </backend>
        <backend id="files2" type="disk" weight="1">
            <files_dir path="${temp_directory}/files2"/>
            <extra_dir type="temp" path="${temp_directory}/tmp2"/>
            <extra_dir type="job_work" path="${temp_directory}/job_working_directory2"/>
        </backend>
    </backends>
</object_store>
"""


DISTRIBUTED_TEST_CONFIG_YAML = """
type: distributed
backends:
   - id: files1
     type: disk
     weight: 2
     files_dir: "${temp_directory}/files1"
     extra_dirs:
     - type: temp
       path: "${temp_directory}/tmp1"
     - type: job_work
       path: "${temp_directory}/job_working_directory1"
   - id: files2
     type: disk
     weight: 1
     files_dir: "${temp_directory}/files2"
     extra_dirs:
     - type: temp
       path: "${temp_directory}/tmp2"
     - type: job_work
       path: "${temp_directory}/job_working_directory2"
"""


def test_distributed_store():
    for config_str in [DISTRIBUTED_TEST_CONFIG, DISTRIBUTED_TEST_CONFIG_YAML]:
        with TestConfig(config_str) as (directory, object_store):
            with __stubbed_persistence() as persisted_ids:
                for i in range(100):
                    dataset = MockDataset(100 + i)
                    object_store.create(dataset)

            # Test distributes datasets between backends according to weights
            backend_1_count = len([v for v in persisted_ids.values() if v == "files1"])
            backend_2_count = len([v for v in persisted_ids.values() if v == "files2"])

            assert backend_1_count > 0
            assert backend_2_count > 0
            assert backend_1_count > backend_2_count

            as_dict = object_store.to_dict()
            _assert_has_keys(as_dict, ["backends", "extra_dirs", "type"])
            _assert_key_has_value(as_dict, "type", "distributed")

            extra_dirs = as_dict["extra_dirs"]
            assert len(extra_dirs) == 2


# Unit testing the cloud and advanced infrastructure object stores is difficult, but
# we can at least stub out initializing and test the configuration of these things from
# XML and dicts.
class UnitializedPithosObjectStore(PithosObjectStore):

    def _initialize(self):
        pass


class UnitializeS3ObjectStore(S3ObjectStore):

    def _initialize(self):
        pass


class UnitializedAzureBlobObjectStore(AzureBlobObjectStore):

    def _initialize(self):
        pass


class UnitializedCloudObjectStore(Cloud):

    def _initialize(self):
        pass


PITHOS_TEST_CONFIG = """<?xml version="1.0"?>
<object_store type="pithos">
    <auth url="http://example.org/" token="extoken123" />
    <container name="foo" project="cow" />
    <extra_dir type="temp" path="database/tmp_pithos"/>
    <extra_dir type="job_work" path="database/working_pithos"/>
</object_store>
"""


PITHOS_TEST_CONFIG_YAML = """
type: pithos
auth:
  url: http://example.org/
  token: extoken123

container:
  name: foo
  project: cow

extra_dirs:
  - type: temp
    path: database/tmp_pithos
  - type: job_work
    path: database/working_pithos
"""


def test_config_parse_pithos():
    for config_str in [PITHOS_TEST_CONFIG, PITHOS_TEST_CONFIG_YAML]:
        with TestConfig(config_str, clazz=UnitializedPithosObjectStore) as (directory, object_store):
            configured_config_dict = object_store.config_dict
            _assert_has_keys(configured_config_dict, ["auth", "container", "extra_dirs"])

            auth_dict = configured_config_dict["auth"]
            _assert_key_has_value(auth_dict, "url", "http://example.org/")
            _assert_key_has_value(auth_dict, "token", "extoken123")

            container_dict = configured_config_dict["container"]

            _assert_key_has_value(container_dict, "name", "foo")
            _assert_key_has_value(container_dict, "project", "cow")

            assert object_store.extra_dirs["job_work"] == "database/working_pithos"
            assert object_store.extra_dirs["temp"] == "database/tmp_pithos"

            as_dict = object_store.to_dict()
            _assert_has_keys(as_dict, ["auth", "container", "extra_dirs", "type"])

            _assert_key_has_value(as_dict, "type", "pithos")

            auth_dict = as_dict["auth"]
            _assert_key_has_value(auth_dict, "url", "http://example.org/")
            _assert_key_has_value(auth_dict, "token", "extoken123")

            container_dict = as_dict["container"]

            _assert_key_has_value(container_dict, "name", "foo")
            _assert_key_has_value(container_dict, "project", "cow")

            extra_dirs = as_dict["extra_dirs"]
            assert len(extra_dirs) == 2


S3_TEST_CONFIG = """<object_store type="s3">
     <auth access_key="access_moo" secret_key="secret_cow" />
     <bucket name="unique_bucket_name_all_lowercase" use_reduced_redundancy="False" />
     <cache path="database/object_store_cache" size="1000" />
     <extra_dir type="job_work" path="database/job_working_directory_s3"/>
     <extra_dir type="temp" path="database/tmp_s3"/>
</object_store>
"""


S3_TEST_CONFIG_YAML = """
type: s3
auth:
  access_key: access_moo
  secret_key: secret_cow

bucket:
  name: unique_bucket_name_all_lowercase
  use_reduced_redundancy: false

cache:
  path: database/object_store_cache
  size: 1000

extra_dirs:
- type: job_work
  path: database/job_working_directory_s3
- type: temp
  path: database/tmp_s3
"""


def test_config_parse_s3():
    for config_str in [S3_TEST_CONFIG, S3_TEST_CONFIG_YAML]:
        with TestConfig(config_str, clazz=UnitializeS3ObjectStore) as (directory, object_store):
            assert object_store.access_key == "access_moo"
            assert object_store.secret_key == "secret_cow"

            assert object_store.bucket == "unique_bucket_name_all_lowercase"
            assert object_store.use_rr is False

            assert object_store.host is None
            assert object_store.port == 6000
            assert object_store.multipart is True
            assert object_store.is_secure is True
            assert object_store.conn_path == "/"

            assert object_store.cache_size == 1000
            assert object_store.staging_path == "database/object_store_cache"
            assert object_store.extra_dirs["job_work"] == "database/job_working_directory_s3"
            assert object_store.extra_dirs["temp"] == "database/tmp_s3"

            as_dict = object_store.to_dict()
            _assert_has_keys(as_dict, ["auth", "bucket", "connection", "cache", "extra_dirs", "type"])

            _assert_key_has_value(as_dict, "type", "s3")

            auth_dict = as_dict["auth"]
            bucket_dict = as_dict["bucket"]
            connection_dict = as_dict["connection"]
            cache_dict = as_dict["cache"]

            _assert_key_has_value(auth_dict, "access_key", "access_moo")
            _assert_key_has_value(auth_dict, "secret_key", "secret_cow")

            _assert_key_has_value(bucket_dict, "name", "unique_bucket_name_all_lowercase")
            _assert_key_has_value(bucket_dict, "use_reduced_redundancy", False)

            _assert_key_has_value(connection_dict, "host", None)
            _assert_key_has_value(connection_dict, "port", 6000)
            _assert_key_has_value(connection_dict, "multipart", True)
            _assert_key_has_value(connection_dict, "is_secure", True)

            _assert_key_has_value(cache_dict, "size", 1000)
            _assert_key_has_value(cache_dict, "path", "database/object_store_cache")

            extra_dirs = as_dict["extra_dirs"]
            assert len(extra_dirs) == 2


CLOUD_AWS_TEST_CONFIG = """<object_store type="cloud" provider="aws">
     <auth access_key="access_moo" secret_key="secret_cow" />
     <bucket name="unique_bucket_name_all_lowercase" use_reduced_redundancy="False" />
     <cache path="database/object_store_cache" size="1000" />
     <extra_dir type="job_work" path="database/job_working_directory_cloud"/>
     <extra_dir type="temp" path="database/tmp_cloud"/>
</object_store>
"""


CLOUD_AWS_TEST_CONFIG_YAML = """
type: cloud
provider: aws
auth:
  access_key: access_moo
  secret_key: secret_cow

bucket:
  name: unique_bucket_name_all_lowercase
  use_reduced_redundancy: false

cache:
  path: database/object_store_cache
  size: 1000

extra_dirs:
- type: job_work
  path: database/job_working_directory_cloud
- type: temp
  path: database/tmp_cloud
"""


CLOUD_AZURE_TEST_CONFIG = """<object_store type="cloud" provider="azure">
     <auth subscription_id="a_sub_id" client_id="and_a_client_id" secret="and_a_secret_key"
     tenant="and_some_tenant_info" />
     <bucket name="unique_bucket_name_all_lowercase" use_reduced_redundancy="False" />
     <cache path="database/object_store_cache" size="1000" />
     <extra_dir type="job_work" path="database/job_working_directory_cloud"/>
     <extra_dir type="temp" path="database/tmp_cloud"/>
</object_store>
"""

CLOUD_AZURE_TEST_CONFIG_YAML = """
type: cloud
provider: azure
auth:
  subscription_id: a_sub_id
  client_id: and_a_client_id
  secret: and_a_secret_key
  tenant: and_some_tenant_info

bucket:
  name: unique_bucket_name_all_lowercase
  use_reduced_redundancy: false

cache:
  path: database/object_store_cache
  size: 1000

extra_dirs:
- type: job_work
  path: database/job_working_directory_cloud
- type: temp
  path: database/tmp_cloud
"""


CLOUD_GOOGLE_TEST_CONFIG = """<object_store type="cloud" provider="google">
     <auth credentials_file="gcp.config" />
     <bucket name="unique_bucket_name_all_lowercase" use_reduced_redundancy="False" />
     <cache path="database/object_store_cache" size="1000" />
     <extra_dir type="job_work" path="database/job_working_directory_cloud"/>
     <extra_dir type="temp" path="database/tmp_cloud"/>
</object_store>
"""

CLOUD_GOOGLE_TEST_CONFIG_YAML = """
type: cloud
provider: google
auth:
  credentials_file: gcp.config

bucket:
  name: unique_bucket_name_all_lowercase
  use_reduced_redundancy: false

cache:
  path: database/object_store_cache
  size: 1000

extra_dirs:
- type: job_work
  path: database/job_working_directory_cloud
- type: temp
  path: database/tmp_cloud
"""


def test_config_parse_cloud():
    for config_str in [CLOUD_AWS_TEST_CONFIG, CLOUD_AWS_TEST_CONFIG_YAML,
                       CLOUD_AZURE_TEST_CONFIG, CLOUD_AZURE_TEST_CONFIG_YAML,
                       CLOUD_GOOGLE_TEST_CONFIG, CLOUD_GOOGLE_TEST_CONFIG_YAML]:
        if "google" in config_str:
            tmpdir = mkdtemp()
            if not os.path.exists(tmpdir):
                os.makedirs(tmpdir)
            path = os.path.join(tmpdir, "gcp.config")
            open(path, "w").write("some_gcp_config")
            config_str = config_str.replace("gcp.config", path)
        with TestConfig(config_str, clazz=UnitializedCloudObjectStore) as (directory, object_store):

            assert object_store.bucket_name == "unique_bucket_name_all_lowercase"
            assert object_store.use_rr is False

            assert object_store.host is None
            assert object_store.port == 6000
            assert object_store.multipart is True
            assert object_store.is_secure is True
            assert object_store.conn_path == "/"

            assert object_store.cache_size == 1000.0
            assert object_store.staging_path == "database/object_store_cache"
            assert object_store.extra_dirs["job_work"] == "database/job_working_directory_cloud"
            assert object_store.extra_dirs["temp"] == "database/tmp_cloud"

            as_dict = object_store.to_dict()
            _assert_has_keys(as_dict, ["provider", "auth", "bucket", "connection", "cache", "extra_dirs", "type"])

            _assert_key_has_value(as_dict, "type", "cloud")

            auth_dict = as_dict["auth"]
            bucket_dict = as_dict["bucket"]
            connection_dict = as_dict["connection"]
            cache_dict = as_dict["cache"]

            provider = as_dict["provider"]
            if provider == "aws":
                _assert_key_has_value(auth_dict, "access_key", "access_moo")
                _assert_key_has_value(auth_dict, "secret_key", "secret_cow")
            elif provider == "azure":
                _assert_key_has_value(auth_dict, "subscription_id", "a_sub_id")
                _assert_key_has_value(auth_dict, "client_id", "and_a_client_id")
                _assert_key_has_value(auth_dict, "secret", "and_a_secret_key")
                _assert_key_has_value(auth_dict, "tenant", "and_some_tenant_info")
            elif provider == "google":
                _assert_key_has_value(auth_dict, "credentials_file", path)

            _assert_key_has_value(bucket_dict, "name", "unique_bucket_name_all_lowercase")
            _assert_key_has_value(bucket_dict, "use_reduced_redundancy", False)

            _assert_key_has_value(connection_dict, "host", None)
            _assert_key_has_value(connection_dict, "port", 6000)
            _assert_key_has_value(connection_dict, "multipart", True)
            _assert_key_has_value(connection_dict, "is_secure", True)

            _assert_key_has_value(cache_dict, "size", 1000.0)
            _assert_key_has_value(cache_dict, "path", "database/object_store_cache")

            extra_dirs = as_dict["extra_dirs"]
            assert len(extra_dirs) == 2


AZURE_BLOB_TEST_CONFIG = """<object_store type="azure_blob">
    <auth account_name="azureact" account_key="password123" />
    <container name="unique_container_name" max_chunk_size="250"/>
    <cache path="database/object_store_cache" size="100" />
    <extra_dir type="job_work" path="database/job_working_directory_azure"/>
    <extra_dir type="temp" path="database/tmp_azure"/>
</object_store>
"""


AZURE_BLOB_TEST_CONFIG_YAML = """
type: azure_blob
auth:
  account_name: azureact
  account_key: password123

container:
  name: unique_container_name
  max_chunk_size: 250

cache:
  path: database/object_store_cache
  size: 100

extra_dirs:
- type: job_work
  path: database/job_working_directory_azure
- type: temp
  path: database/tmp_azure
"""


def test_config_parse_azure():
    for config_str in [AZURE_BLOB_TEST_CONFIG, AZURE_BLOB_TEST_CONFIG_YAML]:
        with TestConfig(config_str, clazz=UnitializedAzureBlobObjectStore) as (directory, object_store):
            assert object_store.account_name == "azureact"
            assert object_store.account_key == "password123"

            assert object_store.container_name == "unique_container_name"
            assert object_store.max_chunk_size == 250

            assert object_store.cache_size == 100
            assert object_store.staging_path == "database/object_store_cache"
            assert object_store.extra_dirs["job_work"] == "database/job_working_directory_azure"
            assert object_store.extra_dirs["temp"] == "database/tmp_azure"

            as_dict = object_store.to_dict()
            _assert_has_keys(as_dict, ["auth", "container", "cache", "extra_dirs", "type"])

            _assert_key_has_value(as_dict, "type", "azure_blob")

            auth_dict = as_dict["auth"]
            container_dict = as_dict["container"]
            cache_dict = as_dict["cache"]

            _assert_key_has_value(auth_dict, "account_name", "azureact")
            _assert_key_has_value(auth_dict, "account_key", "password123")

            _assert_key_has_value(container_dict, "name", "unique_container_name")
            _assert_key_has_value(container_dict, "max_chunk_size", 250)

            _assert_key_has_value(cache_dict, "size", 100)
            _assert_key_has_value(cache_dict, "path", "database/object_store_cache")

            extra_dirs = as_dict["extra_dirs"]
            assert len(extra_dirs) == 2


class TestConfig(object):
    def __init__(self, config_str=DISK_TEST_CONFIG, clazz=None, store_by="id"):
        self.temp_directory = mkdtemp()
        if config_str.startswith("<"):
            config_file = "store.xml"
        else:
            config_file = "store.yaml"
        self.write(config_str, config_file)
        config = MockConfig(self.temp_directory, config_file, store_by=store_by)
        if clazz is None:
            self.object_store = objectstore.build_object_store_from_config(config)
        elif config_file == "store.xml":
            self.object_store = clazz.from_xml(config, ElementTree.fromstring(config_str))
        else:
            self.object_store = clazz(config, yaml.safe_load(StringIO(config_str)))

    def __enter__(self):
        return self, self.object_store

    def __exit__(self, type, value, tb):
        rmtree(self.temp_directory)

    def write(self, contents, name):
        path = os.path.join(self.temp_directory, name)
        directory = os.path.dirname(path)
        if not os.path.exists(directory):
            os.makedirs(directory)
        contents_template = Template(contents)
        expanded_contents = contents_template.safe_substitute(temp_directory=self.temp_directory)
        open(path, "w").write(expanded_contents)
        return path


class MockConfig(object):

    def __init__(self, temp_directory, config_file, store_by="id"):
        self.file_path = temp_directory
        self.object_store_config_file = os.path.join(temp_directory, config_file)
        self.object_store_check_old_style = False
        self.object_store_cache_path = os.path.join(temp_directory, "staging")
        self.object_store_store_by = store_by
        self.jobs_directory = temp_directory
        self.new_file_path = temp_directory
        self.umask = 0000
        self.gid = 1000


class MockDataset(object):

    def __init__(self, id):
        self.id = id
        self.object_store_id = None
        self.uuid = uuid4()
        self.tags = []

    def rel_path_for_uuid_test(self):
        rel_path = os.path.join(*directory_hash_id(self.uuid))
        return rel_path


# Poor man's mocking. Need to get a real mocking library as real Galaxy development
# dependnecy.
PERSIST_METHOD_NAME = "_create_object_in_session"


@contextmanager
def __stubbed_persistence():
    real_method = getattr(objectstore, PERSIST_METHOD_NAME)
    try:
        persisted_ids = {}

        def persist(object):
            persisted_ids[object.id] = object.object_store_id
        setattr(objectstore, PERSIST_METHOD_NAME, persist)
        yield persisted_ids

    finally:
        setattr(objectstore, PERSIST_METHOD_NAME, real_method)


def _assert_has_keys(the_dict, keys):
    for key in keys:
        assert key in the_dict, "key [%s] not in [%s]" % (key, the_dict)


def _assert_key_has_value(the_dict, key, value):
    assert key in the_dict, "dict [%s] doesn't container expected key [%s]" % (key, the_dict)
    assert the_dict[key] == value, "%s != %s" % (the_dict[key], value)
