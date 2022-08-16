"""A mixin to extend a class that has self.driver with higher-level constructs.

This should be mixed into classes with a self.driver and self.default_timeout
attribute.
"""

from selenium.common.exceptions import TimeoutException as SeleniumTimeoutException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait

UNSPECIFIED_TIMEOUT = object()


class HasDriver:
    driver: WebDriver

    def re_get_with_query_params(self, params_str: str):
        driver = self.driver
        new_url = driver.current_url
        if "?" not in new_url:
            new_url += "?"
        new_url += params_str
        driver.get(new_url)

    def assert_xpath(self, xpath):
        assert self.driver.find_element_by_xpath(xpath)

    def assert_selector(self, selector):
        assert self.driver.find_element_by_css_selector(selector)

    def assert_selector_absent_or_hidden(self, selector):
        elements = self.driver.find_elements_by_css_selector(selector)
        for element in elements:
            assert not element.is_displayed()

    def assert_absent_or_hidden(self, selector_template):
        elements = self.find_elements(selector_template)
        for element in elements:
            assert not element.is_displayed()

    def selector_is_displayed(self, selector):
        element = self.driver.find_element_by_css_selector(selector)
        return element.is_displayed()

    def is_displayed(self, selector_template):
        element = self.driver.find_element(*selector_template.element_locator)
        return element.is_displayed()

    def assert_selector_absent(self, selector):
        assert len(self.driver.find_elements_by_css_selector(selector)) == 0

    def find_elements(self, selector_template):
        return self.driver.find_elements(*selector_template.element_locator)

    def assert_absent(self, selector_template):
        assert len(self.find_elements(selector_template)) == 0

    def element_absent(self, selector_template):
        return len(self.find_elements(selector_template)) == 0

    def wait_for_xpath(self, xpath, **kwds):
        element = self._wait_on(
            ec.presence_of_element_located((By.XPATH, xpath)), f"XPATH selector [{xpath}] to become present", **kwds
        )
        return element

    def wait_for_xpath_visible(self, xpath, **kwds):
        element = self._wait_on(
            ec.visibility_of_element_located((By.XPATH, xpath)), f"XPATH selector [{xpath}] to become visible", **kwds
        )
        return element

    def wait_for_selector(self, selector, **kwds):
        element = self._wait_on(
            ec.presence_of_element_located((By.CSS_SELECTOR, selector)),
            f"CSS selector [{selector}] to become present",
            **kwds,
        )
        return element

    def wait_for_present(self, selector_template, **kwds):
        element = self._wait_on(
            ec.presence_of_element_located(selector_template.element_locator),
            f"{selector_template.description} to become present",
            **kwds,
        )
        return element

    def wait_for_visible(self, selector_template, **kwds):
        element = self._wait_on(
            ec.visibility_of_element_located(selector_template.element_locator),
            f"{selector_template.description} to become visible",
            **kwds,
        )
        return element

    def wait_for_selector_visible(self, selector, **kwds):
        element = self._wait_on(
            ec.visibility_of_element_located((By.CSS_SELECTOR, selector)),
            f"CSS selector [{selector}] to become visible",
            **kwds,
        )
        return element

    def wait_for_selector_clickable(self, selector, **kwds):
        element = self._wait_on(
            ec.element_to_be_clickable((By.CSS_SELECTOR, selector)),
            f"CSS selector [{selector}] to become clickable",
            **kwds,
        )
        return element

    def wait_for_clickable(self, selector_template, **kwds):
        element = self._wait_on(
            ec.element_to_be_clickable(selector_template.element_locator),
            f"{selector_template.description} to become clickable",
            **kwds,
        )
        return element

    def wait_for_selector_absent_or_hidden(self, selector, **kwds):
        element = self._wait_on(
            ec.invisibility_of_element_located((By.CSS_SELECTOR, selector)),
            f"CSS selector [{selector}] to become absent or hidden",
            **kwds,
        )
        return element

    def wait_for_selector_absent(self, selector, **kwds):
        element = self._wait_on(
            lambda driver: len(driver.find_elements_by_css_selector(selector)) == 0,
            f"CSS selector [{selector}] to become absent",
            **kwds,
        )
        return element

    def wait_for_element_count_of_at_least(self, selector_template, n, **kwds):
        element = self._wait_on(
            lambda driver: len(driver.find_elements(*selector_template.element_locator)) >= n,
            f"{selector_template.description} to become absent",
            **kwds,
        )
        return element

    def wait_for_absent(self, selector_template, **kwds):
        element = self._wait_on(
            lambda driver: len(driver.find_elements(*selector_template.element_locator)) == 0,
            f"{selector_template.description} to become absent",
            **kwds,
        )
        return element

    def wait_for_absent_or_hidden(self, selector_template, **kwds):
        element = self._wait_on(
            ec.invisibility_of_element_located(selector_template.element_locator),
            f"{selector_template.description} to become absent or hidden",
            **kwds,
        )
        return element

    def wait_for_id(self, id, **kwds):
        return self._wait_on(ec.presence_of_element_located((By.ID, id)), f"presence of DOM ID [{id}]", **kwds)

    def click(self, selector_template):
        element = self.driver.find_element(*selector_template.element_locator)
        element.click()

    def _timeout_message(self, on_str):
        return f"Timeout waiting on {on_str}."

    def _wait_on(self, condition, on_str=None, **kwds):
        if on_str is None:
            on_str = str(condition)
        wait = self.wait(**kwds)
        return wait.until(condition, self._timeout_message(on_str))

    def action_chains(self):
        return ActionChains(self.driver)

    def send_enter(self, element):
        element.send_keys(Keys.ENTER)

    def send_escape(self, element=None):
        if element is None:
            self.action_chains().send_keys(Keys.ESCAPE)
        else:
            element.send_keys(Keys.ESCAPE)

    def send_backspace(self, element):
        element.send_keys(Keys.BACKSPACE)

    def timeout_for(self, **kwds) -> float:
        ...

    def wait(self, timeout=UNSPECIFIED_TIMEOUT, **kwds):
        if timeout is UNSPECIFIED_TIMEOUT:
            timeout = self.timeout_for(**kwds)
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
        msg = message
        timeout_msg = timeout_exception.msg
        if timeout_msg:
            msg += f" {timeout_msg}"
        return SeleniumTimeoutException(
            msg=msg,
            screen=timeout_exception.screen,
            stacktrace=timeout_exception.stacktrace,
        )

    def accept_alert(self):
        try:
            alert = self.driver.switch_to.alert
            alert.accept()
        finally:
            self.driver.switch_to.default_content()


def exception_indicates_click_intercepted(exception):
    return "click intercepted" in str(exception)


def exception_indicates_not_clickable(exception):
    return "not clickable" in str(exception)


def exception_indicates_stale_element(exception):
    return "stale" in str(exception)


__all__ = (
    "exception_indicates_click_intercepted",
    "exception_indicates_not_clickable",
    "exception_indicates_stale_element",
    "HasDriver",
    "SeleniumTimeoutException",
)
