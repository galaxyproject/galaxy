import os
from abc import abstractmethod
from typing import Optional
from urllib.parse import urljoin

import yaml

from .driver_factory import ConfiguredDriver
from .navigates_galaxy import (
    galaxy_timeout_handler,
    NavigatesGalaxy,
)


class GalaxySeleniumContext(NavigatesGalaxy):
    url: str
    target_url_from_selenium: str
    configured_driver: ConfiguredDriver

    @property
    def _driver_impl(self):
        """Provide driver implementation from configured_driver.

        This property bridges the HasDriverProxy mixin to the ConfiguredDriver
        used in the test framework. It allows NavigatesGalaxy methods to work
        without requiring constructor changes in the test infrastructure.
        """
        return self.configured_driver.driver_impl

    def build_url(self, url: str, for_selenium: bool = True) -> str:
        if for_selenium:
            base = self.target_url_from_selenium
        else:
            base = self.url
        return urljoin(base, url)

    def screenshot(self, label: str, caption: Optional[str] = None):
        """Take a screenshot and optionally add to story.

        Saves screenshot to the configured directory (story directory if story is enabled,
        otherwise screenshots directory). In test framework, if both are configured,
        screenshot is saved to both locations.

        Args:
            label: Base filename for screenshot
            caption: Optional caption for the screenshot in the story
        """
        target = self._screenshot_path(label)
        if target is None:
            return

        self.save_screenshot(target)

        # Add to story (noop if NoopStory)
        if hasattr(self, "story"):
            self.story.add_screenshot(target, caption or label)

        return target

    def document(self, markdown_content: str):
        """Add markdown documentation to the story.

        This method appends markdown content to the story if story tracking
        is enabled. Content will be interleaved with screenshots in the final
        story document.

        Args:
            markdown_content: Markdown-formatted documentation to add to story
        """
        if hasattr(self, "story"):
            self.story.add_documentation(markdown_content)

    @abstractmethod
    def _screenshot_path(self, label: str, extension=".png") -> Optional[str]:
        """Path to store screenshots in."""


class GalaxySeleniumContextImpl(GalaxySeleniumContext):
    """Minimal, simplified GalaxySeleniumContext useful outside the context of test cases.

    A variant of this concept that can also populate content via the API
    to then interact with via the Selenium is :class:`galaxy_test.selenium.framework.GalaxySeleniumContextImpl`.
    """

    def __init__(self, from_dict: Optional[dict] = None) -> None:
        from_dict = from_dict or {}
        self.timeout_multiplier = from_dict.get("timeout_multiplier", 1)
        timeout_handler = galaxy_timeout_handler(self.timeout_multiplier)
        self.configured_driver = ConfiguredDriver(timeout_handler=timeout_handler, **from_dict.get("driver", {}))
        self.url = from_dict.get("local_galaxy_url", "http://localhost:8080")
        self.target_url_from_selenium = from_dict.get("selenium_galaxy_url", self.url)
        # Optional properties...
        self.login_email = from_dict.get("login_email", "")
        self.login_password = from_dict.get("login_password", "")

    def _screenshot_path(self, label, extension=".png"):
        return label + extension

    # mirror TestWithSelenium method for doing this but use the config.
    def login(self):
        if self.login_email:
            assert self.login_password, "If login_email is set, a password must be set also with login_password"
            self.home()
            self.submit_login(
                email=self.login_email,
                password=self.login_password,
                assert_valid=True,
            )
        else:
            self.register()


def init(config=None, clazz=GalaxySeleniumContextImpl) -> GalaxySeleniumContext:
    if os.path.exists("galaxy_selenium_context.yml"):
        with open("galaxy_selenium_context.yml") as f:
            as_dict = yaml.safe_load(f)
        context = clazz(as_dict)
    else:
        config = config or {}
        context = clazz(config)

    return context
