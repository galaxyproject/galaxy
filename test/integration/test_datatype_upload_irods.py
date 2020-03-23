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
from .test_datatype_upload import upload_datatype_helper

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
    upload_datatype_helper(instance, test_data, temp_file)