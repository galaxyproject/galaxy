from typing import TYPE_CHECKING

from galaxy.objectstore.templates.examples import get_example
from galaxy_test.driver.integration_util import (
    ConfiguresDatabaseVault,
    ConfiguresObjectStoreTemplates,
)
from .framework import SeleniumIntegrationTestCase

if TYPE_CHECKING:
    from galaxy_test.selenium.framework import SeleniumSessionDatasetPopulator


class BaseUserObjectStoreSeleniumIntegration(
    SeleniumIntegrationTestCase, ConfiguresObjectStoreTemplates, ConfiguresDatabaseVault
):
    ensure_registered = True
    dataset_populator: "SeleniumSessionDatasetPopulator"
    example_filename: str

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        cls._configure_database_vault(config)
        template = get_example(cls.example_filename)
        cls._configure_object_Store_template_catalog(template, config)
