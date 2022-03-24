import logging
import os

try:
    from pyvirtualdisplay import Display
except ImportError:
    Display = None

from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.remote.webdriver import WebDriver

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
DEFAULT_WINDOW_WIDTH = 1280
DEFAULT_WINDOW_HEIGHT = 1000
VALID_LOCAL_BROWSERS = ["CHROME", "FIREFOX", "OPERA"]


class ConfiguredDriver:
    driver: WebDriver

    def __init__(
        self,
        browser=DEFAULT_SELENIUM_BROWSER,
        remote=DEFAULT_SELENIUM_REMOTE,
        remote_host=DEFAULT_SELENIUM_REMOTE_HOST,
        remote_port=DEFAULT_SELENIUM_REMOTE_PORT,
        headless=False,
    ):
        self.config = dict(
            browser=browser,
            remote=remote,
            remote_host=remote_host,
            remote_port=remote_port,
            headless=headless,
        )
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
        self.driver = driver

    def to_dict(self):
        return self.config

    @staticmethod
    def from_dict(as_dict):
        return ConfiguredDriver(**as_dict)


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
        "OPERA": webdriver.Opera,
    }
    driver_class = driver_to_class[browser]
    if browser == "CHROME":
        options = ChromeOptions()
        if headless:
            options.add_argument("--headless")
        prefs = {"download.default_directory": DEFAULT_DOWNLOAD_PATH}
        options.add_experimental_option("prefs", prefs)
        return driver_class(desired_capabilities={"loggingPrefs": LOGGING_PREFS}, chrome_options=options)
    elif browser == "FIREFOX":
        fp = webdriver.FirefoxProfile()
        fp.set_preference("network.proxy.type", 2)
        fp.set_preference("network.proxy.autoconfig_url", "http://127.0.0.1:9675")
        fp.set_preference("browser.download.folderList", 2)
        fp.set_preference("browser.download.dir", DEFAULT_DOWNLOAD_PATH)
        fp.set_preference("browser.helperApps.neverAsk.saveToDisk", "application/octet-stream")
        return driver_class(firefox_profile=fp)

    else:
        return driver_class(desired_capabilities={"loggingPrefs": LOGGING_PREFS})


def get_remote_driver(host, port, browser=DEFAULT_BROWSER) -> WebDriver:
    # docker run -d -p 4444:4444 -v /dev/shm:/dev/shm selenium/standalone-chrome:3.0.1-aluminum
    if browser == "auto":
        browser = "CHROME"
    assert browser in ["CHROME", "EDGE", "ANDROID", "FIREFOX", "INTERNETEXPLORER", "IPAD", "IPHONE", "OPERA", "SAFARI"]
    desired_capabilities = getattr(DesiredCapabilities, browser)
    desired_capabilities["loggingPrefs"] = LOGGING_PREFS
    executor = f"http://{host}:{port}/wd/hub"
    driver = webdriver.Remote(
        command_executor=executor,
        desired_capabilities=desired_capabilities,
    )
    return driver


def is_virtual_display_available():
    return Display is not None


def virtual_display_if_enabled(enabled):
    if enabled:
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
    "is_virtual_display_available",
    "virtual_display_if_enabled",
)
