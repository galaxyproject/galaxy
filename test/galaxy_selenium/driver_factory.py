import os

try:
    from pyvirtualdisplay import Display
except ImportError:
    Display = None

from selenium import webdriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities


DEFAULT_BROWSER = "auto"


def get_local_driver(browser=DEFAULT_BROWSER):
    if browser == "auto":
        if _which("chromedriver"):
            browser = "CHROME"
        elif _which("geckodriver"):
            browser = "FIREFOX"
        else:
            raise Exception("Selenium browser is 'auto' but neither geckodriver or chromedriver are found on PATH.")

    assert browser in ["CHROME", "FIREFOX", "OPERA", "PHANTOMJS"]
    driver_to_class = {
        "CHROME": webdriver.Chrome,
        "FIREFOX": webdriver.Firefox,
        "OPERA": webdriver.Opera,
        "PHANTOMJS": webdriver.PhantomJS,
    }
    driver_class = driver_to_class[browser]
    return driver_class()


def get_remote_driver(
    host,
    port,
    browser=DEFAULT_BROWSER
):
    # docker run -d -p 4444:4444 -v /dev/shm:/dev/shm selenium/standalone-chrome:3.0.1-aluminum
    if browser == "auto":
        browser = "CHROME"
    assert browser in ["CHROME", "EDGE", "ANDROID", "FIREFOX", "INTERNETEXPLORER", "IPAD", "IPHONE", "OPERA", "PHANTOMJS", "SAFARI"]
    desired_capabilities = getattr(DesiredCapabilities, browser)

    executor = 'http://%s:%s/wd/hub' % (host, port)
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


class NoopDisplay(object):

    def stop(self):
        """No-op stop for consistent use with pyvirtualdisplay Display class."""


# Purposely copied from galaxy.util - just use galaxy.util if we decide
# galaxy_selenium should definitely depend on Galaxy/galaxy-lib.
def _which(file):
    # http://stackoverflow.com/questions/5226958/which-equivalent-function-in-python
    for path in os.environ["PATH"].split(":"):
        if os.path.exists(path + "/" + file):
                return path + "/" + file

    return None


__all__ = (
    'get_local_driver',
    'get_remote_driver',
    'is_virtual_display_available',
    'virtual_display_if_enabled',
)
