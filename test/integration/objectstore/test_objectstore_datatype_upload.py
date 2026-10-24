"""Tests objectstores by exercising the datatype upload integration tests."""

import os
import string
import subprocess
import time
from typing import Optional

import pytest

from galaxy.objectstore.irods import IRODSObjectStore
from galaxy_test.driver import integration_util
from ..test_datatype_upload import (
    DatatypeUploadCase,
    TEST_CASES,
    upload_datatype_helper,
    upload_datatypes,
    UploadTestDatatypeDataIntegrationInstance,
    verify_datatype_upload,
)

REFRESH_TIME = 3
CONNECTION_POOL_MONITOR_INTERVAL = 6
SCRIPT_DIRECTORY = os.path.abspath(os.path.dirname(__file__))
IRODS_OBJECT_STORE_HOST = os.environ.get("GALAXY_INTEGRATION_IRODS_OBJECT_STORE_HOST", "localhost")
IRODS_OBJECT_STORE_PORT = int(os.environ.get("GALAXY_INTEGRATION_IRODS_OBJECT_STORE_PORT", 1247))
IRODS_OBJECT_STORE_TIMEOUT = int(os.environ.get("GALAXY_INTEGRATION_IRODS_OBJECT_STORE_TIMEOUT", 30))
IRODS_OBJECT_STORE_REFRESH_TIME = int(
    os.environ.get("GALAXY_INTEGRATION_IRODS_OBJECT_STORE_REFRESH_TIME", REFRESH_TIME)
)
IRODS_OBJECT_STORE_CONNECTION_POOL_MONITOR_INTERVAL = int(
    os.environ.get(
        "GALAXY_INTEGRATION_IRODS_OBJECT_STORE_CONNECTION_POOL_MONITOR_INTERVAL", CONNECTION_POOL_MONITOR_INTERVAL
    )
)
IRODS_OBJECT_STORE_USERNAME = os.environ.get("GALAXY_INTEGRATION_IRODS_OBJECT_STORE_USERNAME", "rods")
IRODS_OBJECT_STORE_PASSWORD = os.environ.get("GALAXY_INTEGRATION_IRODS_OBJECT_STORE_PASSWORD", "rods")
IRODS_OBJECT_STORE_RESOURCE = os.environ.get("GALAXY_INTEGRATION_IRODS_OBJECT_STORE_RESOURCE", "demoResc")
IRODS_OBJECT_STORE_ZONE = os.environ.get("GALAXY_INTEGRATION_IRODS_OBJECT_STORE_ZONE", "tempZone")
# Run test for only the first 10 test files
TEST_CASES = dict(list(TEST_CASES.items())[0:10])
SINGLE_TEST_CASE = dict(list(TEST_CASES.items())[0:1])
DISTRIBUTED_OBJECT_STORE_CONFIG = string.Template("""
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
""")
DISTRIBUTED_IRODS_OBJECT_STORE_CONFIG = string.Template("""
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
            <connection host="${host}" port="${port}" timeout="${timeout}" refresh_time="${refresh_time}"  connection_pool_monitor_interval="${connection_pool_monitor_interval}"/>
            <cache path="${temp_directory}/object_store_cache" size="1000"/>
            <extra_dir type="job_work" path="${temp_directory}/job_working_directory_irods"/>
            <extra_dir type="temp" path="${temp_directory}/tmp_irods"/>
        </backend>
    </backends>
</object_store>
""")
IRODS_OBJECT_STORE_CONFIG = string.Template("""<object_store type="irods">
    <auth username="${username}" password="${password}"/>
    <resource name="${resource}"/>
    <zone name="${zone}"/>
    <connection host="${host}" port="${port}" timeout="${timeout}" refresh_time="${refresh_time}" connection_pool_monitor_interval="${connection_pool_monitor_interval}"/>
    <cache path="${temp_directory}/object_store_cache" size="1000"/>
    <extra_dir type="job_work" path="${temp_directory}/job_working_directory_irods"/>
    <extra_dir type="temp" path="${temp_directory}/tmp_irods"/>
</object_store>
""")


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


class BaseObjectstoreUploadIntegrationInstance(UploadTestDatatypeDataIntegrationInstance):
    object_store_template: Optional[string.Template] = None

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        temp_directory = cls._test_driver.mkdtemp()
        cls.object_stores_parent = temp_directory
        cls.object_store_config_path = os.path.join(temp_directory, "object_store_conf.xml")
        config["metadata_strategy"] = "extended"
        config["outputs_to_working_directory"] = True
        config["retry_metadata_internally"] = False
        config["object_store_store_by"] = "uuid"
        with open(cls.object_store_config_path, "w") as f:
            f.write(cls.object_store_template.safe_substitute(**cls.get_object_store_kwargs()))
        config["object_store_config_file"] = cls.object_store_config_path

    @classmethod
    def get_object_store_kwargs(cls):
        return {}


class IrodsUploadTestDatatypeDataIntegrationInstance(BaseObjectstoreUploadIntegrationInstance):
    object_store_template = IRODS_OBJECT_STORE_CONFIG

    @classmethod
    def setUpClass(cls):
        cls.container_name = "irods_integration_container"
        start_irods(cls.container_name)
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        stop_irods(cls.container_name)
        super().tearDownClass()

    @classmethod
    def get_object_store_kwargs(cls):
        return {
            "temp_directory": cls.object_stores_parent,
            "host": IRODS_OBJECT_STORE_HOST,
            "port": IRODS_OBJECT_STORE_PORT,
            "timeout": IRODS_OBJECT_STORE_TIMEOUT,
            "refresh_time": IRODS_OBJECT_STORE_REFRESH_TIME,
            "connection_pool_monitor_interval": IRODS_OBJECT_STORE_CONNECTION_POOL_MONITOR_INTERVAL,
            "username": IRODS_OBJECT_STORE_USERNAME,
            "password": IRODS_OBJECT_STORE_PASSWORD,
            "resource": IRODS_OBJECT_STORE_RESOURCE,
            "zone": IRODS_OBJECT_STORE_ZONE,
        }


class IrodsIdleConnectionUploadIntegrationInstance(IrodsUploadTestDatatypeDataIntegrationInstance):
    object_store_template = IRODS_OBJECT_STORE_CONFIG


class UploadTestDosDiskAndDiskIntegrationInstance(BaseObjectstoreUploadIntegrationInstance):
    object_store_template = DISTRIBUTED_OBJECT_STORE_CONFIG

    @classmethod
    def get_object_store_kwargs(cls):
        return {"temp_directory": cls.object_stores_parent}


class UploadTestDosIrodsAndDiskIntegrationInstance(IrodsUploadTestDatatypeDataIntegrationInstance):
    object_store_template = DISTRIBUTED_IRODS_OBJECT_STORE_CONFIG


distributed_instance = integration_util.integration_module_instance(UploadTestDosDiskAndDiskIntegrationInstance)
irods_instance = integration_util.integration_module_instance(IrodsUploadTestDatatypeDataIntegrationInstance)
distributed_and_irods_instance = integration_util.integration_module_instance(
    UploadTestDosIrodsAndDiskIntegrationInstance
)
idle_connection_irods_instance = integration_util.integration_module_instance(
    IrodsIdleConnectionUploadIntegrationInstance
)


def upload_to_new_history(instance: UploadTestDatatypeDataIntegrationInstance):
    # Not test_history(), whose cleanup runs at module teardown: by then a newer Galaxy
    # instance has started in this process, and older ones answer API requests with 401.
    history_id = instance.dataset_populator.new_history()
    return history_id, upload_datatypes(instance, TEST_CASES.values(), history_id)


@pytest.fixture(scope="module")
def distributed_datasets(distributed_instance: UploadTestDosDiskAndDiskIntegrationInstance):
    return upload_to_new_history(distributed_instance)


@pytest.fixture(scope="module")
def irods_datasets(irods_instance: IrodsUploadTestDatatypeDataIntegrationInstance):
    return upload_to_new_history(irods_instance)


@pytest.fixture(scope="module")
def distributed_and_irods_datasets(distributed_and_irods_instance: UploadTestDosIrodsAndDiskIntegrationInstance):
    return upload_to_new_history(distributed_and_irods_instance)


@pytest.mark.parametrize("test_data", TEST_CASES.values(), ids=list(TEST_CASES.keys()))
def test_upload_datatype_dos_disk_and_disk(
    distributed_instance: UploadTestDosDiskAndDiskIntegrationInstance,
    distributed_datasets,
    test_data: DatatypeUploadCase,
    temp_file,
) -> None:
    history_id, datasets = distributed_datasets
    dataset = datasets[os.path.basename(test_data.path)]
    verify_datatype_upload(distributed_instance, test_data, temp_file, history_id, dataset)


@pytest.mark.parametrize("test_data", TEST_CASES.values(), ids=list(TEST_CASES.keys()))
def test_upload_datatype_irods(
    irods_instance: IrodsUploadTestDatatypeDataIntegrationInstance,
    irods_datasets,
    test_data: DatatypeUploadCase,
    temp_file,
) -> None:
    history_id, datasets = irods_datasets
    dataset = datasets[os.path.basename(test_data.path)]
    verify_datatype_upload(irods_instance, test_data, temp_file, history_id, dataset, delete_cache_dir=True)


@pytest.mark.parametrize("test_data", TEST_CASES.values(), ids=list(TEST_CASES.keys()))
def test_upload_datatype_dos_irods_and_disk(
    distributed_and_irods_instance: UploadTestDosIrodsAndDiskIntegrationInstance,
    distributed_and_irods_datasets,
    test_data: DatatypeUploadCase,
    temp_file,
) -> None:
    history_id, datasets = distributed_and_irods_datasets
    dataset = datasets[os.path.basename(test_data.path)]
    verify_datatype_upload(distributed_and_irods_instance, test_data, temp_file, history_id, dataset)


@pytest.mark.parametrize("test_data", SINGLE_TEST_CASE.values(), ids=list(SINGLE_TEST_CASE.keys()))
def test_upload_datatype_irods_idle_connections(
    idle_connection_irods_instance: IrodsIdleConnectionUploadIntegrationInstance,
    test_data: DatatypeUploadCase,
    temp_file,
) -> None:
    with idle_connection_irods_instance.dataset_populator.test_history() as history_id:
        upload_datatype_helper(idle_connection_irods_instance, test_data, temp_file, history_id, True)

    # Get Irods object store's connection pool
    assert idle_connection_irods_instance._test_driver.app
    assert isinstance(idle_connection_irods_instance._test_driver.app.object_store, IRODSObjectStore)
    connection_pool = idle_connection_irods_instance._test_driver.app.object_store.session.pool

    # Verify the connection pool has 0 active and 1 idle connections
    assert len(connection_pool.active) == 0
    assert len(connection_pool.idle) in [1, 2]

    # Wait for the idle connection to turn stale
    time.sleep(REFRESH_TIME)

    # Wait for the connection pool monitor thread to run and reclaim the stale idle connection
    time.sleep(CONNECTION_POOL_MONITOR_INTERVAL)

    # Check that the stale idle connection has been reclaimed
    assert len(connection_pool.active) == 0
    assert len(connection_pool.idle) == 0
