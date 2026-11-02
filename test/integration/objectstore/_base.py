import os
import random
import string
import subprocess
import time
from collections.abc import Callable
from typing import (
    Any,
    TYPE_CHECKING,
)
from unittest import SkipTest

import boto3
import pytest
from botocore.client import Config
from botocore.exceptions import (
    BotoCoreError,
    ClientError,
)

from galaxy.exceptions import ObjectNotFound
from galaxy.model import (
    Dataset,
    HistoryDatasetAssociation,
)
from galaxy.objectstore import ObjectStore
from galaxy_test.base.populators import DatasetPopulator
from galaxy_test.driver import integration_util
from galaxy_test.driver.integration_util import (
    docker_exec,
    docker_ip_address,
    docker_rm,
    docker_run,
)

if TYPE_CHECKING:
    from galaxy.app import UniverseApplication

OBJECT_STORE_HOST = os.environ.get("GALAXY_INTEGRATION_OBJECT_STORE_HOST", "127.0.0.1")
# Each pytest-xdist worker publishes its object store container on its own host port. The default
# base sits outside the 8000-10000 range Galaxy test servers pick their ports from (see
# galaxy_test.driver.driver_util) and below the kernel's ephemeral port range.
OBJECT_STORE_PORT = int(os.environ.get("GALAXY_INTEGRATION_OBJECT_STORE_PORT", 18333)) + int(
    os.environ.get("PYTEST_XDIST_WORKER", "gw0").removeprefix("gw")
)
OBJECT_STORE_ACCESS_KEY = os.environ.get("GALAXY_INTEGRATION_OBJECT_STORE_ACCESS_KEY", "admin")
OBJECT_STORE_SECRET_KEY = os.environ.get("GALAXY_INTEGRATION_OBJECT_STORE_SECRET_KEY", "admin")
OBJECT_STORE_RUCIO_ACCOUNT = os.environ.get("GALAXY_INTEGRATION_OBJECT_STORE_RUCIO_ACCOUNT", "root")
OBJECT_STORE_RUCIO_USERNAME = os.environ.get("GALAXY_INTEGRATION_OBJECT_STORE_RUCIO_USERNAME", "rucio")
OBJECT_STORE_RUCIO_RSE_NAME = "TEST"
OBJECT_STORE_RUCIO_ACCESS = os.environ.get("GALAXY_INTEGRATION_OBJECT_STORE_RUCIO_ACCESS", "rucio")
OBJECT_STORE_RUCIO_IMAGE = os.environ.get(
    "GALAXY_INTEGRATION_OBJECT_STORE_RUCIO_IMAGE", "savannah.ornl.gov/ndip/public-docker/rucio:40.2.0-pg"
)

OBJECT_STORE_CONFIG = string.Template("""
<object_store type="hierarchical" id="primary">
    <backends>
        <object_store id="swifty" type="boto3" weight="1" order="0">
            <auth access_key="${access_key}" secret_key="${secret_key}" />
            <bucket name="galaxy" />
            <connection endpoint_url="http://${host}:${port}" region="us-east-1" />
            <cache path="${temp_directory}/object_store_cache" size="1000" cache_updated_data="${cache_updated_data}" />
            <extra_dir type="job_work" path="${temp_directory}/job_working_directory_swift"/>
            <extra_dir type="temp" path="${temp_directory}/tmp_swift"/>
        </object_store>
    </backends>
</object_store>
""")
CLOUD_OBJECT_STORE_CONFIG = string.Template("""
type: cloud
provider: aws
auth:
  access_key: ${access_key}
  secret_key: ${secret_key}

bucket:
  name: galaxy

connection:
  endpoint_url: http://${host}:${port}

transfer:
  multipart_threshold: 5242880
  multipart_chunksize: 5242880
  max_concurrency: 2

cache:
  path: ${temp_directory}/object_store_cache
  size: 1000
  cache_updated_data: ${cache_updated_data}

extra_dirs:
- type: job_work
  path: ${temp_directory}/job_working_directory_cloud
- type: temp
  path: ${temp_directory}/tmp_cloud
""")
RUCIO_OBJECT_STORE_CONFIG = string.Template("""
    type: rucio
    upload_rse_name: ${rucio_rse}
    upload_scheme: file
    register_only: false
    download_schemes:
      - rse: ${rucio_rse}
        scheme: file
        ignore_checksum: false
    scope: galaxy
    host: http://${host}:${port}
    account: ${rucio_account}
    auth_host: http://${host}:${port}
    username: ${rucio_username}
    password: ${rucio_password}
    auth_type: userpass
    cache:
      path: ${temp_directory}/object_store_cache
      size: 1000
      cache_updated_data: ${cache_updated_data}
""")
AZURE_OBJECT_STORE_CONFIG = string.Template("""
type: distributed
backends:
- type: azure_blob
  id: azure1
  name: Azure Store 1
  allow_selection: true
  weight: 1
  auth:
    account_name: ${account_name}
    account_key: ${account_key}

  container:
    name: ${container_name}

  extra_dirs:
  - type: job_work
    path: "${temp_directory}/database/job_working_directory_azure_1"
  - type: temp
    path: "${temp_directory}/database/tmp_azure_1"
- type: azure_blob
  id: azure2
  name: Azure Store 2
  allow_selection: true
  weight: 1
  auth:
    account_name: ${account_name}
    account_key: ${account_key}

  container:
    name: ${container_name}

  extra_dirs:
  - type: job_work
    path: "${temp_directory}/database/job_working_directory_azure_2"
  - type: temp
    path: "${temp_directory}/database/tmp_azure_2"
""")

# Onedata setup for the test is done according to this documentation:
# https://onedata.org/#/home/documentation/topic/stable/demo-mode
ONEDATA_DEMO_SPACE_NAME = "demo-space"
ONEDATA_OBJECT_STORE_CONFIG = string.Template("""
<object_store type="onedata">
    <auth access_token="${access_token}" />
    <connection onezone_domain="${onezone_domain}" disable_tls_certificate_validation="True"/>
    <space name="${space_name}" ${optional_space_params} />
    <cache path="${temp_directory}/object_store_cache" size="1000" cache_updated_data="${cache_updated_data}" />
    <extra_dir type="job_work" path="${temp_directory}/job_working_directory_onedata"/>
    <extra_dir type="temp" path="${temp_directory}/tmp_onedata"/>
</object_store>
""")


def wait_rucio_ready(container_name):
    timeout = 30
    start_time = time.time()
    rse = None
    while True:
        try:
            rse = docker_exec(container_name, "rucio", "list-rses").decode("utf-8").strip()
            if rse == OBJECT_STORE_RUCIO_RSE_NAME:
                return
        except subprocess.CalledProcessError:
            pass
        if time.time() - start_time >= timeout:
            raise TimeoutError(f"cannot start Rucio {rse}")
        time.sleep(1)


def start_rucio(container_name):
    ports = [(OBJECT_STORE_PORT, 80)]
    try:
        docker_run(OBJECT_STORE_RUCIO_IMAGE, container_name, ports=ports)
    except subprocess.CalledProcessError as e:
        raise SkipTest(f"cannot start Rucio container: {e}")

    try:
        wait_rucio_ready(container_name)
    except TimeoutError as e:
        docker_rm(container_name)
        raise SkipTest(str(e))


class BaseObjectStoreIntegrationTestCase(integration_util.IntegrationTestCase, integration_util.ConfiguresObjectStores):
    dataset_populator: DatasetPopulator
    framework_tool_and_types = True

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)

    def upload_dataset_and_wait_for_hash(self, history_id: str, **new_dataset_kwds) -> dict[str, Any]:
        """Upload a dataset and block until its ``compute_dataset_hash`` task has run.

        The upload job is visible as terminal before ``JobWrapper.finish`` dispatches that task,
        and the task reads the dataset file, pulling it back into the object store cache if it is
        no longer there. A test that evicts cache files and then counts them must not leave the
        task pending, or it (or the next test in the class) sees a stray file.
        """
        hda = self.dataset_populator.new_dataset(history_id, wait=True, **new_dataset_kwds)
        self.dataset_populator.wait_for_dataset_hashes(history_id, hda["id"])
        return hda


def get_files(directory):
    for rel_directory, _, files in os.walk(directory):
        for file_ in files:
            yield os.path.join(rel_directory, file_)


def files_count(directory):
    return sum(1 for _ in get_files(directory))


@integration_util.skip_unless_docker()
class BaseSeaweedFSObjectStoreIntegrationTestCase(BaseObjectStoreIntegrationTestCase):
    """A store backed by a disposable SeaweedFS container.

    Subclasses supply the store configuration; everything else -- container
    lifecycle, temp directories and the metadata settings the object store
    tests need -- is shared.
    """

    object_store_config = OBJECT_STORE_CONFIG
    object_store_config_filename = "object_store_conf.xml"
    object_store_cache_path: str

    @classmethod
    def setUpClass(cls):
        cls.container_name = f"{cls.__name__}_container"
        start_seaweedfs(cls.container_name)
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        docker_rm(cls.container_name)
        super().tearDownClass()

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        temp_directory = cls._test_driver.mkdtemp()
        cls.object_stores_parent = temp_directory
        cls.object_store_cache_path = os.path.join(temp_directory, "object_store_cache")
        config_path = os.path.join(temp_directory, cls.object_store_config_filename)
        config["object_store_store_by"] = "uuid"
        config["metadata_strategy"] = "extended"
        config["outputs_to_working_directory"] = True
        config["retry_metadata_internally"] = False
        with open(config_path, "w") as f:
            f.write(
                cls.object_store_config.safe_substitute(
                    {
                        "temp_directory": temp_directory,
                        "host": OBJECT_STORE_HOST,
                        "port": OBJECT_STORE_PORT,
                        "access_key": OBJECT_STORE_ACCESS_KEY,
                        "secret_key": OBJECT_STORE_SECRET_KEY,
                        "cache_updated_data": cls.updateCacheData(),
                    }
                )
            )
        config["object_store_config_file"] = config_path

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)

    @classmethod
    def updateCacheData(cls):
        return True


# The shared default is the S3-style XML configuration the swift tests use.
BaseSwiftObjectStoreIntegrationTestCase = BaseSeaweedFSObjectStoreIntegrationTestCase


@integration_util.skip_unless_docker()
class BaseCloudObjectStoreIntegrationTestCase(BaseSeaweedFSObjectStoreIntegrationTestCase):
    """The cloudbridge-based cloud store.

    The transfer block keeps the multipart threshold at the 5 MiB provider
    minimum so modest test datasets exercise the multipart upload path.
    """

    object_store_config = CLOUD_OBJECT_STORE_CONFIG
    object_store_config_filename = "object_store_conf.yml"


class GetDataHeadTests:
    """``get_data_head`` against SeaweedFS; mix into a SeaweedFS-backed test case."""

    dataset_populator: DatasetPopulator
    upload_dataset_and_wait_for_hash: Callable[..., dict[str, Any]]

    if TYPE_CHECKING:

        @property
        def _app(self) -> "UniverseApplication": ...

    def _get_data_head_store(self) -> ObjectStore:
        """The store whose own handling of a missing object is tested."""
        return self._app.object_store

    def _upload_for_head(self, content: str) -> Dataset:
        history_id = self.dataset_populator.new_history()
        hda = self.upload_dataset_and_wait_for_hash(history_id, content=content)
        hda_model = self._app.model.session.get(HistoryDatasetAssociation, self._app.security.decode_id(hda["id"]))
        assert hda_model and hda_model.dataset
        return hda_model.dataset

    def test_get_data_head_reads_the_bucket_instead_of_a_stale_empty_cached_copy(self):
        dataset = self._upload_for_head("head-me")
        cache_path = self._app.object_store.get_filename(dataset, sync_cache=False)
        # As left by creating the dataset on a host that did not write its data.
        open(cache_path, "wb").close()

        assert self._app.object_store.get_data_head(dataset, 4) == b"head"
        assert self._app.object_store.get_data_head(dataset, 100) == b"head-me\n"
        assert os.path.getsize(cache_path) == 0

    def test_get_data_head_reads_nothing_from_an_empty_dataset(self):
        dataset = self._upload_for_head("")

        assert self._app.object_store.get_data_head(dataset, 10) == b""

    def test_get_data_head_fails_for_a_missing_object(self):
        with pytest.raises(ObjectNotFound):
            self._get_data_head_store().get_data_head(Dataset(), 10)


class BaseAzureObjectStoreIntegrationTestCase(
    BaseObjectStoreIntegrationTestCase, integration_util.ConfiguresWorkflowScheduling
):
    object_store_cache_path: str

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        # disabling workflow scheduling to limit database locking when
        # testing without postgres.
        cls._disable_workflow_scheduling(config)
        temp_directory = cls._test_driver.mkdtemp()
        cls.object_stores_parent = temp_directory
        cls.object_store_cache_path = os.path.join(temp_directory, "object_store_cache")
        config_path = os.path.join(temp_directory, "object_store_conf.yml")
        config["object_store_store_by"] = "uuid"
        config["metadata_strategy"] = "extended"
        config["outputs_to_working_directory"] = True
        config["retry_metadata_internally"] = False
        with open(config_path, "w") as f:
            f.write(
                AZURE_OBJECT_STORE_CONFIG.safe_substitute(
                    {
                        "temp_directory": temp_directory,
                        "account_name": os.environ["GALAXY_TEST_AZURE_ACCOUNT_NAME"],
                        "account_key": os.environ["GALAXY_TEST_AZURE_ACCOUNT_KEY"],
                        "container_name": os.environ["GALAXY_TEST_AZURE_CONTAINER_NAME"],
                    }
                )
            )
        config["object_store_config_file"] = config_path

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)

    @classmethod
    def updateCacheData(cls):
        return True


@integration_util.skip_unless_docker()
class BaseRucioObjectStoreIntegrationTestCase(BaseObjectStoreIntegrationTestCase):
    object_store_cache_path: str

    @classmethod
    def setUpClass(cls):
        cls.container_name = f"{cls.__name__}_container"
        start_rucio(cls.container_name)
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        docker_rm(cls.container_name)
        super().tearDownClass()

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        temp_directory = cls._test_driver.mkdtemp()
        cls.object_stores_parent = temp_directory
        cls.object_store_cache_path = os.path.join(temp_directory, "object_store_cache")
        config_path = os.path.join(temp_directory, "object_store_conf.yml")
        config["object_store_store_by"] = "uuid"
        config["metadata_strategy"] = "extended"
        config["outputs_to_working_directory"] = True
        config["retry_metadata_internally"] = False
        with open(config_path, "w") as f:
            f.write(
                RUCIO_OBJECT_STORE_CONFIG.safe_substitute(
                    {
                        "temp_directory": temp_directory,
                        "host": OBJECT_STORE_HOST,
                        "port": OBJECT_STORE_PORT,
                        "rucio_account": OBJECT_STORE_RUCIO_ACCOUNT,
                        "rucio_username": OBJECT_STORE_RUCIO_USERNAME,
                        "rucio_password": OBJECT_STORE_RUCIO_ACCESS,
                        "rucio_rse": OBJECT_STORE_RUCIO_RSE_NAME,
                        "cache_updated_data": cls.updateCacheData(),
                    }
                )
            )
        config["object_store_config_file"] = config_path

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)

    @classmethod
    def updateCacheData(cls):
        return True


@integration_util.skip_unless_docker()
class BaseOnedataObjectStoreIntegrationTestCase(BaseObjectStoreIntegrationTestCase):
    object_store_cache_path: str

    @classmethod
    def setUpClass(cls):
        cls.oz_container_name = f"{cls.__name__}_oz_container"
        cls.op_container_name = f"{cls.__name__}_op_container"

        start_onezone(cls.oz_container_name)

        oz_ip_address = docker_ip_address(cls.oz_container_name)
        start_oneprovider(cls.op_container_name, oz_ip_address)
        await_oneprovider_demo_readiness(cls.op_container_name)

        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        docker_rm(cls.op_container_name)
        docker_rm(cls.oz_container_name)

        super().tearDownClass()

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        temp_directory = cls._test_driver.mkdtemp()
        cls.object_stores_parent = temp_directory
        cls.object_store_cache_path = os.path.join(temp_directory, "object_store_cache")
        config_path = os.path.join(temp_directory, "object_store_conf.xml")
        config["object_store_store_by"] = "uuid"
        config["metadata_strategy"] = "extended"
        config["outputs_to_working_directory"] = True
        config["retry_metadata_internally"] = False
        with open(config_path, "w") as f:
            f.write(
                ONEDATA_OBJECT_STORE_CONFIG.safe_substitute(
                    {
                        "temp_directory": temp_directory,
                        "access_token": get_onedata_access_token(cls.oz_container_name),
                        "onezone_domain": docker_ip_address(cls.oz_container_name),
                        "space_name": ONEDATA_DEMO_SPACE_NAME,
                        "optional_space_params": random.choice(["", 'path=""', 'path="a/b/c/d"']),
                        "cache_updated_data": cls.updateCacheData(),
                    }
                )
            )

        config["object_store_config_file"] = config_path

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)

    @classmethod
    def updateCacheData(cls):
        return True


def start_seaweedfs(container_name):
    ports = [(OBJECT_STORE_PORT, 8333)]
    docker_run("chrislusf/seaweedfs:latest", container_name, "server", "-s3", ports=ports)
    wait_seaweedfs_ready()


def wait_seaweedfs_ready(bucket: str = "galaxy", timeout: float = 60) -> None:
    """Block until the SeaweedFS S3 gateway accepts requests and ``bucket`` exists.

    The gateway comes up a few seconds after the container does, and the object store
    initialization in Galaxy does not retry, so wait for the whole master -> volume -> filer -> s3
    chain to be up by creating the bucket through it.
    """
    s3 = boto3.client(
        "s3",
        endpoint_url=f"http://{OBJECT_STORE_HOST}:{OBJECT_STORE_PORT}",
        aws_access_key_id=OBJECT_STORE_ACCESS_KEY,
        aws_secret_access_key=OBJECT_STORE_SECRET_KEY,
        region_name="us-east-1",
        config=Config(signature_version="s3v4", retries={"max_attempts": 1}, connect_timeout=2, read_timeout=5),
    )
    deadline = time.monotonic() + timeout
    while True:
        try:
            s3.create_bucket(Bucket=bucket)
            return
        except ClientError as e:
            if e.response["Error"]["Code"] in ("BucketAlreadyOwnedByYou", "BucketAlreadyExists"):
                return
            if e.response["ResponseMetadata"]["HTTPStatusCode"] < 500:
                raise
            last_error: Exception = e
        except BotoCoreError as e:
            last_error = e
        if time.monotonic() > deadline:
            raise TimeoutError(f"SeaweedFS S3 gateway not ready after {timeout}s: {last_error}") from last_error
        time.sleep(0.5)


def start_onezone(oz_container_name):
    docker_run("onedata/onezone:21.02.5-dev", oz_container_name, "demo")


def start_oneprovider(op_container_name, oz_ip_address):
    docker_run("onedata/oneprovider:21.02.5-dev", op_container_name, "demo", oz_ip_address)


def await_oneprovider_demo_readiness(op_container_name):
    docker_exec(op_container_name, "await-demo", output=False)


def get_onedata_access_token(oz_container_name):
    return docker_exec(oz_container_name, "demo-access-token").decode("utf-8").strip()
