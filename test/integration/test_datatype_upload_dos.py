
import os
import string

import pytest

from galaxy_test.driver import integration_util
from .test_datatype_upload import (
    TEST_CASES,
    upload_datatype_helper,
    UploadTestDatatypeDataTestCase
)

SCRIPT_DIRECTORY = os.path.abspath(os.path.dirname(__file__))
# Run test for only the first 10 test files
DOS_TEST_CASES = dict(list(TEST_CASES.items())[0:10])
OBJECT_STORE_CONFIG = string.Template("""
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


class UploadTestDatatypeDataTestCaseDos(UploadTestDatatypeDataTestCase):

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        temp_directory = cls._test_driver.mkdtemp()
        print('temp_directory:', temp_directory)
        cls.object_stores_parent = temp_directory
        config_path = os.path.join(temp_directory, "object_store_conf.xml")
        # This doesn't quite work yet, fails with extra_files_path
        # config["metadata_strategy"] = "extended"
        config["outpus_to_working_dir"] = True
        config["retry_metadata_internally"] = False
        config["object_store_store_by"] = "uuid"
        with open(config_path, "w") as f:
            f.write(
                OBJECT_STORE_CONFIG.safe_substitute(
                    {
                        "temp_directory": temp_directory,
                    }
                )
            )
        config["object_store_config_file"] = config_path


instance = integration_util.integration_module_instance(UploadTestDatatypeDataTestCaseDos)


@pytest.mark.parametrize('test_data', DOS_TEST_CASES.values(), ids=list(DOS_TEST_CASES.keys()))
def test_upload_datatype_dos(instance, test_data, temp_file):
    upload_datatype_helper(instance, test_data, temp_file)
