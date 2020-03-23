import collections
import os
import tempfile

import pytest

from galaxy.datatypes.registry import Registry
from galaxy.util.checkers import (
    is_bz2,
    is_gzip,
    is_zip
)
from galaxy.util.hash_util import md5_hash_file
from galaxy_test.driver import integration_util
from .test_upload_configuration_options import BaseUploadContentConfigurationInstance
from .test_datatype_upload import TEST_CASES

SCRIPT_DIRECTORY = os.path.abspath(os.path.dirname(__file__))
GALAXY_ROOT = os.path.abspath('%s/../../' % SCRIPT_DIRECTORY)
DATATYPES_CONFIG = os.path.join(GALAXY_ROOT, 'lib/galaxy/config/sample/datatypes_conf.xml.sample')
PARENT_SNIFFER_MAP = {'fastqsolexa': 'fastq'}
OBJECT_STORE_CONFIG_FILE = os.path.join(SCRIPT_DIRECTORY, "irods_object_store_conf.xml")
# Run test for only the first 10 test files
IRODS_TEST_CASES = dict(list(TEST_CASES.items())[0:10])

class UploadTestDatatypeDataTestCase(BaseUploadContentConfigurationInstance):
    framework_tool_and_types = False
    datatypes_conf_override = DATATYPES_CONFIG

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        config["object_store_config_file"] = OBJECT_STORE_CONFIG_FILE

instance = integration_util.integration_module_instance(UploadTestDatatypeDataTestCase)

@pytest.fixture
def temp_file():
    with tempfile.NamedTemporaryFile(delete=True, mode='wb') as fh:
        yield fh

registry = Registry()
registry.load_datatypes(root_dir=GALAXY_ROOT, config=DATATYPES_CONFIG)

@pytest.mark.parametrize('test_data', IRODS_TEST_CASES.values(), ids=list(IRODS_TEST_CASES.keys()))
def test_upload_datatype_auto(instance, test_data, temp_file):
    is_compressed = False
    for is_method in (is_bz2, is_gzip, is_zip):
        is_compressed = is_method(test_data.path)
        if is_compressed:
            break
    with open(test_data.path, 'rb') as content:
        if hasattr(test_data.datatype, 'sniff') or 'false' in test_data.path:
            file_type = 'auto'
        else:
            file_type = test_data.datatype.file_ext
        dataset = instance.dataset_populator.new_dataset(instance.history_id, content=content, wait=False, file_type=file_type)
    dataset = instance.dataset_populator.get_history_dataset_details(instance.history_id, dataset=dataset, assert_ok=False)
    expected_file_ext = test_data.datatype.file_ext
    # State might be error if the datatype can't be uploaded
    if dataset['state'] == 'error' and not test_data.uploadable:
        # Some things can't be uploaded, if attempting to upload these datasets we mention why
        assert 'invalid' in dataset['misc_info'] or 'unsupported' in dataset['misc_info']
        return
    elif dataset['state'] == 'error' and 'empty' in dataset['misc_info']:
        return
    else:
        # state should be OK
        assert dataset['state'] == 'ok'
    # Check that correct datatype has been detected
    file_ext = dataset['file_ext']
    if 'false' in test_data.path:
        # datasets with false in their name are not of a specific datatype
        assert file_ext != PARENT_SNIFFER_MAP.get(expected_file_ext, expected_file_ext)
    else:
        assert file_ext == PARENT_SNIFFER_MAP.get(expected_file_ext, expected_file_ext)
    datatype = registry.datatypes_by_extension[file_ext]
    datatype_compressed = getattr(datatype, "compressed", False)
    if not is_compressed or datatype_compressed:
        # download file and verify it hasn't been manipulated
        temp_file.write(instance.dataset_populator.get_history_dataset_content(history_id=instance.history_id,
                                                                               dataset=dataset,
                                                                               type='bytes',
                                                                               assert_ok=False,
                                                                               raw=True))
        temp_file.flush()
        assert md5_hash_file(test_data.path) == md5_hash_file(temp_file.name)
