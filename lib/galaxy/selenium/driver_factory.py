import logging
import os
from typing import (
    Any,
    cast,
    Literal,
    Union,
)

# Playwright browser type names (matches BrowserType.name property)
PlaywrightBrowserName = Literal["chromium", "firefox", "webkit"]

try:
    from pyvirtualdisplay import Display
except ImportError:
    Display = None

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None  # type: ignore[assignment]

from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.safari.options import Options as SafariOptions

from .has_driver import HasDriver
from .has_driver_protocol import (
    HasDriverProtocol,
    TimeoutCallback,
)
from .has_playwright_driver import (
    HasPlaywrightDriver,
    PlaywrightResources,
)

logger = logging.getLogger("selenium.webdriver.remote.remote_connection")
logger.setLevel(logging.WARNING)

DEFAULT_BROWSER = "auto"
DEFAULT_DOWNLOAD_PATH = "/tmp/"
LOGGING_PREFS = {
    "browser": "ALL",
}
DEFAULT_SELENIUM_BROWSER = "auto"
DEFAULT_SELENIUM_REMOTE = False
DEFAULT_SELENIUM_REMOTE_PORT = "4444"
DEFAULT_SELENIUM_REMOTE_HOST = "127.0.0.1"
DEFAULT_BACKEND_TYPE: Literal["selenium", "playwright"] = "selenium"
DEFAULT_WINDOW_WIDTH = 1280
DEFAULT_WINDOW_HEIGHT = 1000
VALID_LOCAL_BROWSERS = ["CHROME", "FIREFOX"]
PLAYWRIGHT_UNAVAILABLE_MESSAGE = "playwright must be installed to use the playwright backend, install with 'pip install playwright' and run 'playwright install chromium'"
PYVIRTUALDISPLAY_UNAVAILABLE_MESSAGE = "pyvirtualdisplay must be installed to run this test configuration and is not, install with 'pip install pyvirtualdisplay'"
PLAYWRIGHT_REMOTE_UNSUPPORTED_MESSAGE = "Playwright backend does not support remote drivers (Selenium Grid). Use backend_type='selenium' for remote testing."


class _SeleniumDriverImpl(HasDriver[Any]):
    """Internal wrapper implementing HasDriver for ConfiguredDriver."""

    def __init__(self, driver: WebDriver, timeout_handler: TimeoutCallback):
        self.driver = driver
        self._timeout_handler = timeout_handler

    @property
    def timeout_handler(self) -> TimeoutCallback:
        """Return timeout value, using kwds override or default."""
        return self._timeout_handler


class _PlaywrightDriverImpl(HasPlaywrightDriver[Any]):
    """Internal wrapper implementing HasPlaywrightDriver for ConfiguredDriver."""

    def __init__(self, resources: PlaywrightResources, timeout_handler: TimeoutCallback):
        self._playwright_resources = resources
        self._timeout_handler = timeout_handler
        self._current_frame = None

    @property
    def timeout_handler(self) -> TimeoutCallback:
        """Return timeout value, using kwds override or default."""
        return self._timeout_handler


class ConfiguredDriver:
    """
    Configured driver factory supporting both Selenium and Playwright backends.

    This class creates and manages either a Selenium WebDriver or Playwright driver
    based on the backend_type parameter. It provides a unified interface via
    HasDriverProtocol for both implementations.

    Attributes:
        driver_impl: The HasDriverProtocol implementation (HasDriver or HasPlaywrightDriver)
        config: Configuration dictionary for serialization
        backend_type: Which backend is being used ("selenium" or "playwright")
    """

    driver_impl: HasDriverProtocol[Any]
    config: dict[str, Any]
    backend_type: Literal["selenium", "playwright"]

    def __init__(
        self,
        timeout_handler: TimeoutCallback,
        browser: str = DEFAULT_SELENIUM_BROWSER,
        remote: bool = DEFAULT_SELENIUM_REMOTE,
        remote_host: str = DEFAULT_SELENIUM_REMOTE_HOST,
        remote_port: str = DEFAULT_SELENIUM_REMOTE_PORT,
        headless: bool = False,
        backend_type: Literal["selenium", "playwright"] = DEFAULT_BACKEND_TYPE,
    ):
        """
        Initialize a configured driver with the specified backend.

        Args:
            browser: Browser name ("auto", "CHROME", "FIREFOX", etc.)
            remote: Whether to use remote Selenium Grid (Selenium only)
            remote_host: Remote Selenium Grid host
            remote_port: Remote Selenium Grid port
            headless: Whether to run browser in headless mode
            backend_type: Which backend to use ("selenium" or "playwright")
            default_timeout: Default timeout for wait operations in seconds

        Raises:
            Exception: If Playwright backend is requested with remote=True
            Exception: If Playwright is not installed when backend_type="playwright"
        """
        self.backend_type = backend_type
        self.config = dict(
            browser=browser,
            remote=remote,
            remote_host=remote_host,
            remote_port=remote_port,
            headless=headless,
            backend_type=backend_type,
        )

        # Validate Playwright limitations
        if backend_type == "playwright" and remote:
            raise Exception(PLAYWRIGHT_REMOTE_UNSUPPORTED_MESSAGE)

        if backend_type == "selenium":
            # Create Selenium driver
            if remote:
                driver = get_remote_driver(
                    host=remote_host,
                    port=remote_port,
                    browser=browser,
                )
            else:
                driver = get_local_driver(
                    browser=browser,
                    headless=headless,
                )
            # Need larger than default window size for workflow index page, paired list creator.
            driver.set_window_size(DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT)
            self.driver_impl = cast(HasDriverProtocol, _SeleniumDriverImpl(driver, timeout_handler))

        elif backend_type == "playwright":
            # Create Playwright driver
            resources = get_playwright_driver(
                browser=browser,
                headless=headless,
            )
            self.driver_impl = cast(HasDriverProtocol, _PlaywrightDriverImpl(resources, timeout_handler))

        else:
            raise ValueError(f"Invalid backend_type: {backend_type}. Must be 'selenium' or 'playwright'")

    def to_dict(self) -> dict[str, Any]:
        """Serialize configuration to dictionary."""
        return self.config.copy()

    @staticmethod
    def from_dict(timeout_handler: TimeoutCallback, as_dict: dict[str, Any]) -> "ConfiguredDriver":
        """Deserialize configuration from dictionary."""
        return ConfiguredDriver(timeout_handler, **as_dict)

    def quit(self) -> None:
        """Clean up and close the driver."""
        self.driver_impl.quit()


def get_local_browser(browser):
    if browser == "auto":
        if _which("chromedriver"):
            browser = "CHROME"
        elif _which("geckodriver"):
            browser = "FIREFOX"
        else:
            raise Exception("Selenium browser is 'auto' but neither geckodriver or chromedriver are found on PATH.")
    return browser


def get_local_driver(browser=DEFAULT_BROWSER, headless=False) -> WebDriver:
    browser = get_local_browser(browser)
    if browser not in VALID_LOCAL_BROWSERS:
        raise AssertionError(f"{browser} not in VALID_LOCAL_BROWSERS ({VALID_LOCAL_BROWSERS})")
    driver_to_class = {
        "CHROME": webdriver.Chrome,
        "FIREFOX": webdriver.Firefox,
    }
    driver_class = driver_to_class[browser]
    if browser == "CHROME":
        chrome_options = ChromeOptions()
        if headless:
            chrome_options.add_argument("--headless")
        prefs = {"download.default_directory": DEFAULT_DOWNLOAD_PATH}
        chrome_options.add_experimental_option("prefs", prefs)
        chrome_options.set_capability("goog:loggingPrefs", LOGGING_PREFS)
        return driver_class(options=chrome_options)
    else:
        firefox_options = webdriver.FirefoxOptions()
        firefox_options.set_preference("network.proxy.type", 2)
        firefox_options.set_preference("network.proxy.autoconfig_url", "http://127.0.0.1:9675")
        firefox_options.set_preference("browser.download.folderList", 2)
        firefox_options.set_preference("browser.download.dir", DEFAULT_DOWNLOAD_PATH)
        firefox_options.set_preference("browser.helperApps.neverAsk.saveToDisk", "application/octet-stream")
        return driver_class(options=firefox_options)


def get_playwright_browser_type(browser: str = DEFAULT_BROWSER) -> PlaywrightBrowserName:
    """
    Map Selenium browser names to Playwright browser types.

    Args:
        browser: Browser name (CHROME, FIREFOX, auto, etc.)

    Returns:
        Playwright browser type: 'chromium', 'firefox', or 'webkit'
        This matches the BrowserType.name property values.

    Raises:
        NotImplementedError: If browser type has no direct Playwright mapping
    """
    if browser == "auto" or browser == "CHROME":
        return "chromium"
    elif browser == "FIREFOX":
        return "firefox"
    elif browser == "EDGE":
        raise NotImplementedError(
            f"Browser '{browser}' does not have a direct Playwright mapping. "
            "EDGE uses Chromium under the hood - use 'CHROME' or 'auto' instead."
        )
    elif browser == "SAFARI":
        raise NotImplementedError(
            f"Browser '{browser}' does not have a direct Playwright mapping. "
            "Safari uses WebKit - however, Playwright's 'webkit' is not identical to Safari. "
            "If you need Safari-specific testing, use the Selenium backend instead."
        )
    else:
        # Unknown browser type
        raise NotImplementedError(
            f"Browser '{browser}' is not supported with Playwright backend. "
            f"Supported browsers: CHROME, FIREFOX, auto. Use backend_type='selenium' for other browsers."
        )


def get_playwright_driver(browser: str = DEFAULT_BROWSER, headless: bool = False) -> PlaywrightResources:
    """
    Create Playwright browser resources.

    Args:
        browser: Browser name to launch (CHROME, FIREFOX, auto, etc.)
        headless: Whether to run in headless mode

    Returns:
        PlaywrightResources containing playwright, browser, and page instances

    Raises:
        Exception: If playwright is not installed
    """
    if sync_playwright is None:
        raise Exception(PLAYWRIGHT_UNAVAILABLE_MESSAGE)

    browser_type_name = get_playwright_browser_type(browser)
    playwright = sync_playwright().start()

    # Get the appropriate browser type
    if browser_type_name == "firefox":
        browser_type = playwright.firefox
    elif browser_type_name == "webkit":
        browser_type = playwright.webkit
    else:
        browser_type = playwright.chromium

    # Launch browser with headless setting
    browser_instance = browser_type.launch(headless=headless)

    # Create page with viewport size matching Selenium's window size
    page = browser_instance.new_page(viewport={"width": DEFAULT_WINDOW_WIDTH, "height": DEFAULT_WINDOW_HEIGHT})

    return PlaywrightResources(
        playwright=playwright,
        browser=browser_instance,
        page=page,
    )


def get_remote_driver(host, port, browser=DEFAULT_BROWSER) -> WebDriver:
    # docker run -d -p 4444:4444 -v /dev/shm:/dev/shm selenium/standalone-chrome:3.0.1-aluminum
    options: Union[webdriver.ChromeOptions, webdriver.FirefoxOptions, webdriver.EdgeOptions, SafariOptions]
    if browser == "auto" or browser == "CHROME":
        options = webdriver.ChromeOptions()
        options.set_capability("goog:loggingPrefs", LOGGING_PREFS)
    elif browser == "FIREFOX":
        options = webdriver.FirefoxOptions()
    elif browser == "EDGE":
        options = webdriver.EdgeOptions()
    elif browser == "SAFARI":
        options = SafariOptions()
    else:
        raise Exception(f"Browser '{browser}' not supported.")
    executor = f"http://{host}:{port}/wd/hub"
    driver = webdriver.Remote(
        command_executor=executor,
        options=options,
    )
    return driver


def is_virtual_display_available():
    return Display is not None


def virtual_display_if_enabled(enabled):
    if enabled:
        if Display is None:
            raise Exception(PYVIRTUALDISPLAY_UNAVAILABLE_MESSAGE)
        display = Display(visible=0, size=(800, 600))
        display.start()
        return display
    else:
        return NoopDisplay()


class NoopDisplay:
    def stop(self):
        """No-op stop for consistent use with pyvirtualdisplay Display class."""


# Purposely copied from galaxy.util - just use galaxy.util if we decide
# galaxy_selenium should definitely depend on Galaxy/galaxy-lib.
def _which(file):
    # http://stackoverflow.com/questions/5226958/which-equivalent-function-in-python
    for path in os.environ["PATH"].split(":"):
        if os.path.exists(f"{path}/{file}"):
            return f"{path}/{file}"

    return None


__all__ = (
    "ConfiguredDriver",
    "get_local_driver",
    "get_remote_driver",
    "get_playwright_browser_type",
    "is_virtual_display_available",
    "virtual_display_if_enabled",
    "PlaywrightBrowserName",
)
