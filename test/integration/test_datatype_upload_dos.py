import os
import string

import pytest

from galaxy_test.driver import integration_util
from .test_datatype_upload import (
    TEST_CASES,
    upload_datatype_helper,
    UploadTestDatatypeDataTestCase
)
from .test_datatype_upload_irods import (
    IrodsUploadTestDatatypeDataTestCase
)

SCRIPT_DIRECTORY = os.path.abspath(os.path.dirname(__file__))
IRODS_OBJECT_STORE_HOST = os.environ.get('GALAXY_INTEGRATION_IRODS_OBJECT_STORE_HOST', 'localhost')
IRODS_OBJECT_STORE_PORT = int(os.environ.get('GALAXY_INTEGRATION_IRODS_OBJECT_STORE_PORT', 1247))
IRODS_OBJECT_STORE_TIMEOUT = int(os.environ.get('GALAXY_INTEGRATION_IRODS_OBJECT_STORE_TIMEOUT', 30))
IRODS_OBJECT_STORE_USERNAME = os.environ.get('GALAXY_INTEGRATION_IRODS_OBJECT_STORE_USERNAME', 'rods')
IRODS_OBJECT_STORE_PASSWORD = os.environ.get('GALAXY_INTEGRATION_IRODS_OBJECT_STORE_PASSWORD', 'rods')
IRODS_OBJECT_STORE_RESOURCE = os.environ.get('GALAXY_INTEGRATION_IRODS_OBJECT_STORE_RESOURCE', 'demoResc')
IRODS_OBJECT_STORE_ZONE = os.environ.get('GALAXY_INTEGRATION_IRODS_OBJECT_STORE_ZONE', 'tempZone')
# Run test for only the first 10 test files
DOS_TEST_CASES = dict(list(TEST_CASES.items())[0:10])
DISK_OBJECT_STORE_CONFIG = string.Template("""
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
IRODS_OBJECT_STORE_CONFIG = string.Template("""
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
            <connection host="${host}" port="${port}" timeout="${timeout}"/>
            <cache path="${temp_directory}/object_store_cache" size="1000"/>
            <extra_dir type="job_work" path="${temp_directory}/job_working_directory_irods"/>
            <extra_dir type="temp" path="${temp_directory}/tmp_irods"/>
        </backend>
    </backends>
</object_store>
""")


class UploadTestDosDiskAndDiskTestCase(UploadTestDatatypeDataTestCase):

    UploadTestDatatypeDataTestCase.object_store_config = DISK_OBJECT_STORE_CONFIG

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super(UploadTestDosDiskAndDiskTestCase, cls).handle_galaxy_config_kwds(config)
        temp_directory = cls._test_driver.mkdtemp()
        cls.object_stores_parent = temp_directory
        cls.object_store_config_path = os.path.join(temp_directory, "object_store_conf.xml")
        # This doesn't quite work yet, fails with extra_files_path
        # config["metadata_strategy"] = "extended"
        config["outpus_to_working_dir"] = True
        config["retry_metadata_internally"] = False
        config["object_store_store_by"] = "uuid"
        with open(cls.object_store_config_path, "w") as f:
            f.write(
                UploadTestDatatypeDataTestCase.object_store_config.safe_substitute(
                    {
                        "temp_directory": cls.object_stores_parent,
                    }
                )
            )


class UploadTestDosIrodsAndDiskTestCase(IrodsUploadTestDatatypeDataTestCase):

    UploadTestDatatypeDataTestCase.object_store_config = IRODS_OBJECT_STORE_CONFIG

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super(UploadTestDosIrodsAndDiskTestCase, cls).handle_galaxy_config_kwds(config)
        with open(cls.object_store_config_path, "w") as f:
            f.write(
                UploadTestDatatypeDataTestCase.object_store_config.safe_substitute(
                    {
                        "temp_directory": cls.object_stores_parent,
                        "host": IRODS_OBJECT_STORE_HOST,
                        "port": IRODS_OBJECT_STORE_PORT,
                        "timeout": IRODS_OBJECT_STORE_TIMEOUT,
                        "username": IRODS_OBJECT_STORE_USERNAME,
                        "password": IRODS_OBJECT_STORE_PASSWORD,
                        "resource": IRODS_OBJECT_STORE_RESOURCE,
                        "zone": IRODS_OBJECT_STORE_ZONE
                    }
                )
            )


instance1 = integration_util.integration_module_instance(UploadTestDosDiskAndDiskTestCase)
instance2 = integration_util.integration_module_instance(UploadTestDosIrodsAndDiskTestCase)


@pytest.mark.parametrize('test_data', DOS_TEST_CASES.values(), ids=list(DOS_TEST_CASES.keys()))
def test_upload_datatype_dos_disk_and_disk(instance1, test_data, temp_file):
    upload_datatype_helper(instance1, test_data, temp_file)


@pytest.mark.parametrize('test_data', DOS_TEST_CASES.values(), ids=list(DOS_TEST_CASES.keys()))
def test_upload_datatype_dos_irods_and_disk(instance2, test_data, temp_file):
    upload_datatype_helper(instance2, test_data, temp_file)
