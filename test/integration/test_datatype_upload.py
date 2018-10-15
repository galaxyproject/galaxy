import collections
import os

import pytest

from galaxy.datatypes.registry import Registry
from .test_upload_configuration_options import BaseUploadContentConfigurationTestCase

SCRIPT_DIRECTORY = os.path.abspath(os.path.dirname(__file__))
TEST_FILE_DIR = '%s/../../lib/galaxy/datatypes/test' % SCRIPT_DIRECTORY
TEST_DATA = collections.namedtuple('UploadDatatypesData', 'path datatype')
GALAXY_ROOT = os.path.abspath('%s/../../' % SCRIPT_DIRECTORY)
DATATYPES_CONFIG = os.path.join(GALAXY_ROOT, 'config/datatypes_conf.xml.sample')
PARENT_SNIFFER_MAP = {'fastqsolexa': 'fastq'}


def find_datatype(registry, filename):
    # match longest extension first
    sorted_extensions = sorted(registry.datatypes_by_extension.keys(), key=len, reverse=True)
    for extension in sorted_extensions:
        if filename.endswith(extension) or filename.startswith(extension):
            return registry.datatypes_by_extension[extension]
    raise Exception("Couldn't guess datatype for file '%s'" % filename)


def collect_test_data():
    registry = Registry()
    registry.load_datatypes(root_dir=GALAXY_ROOT, config=DATATYPES_CONFIG)
    test_data_description = [TEST_DATA(path=os.path.join(TEST_FILE_DIR, f),
                                       datatype=find_datatype(registry, f)
                                       ) for f in os.listdir(TEST_FILE_DIR)]
    return {os.path.basename(data.path): data for data in test_data_description}


class UploadTestDatatypeDataTestCase(BaseUploadContentConfigurationTestCase):
    framework_tool_and_types = False
    datatypes_conf_override = DATATYPES_CONFIG

    def runTest(self):
        pass


@pytest.fixture(scope='module')
def instance():
    instance = UploadTestDatatypeDataTestCase()
    instance.setUpClass()
    instance.setUp()
    yield instance
    instance.tearDownClass()


TEST_CASES = collect_test_data()


@pytest.mark.parametrize('test_data', TEST_CASES.values(), ids=list(TEST_CASES.keys()))
def test_upload_datatype_auto(instance, test_data):
    with open(test_data.path, 'rb') as content:
        if hasattr(test_data.datatype, 'sniff') or 'false' in test_data.path:
            file_type = 'auto'
        else:
            file_type = test_data.datatype.file_ext
        dataset = instance.dataset_populator.new_dataset(instance.history_id, content=content, wait=False, file_type=file_type)
    dataset = instance.dataset_populator.get_history_dataset_details(instance.history_id, dataset=dataset, assert_ok=False)
    expected_file_ext = test_data.datatype.file_ext
    if 'false' in test_data.path:
        assert dataset['file_ext'] != PARENT_SNIFFER_MAP.get(expected_file_ext, expected_file_ext)
    else:
        assert dataset['file_ext'] == PARENT_SNIFFER_MAP.get(expected_file_ext, expected_file_ext)
