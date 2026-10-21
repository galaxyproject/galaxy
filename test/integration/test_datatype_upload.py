import collections
import contextlib
import os
import shutil
from collections.abc import Iterable
from typing import (
    Any,
    TYPE_CHECKING,
)

import pytest

from galaxy.datatypes.data import Text
from galaxy.datatypes.registry import Registry
from galaxy.util.checkers import (
    is_bz2,
    is_gzip,
    is_xz,
    is_zip,
)
from galaxy.util.hash_util import md5_hash_file
from galaxy_test.base import api_asserts
from galaxy_test.driver import integration_util
from .test_upload_configuration_options import BaseUploadContentConfigurationIntegrationInstance

SCRIPT_DIRECTORY = os.path.abspath(os.path.dirname(__file__))
GALAXY_ROOT = os.path.abspath(os.path.dirname(os.path.dirname(SCRIPT_DIRECTORY)))
TEST_FILE_DIR = os.path.join(GALAXY_ROOT, "packages/data/src/galaxy/datatypes/test")
DatatypeUploadCase = collections.namedtuple("DatatypeUploadCase", "path datatype uploadable")
DATATYPES_CONFIG = os.path.join(GALAXY_ROOT, "packages/config/src/galaxy/config/sample/datatypes_conf.xml.sample")
PARENT_SNIFFER_MAP = {"fastqsolexa": "fastq"}
# A single fetch job processes every test file in turn.
UPLOAD_TIMEOUT = 600


def find_datatype(registry, filename):
    # match longest extension first
    sorted_extensions = sorted(registry.datatypes_by_extension.keys(), key=len, reverse=True)
    for extension in sorted_extensions:
        if filename.endswith(extension) or filename.startswith(extension):
            return registry.datatypes_by_extension[extension]
    raise Exception(f"Couldn't guess datatype for file '{filename}'")


def collect_test_data(registry):
    test_files = [f for f in os.listdir(TEST_FILE_DIR) if "." in f]
    files = [os.path.join(TEST_FILE_DIR, f) for f in test_files]
    datatypes = [find_datatype(registry, f) for f in test_files]
    uploadable = [datatype.file_ext in registry.upload_file_formats for datatype in datatypes]
    test_data_description = [DatatypeUploadCase(*items) for items in zip(files, datatypes, uploadable)]
    return {os.path.basename(data.path): data for data in test_data_description}


class UploadTestDatatypeDataIntegrationInstance(BaseUploadContentConfigurationIntegrationInstance):
    framework_tool_and_types = False
    datatypes_conf_override = DATATYPES_CONFIG
    object_store_config = None
    object_store_config_path = None


instance = integration_util.integration_module_instance(UploadTestDatatypeDataIntegrationInstance)


registry = Registry()
registry.load_datatypes(root_dir=GALAXY_ROOT, config=DATATYPES_CONFIG)
TEST_CASES = collect_test_data(registry)


@pytest.fixture(scope="module")
def uploaded_datasets(
    instance: UploadTestDatatypeDataIntegrationInstance,
    celery_session_worker,
    celery_session_app,
):
    with instance.dataset_populator.test_history() as history_id:
        yield history_id, upload_datatypes(instance, TEST_CASES.values(), history_id)


@pytest.mark.parametrize("test_data", TEST_CASES.values(), ids=list(TEST_CASES.keys()))
def test_upload_datatype_auto(
    instance: UploadTestDatatypeDataIntegrationInstance,
    test_data: DatatypeUploadCase,
    temp_file,
    uploaded_datasets,
) -> None:
    history_id, datasets = uploaded_datasets
    dataset = datasets[os.path.basename(test_data.path)]
    verify_datatype_upload(instance, test_data, temp_file, history_id, dataset)


def upload_file_type(test_data: DatatypeUploadCase) -> str:
    if hasattr(test_data.datatype, "sniff") or "false" in test_data.path:
        return "auto"
    return test_data.datatype.file_ext


def upload_datatypes(
    instance: UploadTestDatatypeDataIntegrationInstance,
    test_cases: Iterable[DatatypeUploadCase],
    history_id: str,
) -> dict[str, dict[str, Any]]:
    """Upload all test cases in a single fetch request and return the new HDA per file name."""
    test_cases = list(test_cases)
    with contextlib.ExitStack() as stack:
        # The element new_dataset() sends for a single file. The fixed name matters: without
        # it the dataset is named after the file, and sniffing considers the name's extension.
        elements = []
        files = {}
        for i, test_data in enumerate(test_cases):
            elements.append(
                {
                    "src": "files",
                    "ext": upload_file_type(test_data),
                    "dbkey": "?",
                    "name": "Test_Dataset",
                    "auto_decompress": True,
                    "to_posix_lines": True,
                }
            )
            files[f"files_{i}|file_data"] = stack.enter_context(open(test_data.path, "rb"))
        payload = {
            "history_id": history_id,
            "targets": [{"destination": {"type": "hdas"}, "elements": elements}],
            "__files": files,
        }
        response = instance.dataset_populator.fetch(payload, wait=False)
    api_asserts.assert_status_code_is_ok(response)
    response_json = response.json()
    outputs = response_json["outputs"]
    assert len(outputs) == len(test_cases)
    for job in response_json["jobs"]:
        instance.dataset_populator.wait_for_job(job["id"], timeout=UPLOAD_TIMEOUT)
    return {os.path.basename(test_data.path): output for test_data, output in zip(test_cases, outputs)}


def upload_datatype_helper(
    instance: UploadTestDatatypeDataIntegrationInstance,
    test_data: DatatypeUploadCase,
    temp_file,
    history_id: str,
    delete_cache_dir: bool = False,
) -> None:
    with open(test_data.path, "rb") as content:
        dataset = instance.dataset_populator.new_dataset(
            history_id,
            content=content,
            wait=False,
            file_type=upload_file_type(test_data),
            auto_decompress=True,
        )
    verify_datatype_upload(instance, test_data, temp_file, history_id, dataset, delete_cache_dir)


def verify_datatype_upload(
    instance: UploadTestDatatypeDataIntegrationInstance,
    test_data: DatatypeUploadCase,
    temp_file,
    history_id: str,
    dataset: dict[str, Any],
    delete_cache_dir: bool = False,
) -> None:
    is_compressed = False
    for is_method in (is_bz2, is_gzip, is_xz, is_zip):
        is_compressed = is_method(test_data.path)
        if is_compressed:
            break
    dataset = instance.dataset_populator.get_history_dataset_details(history_id, dataset=dataset, assert_ok=False)
    summary = {key: dataset[key] for key in ("state", "file_ext", "misc_info", "misc_blurb")}
    expected_file_ext = test_data.datatype.file_ext
    # State might be error if the datatype can't be uploaded
    if dataset["state"] == "error" and not test_data.uploadable:
        # Some things can't be uploaded, if attempting to upload these datasets we mention why
        assert "invalid" in dataset["misc_info"] or "unsupported" in dataset["misc_info"], summary
        return
    elif dataset["state"] == "error" and "empty" in dataset["misc_info"]:
        return
    else:
        # state should be OK
        assert dataset["state"] == "ok", summary
    # Check that correct datatype has been detected
    file_ext = dataset["file_ext"]
    if "false" in test_data.path:
        # datasets with false in their name are not of a specific datatype
        assert file_ext != PARENT_SNIFFER_MAP.get(expected_file_ext, expected_file_ext), summary
    else:
        assert file_ext == PARENT_SNIFFER_MAP.get(expected_file_ext, expected_file_ext), summary
    datatype = registry.datatypes_by_extension[file_ext]
    datatype_compressed = getattr(datatype, "compressed", False)
    if not is_compressed or datatype_compressed:
        if delete_cache_dir:
            # Delete cache directory and then re-create it. This way we confirm
            # that dataset is fetched from the object store, not from the cache
            if TYPE_CHECKING:
                from .objectstore.test_objectstore_datatype_upload import BaseObjectstoreUploadIntegrationInstance

                assert isinstance(instance, BaseObjectstoreUploadIntegrationInstance)
            temp_dir = instance.get_object_store_kwargs()["temp_directory"]
            cache_dir = temp_dir + "/object_store_cache"
            shutil.rmtree(cache_dir)
            os.mkdir(cache_dir)

        # download file and verify it hasn't been manipulated
        temp_file.write(
            instance.dataset_populator.get_history_dataset_content(
                history_id=history_id, dataset=dataset, type="bytes", assert_ok=False, raw=True
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
