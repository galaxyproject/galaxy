import hashlib
import os
import shutil
import time
from functools import wraps
from tempfile import (
    mkdtemp,
    mkstemp,
)
from unittest.mock import (
    MagicMock,
    patch,
)
from uuid import uuid4

import pytest
from requests import get

from galaxy.exceptions import ObjectInvalid
from galaxy.objectstore import persist_extra_files_for_dataset
from galaxy.objectstore.azure_blob import AzureBlobObjectStore
from galaxy.objectstore.caching import (
    CacheTarget,
    check_cache,
    InProcessCacheMonitor,
    reset_cache,
)
from galaxy.objectstore.cloud import Cloud
from galaxy.objectstore.examples import get_example
from galaxy.objectstore.pithos import PithosObjectStore
from galaxy.objectstore.s3 import S3ObjectStore
from galaxy.objectstore.s3_boto3 import S3ObjectStore as Boto3ObjectStore
from galaxy.objectstore.unittest_utils import (
    Config as TestConfig,
    DISK_TEST_CONFIG,
    DISK_TEST_CONFIG_YAML,
)
from galaxy.util import (
    directory_hash_id,
    unlink,
)
from galaxy.util.unittest_utils import skip_unless_environ


# Unit testing the cloud and advanced infrastructure object stores is difficult, but
# we can at least stub out initializing and test the configuration of these things from
# XML and dicts.
class UninitializedPithosObjectStore(PithosObjectStore):
    def _initialize(self):
        pass


class UninitializedS3ObjectStore(S3ObjectStore):
    def _initialize(self):
        pass


class UninitializedBoto3ObjectStore(Boto3ObjectStore):
    def _initialize(self):
        pass


class UninitializedAzureBlobObjectStore(AzureBlobObjectStore):
    def _initialize(self):
        pass


class UninitializedCloudObjectStore(Cloud):
    def _initialize(self):
        pass


def patch_object_stores_to_skip_initialize(f):

    @wraps(f)
    @patch("galaxy.objectstore.s3.S3ObjectStore", UninitializedS3ObjectStore)
    @patch("galaxy.objectstore.s3_boto3.S3ObjectStore", UninitializedBoto3ObjectStore)
    @patch("galaxy.objectstore.pithos.PithosObjectStore", UninitializedPithosObjectStore)
    @patch("galaxy.objectstore.cloud.Cloud", UninitializedCloudObjectStore)
    @patch("galaxy.objectstore.azure_blob.AzureBlobObjectStore", UninitializedAzureBlobObjectStore)
    def wrapper(*args, **kwd):
        f(*args, **kwd)

    return wrapper


def test_unlink_path():
    with pytest.raises(FileNotFoundError):
        unlink(uuid4().hex)
    unlink(uuid4().hex, ignore_errors=True)
    fd, path = mkstemp()
    os.close(fd)
    assert os.path.exists(path)
    unlink(path)
    assert not os.path.exists(path)


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
            directory.write("", f"files1/{empty_dataset.rel_path_for_uuid_test()}/dataset_{empty_dataset.uuid}.dat")
            assert object_store.exists(empty_dataset)
            assert object_store.empty(empty_dataset)

            # Write non-empty dataset in backend 1, test it is not emtpy & exists.
            hello_world_dataset = MockDataset(3)
            directory.write(
                "Hello World!",
                f"files1/{hello_world_dataset.rel_path_for_uuid_test()}/dataset_{hello_world_dataset.uuid}.dat",
            )
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
            output_real_path = os.path.join(
                directory.temp_directory,
                "files1",
                output_dataset.rel_path_for_uuid_test(),
                f"dataset_{output_dataset.uuid}.dat",
            )
            assert not os.path.exists(output_real_path)
            output_working_path = directory.write("NEW CONTENTS", "job_working_directory1/example_output")
            object_store.update_from_file(output_dataset, file_name=output_working_path, create=True)
            assert os.path.exists(output_real_path)

            # Test delete
            to_delete_dataset = MockDataset(5)
            to_delete_real_path = directory.write(
                "content to be deleted!",
                f"files1/{to_delete_dataset.rel_path_for_uuid_test()}/dataset_{to_delete_dataset.uuid}.dat",
            )
            assert object_store.exists(to_delete_dataset)
            assert object_store.delete(to_delete_dataset)
            assert not object_store.exists(to_delete_dataset)
            assert not os.path.exists(to_delete_real_path)


def test_disk_store_alt_name_relpath():
    """Test that alt_name cannot be used to access arbitrary paths using a
    relative path
    """
    with TestConfig(DISK_TEST_CONFIG) as (directory, object_store):
        empty_dataset = MockDataset(1)
        directory.write("", "files1/000/dataset_1.dat")
        directory.write("foo", "foo.txt")
        try:
            assert (
                object_store.get_data(empty_dataset, extra_dir="dataset_1_files", alt_name="../../../foo.txt") != "foo"
            )
        except ObjectInvalid:
            pass


def test_disk_store_alt_name_abspath():
    """Test that alt_name cannot be used to access arbitrary paths using a
    absolute path
    """
    with TestConfig(DISK_TEST_CONFIG) as (directory, object_store):
        empty_dataset = MockDataset(1)
        directory.write("", "files1/000/dataset_1.dat")
        absfoo = os.path.abspath(os.path.join(directory.temp_directory, "foo.txt"))
        with open(absfoo, "w") as f:
            f.write("foo")
        try:
            assert object_store.get_data(empty_dataset, extra_dir="dataset_1_files", alt_name=absfoo) != "foo"
        except ObjectInvalid:
            pass


HIERARCHICAL_TEST_CONFIG = get_example("hierarchical_simple.xml")
HIERARCHICAL_TEST_CONFIG_YAML = get_example("hierarchical_simple.yml")


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

            # Write non-empty dataset in backend 1, test it is not empty & exists.
            directory.write("Hello World!", "files1/000/dataset_3.dat")
            assert object_store.exists(MockDataset(3))
            assert not object_store.empty(MockDataset(3))

            # check and description routed correctly
            files1_desc = object_store.get_concrete_store_description_markdown(MockDataset(3))
            files1_name = object_store.get_concrete_store_name(MockDataset(3))
            files2_desc = object_store.get_concrete_store_description_markdown(MockDataset(2))
            files2_name = object_store.get_concrete_store_name(MockDataset(2))
            assert "fancy" in files1_desc
            assert "Newer Cool" in files1_name
            assert "older" in files2_desc
            assert "Legacy" in files2_name

            # Assert creation always happens in first backend.
            for i in range(100):
                dataset = MockDataset(100 + i)
                object_store.create(dataset)
                assert object_store.get_filename(dataset).find("files1") > 0

            as_dict = object_store.to_dict()
            _assert_has_keys(as_dict, ["backends", "extra_dirs", "type"])
            _assert_key_has_value(as_dict, "type", "hierarchical")


def test_concrete_name_without_objectstore_id():
    for config_str in [HIERARCHICAL_TEST_CONFIG, HIERARCHICAL_TEST_CONFIG_YAML]:
        with TestConfig(config_str) as (directory, object_store):
            files1_desc = object_store.get_concrete_store_description_markdown(MockDataset(3))
            files1_name = object_store.get_concrete_store_name(MockDataset(3))
            assert files1_desc is None
            assert files1_name is None


MIXED_STORE_BY_DISTRIBUTED_TEST_CONFIG = """<?xml version="1.0"?>
<object_store type="distributed">
    <backends>
        <backend id="files1" type="disk" weight="1" order="0" store_by="id">
            <files_dir path="${temp_directory}/files1"/>
            <extra_dir type="temp" path="${temp_directory}/tmp1"/>
            <extra_dir type="job_work" path="${temp_directory}/job_working_directory1"/>
        </backend>
        <backend id="files2" type="disk" weight="1" order="1" store_by="uuid" private="true">
            <files_dir path="${temp_directory}/files2"/>
            <extra_dir type="temp" path="${temp_directory}/tmp2"/>
            <extra_dir type="job_work" path="${temp_directory}/job_working_directory2"/>
        </backend>
    </backends>
</object_store>
"""


MIXED_STORE_BY_HIERARCHICAL_TEST_CONFIG = """<?xml version="1.0"?>
<object_store type="hierarchical" private="true">
    <backends>
        <backend id="files1" type="disk" weight="1" order="0" store_by="id">
            <files_dir path="${temp_directory}/files1"/>
            <extra_dir type="temp" path="${temp_directory}/tmp1"/>
            <extra_dir type="job_work" path="${temp_directory}/job_working_directory1"/>
        </backend>
        <backend id="files2" type="disk" weight="1" order="1" store_by="uuid">
            <files_dir path="${temp_directory}/files2"/>
            <extra_dir type="temp" path="${temp_directory}/tmp2"/>
            <extra_dir type="job_work" path="${temp_directory}/job_working_directory2"/>
        </backend>
    </backends>
</object_store>
"""


def test_mixed_store_by():
    with TestConfig(MIXED_STORE_BY_DISTRIBUTED_TEST_CONFIG) as (directory, object_store):
        as_dict = object_store.to_dict()
        assert as_dict["backends"][0]["store_by"] == "id"
        assert as_dict["backends"][1]["store_by"] == "uuid"

    with TestConfig(MIXED_STORE_BY_HIERARCHICAL_TEST_CONFIG) as (directory, object_store):
        as_dict = object_store.to_dict()
        assert as_dict["backends"][0]["store_by"] == "id"
        assert as_dict["backends"][1]["store_by"] == "uuid"


def test_mixed_private():
    # Distributed object store can combine private and non-private concrete objectstores
    with TestConfig(MIXED_STORE_BY_DISTRIBUTED_TEST_CONFIG) as (directory, object_store):
        ids = object_store.object_store_ids()
        assert len(ids) == 2

        ids = object_store.object_store_ids(private=True)
        assert len(ids) == 1
        assert ids[0] == "files2"

        ids = object_store.object_store_ids(private=False)
        assert len(ids) == 1
        assert ids[0] == "files1"

        as_dict = object_store.to_dict()
        assert not as_dict["backends"][0]["private"]
        assert as_dict["backends"][1]["private"]

    with TestConfig(MIXED_STORE_BY_HIERARCHICAL_TEST_CONFIG) as (directory, object_store):
        as_dict = object_store.to_dict()
        assert as_dict["backends"][0]["private"]
        assert as_dict["backends"][1]["private"]

        assert object_store.private
        assert as_dict["private"] is True


def test_empty_cache_targets_for_disk_nested_stores():
    with TestConfig(MIXED_STORE_BY_DISTRIBUTED_TEST_CONFIG) as (directory, object_store):
        assert len(object_store.cache_targets()) == 0

    with TestConfig(MIXED_STORE_BY_HIERARCHICAL_TEST_CONFIG) as (directory, object_store):
        assert len(object_store.cache_targets()) == 0


BADGES_TEST_1_CONFIG_XML = get_example("disk_badges.xml")
BADGES_TEST_1_CONFIG_YAML = get_example("disk_badges.yml")


def test_badges_parsing():
    for config_str in [BADGES_TEST_1_CONFIG_XML, BADGES_TEST_1_CONFIG_YAML]:
        with TestConfig(config_str) as (directory, object_store):
            badges = object_store.to_dict()["badges"]
            assert len(badges) == 6
            badge_1 = badges[0]
            assert badge_1["type"] == "short_term"
            assert badge_1["message"] is None

            badge_2 = badges[1]
            assert badge_2["type"] == "faster"
            assert badge_2["message"] == "Fast interconnects."

            badge_3 = badges[2]
            assert badge_3["type"] == "less_stable"
            assert badge_3["message"] is None

            badge_4 = badges[3]
            assert badge_4["type"] == "more_secure"
            assert badge_4["message"] is None


BADGES_TEST_CONFLICTS_1_CONFIG_YAML = """
type: disk
files_dir: "${temp_directory}/files1"
badges:
  - type: slower
  - type: faster
"""


BADGES_TEST_CONFLICTS_2_CONFIG_YAML = """
type: disk
files_dir: "${temp_directory}/files1"
badges:
  - type: more_secure
  - type: less_secure
"""


def test_badges_parsing_conflicts():
    for config_str in [BADGES_TEST_CONFLICTS_1_CONFIG_YAML]:
        exception_raised = False
        try:
            with TestConfig(config_str) as (directory, object_store):
                pass
        except Exception as e:
            assert "faster" in str(e)
            assert "slower" in str(e)
            exception_raised = True
        assert exception_raised

    for config_str in [BADGES_TEST_CONFLICTS_2_CONFIG_YAML]:
        exception_raised = False
        try:
            with TestConfig(config_str) as (directory, object_store):
                pass
        except Exception as e:
            assert "more_secure" in str(e)
            assert "less_secure" in str(e)
            exception_raised = True
        assert exception_raised


DISTRIBUTED_TEST_CONFIG = get_example("distributed_disk.xml")
DISTRIBUTED_TEST_CONFIG_YAML = get_example("distributed_disk.yml")


def test_distributed_store():
    for config_str in [DISTRIBUTED_TEST_CONFIG, DISTRIBUTED_TEST_CONFIG_YAML]:
        with TestConfig(config_str) as (directory, object_store):
            persisted_ids = []
            for i in range(100):
                dataset = MockDataset(100 + i)
                object_store.create(dataset)
                persisted_ids.append(dataset.object_store_id)

            # Test distributes datasets between backends according to weights
            backend_1_count = sum(1 for v in persisted_ids if v == "files1")
            backend_2_count = sum(1 for v in persisted_ids if v == "files2")

            assert backend_1_count > 0
            assert backend_2_count > 0
            assert backend_1_count > backend_2_count

            as_dict = object_store.to_dict()
            _assert_has_keys(as_dict, ["backends", "extra_dirs", "type"])
            _assert_key_has_value(as_dict, "type", "distributed")

            backends = as_dict["backends"]
            assert len(backends)
            assert backends[0]["quota"]["source"] == "1files"
            assert backends[1]["quota"]["source"] == "2files"

            extra_dirs = as_dict["extra_dirs"]
            assert len(extra_dirs) == 2

            device_source_map = object_store.get_device_source_map()
            assert device_source_map
            assert device_source_map.get_device_id("files1") == "primary_disk"
            assert device_source_map.get_device_id("files2") == "primary_disk"


def test_distributed_store_empty_cache_targets():
    for config_str in [DISTRIBUTED_TEST_CONFIG, DISTRIBUTED_TEST_CONFIG_YAML]:
        with TestConfig(config_str) as (directory, object_store):
            assert len(object_store.cache_targets()) == 0


@patch_object_stores_to_skip_initialize
def test_distributed_store_with_cache_targets():
    for config_str in [get_example("distributed_s3.yml")]:
        with TestConfig(config_str) as (_, object_store):
            assert len(object_store.cache_targets()) == 2


def test_distributed_store_start_propagates_to_backends():
    with TestConfig(DISTRIBUTED_TEST_CONFIG) as (_, object_store):
        for backend in object_store.backends.values():
            backend.start = MagicMock()
        object_store.start()
        for backend in object_store.backends.values():
            backend.start.assert_called_once()


HIERARCHICAL_MUST_HAVE_UNIFIED_QUOTA_SOURCE = """<?xml version="1.0"?>
<object_store type="hierarchical" private="true">
    <backends>
        <backend type="disk" weight="1" order="0" store_by="id">
            <quota source="1files" /> <!-- Cannot do this here, only in distributedobjectstore -->
            <files_dir path="${temp_directory}/files1"/>
            <extra_dir type="temp" path="${temp_directory}/tmp1"/>
            <extra_dir type="job_work" path="${temp_directory}/job_working_directory1"/>
        </backend>
        <backend type="disk" weight="1" order="1" store_by="uuid">
            <files_dir path="${temp_directory}/files2"/>
            <extra_dir type="temp" path="${temp_directory}/tmp2"/>
            <extra_dir type="job_work" path="${temp_directory}/job_working_directory2"/>
        </backend>
    </backends>
</object_store>
"""


def test_hiercachical_backend_must_share_quota_source():
    the_exception = None
    for config_str in [HIERARCHICAL_MUST_HAVE_UNIFIED_QUOTA_SOURCE]:
        try:
            with TestConfig(config_str) as (directory, object_store):
                pass
        except Exception as e:
            the_exception = e
    assert the_exception is not None


PITHOS_TEST_CONFIG = get_example("pithos_simple.xml")
PITHOS_TEST_CONFIG_YAML = get_example("pithos_simple.yml")


@patch_object_stores_to_skip_initialize
def test_config_parse_pithos():
    for config_str in [PITHOS_TEST_CONFIG, PITHOS_TEST_CONFIG_YAML]:
        with TestConfig(config_str) as (directory, object_store):
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


S3_TEST_CONFIG = get_example("s3_simple.xml")
S3_TEST_CONFIG_YAML = get_example("s3_simple.yml")


@patch_object_stores_to_skip_initialize
def test_config_parse_s3():
    for config_str in [S3_TEST_CONFIG, S3_TEST_CONFIG_YAML]:
        with TestConfig(config_str) as (directory, object_store):
            assert object_store.private
            assert object_store.access_key == "access_moo"
            assert object_store.secret_key == "secret_cow"

            assert object_store.bucket == "unique_bucket_name_all_lowercase"
            assert object_store.use_rr is False

            assert object_store.host is None
            assert object_store.port == 6000
            assert object_store.multipart is True
            assert object_store.is_secure is True
            assert object_store.conn_path == "/"

            cache_target = object_store.cache_target
            assert cache_target.size == 1000
            assert cache_target.path == "database/object_store_cache"
            assert object_store.extra_dirs["job_work"] == "database/job_working_directory_s3"
            assert object_store.extra_dirs["temp"] == "database/tmp_s3"

            as_dict = object_store.to_dict()
            _assert_has_keys(as_dict, ["auth", "bucket", "connection", "cache", "extra_dirs", "type"])

            _assert_key_has_value(as_dict, "type", "aws_s3")

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


S3_DEFAULT_CACHE_TEST_CONFIG = get_example("s3_global_cache.xml")
S3_DEFAULT_CACHE_TEST_CONFIG_YAML = get_example("s3_global_cache.yml")


@patch_object_stores_to_skip_initialize
def test_config_parse_s3_with_default_cache():
    for config_str in [S3_DEFAULT_CACHE_TEST_CONFIG, S3_DEFAULT_CACHE_TEST_CONFIG_YAML]:
        with TestConfig(config_str) as (directory, object_store):
            assert object_store.cache_size == -1
            assert object_store.staging_path == directory.global_config.object_store_cache_path


@patch_object_stores_to_skip_initialize
def test_config_parse_boto3():
    for config_str in [get_example("boto3_simple.xml"), get_example("boto3_simple.yml")]:
        with TestConfig(config_str) as (directory, object_store):
            assert object_store.access_key == "access_moo"
            assert object_store.secret_key == "secret_cow"

            assert object_store.bucket == "unique_bucket_name_all_lowercase"

            # defaults to AWS
            assert object_store.endpoint_url is None

            # direct download (presigned URL redirects) is opt-in
            assert object_store.enable_direct_download is False

            cache_target = object_store.cache_target
            assert cache_target.size == 1000
            assert cache_target.path == "database/object_store_cache"
            assert object_store.extra_dirs["job_work"] == "database/job_working_directory_s3"
            assert object_store.extra_dirs["temp"] == "database/tmp_s3"

            as_dict = object_store.to_dict()
            _assert_has_keys(as_dict, ["auth", "bucket", "connection", "cache", "extra_dirs", "type"])

            _assert_key_has_value(as_dict, "type", "boto3")

            auth_dict = as_dict["auth"]
            bucket_dict = as_dict["bucket"]
            cache_dict = as_dict["cache"]

            _assert_key_has_value(auth_dict, "access_key", "access_moo")
            _assert_key_has_value(auth_dict, "secret_key", "secret_cow")

            _assert_key_has_value(bucket_dict, "name", "unique_bucket_name_all_lowercase")

            _assert_key_has_value(cache_dict, "size", 1000)
            _assert_key_has_value(cache_dict, "path", "database/object_store_cache")

            extra_dirs = as_dict["extra_dirs"]
            assert len(extra_dirs) == 2


@patch_object_stores_to_skip_initialize
def test_config_parse_enable_direct_download():
    for config_str in [get_example("boto3_direct_download.xml"), get_example("boto3_direct_download.yml")]:
        with TestConfig(config_str) as (directory, object_store):
            assert object_store.enable_direct_download is True

            as_dict = object_store.to_dict()
            _assert_key_has_value(as_dict, "enable_direct_download", True)

            model = object_store.to_model("the_object_store_id")
            assert model.enable_direct_download is True


@patch_object_stores_to_skip_initialize
def test_get_direct_download_url_returns_presigned_url_when_enabled():
    with TestConfig(get_example("boto3_direct_download.yml")) as (directory, object_store):
        object_store._client = MagicMock()
        object_store._client.generate_presigned_url.return_value = "https://s3.example.org/signed"
        with patch.object(object_store, "_exists", return_value=True):
            url = object_store.get_direct_download_url(MockDataset(1))
        assert url == "https://s3.example.org/signed"


@patch_object_stores_to_skip_initialize
def test_get_direct_download_url_returns_none_when_disabled():
    with TestConfig(get_example("boto3_simple.yml")) as (directory, object_store):
        object_store._client = MagicMock()
        with patch.object(object_store, "_exists", return_value=True):
            url = object_store.get_direct_download_url(MockDataset(1))
        assert url is None
        object_store._client.generate_presigned_url.assert_not_called()


@patch_object_stores_to_skip_initialize
def test_get_direct_download_url_forwards_content_disposition():
    with TestConfig(get_example("boto3_direct_download.yml")) as (directory, object_store):
        object_store._client = MagicMock()
        object_store._client.generate_presigned_url.return_value = "https://s3.example.org/signed"
        with patch.object(object_store, "_exists", return_value=True):
            object_store.get_direct_download_url(
                MockDataset(1),
                content_disposition='attachment; filename="Galaxy1-[data].txt"',
                content_type="application/octet-stream",
            )
        _, call_kwargs = object_store._client.generate_presigned_url.call_args
        params = call_kwargs["Params"]
        assert params["ResponseContentDisposition"] == 'attachment; filename="Galaxy1-[data].txt"'
        assert params["ResponseContentType"] == "application/octet-stream"


def test_get_direct_download_url_disk_store_returns_none():
    with TestConfig(DISK_TEST_CONFIG) as (directory, object_store):
        url = object_store.get_direct_download_url(MockDataset(1))
        assert url is None


@patch_object_stores_to_skip_initialize
def test_config_parse_boto3_custom_connection():
    for config_str in [get_example("boto3_custom_connection.xml"), get_example("boto3_custom_connection.yml")]:
        with TestConfig(config_str) as (directory, object_store):
            assert object_store.endpoint_url == "https://s3.example.org/"
            assert object_store.region == "the_example_region"


@patch_object_stores_to_skip_initialize
def test_config_parse_boto3_merged_transfer_options():
    for config_str in [
        get_example("boto3_merged_transfer_options.xml"),
        get_example("boto3_merged_transfer_options.yml"),
    ]:
        with TestConfig(config_str) as (directory, object_store):
            as_dict = object_store.to_dict()
            transfer_dict = as_dict["transfer"]
            assert transfer_dict["multipart_threshold"] == 13
            assert transfer_dict["max_concurrency"] == 13
            assert transfer_dict["multipart_chunksize"] == 13
            assert transfer_dict["num_download_attempts"] == 13
            assert transfer_dict["max_io_queue"] == 13
            assert transfer_dict["io_chunksize"] == 13
            assert transfer_dict["use_threads"] is False
            assert transfer_dict["max_bandwidth"] == 13

            for transfer_type in ["upload", "download"]:
                transfer_config = object_store._transfer_config(transfer_type)
                assert transfer_config.multipart_threshold == 13
                assert transfer_config.max_concurrency == 13
                assert transfer_config.multipart_chunksize == 13
                assert transfer_config.num_download_attempts == 13
                assert transfer_config.max_io_queue == 13
                assert transfer_config.io_chunksize == 13
                assert transfer_config.use_threads is False
                assert transfer_config.max_bandwidth == 13


@patch_object_stores_to_skip_initialize
def test_config_parse_boto3_separated_transfer_options():
    for config_str in [
        get_example("boto3_separated_transfer_options.xml"),
        get_example("boto3_separated_transfer_options.yml"),
    ]:
        with TestConfig(config_str) as (directory, object_store):
            transfer_config = object_store._transfer_config("upload")
            assert transfer_config.multipart_threshold == 13
            assert transfer_config.max_concurrency == 13
            assert transfer_config.multipart_chunksize == 13
            assert transfer_config.num_download_attempts == 13
            assert transfer_config.max_io_queue == 13
            assert transfer_config.io_chunksize == 13
            assert transfer_config.use_threads is False
            assert transfer_config.max_bandwidth == 13

            transfer_config = object_store._transfer_config("download")
            assert transfer_config.multipart_threshold == 14
            assert transfer_config.max_concurrency == 14
            assert transfer_config.multipart_chunksize == 14
            assert transfer_config.num_download_attempts == 14
            assert transfer_config.max_io_queue == 14
            assert transfer_config.io_chunksize == 14
            assert transfer_config.use_threads is True
            assert transfer_config.max_bandwidth == 14


CLOUD_AWS_TEST_CONFIG = get_example("cloud_aws_simple.xml")
CLOUD_AWS_TEST_CONFIG_YAML = get_example("cloud_aws_simple.yml")

CLOUD_AZURE_TEST_CONFIG = get_example("cloud_azure_simple.xml")
CLOUD_AZURE_TEST_CONFIG_YAML = get_example("cloud_azure_simple.yml")

CLOUD_GOOGLE_TEST_CONFIG = get_example("cloud_gcp_simple.xml")
CLOUD_GOOGLE_TEST_CONFIG_YAML = get_example("cloud_gcp_simple.yml")


@patch_object_stores_to_skip_initialize
def test_config_parse_cloud():
    for config_str in [
        CLOUD_AWS_TEST_CONFIG,
        CLOUD_AWS_TEST_CONFIG_YAML,
        CLOUD_AZURE_TEST_CONFIG,
        CLOUD_AZURE_TEST_CONFIG_YAML,
        CLOUD_GOOGLE_TEST_CONFIG,
        CLOUD_GOOGLE_TEST_CONFIG_YAML,
    ]:
        if "google" in config_str:
            tmpdir = mkdtemp()
            if not os.path.exists(tmpdir):
                os.makedirs(tmpdir)
            path = os.path.join(tmpdir, "gcp.config")
            open(path, "w").write("some_gcp_config")
            config_str = config_str.replace("gcp.config", path)
        with TestConfig(config_str) as (directory, object_store):
            assert object_store.bucket_name == "unique_bucket_name_all_lowercase"
            assert object_store.use_rr is False

            cache_target = object_store.cache_target
            assert cache_target.size == 1000.0
            assert cache_target.path == "database/object_store_cache"
            assert object_store.extra_dirs["job_work"] == "database/job_working_directory_cloud"
            assert object_store.extra_dirs["temp"] == "database/tmp_cloud"

            as_dict = object_store.to_dict()
            _assert_has_keys(as_dict, ["provider", "auth", "bucket", "cache", "extra_dirs", "type"])

            _assert_key_has_value(as_dict, "type", "cloud")

            auth_dict = as_dict["auth"]
            bucket_dict = as_dict["bucket"]
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

            _assert_key_has_value(cache_dict, "size", 1000.0)
            _assert_key_has_value(cache_dict, "path", "database/object_store_cache")

            extra_dirs = as_dict["extra_dirs"]
            assert len(extra_dirs) == 2


CLOUD_AWS_NO_AUTH_TEST_CONFIG = get_example("cloud_aws_no_auth.xml")


@patch_object_stores_to_skip_initialize
def test_config_parse_cloud_noauth_for_aws():
    for config_str in [CLOUD_AWS_NO_AUTH_TEST_CONFIG]:
        with TestConfig(config_str) as (directory, object_store):
            assert object_store.bucket_name == "unique_bucket_name_all_lowercase"
            assert object_store.use_rr is False

            cache_target = object_store.cache_target
            assert cache_target.size == 1000.0
            assert cache_target.path == "database/object_store_cache"
            assert object_store.extra_dirs["job_work"] == "database/job_working_directory_cloud"
            assert object_store.extra_dirs["temp"] == "database/tmp_cloud"

            as_dict = object_store.to_dict()
            _assert_has_keys(as_dict, ["provider", "auth", "bucket", "cache", "extra_dirs", "type"])

            _assert_key_has_value(as_dict, "type", "cloud")

            auth_dict = as_dict["auth"]
            bucket_dict = as_dict["bucket"]
            cache_dict = as_dict["cache"]

            provider = as_dict["provider"]
            assert provider == "aws"
            _assert_key_has_value(auth_dict, "access_key", None)
            _assert_key_has_value(auth_dict, "secret_key", None)

            _assert_key_has_value(bucket_dict, "name", "unique_bucket_name_all_lowercase")
            _assert_key_has_value(bucket_dict, "use_reduced_redundancy", False)

            _assert_key_has_value(cache_dict, "size", 1000.0)
            _assert_key_has_value(cache_dict, "path", "database/object_store_cache")

            extra_dirs = as_dict["extra_dirs"]
            assert len(extra_dirs) == 2


CLOUD_AWS_NO_CACHE_TEST_CONFIG = get_example("cloud_aws_default_cache.xml")


@patch_object_stores_to_skip_initialize
def test_config_parse_cloud_no_cache_for_aws():
    for config_str in [CLOUD_AWS_NO_CACHE_TEST_CONFIG]:
        with TestConfig(config_str) as (directory, object_store):
            assert object_store.staging_path == directory.global_config.object_store_cache_path
            assert object_store.cache_size == -1


CLOUD_AWS_REGION_TEST_CONFIG = get_example("cloud_aws_region.xml")
CLOUD_AWS_REGION_TEST_CONFIG_YAML = get_example("cloud_aws_region.yml")


@patch_object_stores_to_skip_initialize
def test_config_parse_cloud_aws_region():
    for config_str in [CLOUD_AWS_REGION_TEST_CONFIG, CLOUD_AWS_REGION_TEST_CONFIG_YAML]:
        with TestConfig(config_str) as (directory, object_store):
            assert object_store.credentials["region"] == "us-east-2"

            as_dict = object_store.to_dict()
            _assert_key_has_value(as_dict["auth"], "region", "us-east-2")


CLOUD_GOOGLE_MISSING_CREDENTIALS_FILE_CONFIG = """<object_store type="cloud" provider="google">
    <auth />
    <bucket name="unique_bucket_name_all_lowercase" use_reduced_redundancy="False" />
    <cache path="database/object_store_cache" size="1000" />
    <extra_dir type="job_work" path="database/job_working_directory_cloud"/>
    <extra_dir type="temp" path="database/tmp_cloud"/>
</object_store>
"""


@patch_object_stores_to_skip_initialize
def test_config_parse_cloud_google_missing_credentials_file():
    # A missing credentials_file must produce the missing-configuration error,
    # not a TypeError from checking a None path on disk.
    with pytest.raises(Exception, match="credentials_file"):
        with TestConfig(CLOUD_GOOGLE_MISSING_CREDENTIALS_FILE_CONFIG):
            pass


@patch_object_stores_to_skip_initialize
def test_config_parse_cloud_is_cloud():
    with TestConfig(CLOUD_AWS_TEST_CONFIG) as (directory, object_store):
        assert object_store.cloud is True


CLOUD_TRANSFER_TEST_CONFIG = get_example("cloud_transfer.xml")
CLOUD_TRANSFER_TEST_CONFIG_YAML = get_example("cloud_transfer.yml")


@patch_object_stores_to_skip_initialize
def test_config_parse_cloud_transfer_options():
    for config_str in [CLOUD_TRANSFER_TEST_CONFIG, CLOUD_TRANSFER_TEST_CONFIG_YAML]:
        with TestConfig(config_str) as (directory, object_store):
            assert object_store.transfer_dict == {
                "multipart_threshold": 5242880,
                "multipart_chunksize": 5242880,
                "max_concurrency": 2,
            }

            as_dict = object_store.to_dict()
            _assert_key_has_value(
                as_dict,
                "transfer",
                {
                    "multipart_threshold": 5242880,
                    "multipart_chunksize": 5242880,
                    "max_concurrency": 2,
                },
            )

            # Bare keys apply to both directions.
            for direction in ("upload", "download"):
                transfer_config = object_store._transfer_config(direction)
                assert transfer_config is not None
                assert transfer_config.threshold == 5242880
                assert transfer_config.part_size == 5242880
                assert transfer_config.max_concurrency == 2


CLOUD_SEPARATED_TRANSFER_TEST_CONFIG_YAML = CLOUD_TRANSFER_TEST_CONFIG_YAML.replace(
    """transfer:
  multipart_threshold: 5242880
  multipart_chunksize: 5242880
  max_concurrency: 2""",
    """transfer:
  multipart_threshold: 10485760
  upload_multipart_threshold: 20971520
  download_multipart_threshold: 31457280
  multipart_chunksize: 5242880
  download_multipart_chunksize: 1048576
  max_concurrency: 2
  upload_max_concurrency: 4""",
)


@patch_object_stores_to_skip_initialize
def test_config_parse_cloud_separated_transfer_options():
    with TestConfig(CLOUD_SEPARATED_TRANSFER_TEST_CONFIG_YAML) as (directory, object_store):
        # Direction-prefixed keys override the bare key for that direction.
        upload_config = object_store._transfer_config("upload")
        assert upload_config.threshold == 20971520
        assert upload_config.part_size == 5242880
        assert upload_config.max_concurrency == 4

        download_config = object_store._transfer_config("download")
        assert download_config.threshold == 31457280
        assert download_config.part_size == 1048576
        assert download_config.max_concurrency == 2


@patch_object_stores_to_skip_initialize
def test_config_parse_cloud_no_transfer_options():
    with TestConfig(CLOUD_AWS_TEST_CONFIG) as (directory, object_store):
        assert object_store.transfer_dict == {}
        # With nothing configured, transfers fall back to cloudbridge's own
        # defaults rather than passing a hollow config.
        assert object_store._transfer_config("upload") is None
        assert object_store._transfer_config("download") is None


@patch_object_stores_to_skip_initialize
def test_config_parse_cloud_transfer_chunksize_below_provider_minimum():
    config_str = CLOUD_TRANSFER_TEST_CONFIG.replace('multipart_chunksize="5242880"', 'multipart_chunksize="1048576"')
    with pytest.raises(Exception, match="multipart_chunksize"):
        with TestConfig(config_str):
            pass

    # The 5 MiB floor is an upload constraint (non-final part minimum);
    # ranged downloads have no minimum part size.
    config_str = CLOUD_TRANSFER_TEST_CONFIG.replace(
        'multipart_chunksize="5242880"', 'download_multipart_chunksize="1048576"'
    )
    with TestConfig(config_str) as (directory, object_store):
        assert object_store._transfer_config("download").part_size == 1048576

    config_str = CLOUD_TRANSFER_TEST_CONFIG.replace(
        'multipart_chunksize="5242880"', 'upload_multipart_chunksize="1048576"'
    )
    with pytest.raises(Exception, match="multipart_chunksize"):
        with TestConfig(config_str):
            pass


class _FakePagedObjectContainer:
    """A bucket.objects fake speaking cloudbridge's real paging protocol.

    list() returns one page at a time (via ClientPagedResultList, the same
    class the AWS provider uses), so code that only consumes the first page
    misses objects; cloudbridge's BasePageableObjectMixin.iter() yields all.
    """

    def __init__(self, keys, page_size=1):
        from types import SimpleNamespace

        from cloudbridge.base.resources import BasePageableObjectMixin

        self._keys = keys
        provider = SimpleNamespace(config=SimpleNamespace(default_result_limit=page_size))

        class _Container(BasePageableObjectMixin):
            def list(self, limit=None, marker=None, prefix=None):
                from cloudbridge.base.resources import ClientPagedResultList

                return ClientPagedResultList(provider, keys, limit=limit, marker=marker)

        self._container = _Container()

    def __getattr__(self, item):
        return getattr(self._container, item)


def _fake_remote_key(name):
    key = MagicMock()
    key.id = name
    key.name = name
    return key


@patch_object_stores_to_skip_initialize
def test_cloud_store_delete_all_paginates():
    with TestConfig(CLOUD_AWS_TEST_CONFIG) as (directory, object_store):
        keys = [_fake_remote_key(f"files/dir/dataset_{i}.dat") for i in range(3)]
        bucket = MagicMock()
        bucket.objects = _FakePagedObjectContainer(keys, page_size=1)
        object_store.bucket = bucket

        assert object_store._delete_remote_all("files/dir")
        for key in keys:
            key.delete.assert_called_once()


@patch_object_stores_to_skip_initialize
def test_cloud_store_download_directory_paginates(tmp_path):
    with TestConfig(CLOUD_AWS_TEST_CONFIG) as (directory, object_store):
        keys = [_fake_remote_key(f"files/dir/part_{i}.dat") for i in range(3)]
        bucket = MagicMock()
        bucket.objects = _FakePagedObjectContainer(keys, page_size=1)
        object_store.bucket = bucket

        downloaded = []

        def fake_download_to(key, destination):
            downloaded.append(key.name)
            open(destination, "wb").close()

        object_store._download_to = fake_download_to
        object_store._download_directory_into_cache("files/dir", str(tmp_path / "cache"))
        assert downloaded == [key.name for key in keys]


@patch_object_stores_to_skip_initialize
def test_cloud_store_download_passes_transfer_config():
    with TestConfig(CLOUD_TRANSFER_TEST_CONFIG) as (directory, object_store):
        key = MagicMock()
        object_store._download_to(key, "/tmp/dataset_1.dat")
        assert key.download_to_file.call_count == 1
        assert key.download_to_file.call_args.args == ("/tmp/dataset_1.dat",)
        transfer_config = key.download_to_file.call_args.kwargs["config"]
        assert transfer_config.threshold == 5242880
        assert transfer_config.part_size == 5242880
        assert transfer_config.max_concurrency == 2

    with TestConfig(CLOUD_AWS_TEST_CONFIG) as (directory, object_store):
        key = MagicMock()
        object_store._download_to(key, "/tmp/dataset_1.dat")
        assert key.download_to_file.call_args.kwargs["config"] is None


@patch_object_stores_to_skip_initialize
def test_cloud_store_push_file_single_remote_lookup():
    with TestConfig(CLOUD_AWS_TEST_CONFIG) as (directory, object_store):
        # An existing remote object is uploaded in place - no create and
        # exactly one remote lookup.
        existing = MagicMock()
        bucket = MagicMock()
        bucket.objects.get.return_value = existing
        object_store.bucket = bucket
        assert object_store._push_file_to_path("files/dataset_1.dat", "/tmp/dataset_1.dat")
        bucket.objects.get.assert_called_once_with("files/dataset_1.dat")
        bucket.objects.create.assert_not_called()
        assert existing.upload_from_file.call_count == 1
        assert existing.upload_from_file.call_args.args == ("/tmp/dataset_1.dat",)

        # A missing remote object is created first, then uploaded.
        created = MagicMock()
        bucket = MagicMock()
        bucket.objects.get.return_value = None
        bucket.objects.create.return_value = created
        object_store.bucket = bucket
        assert object_store._push_file_to_path("files/dataset_2.dat", "/tmp/dataset_2.dat")
        bucket.objects.get.assert_called_once_with("files/dataset_2.dat")
        bucket.objects.create.assert_called_once_with("files/dataset_2.dat")
        assert created.upload_from_file.call_count == 1
        assert created.upload_from_file.call_args.args == ("/tmp/dataset_2.dat",)


@patch_object_stores_to_skip_initialize
def test_cloud_store_push_string_single_remote_lookup():
    with TestConfig(CLOUD_AWS_TEST_CONFIG) as (directory, object_store):
        existing = MagicMock()
        bucket = MagicMock()
        bucket.objects.get.return_value = existing
        object_store.bucket = bucket
        assert object_store._push_string_to_path("files/dataset_1.dat", "some content")
        bucket.objects.get.assert_called_once_with("files/dataset_1.dat")
        bucket.objects.create.assert_not_called()
        assert existing.upload.call_count == 1
        assert existing.upload.call_args.args == ("some content",)

        created = MagicMock()
        bucket = MagicMock()
        bucket.objects.get.return_value = None
        bucket.objects.create.return_value = created
        object_store.bucket = bucket
        assert object_store._push_string_to_path("files/dataset_2.dat", "other content")
        bucket.objects.get.assert_called_once_with("files/dataset_2.dat")
        bucket.objects.create.assert_called_once_with("files/dataset_2.dat")
        assert created.upload.call_count == 1
        assert created.upload.call_args.args == ("other content",)


CLOUD_AWS_CUSTOM_CONNECTION_CONFIG = get_example("cloud_aws_custom_connection.xml")
CLOUD_AWS_CUSTOM_CONNECTION_CONFIG_YAML = get_example("cloud_aws_custom_connection.yml")


@patch_object_stores_to_skip_initialize
def test_config_parse_cloud_aws_custom_connection():
    for config_str in [CLOUD_AWS_CUSTOM_CONNECTION_CONFIG, CLOUD_AWS_CUSTOM_CONNECTION_CONFIG_YAML]:
        with TestConfig(config_str) as (directory, object_store):
            assert object_store.credentials["session_token"] == "session_token_moo"
            assert object_store.credentials["region"] == "us-east-2"
            assert object_store.connection_dict == {
                "endpoint_url": "https://s3.example.org/",
                "validate_certs": False,
                "signature_version": "s3v4",
            }

            as_dict = object_store.to_dict()
            _assert_key_has_value(as_dict["auth"], "session_token", "session_token_moo")
            _assert_key_has_value(as_dict["connection"], "endpoint_url", "https://s3.example.org/")
            _assert_key_has_value(as_dict["connection"], "validate_certs", False)
            _assert_key_has_value(as_dict["connection"], "signature_version", "s3v4")


@patch_object_stores_to_skip_initialize
def test_cloud_connection_aws_maps_full_options():
    with TestConfig(CLOUD_AWS_CUSTOM_CONNECTION_CONFIG_YAML) as (directory, object_store):
        with patch("galaxy.objectstore.cloud.CloudProviderFactory") as factory_class:
            object_store._get_connection(object_store.provider, object_store.credentials, object_store.connection_dict)
        _, provider_config = factory_class.return_value.create_provider.call_args.args
        assert provider_config == {
            "aws_access_key": "access_moo",
            "aws_secret_key": "secret_cow",
            "aws_session_token": "session_token_moo",
            "aws_region_name": "us-east-2",
            "s3_endpoint_url": "https://s3.example.org/",
            "s3_validate_certs": False,
            "s3_signature_version": "s3v4",
        }


CLOUD_AZURE_FULL_CONFIG = get_example("cloud_azure_full.xml")
CLOUD_AZURE_FULL_CONFIG_YAML = get_example("cloud_azure_full.yml")


@patch_object_stores_to_skip_initialize
def test_config_parse_cloud_azure_full():
    for config_str in [CLOUD_AZURE_FULL_CONFIG, CLOUD_AZURE_FULL_CONFIG_YAML]:
        with TestConfig(config_str) as (directory, object_store):
            assert object_store.credentials["storage_account"] == "galaxystorage"
            assert object_store.credentials["resource_group"] == "galaxy_rg"
            assert object_store.credentials["region"] == "eastus2"

            as_dict = object_store.to_dict()
            _assert_key_has_value(as_dict["auth"], "storage_account", "galaxystorage")
            _assert_key_has_value(as_dict["auth"], "resource_group", "galaxy_rg")


@patch_object_stores_to_skip_initialize
def test_cloud_connection_azure_maps_full_options():
    with TestConfig(CLOUD_AZURE_FULL_CONFIG_YAML) as (directory, object_store):
        with patch("galaxy.objectstore.cloud.CloudProviderFactory") as factory_class:
            object_store._get_connection(object_store.provider, object_store.credentials, object_store.connection_dict)
        _, provider_config = factory_class.return_value.create_provider.call_args.args
        assert provider_config == {
            "azure_subscription_id": "a_sub_id",
            "azure_client_id": "and_a_client_id",
            "azure_secret": "and_a_secret_key",
            "azure_tenant": "and_some_tenant_info",
            "azure_storage_account": "galaxystorage",
            "azure_resource_group": "galaxy_rg",
            "azure_region_name": "eastus2",
        }


CLOUD_AZURE_ACCESS_TOKEN_ONLY_CONFIG = """<object_store type="cloud" provider="azure">
    <auth access_token="a_token" storage_account="galaxystorage" resource_group="galaxy_rg" />
    <bucket name="unique_container_name" use_reduced_redundancy="False" />
    <cache path="database/object_store_cache" size="1000" />
    <extra_dir type="job_work" path="database/job_working_directory_cloud"/>
    <extra_dir type="temp" path="database/tmp_cloud"/>
</object_store>
"""


@patch_object_stores_to_skip_initialize
def test_config_parse_cloud_azure_access_token_only():
    # With an access token the service-principal quartet is optional.
    with TestConfig(CLOUD_AZURE_ACCESS_TOKEN_ONLY_CONFIG) as (directory, object_store):
        assert object_store.credentials["access_token"] == "a_token"
        assert "subscription_id" not in object_store.credentials

        with patch("galaxy.objectstore.cloud.CloudProviderFactory") as factory_class:
            object_store._get_connection(object_store.provider, object_store.credentials, object_store.connection_dict)
        _, provider_config = factory_class.return_value.create_provider.call_args.args
        assert provider_config == {
            "azure_access_token": "a_token",
            "azure_storage_account": "galaxystorage",
            "azure_resource_group": "galaxy_rg",
        }


CLOUD_GCP_INLINE_CREDS_CONFIG_YAML = get_example("cloud_gcp_inline_creds.yml")


@patch_object_stores_to_skip_initialize
def test_config_parse_cloud_gcp_inline_credentials():
    with TestConfig(CLOUD_GCP_INLINE_CREDS_CONFIG_YAML) as (directory, object_store):
        assert object_store.credentials["credentials_dict"]["project_id"] == "my_project"

        with patch("galaxy.objectstore.cloud.CloudProviderFactory") as factory_class:
            object_store._get_connection(object_store.provider, object_store.credentials, object_store.connection_dict)
        _, provider_config = factory_class.return_value.create_provider.call_args.args
        assert provider_config["gcp_service_creds_dict"]["project_id"] == "my_project"
        assert provider_config["gcp_region_name"] == "us-central1"
        assert "gcp_service_creds_file" not in provider_config


@patch_object_stores_to_skip_initialize
def test_config_parse_cloud_gcp_requires_exactly_one_credential_source():
    no_creds = CLOUD_GCP_INLINE_CREDS_CONFIG_YAML.replace("credentials_dict:", "ignored_dict:")
    with pytest.raises(Exception, match="exactly one"):
        with TestConfig(no_creds):
            pass

    both_creds = CLOUD_GCP_INLINE_CREDS_CONFIG_YAML.replace(
        "  credentials_dict:", "  credentials_file: gcp.config\n  credentials_dict:"
    )
    with pytest.raises(Exception, match="exactly one"):
        with TestConfig(both_creds):
            pass


CLOUD_OPENSTACK_TEST_CONFIG = get_example("cloud_openstack_simple.xml")
CLOUD_OPENSTACK_TEST_CONFIG_YAML = get_example("cloud_openstack_simple.yml")


@patch_object_stores_to_skip_initialize
def test_config_parse_cloud_openstack():
    for config_str in [CLOUD_OPENSTACK_TEST_CONFIG, CLOUD_OPENSTACK_TEST_CONFIG_YAML]:
        with TestConfig(config_str) as (directory, object_store):
            assert object_store.provider == "openstack"
            assert object_store.credentials["username"] == "os_user"
            assert object_store.credentials["password"] == "os_pass"
            assert object_store.credentials["project_name"] == "os_project"
            assert object_store.credentials["auth_url"] == "https://keystone.example.org:5000/v3"
            assert object_store.credentials["region"] == "RegionOne"

            as_dict = object_store.to_dict()
            _assert_key_has_value(as_dict, "provider", "openstack")
            _assert_key_has_value(as_dict["auth"], "auth_url", "https://keystone.example.org:5000/v3")
            _assert_key_has_value(as_dict["bucket"], "name", "unique_container_name")


@patch_object_stores_to_skip_initialize
def test_cloud_connection_openstack_maps_options():
    with TestConfig(CLOUD_OPENSTACK_TEST_CONFIG_YAML) as (directory, object_store):
        with patch("galaxy.objectstore.cloud.CloudProviderFactory") as factory_class:
            object_store._get_connection(object_store.provider, object_store.credentials, object_store.connection_dict)
        _, provider_config = factory_class.return_value.create_provider.call_args.args
        assert provider_config == {
            "os_username": "os_user",
            "os_password": "os_pass",
            "os_project_name": "os_project",
            "os_auth_url": "https://keystone.example.org:5000/v3",
            "os_region_name": "RegionOne",
            "os_user_domain_name": "Default",
            "os_project_domain_name": "Default",
        }


CLOUD_OPENSTACK_APP_CREDENTIAL_CONFIG = """<object_store type="cloud" provider="openstack">
    <auth auth_url="https://keystone.example.org:5000/v3" application_credential_id="an_app_cred_id" application_credential_secret="an_app_cred_secret" />
    <bucket name="unique_container_name" use_reduced_redundancy="False" />
    <cache path="database/object_store_cache" size="1000" />
    <extra_dir type="job_work" path="database/job_working_directory_cloud"/>
    <extra_dir type="temp" path="database/tmp_cloud"/>
</object_store>
"""


@patch_object_stores_to_skip_initialize
def test_config_parse_cloud_openstack_app_credentials():
    # With an application credential, username/password/project_name are optional.
    with TestConfig(CLOUD_OPENSTACK_APP_CREDENTIAL_CONFIG) as (directory, object_store):
        assert object_store.credentials["application_credential_id"] == "an_app_cred_id"
        assert "username" not in object_store.credentials

        with patch("galaxy.objectstore.cloud.CloudProviderFactory") as factory_class:
            object_store._get_connection(object_store.provider, object_store.credentials, object_store.connection_dict)
        _, provider_config = factory_class.return_value.create_provider.call_args.args
        assert provider_config == {
            "os_auth_url": "https://keystone.example.org:5000/v3",
            "os_application_credential_id": "an_app_cred_id",
            "os_application_credential_secret": "an_app_cred_secret",
        }


CLOUD_DIRECT_DOWNLOAD_CONFIG = get_example("cloud_direct_download.xml")
CLOUD_DIRECT_DOWNLOAD_CONFIG_YAML = get_example("cloud_direct_download.yml")


@patch_object_stores_to_skip_initialize
def test_config_parse_cloud_direct_download():
    for config_str in [CLOUD_DIRECT_DOWNLOAD_CONFIG, CLOUD_DIRECT_DOWNLOAD_CONFIG_YAML]:
        with TestConfig(config_str) as (directory, object_store):
            assert object_store.enable_direct_download is True

            as_dict = object_store.to_dict()
            _assert_key_has_value(as_dict, "enable_direct_download", True)

            model = object_store.to_model("the_object_store_id")
            assert model.enable_direct_download is True


@patch_object_stores_to_skip_initialize
def test_cloud_get_direct_download_url_forwards_response_headers():
    with TestConfig(CLOUD_DIRECT_DOWNLOAD_CONFIG_YAML) as (directory, object_store):
        key = MagicMock()
        key.generate_url.return_value = "https://cloud.example.org/signed"
        bucket = MagicMock()
        bucket.objects.get.return_value = key
        object_store.bucket = bucket
        with patch.object(object_store, "_exists", return_value=True):
            url = object_store.get_direct_download_url(
                MockDataset(1),
                content_disposition='attachment; filename="Galaxy1-[data].txt"',
                content_type="application/octet-stream",
            )
        assert url == "https://cloud.example.org/signed"
        key.generate_url.assert_called_once_with(
            expires_in=86400,
            content_disposition='attachment; filename="Galaxy1-[data].txt"',
            content_type="application/octet-stream",
        )


@patch_object_stores_to_skip_initialize
def test_cloud_get_direct_download_url_returns_none_when_disabled():
    with TestConfig(CLOUD_AWS_TEST_CONFIG) as (directory, object_store):
        key = MagicMock()
        bucket = MagicMock()
        bucket.objects.get.return_value = key
        object_store.bucket = bucket
        with patch.object(object_store, "_exists", return_value=True):
            url = object_store.get_direct_download_url(MockDataset(1))
        assert url is None
        key.generate_url.assert_not_called()


@patch_object_stores_to_skip_initialize
def test_cloud_store_uploads_pass_transfer_config():
    with TestConfig(CLOUD_TRANSFER_TEST_CONFIG) as (directory, object_store):
        obj = MagicMock()
        bucket = MagicMock()
        bucket.objects.get.return_value = obj
        object_store.bucket = bucket

        assert object_store._push_file_to_path("files/dataset_1.dat", "/tmp/dataset_1.dat")
        upload_config = obj.upload_from_file.call_args.kwargs["config"]
        assert upload_config.threshold == 5242880
        assert upload_config.part_size == 5242880
        assert upload_config.max_concurrency == 2

        assert object_store._push_string_to_path("files/dataset_1.dat", "some content")
        upload_config = obj.upload.call_args.kwargs["config"]
        assert upload_config.threshold == 5242880
        assert upload_config.part_size == 5242880
        assert upload_config.max_concurrency == 2


@patch_object_stores_to_skip_initialize
def test_cloud_store_uploads_pass_no_config_when_unconfigured():
    with TestConfig(CLOUD_AWS_TEST_CONFIG) as (directory, object_store):
        obj = MagicMock()
        bucket = MagicMock()
        bucket.objects.get.return_value = obj
        object_store.bucket = bucket

        assert object_store._push_file_to_path("files/dataset_1.dat", "/tmp/dataset_1.dat")
        assert obj.upload_from_file.call_args.kwargs["config"] is None

        assert object_store._push_string_to_path("files/dataset_1.dat", "some content")
        assert obj.upload.call_args.kwargs["config"] is None


AZURE_BLOB_TEST_CONFIG = get_example("azure_simple.xml")
AZURE_BLOB_TEST_CONFIG_YAML = get_example("azure_simple.yml")


@patch_object_stores_to_skip_initialize
def test_config_parse_azure():
    for config_str in [AZURE_BLOB_TEST_CONFIG, AZURE_BLOB_TEST_CONFIG_YAML]:
        with TestConfig(config_str) as (directory, object_store):
            assert object_store.account_name == "azureact"
            assert object_store.account_key == "password123"

            assert object_store.container_name == "unique_container_name"

            cache_target = object_store.cache_target
            assert cache_target.size == 100
            assert cache_target.path == "database/object_store_cache"
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

            _assert_key_has_value(cache_dict, "size", 100)
            _assert_key_has_value(cache_dict, "path", "database/object_store_cache")

            extra_dirs = as_dict["extra_dirs"]
            assert len(extra_dirs) == 2


@patch_object_stores_to_skip_initialize
def test_config_parse_azure_transfer():
    for config_str in [get_example("azure_transfer.xml"), get_example("azure_transfer.yml")]:
        with TestConfig(config_str) as (directory, object_store):
            as_dict = object_store.to_dict()["transfer"]
            assert as_dict["download_max_concurrency"] == 1
            assert as_dict["upload_max_concurrency"] == 2
            assert as_dict["max_single_put_size"] == 10
            assert as_dict["max_single_get_size"] == 20
            assert as_dict["max_block_size"] == 3


def test_cache_monitor_thread(tmp_path):
    cache_dir = tmp_path
    path = cache_dir / "a_file_0"
    path.write_text("this is an example file")

    cache_target = CacheTarget(cache_dir, 1, 0.000000001)
    monitor = InProcessCacheMonitor(cache_target, 30, 0)

    path_cleaned = False
    for _ in range(100):
        time.sleep(0.1)
        path_cleaned = not path.exists()
        if path_cleaned:
            break
    monitor.shutdown()
    assert path_cleaned

    # just verify things cleaned up okay also
    assert not monitor.cache_monitor_thread.is_alive()
    assert monitor.stop_cache_monitor_event.is_set()


def test_check_cache_sanity(tmp_path):
    # sanity check the caching code - create a 1 gig cache with a single file.
    # when the cache is allowed to be 20% full the file will exist but when the
    # cache is only allowed to be a very small fraction full headed toward zero
    # the file will be deleted
    cache_dir = tmp_path
    path = cache_dir / "a_file_0"
    path.write_text("this is an example file")
    big_cache_target = CacheTarget(cache_dir, 1, 0.2)
    check_cache(big_cache_target)
    assert path.exists()
    small_cache_target = CacheTarget(cache_dir, 1, 0.000000001)
    check_cache(small_cache_target)
    assert not path.exists()


def test_fits_in_cache_check(tmp_path):
    cache_dir = tmp_path
    big_cache_target = CacheTarget(cache_dir, 1, 0.2)
    assert not big_cache_target.fits_in_cache(int(1024 * 1024 * 1024 * 0.3))
    assert big_cache_target.fits_in_cache(int(1024 * 1024 * 1024 * 0.1))

    noop_cache_target = CacheTarget(cache_dir, -1, 0.2)
    assert noop_cache_target.fits_in_cache(1024 * 1024 * 1024 * 100)


AZURE_BLOB_NO_CACHE_TEST_CONFIG = get_example("azure_default_cache.xml")
AZURE_BLOB_NO_CACHE_TEST_CONFIG_YAML = get_example("azure_default_cache.yml")


@patch_object_stores_to_skip_initialize
def test_config_parse_azure_no_cache():
    for config_str in [AZURE_BLOB_NO_CACHE_TEST_CONFIG, AZURE_BLOB_NO_CACHE_TEST_CONFIG_YAML]:
        with TestConfig(config_str) as (directory, object_store):
            assert object_store.cache_size == -1
            assert object_store.staging_path == directory.global_config.object_store_cache_path


def verify_caching_object_store_functionality(tmp_path, object_store, check_get_url=True):
    # Test no dataset with id 1 exists.
    absent_dataset = MockDataset(1)
    assert not object_store.exists(absent_dataset)

    # Write empty dataset 2 in second backend, ensure it is empty and
    # exists.
    empty_dataset = MockDataset(2)
    object_store.create(empty_dataset)
    assert object_store.exists(empty_dataset)
    assert object_store.empty(empty_dataset)

    # Write non-empty dataset in backend 1, test it is not emtpy & exists.
    # with cache...
    hello_world_dataset = MockDataset(3)
    hello_path = tmp_path / "hello.txt"
    hello_path.write_text("Hello World!")
    object_store.update_from_file(hello_world_dataset, file_name=hello_path, create=True)
    assert object_store.exists(hello_world_dataset)
    assert not object_store.empty(hello_world_dataset)

    # Test get_data
    data = object_store.get_data(hello_world_dataset)
    assert data == "Hello World!"

    data = object_store.get_data(hello_world_dataset, start=1, count=6)
    assert data == "ello W"
    path = object_store.get_filename(hello_world_dataset)
    assert open(path).read() == "Hello World!"

    # Write non-empty dataset in backend 1, test it is not emtpy & exists.
    # without cache...
    hello_world_dataset_2 = MockDataset(10)
    object_store.update_from_file(hello_world_dataset_2, file_name=hello_path, create=True)
    reset_cache(object_store.cache_target)
    assert object_store.exists(hello_world_dataset_2)
    reset_cache(object_store.cache_target)
    assert not object_store.empty(hello_world_dataset_2)
    reset_cache(object_store.cache_target)

    data = object_store.get_data(hello_world_dataset_2)
    assert data == "Hello World!"
    reset_cache(object_store.cache_target)
    data = object_store.get_data(hello_world_dataset_2, start=1, count=6)
    assert data == "ello W"
    reset_cache(object_store.cache_target)
    path = object_store.get_filename(hello_world_dataset_2)
    assert open(path).read() == "Hello World!"

    # Test Size

    # Test absent and empty datasets yield size of 0.
    assert object_store.size(absent_dataset) == 0
    assert object_store.size(empty_dataset) == 0
    # Elsewise
    assert object_store.size(hello_world_dataset) == 12

    # Test percent used (to some degree)
    percent_store_used = object_store.get_store_usage_percent()
    assert percent_store_used >= 0.0
    assert percent_store_used < 100.0

    # Test delete
    to_delete_dataset = MockDataset(5)
    object_store.create(to_delete_dataset)
    assert object_store.exists(to_delete_dataset)
    assert object_store.delete(to_delete_dataset)
    assert not object_store.exists(to_delete_dataset)

    # Test delete no cache
    to_delete_dataset = MockDataset(5)
    object_store.create(to_delete_dataset)
    assert object_store.exists(to_delete_dataset)
    reset_cache(object_store.cache_target)
    assert object_store.delete(to_delete_dataset)
    reset_cache(object_store.cache_target)
    assert not object_store.exists(to_delete_dataset)

    # Test bigger file to force multi-process.
    big_file_dataset = MockDataset(6)
    size = 1024
    path = tmp_path / "big_file.bytes"
    with path.open("wb") as f:
        f.write(os.urandom(size))
    object_store.update_from_file(big_file_dataset, file_name=path, create=True)
    assert object_store.exists(big_file_dataset)
    assert object_store.size(big_file_dataset) == size

    extra_files_dataset = MockDataset(7)
    object_store.create(extra_files_dataset)
    extra = tmp_path / "extra"
    extra.mkdir()
    extra_file = extra / "new_value.txt"
    extra_file.write_text("My new value")

    persist_extra_files_for_dataset(
        object_store,
        extra,
        extra_files_dataset,  # type: ignore[arg-type,unused-ignore]
        extra_files_dataset._extra_files_rel_path,
    )

    # The following checks used to exhibit different behavior depending
    # on how the cache was cleaned - removing the whole directory vs
    # just cleaning up files the way Galaxy's internal caching works with
    # reset_cache. So we test both here.

    # hard reset
    shutil.rmtree(object_store.cache_target.path)
    os.makedirs(object_store.cache_target.path)

    extra_path = _extra_file_path(object_store, extra_files_dataset)
    assert os.path.exists(extra_path)
    expected_extra_file = os.path.join(extra_path, "new_value.txt")
    assert os.path.exists(expected_extra_file)
    assert open(expected_extra_file).read() == "My new value"

    # Redo the above test with Galaxy's reset_cache which leaves empty directories
    # around.
    reset_cache(object_store.cache_target)
    extra_path = _extra_file_path(object_store, extra_files_dataset)
    assert os.path.exists(extra_path)
    expected_extra_file = os.path.join(extra_path, "new_value.txt")
    assert os.path.exists(expected_extra_file)
    assert open(expected_extra_file).read() == "My new value"

    # Test get_object_url returns a read-only URL
    url = object_store.get_object_url(hello_world_dataset)
    if check_get_url:
        response = get(url)
        response.raise_for_status()
        assert response.text == "Hello World!"


def verify_big_file_storage_roundtrip(tmp_path, object_store, size_bytes):
    # Store a file large enough to cross the configured multipart threshold
    # and verify it round-trips bit-for-bit through the remote store.
    big_file_dataset = MockDataset(11)
    path = tmp_path / "big_file_roundtrip.bytes"
    content = os.urandom(size_bytes)
    with path.open("wb") as f:
        f.write(content)
    expected_sha256 = hashlib.sha256(content).hexdigest()

    object_store.update_from_file(big_file_dataset, file_name=path, create=True)
    reset_cache(object_store.cache_target)
    assert object_store.exists(big_file_dataset)
    reset_cache(object_store.cache_target)
    assert object_store.size(big_file_dataset) == size_bytes

    reset_cache(object_store.cache_target)
    stored_path = object_store.get_filename(big_file_dataset)
    with open(stored_path, "rb") as f:
        stored_sha256 = hashlib.sha256(f.read()).hexdigest()
    assert stored_sha256 == expected_sha256


def _extra_file_path(object_store, dataset):
    # invoke the magic calls the model layer would invoke here...
    if object_store.exists(dataset, dir_only=True, extra_dir=dataset._extra_files_rel_path):
        return object_store.get_filename(dataset, dir_only=True, extra_dir=dataset._extra_files_rel_path)
    return object_store.construct_path(dataset, dir_only=True, extra_dir=dataset._extra_files_rel_path, in_cache=True)


def verify_object_store_functionality(tmp_path, object_store, check_get_url=True):
    # Test no dataset with id 1 exists.
    absent_dataset = MockDataset(1)
    assert not object_store.exists(absent_dataset)

    # Write empty dataset 2 in second backend, ensure it is empty and
    # exists.
    empty_dataset = MockDataset(2)
    object_store.create(empty_dataset)
    assert object_store.exists(empty_dataset)
    assert object_store.empty(empty_dataset)

    # Write non-empty dataset in backend 1, test it is not emtpy & exists.
    # with cache...
    hello_world_dataset = MockDataset(3)
    hello_path = tmp_path / "hello.txt"
    hello_path.write_text("Hello World!")
    object_store.update_from_file(hello_world_dataset, file_name=hello_path, create=True)
    assert object_store.exists(hello_world_dataset)
    assert not object_store.empty(hello_world_dataset)

    # Test get_data
    data = object_store.get_data(hello_world_dataset)
    assert data == "Hello World!"

    data = object_store.get_data(hello_world_dataset, start=1, count=6)
    assert data == "ello W"
    path = object_store.get_filename(hello_world_dataset)
    assert open(path).read() == "Hello World!"

    # Test Size

    # Test absent and empty datasets yield size of 0.
    assert object_store.size(absent_dataset) == 0
    assert object_store.size(empty_dataset) == 0
    # Elsewise
    assert object_store.size(hello_world_dataset) == 12

    # Test delete
    to_delete_dataset = MockDataset(5)
    object_store.create(to_delete_dataset)
    assert object_store.exists(to_delete_dataset)
    assert object_store.delete(to_delete_dataset)
    assert not object_store.exists(to_delete_dataset)

    # Test get_object_url returns a read-only URL
    url = object_store.get_object_url(hello_world_dataset)
    if check_get_url:
        response = get(url)
        response.raise_for_status()
        assert response.text == "Hello World!"


def integration_test_config(example_filename: str):
    return TestConfig(get_example(example_filename), inject_galaxy_test_env=True)


@skip_unless_environ("GALAXY_TEST_AZURE_CONTAINER_NAME")
@skip_unless_environ("GALAXY_TEST_AZURE_ACCOUNT_KEY")
@skip_unless_environ("GALAXY_TEST_AZURE_ACCOUNT_NAME")
def test_real_azure_blob_store(tmp_path):
    with integration_test_config("azure_integration_test.yml") as (_, object_store):
        verify_caching_object_store_functionality(tmp_path, object_store)


@skip_unless_environ("GALAXY_TEST_AZURE_CONTAINER_NAME")
@skip_unless_environ("GALAXY_TEST_AZURE_ACCOUNT_KEY")
@skip_unless_environ("GALAXY_TEST_AZURE_ACCOUNT_NAME")
@skip_unless_environ("GALAXY_TEST_AZURE_ACCOUNT_URL")
def test_real_azure_blob_store_with_account_url(tmp_path):
    with integration_test_config("azure_integration_test_with_account_url.yml") as (
        _,
        object_store,
    ):
        verify_caching_object_store_functionality(tmp_path, object_store)


@skip_unless_environ("GALAXY_TEST_AZURE_CONTAINER_NAME")
@skip_unless_environ("GALAXY_TEST_AZURE_ACCOUNT_KEY")
@skip_unless_environ("GALAXY_TEST_AZURE_ACCOUNT_NAME")
def test_real_azure_blob_store_in_hierarchical(tmp_path):
    with integration_test_config("azure_integration_test_distributed.yml") as (_, object_store):
        verify_object_store_functionality(tmp_path, object_store)


@skip_unless_environ("GALAXY_TEST_AWS_ACCESS_KEY")
@skip_unless_environ("GALAXY_TEST_AWS_SECRET_KEY")
@skip_unless_environ("GALAXY_TEST_AWS_BUCKET")
@skip_unless_environ("GALAXY_TEST_AWS_REGION")
def test_real_aws_s3_store(tmp_path):
    with integration_test_config("aws_s3_integration_test.yml") as (_, object_store):
        verify_caching_object_store_functionality(tmp_path, object_store)


@skip_unless_environ("GALAXY_TEST_AWS_ACCESS_KEY")
@skip_unless_environ("GALAXY_TEST_AWS_SECRET_KEY")
@skip_unless_environ("GALAXY_TEST_AWS_BUCKET")
def test_real_aws_s3_store_boto3(tmp_path):
    with integration_test_config("boto3_integration_test_aws.yml") as (_, object_store):
        verify_caching_object_store_functionality(tmp_path, object_store)


@skip_unless_environ("GALAXY_TEST_AWS_ACCESS_KEY")
@skip_unless_environ("GALAXY_TEST_AWS_SECRET_KEY")
@skip_unless_environ("GALAXY_TEST_AWS_BUCKET")
def test_real_aws_s3_store_boto3_multipart(tmp_path):
    with integration_test_config("boto3_integration_test_multithreaded.yml") as (_, object_store):
        verify_caching_object_store_functionality(tmp_path, object_store)


@skip_unless_environ("GALAXY_TEST_AWS_ACCESS_KEY")
@skip_unless_environ("GALAXY_TEST_AWS_SECRET_KEY")
def test_real_aws_s3_store_boto3_new_bucket(tmp_path):
    with integration_test_config("boto3_integration_test_aws_new_bucket.yml") as (_, object_store):
        verify_caching_object_store_functionality(tmp_path, object_store)


# this test fails if you have axel installed because axel requires URLs to work and that requires
# setting a region with the cloudbridge store.
@skip_unless_environ("GALAXY_TEST_AWS_ACCESS_KEY")
@skip_unless_environ("GALAXY_TEST_AWS_SECRET_KEY")
@skip_unless_environ("GALAXY_TEST_AWS_BUCKET")
def test_aws_via_cloudbridge_store(tmp_path):
    with integration_test_config("cloud_integration_test_aws.yml") as (_, object_store):
        # disabling get_object_url check - cloudbridge in this config assumes the region
        # is us-east-1 and generates a URL for that region. This functionality works and can
        # be tested if a region is specified in the configuration (see next config and test case).
        verify_caching_object_store_functionality(tmp_path, object_store, check_get_url=False)


@skip_unless_environ("GALAXY_TEST_AWS_ACCESS_KEY")
@skip_unless_environ("GALAXY_TEST_AWS_SECRET_KEY")
@skip_unless_environ("GALAXY_TEST_AWS_BUCKET")
@skip_unless_environ("GALAXY_TEST_AWS_REGION")
def test_aws_via_cloudbridge_store_with_region(tmp_path):
    with integration_test_config("cloud_integration_test_aws_with_region.yml") as (_, object_store):
        verify_caching_object_store_functionality(tmp_path, object_store)


@skip_unless_environ("GALAXY_TEST_AWS_ACCESS_KEY")
@skip_unless_environ("GALAXY_TEST_AWS_SECRET_KEY")
@skip_unless_environ("GALAXY_TEST_AWS_BUCKET")
@skip_unless_environ("GALAXY_TEST_AWS_REGION")
def test_aws_via_cloudbridge_store_multipart(tmp_path):
    # 12 MiB crosses the configured 5 MiB threshold -> 3 parts, exercising
    # cloudbridge's multipart upload path end to end.
    with integration_test_config("cloud_integration_test_aws_multipart.yml") as (_, object_store):
        verify_caching_object_store_functionality(tmp_path, object_store)
        verify_big_file_storage_roundtrip(tmp_path, object_store, 12 * 1024 * 1024)


@skip_unless_environ("GALAXY_TEST_OS_USERNAME")
@skip_unless_environ("GALAXY_TEST_OS_PASSWORD")
@skip_unless_environ("GALAXY_TEST_OS_PROJECT_NAME")
@skip_unless_environ("GALAXY_TEST_OS_AUTH_URL")
@skip_unless_environ("GALAXY_TEST_OS_REGION_NAME")
@skip_unless_environ("GALAXY_TEST_OS_CONTAINER")
def test_openstack_via_cloudbridge_store(tmp_path):
    # Exercises cloudbridge's generic clone-pool multipart driver on Swift
    # (static large objects) with the big-file roundtrip.
    with integration_test_config("cloud_integration_test_openstack.yml") as (_, object_store):
        verify_caching_object_store_functionality(tmp_path, object_store)
        verify_big_file_storage_roundtrip(tmp_path, object_store, 12 * 1024 * 1024)


@skip_unless_environ("GALAXY_TEST_GOOGLE_INTEROP_ACCESS_KEY")
@skip_unless_environ("GALAXY_TEST_GOOGLE_INTEROP_SECRET_KEY")
@skip_unless_environ("GALAXY_TEST_GOOGLE_BUCKET")
def test_gcp_via_s3_interop(tmp_path):
    with integration_test_config("gcp_s3_integration_test.yml") as (_, object_store):
        verify_caching_object_store_functionality(tmp_path, object_store)


@skip_unless_environ("GALAXY_TEST_GOOGLE_INTEROP_ACCESS_KEY")
@skip_unless_environ("GALAXY_TEST_GOOGLE_INTEROP_SECRET_KEY")
@skip_unless_environ("GALAXY_TEST_GOOGLE_BUCKET")
def test_gcp_via_s3_interop_and_boto3(tmp_path):
    with integration_test_config("gcp_boto3_integration_test.yml") as (_, object_store):
        verify_caching_object_store_functionality(tmp_path, object_store)


# Ensure's boto3 will use legacy connection parameters that the generic_s3 object store
# would consume.
@skip_unless_environ("GALAXY_TEST_GOOGLE_INTEROP_ACCESS_KEY")
@skip_unless_environ("GALAXY_TEST_GOOGLE_INTEROP_SECRET_KEY")
@skip_unless_environ("GALAXY_TEST_GOOGLE_BUCKET")
def test_gcp_via_s3_interop_and_boto3_with_legacy_params(tmp_path):
    with integration_test_config("gcp_boto3_integration_test_legacy_params.yml") as (_, object_store):
        verify_caching_object_store_functionality(tmp_path, object_store)


class MockDataset:
    def __init__(self, id):
        self.id = id
        self.object_store_id = None
        self.uuid = uuid4()
        self.tags = []

    def rel_path_for_uuid_test(self):
        rel_path = os.path.join(*directory_hash_id(self.uuid))
        return rel_path

    @property
    def _extra_files_rel_path(self):
        return f"dataset_{self.uuid}_files"


def _assert_has_keys(the_dict, keys):
    for key in keys:
        assert key in the_dict, f"key [{key}] not in [{the_dict}]"


def _assert_key_has_value(the_dict, key, value):
    assert key in the_dict, f"dict [{key}] doesn't container expected key [{the_dict}]"
    assert the_dict[key] == value, f"{the_dict[key]} != {value}"
