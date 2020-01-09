import os
import re

from galaxy_test.base.populators import (
    DatasetPopulator,
)
from galaxy_test.driver import integration_util


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
        super(BaseObjectStoreIntegrationTestCase, self).setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)


def files_count(directory):
    return sum(len(files) for _, _, files in os.walk(directory))
