from typing import Optional
from six.moves.urllib.parse import urljoin

from .driver_factory import ConfiguredDriver
from .navigates_galaxy import NavigatesGalaxy


class GalaxySeleniumContext(NavigatesGalaxy):

    def build_url(self, url, for_selenium=True):
        if for_selenium:
            base = self.target_url_from_selenium
        else:
            base = self.url
        return urljoin(base, url)

    @property
    def driver(self):
        return self.configured_driver.driver

    def screenshot(self, label):
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


class GalaxySeleniumContextImpl(GalaxySeleniumContext):
    """Minimal, simplified GalaxySeleniumContext useful outside the context of test cases."""

    def __init__(self, from_dict: Optional[dict] = None) -> None:
        from_dict = from_dict or {}
        self.configured_driver = ConfiguredDriver(**from_dict.get("driver", {}))
        self.url = from_dict.get("local_galaxy_url", "http://localhost:8080")
        self.target_url_from_selenium = from_dict.get("selenium_galaxy_url", self.url)
        self.timeout_multiplier = from_dict.get("timeout_multiplier", 1)

    def _screenshot_path(self, label, extension=".png"):
        return label + extension
