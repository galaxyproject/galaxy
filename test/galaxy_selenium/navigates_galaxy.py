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

    def history_panel_wait_for_hid_ok(self, hid, timeout=30):
        current_history_id = self.current_history_id()

        def history_has_hid(driver):
            contents = self.api_get("histories/%s/contents" % current_history_id)
            return any([d for d in contents if d["hid"] == hid])

        self.wait(timeout).until(history_has_hid)
        contents = self.api_get("histories/%s/contents" % current_history_id)
        history_item = [d for d in contents if d["hid"] == hid][0]
        history_item_selector_okay = "#%s-%s.state-ok" % (history_item["history_content_type"], history_item["id"])
        self.wait_for_selector_visible(history_item_selector_okay)

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

    def workflow_index_open(self):
        self.home()
        self.click_masthead_workflow()

    def workflow_index_table_elements(self):
        self.wait_for_selector_visible(".manage-table tbody")
        table_elements = self.driver.find_elements_by_css_selector(".manage-table tbody > tr")
        # drop header
        return table_elements[1:]

    def workflow_index_click_option(self, option_title, workflow_index=0):
        table_elements = self.workflow_index_table_elements()
        workflow_row = table_elements[workflow_index]
        workflow_button = workflow_row.find_element_by_css_selector(".menubutton")
        workflow_button.click()
        menu_element = self.wait_for_selector_visible(".popmenu-wrapper .dropdown-menu")
        menu_options = menu_element.find_elements_by_css_selector("li a")
        found_option = False
        for menu_option in menu_options:
            if option_title in menu_option.text:
                menu_option.click()
                found_option = True
                break

        if not found_option:
            raise AssertionError("Failed to find workflow action option with title [%s]" % option_title)

    def workflow_run_submit(self):
        button = self.wait_for_selector(".ui-form-header button")
        button.click()

    def tool_open(self, tool_id):
        link_element = self.wait_for_selector('a[href$="tool_runner?tool_id=%s"]' % tool_id)
        link_element.click()

    def tool_parameter_div(self, expanded_parameter_id):
        return self.wait_for_selector("div.ui-form-element[tour_id$='%s']" % expanded_parameter_id)

    def tool_set_value(self, expanded_parameter_id, value, expected_type=None, test_data_resolver=None):
        div_element = self.tool_parameter_div(expanded_parameter_id)
        assert div_element
        if expected_type == "data":
            div_selector = "div.ui-form-element[tour_id$='%s']" % expanded_parameter_id
            self.select2_set_value(div_selector, value)
        else:
            input_element = div_element.find_element_by_css_selector("input")
            # Clear default value
            input_element.clear()
            input_element.send_keys(value)

    def tool_execute(self):
        execute_button = self.wait_for_selector("button#execute")
        execute_button.click()

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

    def history_panel_item_selector(self, hid, wait=False):
        current_history_id = self.current_history_id()
        contents = self.api_get("histories/%s/contents" % current_history_id)
        try:
            history_item = [d for d in contents if d["hid"] == hid][0]
        except IndexError:
            raise Exception("Could not find history item with hid [%s] in contents [%s]" % (hid, contents))
        history_item_selector = "#%s-%s" % (history_item["history_content_type"], history_item["id"])
        if wait:
            self.wait_for_selector_visible(history_item_selector)
        return history_item_selector

    def modal_body_selector(self):
        return ".modal-body"

    def history_panel_item_body_selector(self, hid, wait=False):
        selector = "%s %s" % (self.history_panel_item_selector(hid), self.test_data["historyPanel"]["selectors"]["hda"]["body"])
        if wait:
            self.wait_for_selector_visible(selector)
        return selector

    def hda_div_selector(self, hda_id):
        return "#dataset-%s" % hda_id

    def hda_body_selector(self, hda_id):
        return "%s %s" % (self.hda_div_selector(hda_id), self.test_data["historyPanel"]["selectors"]["hda"]["body"])

    def hda_click_primary_action_button(self, hid, button_key):
        self.history_panel_click_item_title(hid=hid, wait=True)
        body_selector = self.history_panel_item_body_selector(hid=hid, wait=True)

        buttons_selector = body_selector + " " + self.test_data["historyPanel"]["selectors"]["hda"]["primaryActionButtons"]
        self.wait_for_selector_visible(buttons_selector)

        button_def = self.test_data["historyPanel"]["hdaPrimaryActionButtons"][button_key]
        button_selector = button_def["selector"]
        button_item = self.wait_for_selector_visible("%s %s" % (buttons_selector, button_selector))
        return button_item.click()

    def history_panel_click_item_title(self, **kwds):
        if "hda_id" in kwds:
            item_selector = self.hda_div_selector(kwds["hda_id"])
        else:
            item_selector = self.history_panel_item_selector(kwds["hid"])
        title_selector = "%s .title" % item_selector
        title_element = self.wait_for_selector(title_selector)
        title_element.click()
        if kwds.get("wait", False):
            # Find a better way to wait for transition
            time.sleep(.5)

    def click_hda_title(self, hda_id, wait=False):
        # TODO: Replace with calls to history_panel_click_item_title.
        return self.history_panel_click_item_title(hda_id=hda_id, wait=wait)

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
        return self._assert_message("error", contains=contains)

    def assert_warning_message(self, contains=None):
        return self._assert_message("warning", contains=contains)

    def _assert_message(self, type, contains=None):
        element = self.wait_for_selector(self.test_data["selectors"]["messages"][type])
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

    def select2_set_value(self, container_selector, value, with_click=True):
        # There are two hacky was to select things from the select2 widget -
        #   with_click=True: This simulates the mouse click after the suggestion contains
        #                    only the selected value.
        #   with_click=False: This presses enter on the selection. Not sure
        #                     why.
        # with_click seems to work in all situtations - the enter methods
        # doesn't seem to work with the tool form for some reason.
        container_elem = self.wait_for_selector(container_selector)
        text_element = container_elem.find_element_by_css_selector("input[type='text']")
        text_element.send_keys(value)
        # Wait for select2 options to load and then click to add this one.
        drop_elem = self.wait_for_selector_visible("#select2-drop")
        # Sleep seems to be needed - at least for send_enter.
        time.sleep(.5)
        if not with_click:
            # Wait for select2 options to load and then click to add this one.
            self.send_enter(text_element)
        else:
            select_elem = drop_elem.find_elements_by_css_selector(".select2-result-label")[0]
            action_chains = self.action_chains()
            action_chains.move_to_element(select_elem).click().perform()
        self.wait_for_selector_absent_or_hidden("#select2-drop")
