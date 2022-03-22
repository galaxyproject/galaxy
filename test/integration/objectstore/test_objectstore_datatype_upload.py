"""Tests objectstores by exercising the datatype upload integration tests."""
import os
import string
import subprocess
import time
from typing import Optional

import pytest

from galaxy_test.driver import integration_util
from ..test_datatype_upload import (
    TEST_CASES,
    upload_datatype_helper,
    UploadTestDatatypeDataTestCase,
)

SCRIPT_DIRECTORY = os.path.abspath(os.path.dirname(__file__))
IRODS_OBJECT_STORE_HOST = os.environ.get("GALAXY_INTEGRATION_IRODS_OBJECT_STORE_HOST", "localhost")
IRODS_OBJECT_STORE_PORT = int(os.environ.get("GALAXY_INTEGRATION_IRODS_OBJECT_STORE_PORT", 1247))
IRODS_OBJECT_STORE_TIMEOUT = int(os.environ.get("GALAXY_INTEGRATION_IRODS_OBJECT_STORE_TIMEOUT", 30))
IRODS_OBJECT_STORE_POOLSIZE = int(os.environ.get("GALAXY_INTEGRATION_IRODS_OBJECT_STORE_POOLSIZE", 3))
IRODS_OBJECT_STORE_USERNAME = os.environ.get("GALAXY_INTEGRATION_IRODS_OBJECT_STORE_USERNAME", "rods")
IRODS_OBJECT_STORE_PASSWORD = os.environ.get("GALAXY_INTEGRATION_IRODS_OBJECT_STORE_PASSWORD", "rods")
IRODS_OBJECT_STORE_RESOURCE = os.environ.get("GALAXY_INTEGRATION_IRODS_OBJECT_STORE_RESOURCE", "demoResc")
IRODS_OBJECT_STORE_ZONE = os.environ.get("GALAXY_INTEGRATION_IRODS_OBJECT_STORE_ZONE", "tempZone")
# Run test for only the first 10 test files
TEST_CASES = dict(list(TEST_CASES.items())[0:10])
DISTRIBUTED_OBJECT_STORE_CONFIG = string.Template(
    """
<object_store type="distributed">
    <backends>
        <backend id="files1" type="disk" weight="1">
            <files_dir path="${temp_directory}/database/files1"/>
            <extra_dir type="temp" path="${temp_directory}/database/tmp1"/>
            <extra_dir type="job_work" path="${temp_directory}/database/job_working_directory1"/>
        </backend>
        <backend id="files2" type="disk" weight="1">
            <files_dir path="${temp_directory}/database/files2"/>
            <extra_dir type="temp" path="${temp_directory}/database/tmp2"/>
            <extra_dir type="job_work" path="${temp_directory}/database/job_working_directory2"/>
        </backend>
    </backends>
</object_store>
"""
)
DISTRIBUTED_IRODS_OBJECT_STORE_CONFIG = string.Template(
    """
<object_store type="distributed">
    <backends>
        <backend id="files1" type="disk" weight="1">
            <files_dir path="${temp_directory}/database/files1"/>
            <extra_dir type="temp" path="${temp_directory}/database/tmp1"/>
            <extra_dir type="job_work" path="${temp_directory}/database/job_working_directory1"/>
        </backend>
        <backend id="files2" type="irods" weight="1">
            <auth username="${username}" password="${password}"/>
            <resource name="${resource}"/>
            <zone name="${zone}"/>
            <connection host="${host}" port="${port}" timeout="${timeout}" poolsize="${poolsize}"/>
            <cache path="${temp_directory}/object_store_cache" size="1000"/>
            <extra_dir type="job_work" path="${temp_directory}/job_working_directory_irods"/>
            <extra_dir type="temp" path="${temp_directory}/tmp_irods"/>
        </backend>
    </backends>
</object_store>
"""
)
IRODS_OBJECT_STORE_CONFIG = string.Template(
    """<object_store type="irods">
    <auth username="${username}" password="${password}"/>
    <resource name="${resource}"/>
    <zone name="${zone}"/>
    <connection host="${host}" port="${port}" timeout="${timeout}" poolsize="${poolsize}"/>
    <cache path="${temp_directory}/object_store_cache" size="1000"/>
    <extra_dir type="job_work" path="${temp_directory}/job_working_directory_irods"/>
    <extra_dir type="temp" path="${temp_directory}/tmp_irods"/>
</object_store>
"""
)


def check_container_active(container_name):
    return subprocess.call(["docker", "inspect", "-f", "{{.State.Running}}", container_name]) == 0


def start_irods(container_name):
    if not check_container_active(container_name):
        irods_start_args = [
            "docker",
            "run",
            "-p",
            "1247:1247",
            "-d",
            "--name",
            container_name,
            "kxk302/irods-server:0.1",
        ]
        subprocess.check_call(irods_start_args)

        # Sleep so integration test's iRODS instance is up and running
        time.sleep(20)


def stop_irods(container_name):
    if check_container_active(container_name):
        subprocess.check_call(["docker", "rm", "-f", container_name])


class BaseObjectstoreUploadTest(UploadTestDatatypeDataTestCase):

    object_store_template: Optional[string.Template] = None

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        temp_directory = cls._test_driver.mkdtemp()
        cls.object_stores_parent = temp_directory
        cls.object_store_config_path = os.path.join(temp_directory, "object_store_conf.xml")
        config["metadata_strategy"] = "extended"
        config["outpus_to_working_dir"] = True
        config["retry_metadata_internally"] = False
        config["object_store_store_by"] = "uuid"
        with open(cls.object_store_config_path, "w") as f:
            f.write(cls.object_store_template.safe_substitute(**cls.get_object_store_kwargs()))
        config["object_store_config_file"] = cls.object_store_config_path

    @classmethod
    def get_object_store_kwargs(cls):
        return {}


class IrodsUploadTestDatatypeDataTestCase(BaseObjectstoreUploadTest):

    object_store_template = IRODS_OBJECT_STORE_CONFIG

    @classmethod
    def setUpClass(cls):
        cls.container_name = "irods_integration_container"
        start_irods(cls.container_name)
        super(UploadTestDatatypeDataTestCase, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        stop_irods(cls.container_name)
        super(UploadTestDatatypeDataTestCase, cls).tearDownClass()

    @classmethod
    def get_object_store_kwargs(cls):
        return {
            "temp_directory": cls.object_stores_parent,
            "host": IRODS_OBJECT_STORE_HOST,
            "port": IRODS_OBJECT_STORE_PORT,
            "timeout": IRODS_OBJECT_STORE_TIMEOUT,
            "poolsize": IRODS_OBJECT_STORE_POOLSIZE,
            "username": IRODS_OBJECT_STORE_USERNAME,
            "password": IRODS_OBJECT_STORE_PASSWORD,
            "resource": IRODS_OBJECT_STORE_RESOURCE,
            "zone": IRODS_OBJECT_STORE_ZONE,
        }


class UploadTestDosDiskAndDiskTestCase(BaseObjectstoreUploadTest):

    object_store_template = DISTRIBUTED_OBJECT_STORE_CONFIG

    @classmethod
    def get_object_store_kwargs(cls):
        return {"temp_directory": cls.object_stores_parent}


class UploadTestDosIrodsAndDiskTestCase(IrodsUploadTestDatatypeDataTestCase):

    object_store_template = DISTRIBUTED_IRODS_OBJECT_STORE_CONFIG


distributed_instance = integration_util.integration_module_instance(UploadTestDosDiskAndDiskTestCase)
irods_instance = integration_util.integration_module_instance(IrodsUploadTestDatatypeDataTestCase)
distributed_and_irods_instance = integration_util.integration_module_instance(UploadTestDosIrodsAndDiskTestCase)


@pytest.mark.parametrize("test_data", TEST_CASES.values(), ids=list(TEST_CASES.keys()))
def test_upload_datatype_dos_disk_and_disk(distributed_instance, test_data, temp_file):
    upload_datatype_helper(distributed_instance, test_data, temp_file)


@pytest.mark.parametrize("test_data", TEST_CASES.values(), ids=list(TEST_CASES.keys()))
def test_upload_datatype_irods(irods_instance, test_data, temp_file):
    upload_datatype_helper(irods_instance, test_data, temp_file, True)


@pytest.mark.parametrize("test_data", TEST_CASES.values(), ids=list(TEST_CASES.keys()))
def test_upload_datatype_dos_irods_and_disk(distributed_and_irods_instance, test_data, temp_file):
    upload_datatype_helper(distributed_and_irods_instance, test_data, temp_file)
