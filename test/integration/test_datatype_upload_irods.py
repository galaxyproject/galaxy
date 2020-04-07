
import os
import string
import subprocess
import tempfile
import time

import pytest

from galaxy_test.driver import integration_util
from .test_datatype_upload import (
    TEST_CASES,
    upload_datatype_helper,
    UploadTestDatatypeDataTestCase
)

SCRIPT_DIRECTORY = os.path.abspath(os.path.dirname(__file__))
# Run test for only the first 10 test files
IRODS_TEST_CASES = dict(list(TEST_CASES.items())[0:10])
OBJECT_STORE_HOST = os.environ.get('GALAXY_INTEGRATION_IRODS_OBJECT_STORE_HOST', 'localhost')
OBJECT_STORE_PORT = int(os.environ.get('GALAXY_INTEGRATION_IRODS_OBJECT_STORE_PORT', 1247))
OBJECT_STORE_TIMEOUT = int(os.environ.get('GALAXY_INTEGRATION_IRODS_OBJECT_STORE_TIMEOUT', 30))
OBJECT_STORE_USERNAME = os.environ.get('GALAXY_INTEGRATION_IRODS_OBJECT_STORE_USERNAME', 'rods')
OBJECT_STORE_PASSWORD = os.environ.get('GALAXY_INTEGRATION_IRODS_OBJECT_STORE_PASSWORD', 'rods')
OBJECT_STORE_RESOURCE = os.environ.get('GALAXY_INTEGRATION_IRODS_OBJECT_STORE_RESOURCE', 'demoResc')
OBJECT_STORE_ZONE = os.environ.get('GALAXY_INTEGRATION_IRODS_OBJECT_STORE_ZONE', 'tempZone')
OBJECT_STORE_CONFIG = string.Template("""
<object_store type="irods">
    <auth username="${username}" password="${password}"/>
    <resource name="${resource}"/>
    <zone name="${zone}"/>
    <connection host="${host}" port="${port}" timeout="${timeout}"/>
    <cache path="${temp_directory}/object_store_cache" size="1000"/>
    <extra_dir type="job_work" path="${temp_directory}/job_working_directory_irods"/>
    <extra_dir type="temp" path="${temp_directory}/tmp_irods"/>
</object_store>
""")


def start_irods(container_name):
    irods_start_args = [
        'docker',
        'run',
        '-p',
        '1247:1247',
        '-d',
        '--name',
        container_name,
        'kxk302/irods-server:0.1']
    subprocess.check_call(irods_start_args)

    # Sleep so integration test's iRODS instance is up and running
    time.sleep(20)


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
        temp_directory = cls._test_driver.mkdtemp()
        cls.object_stores_parent = temp_directory
        config_path = os.path.join(temp_directory, "object_store_conf.xml")
        # This doesn't quite work yet, fails with extra_files_path
        # config["metadata_strategy"] = "extended"
        config["outpus_to_working_dir"] = True
        config["retry_metadata_internally"] = False
        with open(config_path, "w") as f:
            f.write(
                OBJECT_STORE_CONFIG.safe_substitute(
                    {
                        "temp_directory": temp_directory,
                        "host": OBJECT_STORE_HOST,
                        "port": OBJECT_STORE_PORT,
                        "timeout": OBJECT_STORE_TIMEOUT,
                        "username": OBJECT_STORE_USERNAME,
                        "password": OBJECT_STORE_PASSWORD,
                        "resource": OBJECT_STORE_RESOURCE,
                        "zone": OBJECT_STORE_ZONE,
                    }
                )
            )
        config["object_store_config_file"] = config_path


instance = integration_util.integration_module_instance(UploadTestDatatypeDataTestCase)


@pytest.fixture
def temp_file():
    with tempfile.NamedTemporaryFile(delete=True, mode='wb') as fh:
        yield fh


@pytest.mark.parametrize('test_data', IRODS_TEST_CASES.values(), ids=list(IRODS_TEST_CASES.keys()))
def test_upload_datatype_irods(instance, test_data, temp_file):
    upload_datatype_helper(instance, test_data, temp_file)
