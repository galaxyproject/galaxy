"""Basis for Selenium test framework."""
from __future__ import absolute_import

import contextlib
import datetime
import json
import os

from functools import wraps

try:
    from pyvirtualdisplay import Display
except ImportError:
    Display = None

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait

from six.moves.urllib.parse import urljoin

from base.twilltestcase import FunctionalTestCase
from base.driver_util import classproperty, DEFAULT_WEB_HOST, get_ip_address

from galaxy.util import asbool, which

from .data import TEST_DATA

DEFAULT_WAIT_TIMEOUT = 5
DEFAULT_TEST_ERRORS_DIRECTORY = os.path.abspath("database/test_errors")
DEFAULT_SELENIUM_BROWSER = "auto"
DEFAULT_SELENIUM_REMOTE = False
DEFAULT_SELENIUM_REMOTE_PORT = "4444"
DEFAULT_SELENIUM_REMOTE_HOST = "127.0.0.1"
DEFAULT_SELENIUM_HEADLESS = "auto"

GALAXY_TEST_ERRORS_DIRECTORY = os.environ.get("GALAXY_TEST_ERRORS_DIRECTORY", DEFAULT_TEST_ERRORS_DIRECTORY)
# Test browser can be ["CHROME", "FIREFOX", "OPERA", "PHANTOMJS"]
GALAXY_TEST_SELENIUM_BROWSER = os.environ.get("GALAXY_TEST_SELENIUM_BROWSER", DEFAULT_SELENIUM_BROWSER)
GALAXY_TEST_SELENIUM_REMOTE = os.environ.get("GALAXY_TEST_SELENIUM_REMOTE", DEFAULT_SELENIUM_REMOTE)
GALAXY_TEST_SELENIUM_REMOTE_PORT = os.environ.get("GALAXY_TEST_SELENIUM_REMOTE_PORT", DEFAULT_SELENIUM_REMOTE_PORT)
GALAXY_TEST_SELENIUM_REMOTE_HOST = os.environ.get("GALAXY_TEST_SELENIUM_REMOTE_HOST", DEFAULT_SELENIUM_REMOTE_HOST)
GALAXY_TEST_SELENIUM_HEADLESS = os.environ.get("GALAXY_TEST_SELENIUM_HEADLESS", DEFAULT_SELENIUM_HEADLESS)

try:
    from nose.tools import nottest
except ImportError:
    def nottest(x):
        return x


@nottest
def selenium_test(f):

    @wraps(f)
    def func_wrapper(self, *args, **kwds):
        try:
            return f(self, *args, **kwds)
        except Exception:
            if GALAXY_TEST_ERRORS_DIRECTORY and GALAXY_TEST_ERRORS_DIRECTORY != "0":
                if not os.path.exists(GALAXY_TEST_ERRORS_DIRECTORY):
                    os.makedirs(GALAXY_TEST_ERRORS_DIRECTORY)
                result_name = f.__name__ + datetime.datetime.now().strftime("%Y%m%d%H%M%s")
                target_directory = os.path.join(GALAXY_TEST_ERRORS_DIRECTORY, result_name)
                os.makedirs(target_directory)
                self.driver.save_screenshot(os.path.join(target_directory, "last.png"))
            raise

    return func_wrapper


class HasDriver:

    def assert_xpath(self, xpath):
        assert self.driver.find_element_by_xpath(xpath)

    def assert_selector(self, selector):
        assert self.driver.find_element_by_css_selector(selector)

    def wait_for_xpath(self, xpath):
        wait = self.wait()
        element = wait.until(ec.element_to_be_clickable((By.XPATH, xpath)))
        return element

    def wait_for_id(self, id):
        wait = self.wait()
        element = wait.until(ec.element_to_be_clickable((By.ID, id)))
        return element

    def wait(self, timeout=DEFAULT_WAIT_TIMEOUT):
        return WebDriverWait(self.driver, DEFAULT_WAIT_TIMEOUT)

    def click_xpath(self, xpath):
        element = self.driver.find_element_by_xpath(xpath)
        element.click()

    def click_label(self, text):
        element = self.driver.find_element_by_link_text(text)
        element.click()

    def fill(self, form, info):
        for key, value in info.items():
            input_element = form.find_element_by_name(key)
            input_element.send_keys(value)


class GalaxyNavigation(HasDriver):

    @property
    def test_data(self):
        return TEST_DATA

    def home(self):
        self.get()
        assert self.driver.find_element_by_css_selector('#masthead').is_displayed()
        assert self.driver.find_element_by_css_selector('#current-history-panel').is_displayed()

    def switch_to_main_panel(self):
        self.driver.switch_to.frame(self.test_data["selectors"]["frames"]["main"])

    @contextlib.contextmanager
    def main_panel(self):
        try:
            self.switch_to_main_panel()
            yield
        finally:
            self.driver.switch_to.default_content

    def api_get(self, endpoint):
        url = urljoin(self.target_url, "api/" + endpoint)
        self.driver.get(url)
        raw_json = self.driver.page_source
        if "<pre" in raw_json:  # At least Chrome renders JSON in HTML :(
            raw_json = self.driver.find_element_by_tag_name("pre").text
        return json.loads(raw_json)

    def get_logged_in_user(self):
        return self.api_get("users/current")

    def is_logged_in(self):
        return "email" in self.get_logged_in_user()

    def click_masthead_user(self):
        self.click_xpath(self.test_data["selectors"]["masthead"]["user"])

    def logout_if_needed(self):
        if self.is_logged_in():
            self.home()
            self.click_masthead_user()
            self.click_label(self.test_data["labels"]["masthead"]["userMenu"]["logout"])
            self.click_label('go to the home page')
            assert not self.is_logged_in()


class SeleniumTestCase(FunctionalTestCase, GalaxyNavigation):

    def setUp(self):
        super(SeleniumTestCase, self).setUp()
        self.target_url = self.url
        if headless_selenium():
            display = Display(visible=0, size=(800, 600))
            display.start()
            self.display = display
        else:
            self.display = None
        self.driver = get_driver()

    def tearDown(self):
        exception = None
        try:
            super(SeleniumTestCase, self).tearDown()
        except Exception as e:
            exception = e

        try:
            self.driver.close()
        except Exception as e:
            exception = e

        if self.display is not None:
            try:
                self.display.stop()
            except Exception as e:
                exception = e

        if exception is not None:
            raise exception

    @classproperty
    def default_web_host(cls):
        if asbool(GALAXY_TEST_SELENIUM_REMOTE):
            dev_ip = get_ip_address('docker0')
            return dev_ip
        else:
            return DEFAULT_WEB_HOST

    def get(self, url=""):
        full_url = urljoin(self.target_url, url)
        self.driver.get(full_url)


def get_driver():
    if asbool(GALAXY_TEST_SELENIUM_REMOTE):
        return get_remote_driver()
    else:
        return get_local_driver()


def headless_selenium():
    if asbool(GALAXY_TEST_SELENIUM_REMOTE):
        return False

    if GALAXY_TEST_SELENIUM_HEADLESS == "auto":
        if Display is not None:
            return True
        else:
            return asbool(GALAXY_TEST_SELENIUM_HEADLESS)


def get_local_driver():
    browser = GALAXY_TEST_SELENIUM_BROWSER
    if browser == "auto":
        if which("chromedriver"):
            browser = "CHROME"
        elif which("geckodriver"):
            browser = "FIREFOX"
        else:
            raise Exception("GALAXY_TEST_SELENIUM_BROWSER is auto but neither geckodriver or chromedriver are found on PATH.")

    assert browser in ["CHROME", "FIREFOX", "OPERA", "PHANTOMJS"]
    driver_to_class = {
        "CHROME": webdriver.Chrome,
        "FIREFOX": webdriver.Firefox,
        "OPERA": webdriver.Opera,
        "PHANTOMJS": webdriver.PhantomJS,
    }
    driver_class = driver_to_class[browser]
    return driver_class()


def get_remote_driver():
    # docker run -d -p 4444:4444 -v /dev/shm:/dev/shm selenium/standalone-chrome:3.0.1-aluminum
    browser = GALAXY_TEST_SELENIUM_BROWSER
    if browser == "auto":
        browser = "CHROME"
    assert browser in ["CHROME", "EDGE", "ANDROID", "FIREFOX", "INTERNETEXPLORER", "IPAD", "IPHONE", "OPERA", "PHANTOMJS", "SAFARI"]
    desired_capabilities = getattr(DesiredCapabilities, browser)

    executor = 'http://%s:%s/wd/hub' % (GALAXY_TEST_SELENIUM_REMOTE_HOST, GALAXY_TEST_SELENIUM_REMOTE_PORT)
    driver = webdriver.Remote(
        command_executor=executor,
        desired_capabilities=desired_capabilities,
    )
    return driver
