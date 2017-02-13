"""A mixin to extend a class that has self.driver with higher-level constructs.

This should be mixed into classes with a self.driver and self.default_timeout
attribute.
"""

from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait

UNSPECIFIED_TIMEOUT = object()


class HasDriver:

    def assert_xpath(self, xpath):
        assert self.driver.find_element_by_xpath(xpath)

    def assert_selector(self, selector):
        assert self.driver.find_element_by_css_selector(selector)

    def assert_selector_absent_or_hidden(self, selector):
        elements = self.driver.find_elements_by_css_selector(selector)
        for element in elements:
            assert not element.is_displayed()

    def assert_selector_absent(self, selector):
        assert len(self.driver.find_elements_by_css_selector(selector)) == 0

    def wait_for_xpath(self, xpath):
        wait = self.wait()
        element = wait.until(ec.presence_of_element_located((By.XPATH, xpath)))
        return element

    def wait_for_xpath_visible(self, xpath):
        wait = self.wait()
        element = wait.until(ec.visibility_of_element_located((By.XPATH, xpath)))
        return element

    def wait_for_selector(self, selector):
        wait = self.wait()
        element = wait.until(ec.presence_of_element_located((By.CSS_SELECTOR, selector)))
        return element

    def wait_for_selector_visible(self, selector):
        wait = self.wait()
        return wait.until(ec.visibility_of_element_located((By.CSS_SELECTOR, selector)))

    def wait_for_selector_absent_or_hidden(self, selector):
        wait = self.wait()
        return wait.until(ec.invisibility_of_element_located((By.CSS_SELECTOR, selector)))

    def wait_for_selector_absent(self, selector):
        wait = self.wait()
        return wait.until(lambda driver: len(driver.find_elements_by_css_selector(selector)) == 0)

    def wait_for_id(self, id):
        wait = self.wait()
        element = wait.until(ec.presence_of_element_located((By.ID, id)))
        return element

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
