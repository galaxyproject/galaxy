import collections
import os
import shutil

import pytest

from galaxy.datatypes.data import Text
from galaxy.datatypes.registry import Registry
from galaxy.util.checkers import (
    is_bz2,
    is_gzip,
    is_zip,
)
from galaxy.util.hash_util import md5_hash_file
from galaxy_test.driver import integration_util
from .test_upload_configuration_options import BaseUploadContentConfigurationInstance

SCRIPT_DIRECTORY = os.path.abspath(os.path.dirname(__file__))
TEST_FILE_DIR = "%s/../../lib/galaxy/datatypes/test" % SCRIPT_DIRECTORY
TestData = collections.namedtuple("TestData", "path datatype uploadable")
GALAXY_ROOT = os.path.abspath("%s/../../" % SCRIPT_DIRECTORY)
DATATYPES_CONFIG = os.path.join(GALAXY_ROOT, "lib/galaxy/config/sample/datatypes_conf.xml.sample")
PARENT_SNIFFER_MAP = {"fastqsolexa": "fastq"}


def find_datatype(registry, filename):
    # match longest extension first
    sorted_extensions = sorted(registry.datatypes_by_extension.keys(), key=len, reverse=True)
    for extension in sorted_extensions:
        if filename.endswith(extension) or filename.startswith(extension):
            return registry.datatypes_by_extension[extension]
    raise Exception("Couldn't guess datatype for file '%s'" % filename)


def collect_test_data(registry):
    test_files = [f for f in os.listdir(TEST_FILE_DIR) if "." in f]
    files = [os.path.join(TEST_FILE_DIR, f) for f in test_files]
    datatypes = [find_datatype(registry, f) for f in test_files]
    uploadable = [datatype.file_ext in registry.upload_file_formats for datatype in datatypes]
    test_data_description = [TestData(*items) for items in zip(files, datatypes, uploadable)]
    return {os.path.basename(data.path): data for data in test_data_description}


class UploadTestDatatypeDataTestCase(BaseUploadContentConfigurationInstance):
    framework_tool_and_types = False
    datatypes_conf_override = DATATYPES_CONFIG
    object_store_config = None
    object_store_config_path = None


instance = integration_util.integration_module_instance(UploadTestDatatypeDataTestCase)


registry = Registry()
registry.load_datatypes(root_dir=GALAXY_ROOT, config=DATATYPES_CONFIG)
TEST_CASES = collect_test_data(registry)


@pytest.mark.parametrize("test_data", TEST_CASES.values(), ids=list(TEST_CASES.keys()))
def test_upload_datatype_auto(instance, test_data, temp_file, celery_session_worker, celery_session_app):
    upload_datatype_helper(instance, test_data, temp_file)


def upload_datatype_helper(instance, test_data, temp_file, delete_cache_dir=False):
    is_compressed = False
    for is_method in (is_bz2, is_gzip, is_zip):
        is_compressed = is_method(test_data.path)
        if is_compressed:
            break
    with open(test_data.path, "rb") as content:
        if hasattr(test_data.datatype, "sniff") or "false" in test_data.path:
            file_type = "auto"
        else:
            file_type = test_data.datatype.file_ext
        dataset = instance.dataset_populator.new_dataset(
            instance.history_id,
            content=content,
            wait=False,
            file_type=file_type,
            auto_decompress=True,
        )
    dataset = instance.dataset_populator.get_history_dataset_details(
        instance.history_id, dataset=dataset, assert_ok=False
    )
    expected_file_ext = test_data.datatype.file_ext
    # State might be error if the datatype can't be uploaded
    if dataset["state"] == "error" and not test_data.uploadable:
        # Some things can't be uploaded, if attempting to upload these datasets we mention why
        assert "invalid" in dataset["misc_info"] or "unsupported" in dataset["misc_info"]
        return
    elif dataset["state"] == "error" and "empty" in dataset["misc_info"]:
        return
    else:
        # state should be OK
        assert dataset["state"] == "ok"
    # Check that correct datatype has been detected
    file_ext = dataset["file_ext"]
    if "false" in test_data.path:
        # datasets with false in their name are not of a specific datatype
        assert file_ext != PARENT_SNIFFER_MAP.get(expected_file_ext, expected_file_ext)
    else:
        assert file_ext == PARENT_SNIFFER_MAP.get(expected_file_ext, expected_file_ext)
    datatype = registry.datatypes_by_extension[file_ext]
    datatype_compressed = getattr(datatype, "compressed", False)
    if not is_compressed or datatype_compressed:
        if delete_cache_dir:
            # Delete cache directory and then re-create it. This way we confirm
            # that dataset is fetched from the object store, not from the cache
            temp_dir = instance.get_object_store_kwargs()["temp_directory"]
            cache_dir = temp_dir + "/object_store_cache"
            shutil.rmtree(cache_dir)
            os.mkdir(cache_dir)

        # download file and verify it hasn't been manipulated
        temp_file.write(
            instance.dataset_populator.get_history_dataset_content(
                history_id=instance.history_id, dataset=dataset, type="bytes", assert_ok=False, raw=True
            )
        )
        temp_file.flush()
        expected_hash = md5_hash_file(test_data.path)
        test_hash = md5_hash_file(temp_file.name)
        message = f"Expected md5 sum '{expected_hash}' for {os.path.relpath(test_data.path)}, but test file md5sum is {test_hash}."
        if expected_hash != test_hash:
            if isinstance(datatype, Text):
                with open(test_data.path, "rb") as fh:
                    fh.seek(-1, os.SEEK_END)
                    if fh.read() != b"\n":
                        message = f"{message} You need to add a final newline to {os.path.relpath(test_data.path)}."
        assert expected_hash == test_hash, message
