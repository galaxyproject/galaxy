"""A mixing that extends a HasDriver class with Galaxy-specific utilities.

Implementer must provide a self.build_url method to target Galaxy.
"""
from __future__ import print_function

import contextlib
import random
import string
import time

import requests
import yaml

from .data import NAVIGATION_DATA
from .has_driver import HasDriver
from . import sizzle

# Test case data
DEFAULT_PASSWORD = '123456'


class NullTourCallback(object):

    def handle_step(self, step, step_index):
        pass


class NavigatesGalaxy(HasDriver):

    default_password = DEFAULT_PASSWORD

    def get(self, url=""):
        full_url = self.build_url(url)
        return self.driver.get(full_url)

    @property
    def navigation_data(self):
        return NAVIGATION_DATA

    def home(self):
        self.get()
        self.wait_for_selector_visible("#masthead")
        self.wait_for_selector_visible("#current-history-panel")

    def switch_to_main_panel(self):
        self.driver.switch_to.frame(self.navigation_data["selectors"]["frames"]["main"])

    @contextlib.contextmanager
    def main_panel(self):
        try:
            self.switch_to_main_panel()
            yield
        finally:
            self.driver.switch_to.default_content

    def api_get(self, endpoint, data={}, raw=False):
        full_url = self.build_url("api/" + endpoint, for_selenium=False)
        response = requests.get(full_url, data=data, cookies=self.selenium_to_requests_cookies())
        if raw:
            return response
        else:
            return response.json()

    def get_galaxy_session(self):
        for cookie in self.driver.get_cookies():
            if cookie["name"] == "galaxysession":
                return cookie["value"]

    def selenium_to_requests_cookies(self):
        return {
            'galaxysession': self.get_galaxy_session()
        }

    def history_panel_name_element(self):
        name_selector = self.test_data["historyPanel"]["selectors"]["history"]["name"]
        return self.wait_for_selector(name_selector)

    def current_history(self):
        history = self.api_get("histories")[0]
        return history

    def current_history_id(self):
        return self.current_history()["id"]

    def current_history_contents(self):
        current_history_id = self.current_history_id()
        history_contents = self.api_get("histories/%s/contents" % current_history_id)
        return history_contents

    def latest_history_item(self):
        history_contents = self.current_history_contents()
        assert len(history_contents) > 0
        return history_contents[-1]

    def wait_for_history(self, timeout=30, assert_ok=True):
        def history_becomes_terminal(driver):
            current_history_id = self.current_history_id()
            state = self.api_get("histories/%s" % current_history_id)["state"]
            if state not in ["running", "queued", "new", "ready"]:
                return state
            else:
                return None

        final_state = self.wait(timeout).until(history_becomes_terminal)
        if assert_ok:
            assert final_state == "ok", final_state
        return final_state

    def get_logged_in_user(self):
        return self.api_get("users/current")

    def is_logged_in(self):
        return "email" in self.get_logged_in_user()

    def _get_random_name(self, prefix=None, suffix=None, len=10):
        return '%s%s%s' % (
            prefix or '',
            ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(len)),
            suffix or '',
        )

    def _get_random_email(self, username=None, domain=None):
        username = username or 'test'
        domain = domain or 'test.test'
        return self._get_random_name(prefix=username, suffix="@" + domain)

    def submit_login(self, email, password=None):
        if password is None:
            password = self.default_password

        login_info = {
            'login': email,
            'password': password,
        }

        self.click_masthead_user()
        self.click_label(self.navigation_data["labels"]["masthead"]["userMenu"]["login"])

        with self.main_panel():
            form = self.wait_for_selector(self.navigation_data["selectors"]["loginPage"]["form"])
            self.fill(form, login_info)
            self.click_submit(form)

    def register(self, email=None, password=None, username=None, confirm=None, assert_valid=True):
        if email is None:
            email = self._get_random_email()
        if password is None:
            password = self.default_password
        if confirm is None:
            confirm = password
        if username is None:
            username = email.split("@")[0]

        self.home()
        self.click_masthead_user()
        self.click_label(self.navigation_data["labels"]["masthead"]["userMenu"]["register"])
        with self.main_panel():
            register_form_id = self.navigation_data["selectors"]["registrationPage"]["form"]
            form = self.wait_for_id(register_form_id)
            self.fill(form, dict(
                email=email,
                password=password,
                username=username,
                confirm=confirm
            ))
            self.click_xpath(self.navigation_data["selectors"]["registrationPage"]["submit_xpath"])

        if assert_valid:
            self.home()
            self.click_masthead_user()
            user_email_element = self.wait_for_xpath_visible(self.navigation_data["selectors"]["masthead"]["userMenu"]["userEmail_xpath"])
            text = user_email_element.text
            assert email in text
            assert self.get_logged_in_user()["email"] == email

            # Hide masthead menu click
            self.click_center()

    def click_center(self):
        action_chains = self.action_chains()
        center_element = self.driver.find_element_by_css_selector("#center")
        action_chains.move_to_element(center_element).click().perform()

    def perform_upload(self, test_path):
        self.home()

        upload_button = self.wait_for_selector(".upload-button")
        upload_button.click()

        local_upload_button = self.wait_for_selector("button#btn-local")
        local_upload_button.click()

        file_upload = self.wait_for_selector('input[type="file"]')
        file_upload.send_keys(test_path)

        start_button = self.wait_for_selector("button#btn-start")
        start_button.click()

        close_button = self.wait_for_selector("button#btn-close")
        close_button.click()

    def click_masthead_user(self):
        self.click_xpath(self.navigation_data["selectors"]["masthead"]["user"])

    def click_masthead_workflow(self):
        self.click_xpath(self.navigation_data["selectors"]["masthead"]["workflow"])

    def click_button_new_workflow(self):
        self.click_selector(self.navigation_data["selectors"]["workflows"]["new_button"])

    def click_history_options(self):
        history_options_button_selector = self.test_data["historyOptions"]["selectors"]["button"]
        history_options_element = self.wait_for_selector(history_options_button_selector)
        assert history_options_element.is_displayed()

        history_options_button_icon_selector = self.test_data["historyOptions"]["selectors"]["buttonIcon"]
        history_options_button_icon_element = self.wait_for_selector(history_options_button_icon_selector)
        assert history_options_button_icon_element.is_displayed()

        history_options_element.click()

    def click_history_option(self, option_label):
        # Open menu
        self.click_history_options()

        # Click labelled option
        menu_selector = self.history_options_menu_selector()
        menu_element = self.wait_for_selector(menu_selector)
        menu_selection_element = menu_element.find_element_by_xpath('//ul[@id="history-options-button-menu"]/li/a[text()[contains(.,"%s")]]' % option_label)
        menu_selection_element.click()

    def history_options_menu_selector(self):
        menu_selector = self.test_data["historyOptions"]["selectors"]["menu"]
        return menu_selector

    def hda_div_selector(self, hda_id):
        return "#dataset-%s" % hda_id

    def hda_body_selector(self, hda_id):
        return "%s %s" % (self.hda_div_selector(hda_id), self.test_data["historyPanel"]["selectors"]["hda"]["body"])

    def click_hda_title(self, hda_id, wait=False):
        expand_target = "%s .title" % self.hda_div_selector(hda_id)
        hda_element = self.wait_for_selector(expand_target)
        hda_element.click()
        if wait:
            # Find a better way to wait for transition
            time.sleep(.5)

    def logout_if_needed(self):
        if self.is_logged_in():
            self.home()
            self.click_masthead_user()
            self.click_label(self.navigation_data["labels"]["masthead"]["userMenu"]["logout"])
            self.click_label('go to the home page')
            assert not self.is_logged_in()

    def run_tour(self, path, skip_steps=[], sleep_on_steps={}, tour_callback=None):
        if tour_callback is None:
            tour_callback = NullTourCallback()

        self.home()

        with open(path, "r") as f:
            tour_dict = yaml.load(f)
        steps = tour_dict["steps"]
        for i, step in enumerate(steps):
            title = step.get("title", None)
            skip = False
            if skip_steps:
                for skip_step in skip_steps:
                    if title == skip_step:
                        skip = True

            if title in sleep_on_steps:
                time.sleep(sleep_on_steps[title])

            if skip:
                continue

            self.run_tour_step(step, i, tour_callback)

    def tour_wait_for_clickable_element(self, selector):
        wait = self.wait()
        element = wait.until(sizzle.sizzle_selector_clickable(selector))
        return element

    def tour_wait_for_element_present(self, selector):
        wait = self.wait()
        element = wait.until(sizzle.sizzle_presence_of_selector(selector))
        return element

    def get_tooltip_text(self, element, sleep=0, click_away=True):
        tooltip_selector = self.test_data["selectors"]["tooltipBalloon"]
        self.wait_for_selector_absent(tooltip_selector)

        action_chains = self.action_chains()
        action_chains.move_to_element(element)
        action_chains.perform()

        if sleep > 0:
            time.sleep(sleep)

        tooltip_element = self.wait_for_selector_visible(tooltip_selector)
        text = tooltip_element.text
        if click_away:
            self.click_center()
        return text

    def assert_tooltip_text(self, element, expected, sleep=0, click_away=True):
        text = self.get_tooltip_text(element, sleep=sleep, click_away=click_away)
        assert text == expected, "Tooltip text [%s] was not expected text [%s]." % (text, expected)

    def assert_error_message(self, contains=None):
        element = self.wait_for_selector(self.test_data["selectors"]["messages"]["error"])
        assert element, "No error message found, one expected."
        if contains is not None:
            assert contains in element.text

    def assert_no_error_message(self):
        self.assert_selector_absent(self.test_data["selectors"]["messages"]["error"])

    def run_tour_step(self, step, step_index, tour_callback):
        preclick = step.get("preclick", [])
        for preclick_selector in preclick:
            print("(Pre)Clicking %s" % preclick_selector)
            element = self.tour_wait_for_clickable_element(preclick_selector)
            element.click()

        element_str = step.get("element", None)
        if element_str is not None:
            print("Waiting for element %s" % element_str)
            element = self.tour_wait_for_element_present(element_str)
            assert element is not None

        textinsert = step.get("textinsert", None)
        if textinsert is not None:
            element.send_keys(textinsert)

        tour_callback.handle_step(step, step_index)

        postclick = step.get("postclick", [])
        for postclick_selector in postclick:
            print("(Post)Clicking %s" % postclick_selector)
            element = self.tour_wait_for_clickable_element(postclick_selector)
            element.click()
