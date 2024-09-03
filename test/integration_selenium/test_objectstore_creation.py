from typing import TYPE_CHECKING

from galaxy_test.driver.integration_util import (
    ConfiguresDatabaseVault,
    ConfiguresObjectStores,
)
from .framework import (
    selenium_test,
    SeleniumIntegrationTestCase,
)
from .test_objectstore_selection import MSI_EXAMPLE_OBJECT_STORE_CONFIG_TEMPLATE

if TYPE_CHECKING:
    from galaxy_test.selenium.framework import SeleniumSessionDatasetPopulator


MULTI_VERSION_WITH_SECRETS_LIBRARY = """
- id: secure_disk
  version: 0
  name: Secure Disk
  description: Secure Disk Bound to You
  secrets:
    sec1:
      help: This is my test secret.
  configuration:
    type: disk
    files_dir: '/data/secure/{{ user.username }}/{{ secrets.sec1 }}/aftersec'
    badges:
    - type: more_secure
    - type: slower
- id: secure_disk
  version: 1
  name: Secure Disk
  description: Secure Disk Bound to You
  secrets:
    sec1:
      help: This is my test secret.
    sec2:
      help: This is my test secret 2.
  configuration:
    type: disk
    files_dir: '/data/secure/{{ user.username }}/{{ secrets.sec1 }}/{{ secrets.sec2 }}'
    badges:
    - type: more_secure
    - type: slower
- id: secure_disk
  version: 2
  name: Secure Disk
  description: Secure Disk Bound to You
  secrets:
    sec2:
      help: This is my test secret 2.
  configuration:
    type: disk
    files_dir: '/data/secure/{{ user.username }}/newbar/{{ secrets.sec2 }}'
    badges:
    - type: more_secure
    - type: slower
"""


class TestObjectStoreSelectionSeleniumIntegration(
    SeleniumIntegrationTestCase, ConfiguresObjectStores, ConfiguresDatabaseVault
):
    ensure_registered = True
    dataset_populator: "SeleniumSessionDatasetPopulator"

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        cls._configure_object_store(MSI_EXAMPLE_OBJECT_STORE_CONFIG_TEMPLATE, config)
        cls._configure_database_vault(config)
        cls._configure_object_store_template_catalog(MULTI_VERSION_WITH_SECRETS_LIBRARY, config)

    @selenium_test
    def test_create_and_use(self):
        self.navigate_to_user_preferences()
        preferences = self.components.preferences
        preferences.manage_object_stores.wait_for_and_click()
        object_store_instances = self.components.object_store_instances
        object_store_instances.index.create_button.wait_for_and_click()
