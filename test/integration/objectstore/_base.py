import os
import re
import string
import subprocess

from galaxy_test.base.populators import DatasetPopulator
from galaxy_test.driver import integration_util

OBJECT_STORE_HOST = os.environ.get("GALAXY_INTEGRATION_OBJECT_STORE_HOST", "127.0.0.1")
OBJECT_STORE_PORT = int(os.environ.get("GALAXY_INTEGRATION_OBJECT_STORE_PORT", 9000))
OBJECT_STORE_ACCESS_KEY = os.environ.get("GALAXY_INTEGRATION_OBJECT_STORE_ACCESS_KEY", "minioadmin")
OBJECT_STORE_SECRET_KEY = os.environ.get("GALAXY_INTEGRATION_OBJECT_STORE_SECRET_KEY", "minioadmin")
OBJECT_STORE_CONFIG = string.Template(
    """
<object_store type="hierarchical" id="primary">
    <backends>
        <object_store id="swifty" type="swift" weight="1" order="0">
            <auth access_key="${access_key}" secret_key="${secret_key}" />
            <bucket name="galaxy" use_reduced_redundancy="False" max_chunk_size="250"/>
            <connection host="${host}" port="${port}" is_secure="False" conn_path="" multipart="True"/>
            <cache path="${temp_directory}/object_store_cache" size="1000" />
            <extra_dir type="job_work" path="${temp_directory}/job_working_directory_swift"/>
            <extra_dir type="temp" path="${temp_directory}/tmp_swift"/>
        </object_store>
    </backends>
</object_store>
"""
)


def start_minio(container_name):
    minio_start_args = [
        "docker",
        "run",
        "-p",
        f"{OBJECT_STORE_PORT}:9000",
        "-d",
        "--name",
        container_name,
        "--rm",
        "minio/minio:latest",
        "server",
        "/data",
    ]
    subprocess.check_call(minio_start_args)


def stop_minio(container_name):
    subprocess.check_call(["docker", "rm", "-f", container_name])


class BaseObjectStoreIntegrationTestCase(integration_util.IntegrationTestCase):

    framework_tool_and_types = True

    @classmethod
    def _configure_object_store(cls, template, config):
        temp_directory = cls._test_driver.mkdtemp()
        cls.object_stores_parent = temp_directory
        config_path = os.path.join(temp_directory, "object_store_conf.xml")
        xml = template.safe_substitute({"temp_directory": temp_directory})
        with open(config_path, "w") as f:
            f.write(xml)
        config["object_store_config_file"] = config_path
        for path in re.findall(r'files_dir path="([^"]*)"', xml):
            assert path.startswith(temp_directory)
            dir_name = os.path.basename(path)
            os.path.join(temp_directory, dir_name)
            os.makedirs(path)
            setattr(cls, "%s_path" % dir_name, path)

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)


def files_count(directory):
    return sum(len(files) for _, _, files in os.walk(directory))


@integration_util.skip_unless_docker()
class BaseSwiftObjectStoreIntegrationTestCase(BaseObjectStoreIntegrationTestCase):

    object_store_cache_path: str

    @classmethod
    def setUpClass(cls):
        cls.container_name = "%s_container" % cls.__name__
        start_minio(cls.container_name)
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        stop_minio(cls.container_name)
        super().tearDownClass()

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        temp_directory = cls._test_driver.mkdtemp()
        cls.object_stores_parent = temp_directory
        cls.object_store_cache_path = f"{temp_directory}/object_store_cache"
        config_path = os.path.join(temp_directory, "object_store_conf.xml")
        config["object_store_store_by"] = "uuid"
        config["metadata_strategy"] = "extended"
        config["outpus_to_working_dir"] = True
        config["retry_metadata_internally"] = False
        with open(config_path, "w") as f:
            f.write(
                OBJECT_STORE_CONFIG.safe_substitute(
                    {
                        "temp_directory": temp_directory,
                        "host": OBJECT_STORE_HOST,
                        "port": OBJECT_STORE_PORT,
                        "access_key": OBJECT_STORE_ACCESS_KEY,
                        "secret_key": OBJECT_STORE_SECRET_KEY,
                    }
                )
            )
        config["object_store_config_file"] = config_path

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)
