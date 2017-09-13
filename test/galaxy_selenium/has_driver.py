"""A mixin to extend a class that has self.driver with higher-level constructs.

This should be mixed into classes with a self.driver and self.default_timeout
attribute.
"""

from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait

UNSPECIFIED_TIMEOUT = object()


class HasDriver:
    TimeoutException = TimeoutException

    def assert_xpath(self, xpath):
        assert self.driver.find_element_by_xpath(xpath)

    def assert_selector(self, selector):
        assert self.driver.find_element_by_css_selector(selector)

    def assert_selector_absent_or_hidden(self, selector):
        elements = self.driver.find_elements_by_css_selector(selector)
        for element in elements:
            assert not element.is_displayed()

    def selector_is_displayed(self, selector):
        element = self.driver.find_element_by_css_selector(selector)
        return element.is_displayed()

    def assert_selector_absent(self, selector):
        assert len(self.driver.find_elements_by_css_selector(selector)) == 0

    def wait_for_xpath(self, xpath):
        element = self._wait_on(
            ec.presence_of_element_located((By.XPATH, xpath)),
            "XPATH selector [%s] to become present" % xpath,
        )
        return element

    def wait_for_xpath_visible(self, xpath):
        element = self._wait_on(
            ec.visibility_of_element_located((By.XPATH, xpath)),
            "XPATH selector [%s] to become visible" % xpath,
        )
        return element

    def wait_for_selector(self, selector):
        element = self._wait_on(
            ec.presence_of_element_located((By.CSS_SELECTOR, selector)),
            "CSS selector [%s] to become present" % selector,
        )
        return element

    def wait_for_selector_visible(self, selector):
        element = self._wait_on(
            ec.visibility_of_element_located((By.CSS_SELECTOR, selector)),
            "CSS selector [%s] to become visible" % selector,
        )
        return element

    def wait_for_selector_clickable(self, selector):
        element = self._wait_on(
            ec.element_to_be_clickable((By.CSS_SELECTOR, selector)),
            "CSS selector [%s] to become clickable" % selector,
        )
        return element

    def wait_for_selector_absent_or_hidden(self, selector):
        element = self._wait_on(
            ec.invisibility_of_element_located((By.CSS_SELECTOR, selector)),
            "CSS selector [%s] to become absent or hidden" % selector,
        )
        return element

    def wait_for_selector_absent(self, selector):
        element = self._wait_on(
            lambda driver: len(driver.find_elements_by_css_selector(selector)) == 0,
            "CSS selector [%s] to become absent" % selector,
        )
        return element

    def wait_for_id(self, id):
        return self._wait_on(
            ec.presence_of_element_located((By.ID, id)),
            "presence of DOM ID [%s]" % id,
        )

    def _wait_on(self, condition, on_str=None):
        if on_str is None:
            on_str = str(condition)
        message = "Timeout waiting on %s." % on_str
        wait = self.wait()
        return wait.until(condition, message)

    def action_chains(self):
        return ActionChains(self.driver)

    def send_enter(self, element):
        element.send_keys(Keys.ENTER)

    def send_escape(self, element):
        element.send_keys(Keys.ESCAPE)

    def wait(self, timeout=UNSPECIFIED_TIMEOUT):
        if timeout is UNSPECIFIED_TIMEOUT:
            timeout = self.default_timeout
        return WebDriverWait(self.driver, timeout)

    def click_xpath(self, xpath):
        element = self.driver.find_element_by_xpath(xpath)
        element.click()

    def click_label(self, text):
        element = self.driver.find_element_by_link_text(text)
        element.click()

    def click_selector(self, selector):
        element = self.driver.find_element_by_css_selector(selector)
        element.click()

    def fill(self, form, info):
        for key, value in info.items():
            input_element = form.find_element_by_name(key)
            input_element.send_keys(value)

    def click_submit(self, form):
        submit_button = form.find_element_by_css_selector("input[type='submit']")
        submit_button.click()

    def prepend_timeout_message(self, timeout_exception, message):
        return TimeoutException(
            msg=message + (timeout_exception.msg or ''),
            screen=timeout_exception.screen,
            stacktrace=timeout_exception.stacktrace,
        )


def exception_indicates_stale_element(exception):
    return "stale" in str(exception)
