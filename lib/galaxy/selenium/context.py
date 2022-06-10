import os
from abc import abstractmethod
from typing import Optional
from urllib.parse import urljoin

import yaml

from .driver_factory import ConfiguredDriver
from .navigates_galaxy import NavigatesGalaxy


class GalaxySeleniumContext(NavigatesGalaxy):
    url: str
    target_url_from_selenium: str

    def build_url(self, url: str, for_selenium: bool = True) -> str:
        if for_selenium:
            base = self.target_url_from_selenium
        else:
            base = self.url
        return urljoin(base, url)

    @property
    def driver(self):
        return self.configured_driver.driver

    def screenshot(self, label: str):
        """If GALAXY_TEST_SCREENSHOTS_DIRECTORY is set create a screenshot there named <label>.png.

        Unlike the above "snapshot" feature, this will be written out regardless and not in a per-test
        directory. The above method is used for debugging failures within a specific test. This method
        if more for creating a set of images to augment automated testing with manual human inspection
        after a test or test suite has executed.
        """
        target = self._screenshot_path(label)
        if target is None:
            return

        self.driver.save_screenshot(target)
        return target

    def screenshot_if(self, label: Optional[str]) -> Optional[str]:
        target = None
        if label:
            target = self.screenshot(label)
        return target

    @abstractmethod
    def _screenshot_path(self, label: str, extension=".png") -> str:
        """Path to store screenshots in."""


class GalaxySeleniumContextImpl(GalaxySeleniumContext):
    """Minimal, simplified GalaxySeleniumContext useful outside the context of test cases.

    A variant of this concept that can also populate content via the API
    to then interact with via the Selenium is :class:`galaxy_test.selenium.framework.GalaxySeleniumContextImpl`.
    """

    def __init__(self, from_dict: Optional[dict] = None) -> None:
        from_dict = from_dict or {}
        self.configured_driver = ConfiguredDriver(**from_dict.get("driver", {}))
        self.url = from_dict.get("local_galaxy_url", "http://localhost:8080")
        self.target_url_from_selenium = from_dict.get("selenium_galaxy_url", self.url)
        self.timeout_multiplier = from_dict.get("timeout_multiplier", 1)

    def _screenshot_path(self, label, extension=".png"):
        return label + extension


def init(config=None, clazz=GalaxySeleniumContextImpl) -> GalaxySeleniumContext:
    if os.path.exists("galaxy_selenium_context.yml"):
        with open("galaxy_selenium_context.yml") as f:
            as_dict = yaml.safe_load(f)
        context = clazz(as_dict)
    else:
        config = config or {}
        context = clazz(config)

    return context
