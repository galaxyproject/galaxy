
import os
import pytest
import tempfile

from galaxy_test.driver import integration_util

from .test_datatype_upload import (
    TEST_CASES,
    upload_datatype_helper,
    UploadTestDatatypeDataTestCase
)

SCRIPT_DIRECTORY = os.path.abspath(os.path.dirname(__file__))
OBJECT_STORE_CONFIG_FILE = os.path.join(SCRIPT_DIRECTORY, "irods_object_store_conf.xml")
# Run test for only the first 10 test files
IRODS_TEST_CASES = dict(list(TEST_CASES.items())[0:10])


class UploadTestDatatypeDataTestCase(UploadTestDatatypeDataTestCase):

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        config["object_store_config_file"] = OBJECT_STORE_CONFIG_FILE


instance = integration_util.integration_module_instance(UploadTestDatatypeDataTestCase)


@pytest.fixture
def temp_file():
    with tempfile.NamedTemporaryFile(delete=True, mode='wb') as fh:
        yield fh


@pytest.mark.parametrize('test_data', IRODS_TEST_CASES.values(), ids=list(IRODS_TEST_CASES.keys()))
def test_upload_datatype_auto(instance, test_data, temp_file):
    upload_datatype_helper(instance, test_data, temp_file)
