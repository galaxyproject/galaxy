
import os
import subprocess
import tempfile

import pytest

from galaxy_test.driver import integration_util
from .test_datatype_upload import (TEST_CASES, upload_datatype_helper, UploadTestDatatypeDataTestCase)

SCRIPT_DIRECTORY = os.path.abspath(os.path.dirname(__file__))
OBJECT_STORE_CONFIG_FILE = os.path.join(SCRIPT_DIRECTORY, "irods_object_store_conf.xml")
# Run test for only the first 10 test files
IRODS_TEST_CASES = dict(list(TEST_CASES.items())[0:10])


def start_irods(container_name):
    irods_start_args = [
        'docker',
        'run',
        '-p',
        '2020:1247',
        '-d',
        '--name',
        container_name,
        'kxk302/irods-server:0.3']
    subprocess.check_call(irods_start_args)


def stop_irods(container_name):
    subprocess.check_call(['docker', 'rm', '-f', container_name])


class UploadTestDatatypeDataTestCase(UploadTestDatatypeDataTestCase):

    @classmethod
    def setUpClass(cls):
        cls.container_name = "%s_container" % cls.__name__
        start_irods(cls.container_name)
        super(UploadTestDatatypeDataTestCase, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        stop_irods(cls.container_name)
        super(UploadTestDatatypeDataTestCase, cls).tearDownClass()

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        config["object_store_config_file"] = OBJECT_STORE_CONFIG_FILE


instance = integration_util.integration_module_instance(UploadTestDatatypeDataTestCase)


@pytest.fixture
def temp_file():
    with tempfile.NamedTemporaryFile(delete=True, mode='wb') as fh:
        yield fh


@pytest.mark.parametrize('test_data', IRODS_TEST_CASES.values(), ids=list(IRODS_TEST_CASES.keys()))
def test_upload_datatype_irods(instance, test_data, temp_file):
    upload_datatype_helper(instance, test_data, temp_file)
