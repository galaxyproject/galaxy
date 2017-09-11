"""A mixing that extends a HasDriver class with Galaxy-specific utilities.

Implementer must provide a self.build_url method to target Galaxy.
"""
from __future__ import print_function

import contextlib
import random
import string
import time

from functools import partial, wraps

import requests
import yaml

from .data import NAVIGATION_DATA
from .has_driver import exception_indicates_stale_element, HasDriver
from . import sizzle

# Test case data
DEFAULT_PASSWORD = '123456'


class NullTourCallback(object):

    def handle_step(self, step, step_index):
        pass


def retry_call_during_transitions(f, attempts=5, sleep=.1, exception_check=exception_indicates_stale_element):
    previous_attempts = 0
    while True:
        try:
            return f()
        except Exception as e:
            if previous_attempts > attempts:
                raise

            if not exception_check(e):
                raise

            time.sleep(sleep)
            previous_attempts += 1


def retry_during_transitions(f, attempts=5, sleep=.1, exception_check=exception_indicates_stale_element):

    @wraps(f)
    def _retry(*args, **kwds):
        return retry_call_during_transitions(partial(f, *args, **kwds), attempts=attempts, sleep=sleep, exception_check=exception_check)

    return _retry


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
            self.driver.switch_to.default_content()

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

    def history_panel_name_selector(self):
        name_selector = self.test_data["historyPanel"]["selectors"]["history"]["name"]
        return name_selector

    def history_panel_name_element(self):
        return self.wait_for_selector(self.history_panel_name_selector())

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

    def history_panel_wait_for_hid_ok(self, hid, timeout=60, allowed_force_refreshes=0):
        self.history_panel_wait_for_hid_state(hid, 'ok', timeout=timeout, allowed_force_refreshes=allowed_force_refreshes)

    def history_panel_wait_for_hid_visible(self, hid, timeout=60, allowed_force_refreshes=0):
        current_history_id = self.current_history_id()

        def history_has_hid(driver):
            contents = self.api_get("histories/%s/contents" % current_history_id)
            return any([d for d in contents if d["hid"] == hid])

        self.wait(timeout).until(history_has_hid)
        contents = self.api_get("histories/%s/contents" % current_history_id)
        history_item = [d for d in contents if d["hid"] == hid][0]
        history_item_selector = "#%s-%s" % (history_item["history_content_type"], history_item["id"])

        try:
            self.history_item_wait_for_selector(history_item_selector, allowed_force_refreshes)
        except self.TimeoutException as e:
            dataset_elements = self.driver.find_elements_by_css_selector("#current-history-panel .list-items div")
            div_ids = [d.get_attribute('id') for d in dataset_elements]
            template = "Failed waiting on history item %d to become visible, visible datasets include [%s]."
            message = template % (hid, ",".join(div_ids))
            raise self.prepend_timeout_message(e, message)
        return history_item_selector

    def history_item_wait_for_selector(self, history_item_selector, allowed_force_refreshes):
        attempt = 0
        while True:
            try:
                rval = self.wait_for_selector_visible(history_item_selector)
                break
            except self.TimeoutException:
                if attempt >= allowed_force_refreshes:
                    raise

            attempt += 1
            self.history_panel_refresh_click()
        return rval

    def history_panel_wait_for_hid_hidden(self, hid, timeout=60):
        current_history_id = self.current_history_id()
        contents = self.api_get("histories/%s/contents" % current_history_id)
        history_item = [d for d in contents if d["hid"] == hid][0]
        history_item_selector = "#%s-%s" % (history_item["history_content_type"], history_item["id"])
        self.wait_for_selector_absent(history_item_selector)
        return history_item_selector

    def history_panel_wait_for_hid_state(self, hid, state, timeout=60, allowed_force_refreshes=0):
        history_item_selector = self.history_panel_wait_for_hid_visible(hid, timeout=timeout, allowed_force_refreshes=allowed_force_refreshes)
        history_item_selector_state = "%s.state-%s" % (history_item_selector, state)
        try:
            self.history_item_wait_for_selector(history_item_selector_state, allowed_force_refreshes)
        except self.TimeoutException as e:
            history_item = self.driver.find_element_by_css_selector(history_item_selector)
            current_state = "UNKNOWN"
            classes = history_item.get_attribute("class").split(" ")
            for clazz in classes:
                if clazz.startswith("state-"):
                    current_state = clazz[len("state-"):]
            template = "Failed waiting on history item %d state to change to [%s] current state [%s]. "
            message = template % (hid, state, current_state)
            raise self.prepend_timeout_message(e, message)
        return history_item_selector_state

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

    def submit_login(self, email, password=None, assert_valid=True):
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

        if assert_valid:
            self.wait_for_logged_in()

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
            # Give the browser a bit of time to submit the request.
            # It would be good to eliminate this sleep, but it can't be because Galaxy
            # doesn't swap the "User" menu automatically after it registers a user and
            # and the donemessage visible comment below doesn't work when using Selenium.
            # Something about the Selenium session or quickness of registering causes the
            # following in the Galaxy logs which gets propaged to the GUI as a generic error:
            # /api/histories/cfc05ccec54895e2/contents?keys=type_id%2Celement_count&order=hid&v=dev&q=history_content_type&q=deleted&q=purged&q=visible&qv=dataset_collection&qv=False&qv=False&qv=True HTTP/1.1" 403 - "http://localhost:8080/"
            # Like the logged in user doesn't have permission to the previously anonymous user's
            # history, it is odd but I cannot replicate this outside of Selenium.
            time.sleep(.35)

        if assert_valid:
            # self.wait_for_selector_visible(".donemessage")
            self.home()
            self.click_masthead_user()
            # Make sure the user menu was dropped down
            user_menu = self.wait_for_selector_visible("ul.nav#user .dropdown-menu")
            try:
                user_email_element = self.wait_for_xpath_visible(self.navigation_data["selectors"]["masthead"]["userMenu"]["userEmail_xpath"])
            except self.TimeoutException as e:
                menu_items = user_menu.find_elements_by_css_selector("li a")
                menu_text = [mi.text for mi in menu_items]
                message = "Failed to find logged in message in menu items %s" % ", ".join(menu_text)
                raise self.prepend_timeout_message(e, message)

            text = user_email_element.text
            assert email in text
            assert self.get_logged_in_user()["email"] == email

            # Hide masthead menu click
            self.click_center()

    def wait_for_logged_in(self):
        try:
            self.wait_for_selector_visible("a.loggedin-only")
        except self.TimeoutException as e:
            user_info = self.api_get("users/current")
            if "username" in user_info:
                template = "Failed waiting for masthead to update for login, but user API response indicates [%s] is logged in. This seems to be a bug in Galaxy. API response was [%s]. "
                message = template % (user_info["username"], user_info)
            else:
                template = "Failed waiting for masthead to update for login, API indicates no user is logged in - there is a problem with this test. API response was [%s]. "
                message = template % user_info
            raise self.prepend_timeout_message(e, message)

    def click_center(self):
        action_chains = self.action_chains()
        center_element = self.driver.find_element_by_css_selector("#center")
        action_chains.move_to_element(center_element).click().perform()

    def perform_upload(self, test_path, ext=None, genome=None, ext_all=None, genome_all=None):
        self.home()
        self.upload_start_click()

        self.upload_set_footer_extension(ext_all)
        self.upload_set_footer_genome(genome_all)

        self.upload_queue_local_file(test_path)

        if ext is not None:
            self.wait_for_selector_visible('.upload-extension')
            self.select2_set_value(".upload-extension", ext)

        if genome is not None:
            self.wait_for_selector_visible('.upload-genome')
            self.select2_set_value(".upload-genome", genome)

        self.upload_start()

        self.wait_for_and_click_selector("button#btn-close")

    def upload_list(self, test_paths, name="test", ext=None, genome=None, hide_source_items=True):
        self._collection_upload_start(test_paths, ext, genome, "List")
        if not hide_source_items:
            self.collection_builder_hide_originals()

        self.collection_builder_set_name(name)
        self.collection_builder_create()

    def upload_pair(self, test_paths, name="test", ext=None, genome=None, hide_source_items=True):
        self._collection_upload_start(test_paths, ext, genome, "Pair")
        if not hide_source_items:
            self.collection_builder_hide_originals()

        self.collection_builder_set_name(name)
        self.collection_builder_create()

    def upload_paired_list(self, test_paths, name="test", ext=None, genome=None, hide_source_items=True):
        self._collection_upload_start(test_paths, ext, genome, "List of Pairs")
        if not hide_source_items:
            self.collection_builder_hide_originals()

        self.collection_builder_clear_filters()
        # TODO: generalize and loop these clicks so we don't need the assert
        assert len(test_paths) == 2
        self.collection_builder_click_paired_item("forward", 0)
        self.collection_builder_click_paired_item("reverse", 1)

        self.collection_builder_set_name(name)
        self.collection_builder_create()

    def _collection_upload_start(self, test_paths, ext, genome, collection_type):
        # Perform upload of files and open the collection builder for specified
        # type.
        self.home()
        self.upload_start_click()
        self.upload_tab_click("collection")

        self.upload_set_footer_extension(ext, tab_id="collection")
        self.upload_set_footer_genome(genome, tab_id="collection")
        self.upload_set_collection_type(collection_type)

        for test_path in test_paths:
            self.upload_queue_local_file(test_path, tab_id="collection")

        self.upload_start(tab_id="collection")
        self.upload_build()

    def upload_tab_click(self, tab):
        tab_tag_id = "#tab-title-link-%s" % tab
        self.wait_for_and_click_selector(tab_tag_id)

    def upload_start_click(self):
        self.wait_for_and_click_selector(".upload-button")

    @retry_during_transitions
    def upload_set_footer_extension(self, ext, tab_id="regular"):
        if ext is not None:
            selector = 'div#%s .upload-footer-extension' % tab_id
            self.wait_for_selector_visible(selector)
            self.select2_set_value(selector, ext)

    @retry_during_transitions
    def upload_set_footer_genome(self, genome, tab_id="regular"):
        if genome is not None:
            selector = 'div#%s .upload-footer-genome' % tab_id
            self.wait_for_selector_visible(selector)
            self.select2_set_value(selector, genome)

    @retry_during_transitions
    def upload_set_collection_type(self, collection_type):
        self.wait_for_selector_visible(".upload-footer-collection-type")
        self.select2_set_value(".upload-footer-collection-type", collection_type)

    def upload_start(self, tab_id="regular"):
        self.wait_for_and_click_selector("div#%s button#btn-start" % tab_id)

    @retry_during_transitions
    def upload_build(self):
        build_button = self.wait_for_selector_clickable("div#collection button#btn-build")
        # TODO: Eliminate the need for this hack. This hack is in here because the test
        # occasionally fails at the next step because the UI has not transitioned to the
        # new content. I assume that means this click is sent before the callback is
        # registered.
        time.sleep(.5)
        build_button.click()

    def upload_queue_local_file(self, test_path, tab_id="regular"):
        self.wait_for_and_click_selector("div#%s button#btn-local" % tab_id)

        file_upload = self.wait_for_selector('div#%s input[type="file"]' % tab_id)
        file_upload.send_keys(test_path)

    def workflow_editor_click_option(self, option_label):
        self.workflow_editor_click_options()
        menu_element = self.workflow_editor_options_menu_element()
        option_elements = menu_element.find_elements_by_css_selector("a")
        assert len(option_elements) > 0, "Failed to find workflow editor options"
        time.sleep(1)
        found_option = False
        for option_element in option_elements:
            if option_label in option_element.text:
                action_chains = self.action_chains()
                action_chains.move_to_element(option_element)
                action_chains.click()
                action_chains.perform()
                found_option = True
                break

        if not found_option:
            raise Exception("Failed to find workflow editor option with label [%s]" % option_label)

    def workflow_editor_click_options(self):
        return self.wait_for_and_click_selector("#workflow-options-button")

    def workflow_editor_options_menu_element(self):
        return self.wait_for_selector_visible("#workflow-options-button-menu")

    def workflow_index_open(self):
        self.home()
        self.click_masthead_workflow()

    def workflow_index_table_elements(self):
        self.wait_for_selector_visible("tbody.workflow-search")
        table_elements = self.driver.find_elements_by_css_selector("tbody.workflow-search > tr:not([style*='display: none'])")
        return table_elements

    def workflow_index_table_row(self, workflow_index=0):
        return self.workflow_index_table_elements()[workflow_index]

    def workflow_index_click_search(self):
        return self.wait_for_and_click_selector("input.search-wf")

    def workflow_index_click_import(self):
        self.wait_for_and_click_selector(self.test_data["selectors"]["workflows"]["import_button"])

    def workflow_index_rename(self, new_name, workflow_index=0):
        self.workflow_index_click_option("Rename", workflow_index=workflow_index)
        alert = self.driver.switch_to.alert
        alert.send_keys(new_name)
        alert.accept()

    def workflow_index_click_option(self, option_title, workflow_index=0):
        workflow_row = self.workflow_index_table_row(workflow_index=workflow_index)
        workflow_button = workflow_row.find_element_by_css_selector(".menubutton")
        workflow_button.click()
        menu_element = self.wait_for_selector_visible("ul.action-dpd")
        menu_options = menu_element.find_elements_by_css_selector("li a")
        found_option = False
        for menu_option in menu_options:
            if option_title in menu_option.text:
                menu_option.click()
                found_option = True
                break

        if not found_option:
            raise AssertionError("Failed to find workflow action option with title [%s]" % option_title)

    def workflow_index_click_tag_display(self, workflow_index=0):
        workflow_row_element = self.workflow_index_table_row(workflow_index)
        tag_display = workflow_row_element.find_element_by_css_selector(".tags-display")
        tag_display.click()

    def workflow_index_tags(self, workflow_index=0):
        workflow_row_element = self.workflow_index_table_row(workflow_index)
        tag_display = workflow_row_element.find_element_by_css_selector(".tags-display")
        tag_spans = tag_display.find_elements_by_css_selector("span.label")
        tags = []
        for tag_span in tag_spans:
            tags.append(tag_span.text)
        return tags

    def workflow_import_submit_url(self, url):
        form_element = self.wait_for_selector_visible("#center form")
        url_element = form_element.find_element_by_css_selector("input[type='text']")
        url_element.send_keys(url)
        self.click_submit(form_element)

    def workflow_sharing_click_publish(self):
        self.wait_for_and_click_selector("input[name='make_accessible_and_publish']")

    def tagging_add(self, tags, auto_closes=True, parent_selector=""):

        for i, tag in enumerate(tags):
            if auto_closes or i == 0:
                tag_area = parent_selector + ".tags-input input[type='text']"
                tag_area = self.wait_for_selector_clickable(tag_area)
                tag_area.click()

            tag_area.send_keys(tag)
            self.send_enter(tag_area)

    def workflow_run_submit(self):
        self.wait_for_and_click_selector("button.btn-primary")

    def tool_open(self, tool_id):
        self.wait_for_and_click_selector('a[href$="tool_runner?tool_id=%s"]' % tool_id)

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
        self.wait_for_and_click_selector("button#execute")

    def click_masthead_user(self):
        self.click_xpath(self.navigation_data["selectors"]["masthead"]["user"])

    def click_masthead_workflow(self):
        self.click_xpath(self.navigation_data["selectors"]["masthead"]["workflow"])

    def click_button_new_workflow(self):
        self.wait_for_and_click_selector(self.navigation_data["selectors"]["workflows"]["new_button"])

    def wait_for_sizzle_selector_clickable(self, selector):
        element = self._wait_on(
            sizzle.sizzle_selector_clickable(selector),
            "sizzle/jQuery selector [%s] to become clickable" % selector,
        )
        return element

    @retry_during_transitions
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
        self.wait_for_selector_visible(menu_selector)
        menu_item_sizzle_selector = '#history-options-button-menu > li > a:contains("%s")' % option_label
        menu_selection_element = self.wait_for_sizzle_selector_clickable(menu_item_sizzle_selector)
        menu_selection_element.click()

    def history_options_menu_selector(self):
        menu_selector = self.test_data["historyOptions"]["selectors"]["menu"]
        return menu_selector

    def history_panel_add_tags(self, tags):
        tag_icon_selector = self.test_data['historyPanel']['selectors']['history']['tagIcon']
        tag_area_selector = self.test_data['historyPanel']['selectors']['history']['tagArea']

        if not self.selector_is_displayed(tag_area_selector):
            self.wait_for_and_click_selector(tag_icon_selector)

        tag_area_selector += ' .tags-input input'
        tag_area = self.wait_for_and_click_selector(tag_area_selector)

        for tag in tags:
            tag_area.send_keys(tag)
            self.send_enter(tag_area)
            time.sleep(.5)

    def history_panel_rename(self, new_name):
        editable_text_input_element = self.history_panel_click_to_rename()
        editable_text_input_element.send_keys(new_name)
        self.send_enter(editable_text_input_element)

    def history_panel_click_to_rename(self):
        self.wait_for_and_click_selector(self.history_panel_name_selector())
        return self.wait_for_selector(self.history_panel_edit_title_input_selector())

    def history_panel_edit_title_input_selector(self):
        return self.test_data["historyPanel"]["selectors"]["history"]["nameEditableTextInput"]

    def history_panel_refresh_click(self):
        self.wait_for_and_click_selector("#history-refresh-button")

    def history_panel_multi_operations_selector(self):
        return self.test_data["historyPanel"]["selectors"]["history"]["multiOperationsIcon"]

    def history_panel_multi_operations_show(self):
        operations_selector = self.history_panel_multi_operations_selector()
        self.wait_for_and_click_selector(operations_selector)

    def history_panel_muli_operation_select_hid(self, hid):
        item_selector = self.history_panel_item_selector(hid, wait=True)
        operation_radio_selector = "%s .selector" % item_selector
        self.wait_for_and_click_selector(operation_radio_selector)

    def history_panel_multi_operation_action_selector(self):
        return self.test_data["historyPanel"]["selectors"]["history"]["multiOperationsActionBtn"]

    def history_panel_multi_operation_action_click(self, action):
        time.sleep(5)
        self.wait_for_and_click_selector(self.history_panel_multi_operation_action_selector())
        menu_element = self.wait_for_selector_visible(".list-action-menu.open")
        action_element = menu_element.find_element_by_link_text(action)
        action_element.click()

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
        return self.wait_for_and_click_selector("%s %s" % (buttons_selector, button_selector))

    def history_panel_click_item_title(self, **kwds):
        if "hda_id" in kwds:
            item_selector = self.hda_div_selector(kwds["hda_id"])
        else:
            item_selector = self.history_panel_item_selector(kwds["hid"])
        title_selector = "%s .title" % item_selector
        self.wait_for_and_click_selector(title_selector)
        if kwds.get("wait", False):
            # Find a better way to wait for transition
            time.sleep(.5)

    def click_hda_title(self, hda_id, wait=False):
        # TODO: Replace with calls to history_panel_click_item_title.
        return self.history_panel_click_item_title(hda_id=hda_id, wait=wait)

    def collection_builder_set_name(self, name):
        name_element = self.wait_for_selector_visible("input.collection-name")
        name_element.send_keys(name)

    def collection_builder_hide_originals(self):
        self.wait_for_and_click_selector("input.hide-originals")

    def collection_builder_create(self):
        self.wait_for_and_click_selector("button.create-collection")

    def collection_builder_clear_filters(self):
        self.wait_for_and_click_selector("a.clear-filters-link")

    def collection_builder_click_paired_item(self, forward_or_reverse, item):
        assert forward_or_reverse in ["forward", "reverse"]
        forward_column = self.wait_for_selector_visible(".%s-column .column-datasets" % forward_or_reverse)
        first_datset_forward = forward_column.find_elements_by_css_selector("li")[item]
        first_datset_forward.click()

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
        element = self.wait_for_selector_visible(self.test_data["selectors"]["messages"][type])
        assert element, "No error message found, one expected."
        if contains is not None:
            text = element.text
            if contains not in text:
                message = "Text [%s] expected inside of [%s] but not found." % (contains, text)
                raise AssertionError(message)

    def assert_no_error_message(self):
        self.wait_for_selector_absent(self.test_data["selectors"]["messages"]["error"])

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

    @retry_during_transitions
    def wait_for_and_click_selector(self, selector):
        element = self.wait_for_selector_clickable(selector)
        element.click()
        return element

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
