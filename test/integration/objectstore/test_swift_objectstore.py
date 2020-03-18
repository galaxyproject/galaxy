
import os
import string
import subprocess

from galaxy_test.driver import integration_util

OBJECT_STORE_HOST = os.environ.get('GALAXY_INTEGRATION_OBJECT_STORE_HOST', '127.0.0.1')
OBJECT_STORE_PORT = int(os.environ.get('GALAXY_INTEGRATION_OBJECT_STORE_PORT', 9000))
OBJECT_STORE_ACCESS_KEY = os.environ.get('GALAXY_INTEGRATION_OBJECT_STORE_ACCESS_KEY', 'minioadmin')
OBJECT_STORE_SECRET_KEY = os.environ.get('GALAXY_INTEGRATION_OBJECT_STORE_SECRET_KEY', 'minioadmin')
OBJECT_STORE_CONFIG = string.Template("""
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
""")
TEST_TOOL_IDS = [
    "multi_output",
    "multi_output_configured",
    "multi_output_assign_primary",
    "multi_output_recurse",
    "tool_provided_metadata_1",
    "tool_provided_metadata_2",
    "tool_provided_metadata_3",
    "tool_provided_metadata_4",
    "tool_provided_metadata_5",
    "tool_provided_metadata_6",
    "tool_provided_metadata_7",
    "tool_provided_metadata_8",
    "tool_provided_metadata_9",
    "tool_provided_metadata_10",
    "tool_provided_metadata_11",
    "tool_provided_metadata_12",
    "composite_output",
    "composite_output_tests",
    "metadata",
    "metadata_bam",
    "output_format",
    "output_auto_format",
]


def start_minio(container_name):
    minio_start_args = [
        'docker',
        'run',
        '-p',
        '{port}:9000'.format(port=OBJECT_STORE_PORT),
        '-d',
        '--name',
        container_name,
        # '--rm',
        'minio/minio:latest',
        'server',
        '/tmp/data']
    subprocess.check_call(minio_start_args)


def stop_minio(container_name):
    subprocess.check_call(['docker', 'rm', '-f', container_name])


@integration_util.skip_unless_docker()
class SwiftObjectStoreIntegrationTestCase(integration_util.IntegrationTestCase):

    @classmethod
    def setUpClass(cls):
        cls.container_name = "%s_container" % cls.__name__
        start_minio(cls.container_name)
        super(SwiftObjectStoreIntegrationTestCase, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        stop_minio(cls.container_name)
        super(SwiftObjectStoreIntegrationTestCase, cls).tearDownClass()

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        temp_directory = cls._test_driver.mkdtemp()
        cls.object_stores_parent = temp_directory
        config_path = os.path.join(temp_directory, "object_store_conf.xml")
        config["object_store_store_by"] = "uuid"
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
                        "access_key": OBJECT_STORE_ACCESS_KEY,
                        "secret_key": OBJECT_STORE_SECRET_KEY,
                    }
                )
            )
        config["object_store_config_file"] = config_path


instance = integration_util.integration_module_instance(SwiftObjectStoreIntegrationTestCase)

test_tools = integration_util.integration_tool_runner(TEST_TOOL_IDS)
