"""A mixing that extends a HasDriver class with Galaxy-specific utilities.

Implementer must provide a self.build_url method to target Galaxy.
"""
from __future__ import print_function

import collections
import contextlib
import random
import string
import time
from functools import partial, wraps

import requests
import yaml

from galaxy.util.bunch import Bunch
from . import sizzle
from .data import (
    NAVIGATION,
)
from .has_driver import (
    exception_indicates_not_clickable,
    exception_indicates_stale_element,
    HasDriver,
    TimeoutException,
)
from .smart_components import SmartComponent

# Test case data
DEFAULT_PASSWORD = '123456'

RETRY_DURING_TRANSITIONS_SLEEP_DEFAULT = .1
RETRY_DURING_TRANSITIONS_ATTEMPTS_DEFAULT = 10

WaitType = collections.namedtuple("WaitType", ["name", "default_length"])

# Default wait times should make sense for a development server under low
# load. Wait times for production servers can be scaled up with a multiplier.
WAIT_TYPES = Bunch(
    # Rendering a form and registering callbacks, etc...
    UX_RENDER=WaitType("ux_render", 1),
    # Fade in, fade out, etc...
    UX_TRANSITION=WaitType("ux_transition", 5),
    # Toastr popup and dismissal, etc...
    UX_POPUP=WaitType("ux_popup", 15),
    # Creating a new history and loading it into the panel.
    DATABASE_OPERATION=WaitType("database_operation", 10),
    # Wait time for jobs to complete in default environment.
    JOB_COMPLETION=WaitType("job_completion", 30),
    # Wait time for a GIE to spawn.
    GIE_SPAWN=WaitType("gie_spawn", 30),
)

# Choose a moderate wait type for operations that don't specify a type.
DEFAULT_WAIT_TYPE = WAIT_TYPES.DATABASE_OPERATION


class NullTourCallback(object):

    def handle_step(self, step, step_index):
        pass


def exception_seems_to_indicate_transition(e):
    """True if exception seems to indicate the page state is transitioning.

    Galaxy features many different transition effects that change the page state over time.
    These transitions make it slightly more difficult to test Galaxy because atomic input
    actions take an indeterminate amount of time to be reflected on the screen. This method
    takes a Selenium assertion and tries to infer if such a transition could be the root
    cause of the exception. The methods that follow use it to allow retrying actions during
    transitions.

    Currently the two kinds of exceptions that we say may indicate a transition are
    StaleElement exceptions (a DOM element grabbed at one step is no longer available)
    and "not clickable" exceptions (so perhaps a popup modal is blocking a click).
    """
    return exception_indicates_stale_element(e) or exception_indicates_not_clickable(e)


def retry_call_during_transitions(f, attempts=RETRY_DURING_TRANSITIONS_ATTEMPTS_DEFAULT, sleep=RETRY_DURING_TRANSITIONS_SLEEP_DEFAULT, exception_check=exception_seems_to_indicate_transition):
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


def retry_during_transitions(f, attempts=RETRY_DURING_TRANSITIONS_ATTEMPTS_DEFAULT, sleep=RETRY_DURING_TRANSITIONS_SLEEP_DEFAULT, exception_check=exception_seems_to_indicate_transition):

    @wraps(f)
    def _retry(*args, **kwds):
        return retry_call_during_transitions(partial(f, *args, **kwds), attempts=attempts, sleep=sleep, exception_check=exception_check)

    return _retry


class NavigatesGalaxy(HasDriver):
    """Class with helpers methods for driving components of the Galaxy interface.

    In most cases, methods for interacting with Galaxy components that appear in
    multiple tests or applications should be refactored into this class for now.
    Keep in mind that this class is used outside the context of ``TestCase``s as
    well - so some methods more explicitly related to test data or assertion checking
    may make more sense in SeleniumTestCase for instance.

    Some day this class will likely be split up into smaller mixins for particular
    components of Galaxy, but until that day the best practice is to prefix methods
    for driving or querying the interface with the name of the component or page
    the method operates on. These serve as psedu-namespaces until we decompose this
    class. For instance, the method for clicking an option in the workflow editor is
    workflow_editor_click_option instead of click_workflow_editor_option.
    """

    default_password = DEFAULT_PASSWORD
    wait_types = WAIT_TYPES

    def get(self, url=""):
        full_url = self.build_url(url)
        return self.driver.get(full_url)

    @property
    def navigation(self):
        return NAVIGATION

    @property
    def components(self):
        return SmartComponent(self.navigation, self)

    def wait_length(self, wait_type):
        return wait_type.default_length * self.timeout_multiplier

    def sleep_for(self, wait_type):
        self.sleep_for_seconds(self.wait_length(wait_type))

    def sleep_for_seconds(self, duration):
        time.sleep(duration)

    def timeout_for(self, **kwds):
        wait_type = kwds.get("wait_type", DEFAULT_WAIT_TYPE)
        return self.wait_length(wait_type)

    def home(self):
        self.get()
        self.wait_for_visible(self.navigation.masthead.selector)
        self.wait_for_visible(self.navigation.history_panel.selector)

    def switch_to_main_panel(self):
        self.driver.switch_to.frame("galaxy_main")

    @contextlib.contextmanager
    def local_storage(self, key, value):
        self.driver.execute_script('''window.localStorage.setItem("%s", %s);''' % (key, value))
        try:
            yield
        finally:
            self.driver.execute_script('''window.localStorage.removeItem("%s");''' % key)

    @contextlib.contextmanager
    def main_panel(self):
        try:
            self.switch_to_main_panel()
            yield
        finally:
            self.driver.switch_to.default_content()

    def api_get(self, endpoint, data=None, raw=False):
        data = data or {}
        full_url = self.build_url("api/" + endpoint, for_selenium=False)
        response = requests.get(full_url, data=data, cookies=self.selenium_to_requests_cookies())
        if raw:
            return response
        else:
            return response.json()

    def api_delete(self, endpoint, raw=False):
        full_url = self.build_url("api/" + endpoint, for_selenium=False)
        response = requests.delete(full_url, cookies=self.selenium_to_requests_cookies())
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
        return self.wait_for_present(self.navigation.history_panel.selectors.name)

    @retry_during_transitions
    def history_panel_name(self):
        return self.history_panel_name_element().text

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

    def wait_for_history(self, assert_ok=True):
        def history_becomes_terminal(driver):
            current_history_id = self.current_history_id()
            state = self.api_get("histories/%s" % current_history_id)["state"]
            if state not in ["running", "queued", "new", "ready"]:
                return state
            else:
                return None

        timeout = self.timeout_for(wait_type=WAIT_TYPES.JOB_COMPLETION)
        final_state = self.wait(timeout=timeout).until(history_becomes_terminal)
        if assert_ok:
            assert final_state == "ok", final_state
        return final_state

    def history_panel_create_new_with_name(self, name):
        self.history_panel_create_new()
        self.history_panel_rename(name)

    def history_panel_create_new(self):
        """Click create new and pause a bit for the history to begin to refresh."""
        self.click_history_option('Create New')
        self.sleep_for(WAIT_TYPES.UX_RENDER)

    def history_panel_wait_for_hid_ok(self, hid, allowed_force_refreshes=0):
        self.history_panel_wait_for_hid_state(hid, 'ok', allowed_force_refreshes=allowed_force_refreshes)

    def history_panel_item_component(self, history_item=None, hid=None):
        if history_item is None:
            assert hid
            history_item = self.hid_to_history_item(hid)
        return self.components.history_panel.item.selector(
            history_content_type=history_item["history_content_type"],
            id=history_item["id"]
        )

    def history_panel_wait_for_hid_visible(self, hid, allowed_force_refreshes=0):
        current_history_id = self.current_history_id()

        def history_has_hid(driver):
            contents = self.api_get("histories/%s/contents" % current_history_id)
            return any([d for d in contents if d["hid"] == hid])

        timeout = self.timeout_for(wait_type=WAIT_TYPES.JOB_COMPLETION)
        self.wait(timeout).until(history_has_hid)
        history_item = self.hid_to_history_item(hid, current_history_id=current_history_id)
        history_item_selector = self.history_panel_item_component(history_item)
        try:
            self.history_item_wait_for(history_item_selector, allowed_force_refreshes)
        except self.TimeoutException as e:
            contents_elements = self.find_elements(self.navigation.history_panel.selectors.contents)
            div_ids = [("#" + d.get_attribute('id')) for d in contents_elements]
            template = "Failed waiting on history item %d to become visible, visible datasets include [%s]."
            message = template % (hid, ",".join(div_ids))
            raise self.prepend_timeout_message(e, message)
        return history_item_selector

    def hid_to_history_item(self, hid, current_history_id=None):
        if current_history_id is None:
            current_history_id = self.current_history_id()
        contents = self.api_get("histories/%s/contents" % current_history_id)
        history_item = [d for d in contents if d["hid"] == hid][0]
        return history_item

    def history_item_wait_for(self, history_item_selector, allowed_force_refreshes):
        attempt = 0
        while True:
            try:
                rval = self.wait_for_visible(history_item_selector, wait_type=WAIT_TYPES.JOB_COMPLETION)
                break
            except self.TimeoutException:
                if attempt >= allowed_force_refreshes:
                    raise

            attempt += 1
            self.history_panel_refresh_click()
        return rval

    def history_panel_wait_for_history_loaded(self):
        # Use the search box showing up as a proxy that the history display
        # has left the "loading" state and is showing a valid set of history contents
        # (even if empty).
        self.wait_for_visible(self.navigation.history_panel.selectors.search, wait_type=WAIT_TYPES.DATABASE_OPERATION)

    def history_panel_wait_for_hid_hidden(self, hid):
        history_item = self.hid_to_history_item(hid)
        history_item_selector = self.history_panel_item_component(history_item)
        self.wait_for_absent_or_hidden(history_item_selector, wait_type=WAIT_TYPES.JOB_COMPLETION)
        return history_item_selector

    def history_panel_wait_for_hid_state(self, hid, state, allowed_force_refreshes=0):
        history_item_selector = self.history_panel_wait_for_hid_visible(hid, allowed_force_refreshes=allowed_force_refreshes)
        history_item_selector_state = history_item_selector.with_class("state-%s" % state)
        try:
            self.history_item_wait_for(history_item_selector_state, allowed_force_refreshes)
        except self.TimeoutException as e:
            history_item = self.wait_for_visible(history_item_selector)
            current_state = "UNKNOWN"
            classes = history_item.get_attribute("class").split(" ")
            for clazz in classes:
                if clazz.startswith("state-"):
                    current_state = clazz[len("state-"):]
            template = "Failed waiting on history item %d state to change to [%s] current state [%s]. "
            message = template % (hid, state, current_state)
            raise self.prepend_timeout_message(e, message)
        return history_item_selector_state

    def published_grid_search_for(self, search_term=None):
        return self._inline_search_for(
            '#input-free-text-search-filter',
            search_term,
        )

    def get_logged_in_user(self):
        return self.api_get("users/current")

    def is_logged_in(self):
        return "email" in self.get_logged_in_user()

    @retry_during_transitions
    def _inline_search_for(self, selector, search_term=None):
        search_box = self.wait_for_and_click_selector(selector)
        search_box.clear()
        if search_term is not None:
            search_box.send_keys(search_term)
        self.send_enter(search_box)
        return search_box

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

    def submit_login(self, email, password=None, assert_valid=True, retries=0):
        if password is None:
            password = self.default_password
        login_info = {
            'login': email,
            'password': password,
        }
        self.click_masthead_user()
        self.sleep_for(WAIT_TYPES.UX_RENDER)
        form = self.wait_for_visible(self.navigation.login.selectors.form)
        self.fill(form, login_info)
        self.snapshot("logging-in")
        self.wait_for_and_click(self.navigation.login.selectors.submit)
        self.snapshot("login-submitted")
        if assert_valid:
            try:
                self.wait_for_logged_in()
            except NotLoggedInException:
                self.snapshot("login-failed")
                if retries > 0:
                    self.submit_login(email, password, assert_valid, retries - 1)
                else:
                    raise
            self.snapshot("logged-in")

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
        self.wait_for_and_click(self.navigation.registration.selectors.toggle)
        form = self.wait_for_visible(self.navigation.registration.selectors.form)
        self.fill(form, dict(
            email=email,
            password=password,
            username=username,
            confirm=confirm
        ))
        self.wait_for_and_click(self.navigation.registration.selectors.submit)
        # Give the browser a bit of time to submit the request.
        # It would be good to eliminate this sleep, but it can't be because Galaxy
        # doesn't swap the "User" menu automatically after it registers a user and
        # and the donemessage visible comment below doesn't work when using Selenium.
        # Something about the Selenium session or quickness of registering causes the
        # following in the Galaxy logs which gets propaged to the GUI as a generic error:
        # /api/histories/cfc05ccec54895e2/contents?keys=type_id%2Celement_count&order=hid&v=dev&q=history_content_type&q=deleted&q=purged&q=visible&qv=dataset_collection&qv=False&qv=False&qv=True HTTP/1.1" 403 - "http://localhost:8080/"
        # Like the logged in user doesn't have permission to the previously anonymous user's
        # history, it is odd but I cannot replicate this outside of Selenium.
        time.sleep(1.35)

        if assert_valid:
            # self.wait_for_selector_visible(".donemessage")
            self.home()
            self.click_masthead_user()
            # Make sure the user menu was dropped down
            user_menu = self.components.masthead.user_menu.wait_for_visible()
            try:
                user_email_element = self.components.masthead.user_email.wait_for_visible()
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
            self.wait_for_visible(self.navigation.masthead.selectors.logged_in_only)
        except self.TimeoutException as e:
            user_info = self.api_get("users/current")
            if "username" in user_info:
                template = "Failed waiting for masthead to update for login, but user API response indicates [%s] is logged in. This seems to be a bug in Galaxy. API response was [%s]. "
                message = template % (user_info["username"], user_info)
                raise self.prepend_timeout_message(e, message)
            else:
                raise NotLoggedInException(e, user_info)

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
        self.components.upload.tab(tab=tab).wait_for_and_click()

    def upload_start_click(self):
        self.components.upload.start.wait_for_and_click()

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
    def upload_build(self, tab="collection"):
        build_selector = "div#%s button#btn-build" % tab
        # Pause a bit to let the callback on the build button be registered.
        time.sleep(.5)
        # Click the Build button and make sure it disappears.
        self.wait_for_and_click_selector(build_selector)
        try:
            self.wait_for_selector_absent_or_hidden(build_selector)
        except TimeoutException:
            # Sometimes the callback in the JS hasn't be registered by the
            # time that the build button is clicked. By the time the timeout
            # has been registered - it should have been.
            self.wait_for_and_click_selector(build_selector)
            self.wait_for_selector_absent_or_hidden(build_selector)

    def upload_queue_local_file(self, test_path, tab_id="regular"):
        self.wait_for_and_click_selector("div#%s button#btn-local" % tab_id)

        file_upload = self.wait_for_selector('div#%s input[type="file"]' % tab_id)
        file_upload.send_keys(test_path)

    def upload_rule_start(self):
        self.upload_start_click()
        self.upload_tab_click("rule-based")

    def upload_rule_build(self):
        self.upload_build(tab="rule-based")

    def upload_rule_set_data_type(self, type_description):
        upload = self.components.upload
        data_type_element = upload.rule_select_data_type.wait_for_visible()
        self.select2_set_value(data_type_element, type_description)

    def upload_rule_set_input_type(self, input_description):
        upload = self.components.upload
        input_type_element = upload.rule_select_input_type.wait_for_visible()
        self.select2_set_value(input_type_element, input_description)

    def upload_rule_set_dataset(self, dataset_description="1:"):
        upload = self.components.upload
        rule_dataset_element = upload.rule_dataset_selector.wait_for_visible()
        self.select2_set_value(rule_dataset_element, dataset_description)

    def rule_builder_set_collection_name(self, name):
        rule_builder = self.components.rule_builder
        name_element = rule_builder.collection_name_input.wait_for_and_click()
        name_element.send_keys(name)

    def rule_builder_set_extension(self, extension):
        self.select2_set_value(self.navigation.rule_builder.selectors.extension_select, extension)

    def rule_builder_filter_count(self, count=1):
        rule_builder = self.components.rule_builder
        rule_builder.menu_button_filter.wait_for_and_click()
        with self.rule_builder_rule_editor("add-filter-count") as editor_element:
            filter_input = editor_element.find_element_by_css_selector("input[type='number']")
            filter_input.clear()
            filter_input.send_keys("%s" % count)

    def rule_builder_sort(self, column_label, screenshot_name=None):
        rule_builder = self.components.rule_builder
        rule_builder.menu_button_rules.wait_for_and_click()
        with self.rule_builder_rule_editor("sort") as editor_element:
            column_elem = editor_element.find_element_by_css_selector(".rule-column-selector")
            self.select2_set_value(column_elem, column_label)
            if screenshot_name:
                self.screenshot(screenshot_name)

    def rule_builder_add_regex_groups(self, column_label, group_count, regex, screenshot_name):
        rule_builder = self.components.rule_builder
        rule_builder.menu_button_column.wait_for_and_click()
        with self.rule_builder_rule_editor("add-column-regex") as editor_element:

            column_elem = editor_element.find_element_by_css_selector(".rule-column-selector")
            self.select2_set_value(column_elem, column_label)

            groups_elem = editor_element.find_element_by_css_selector("input[type='radio'][value='groups']")
            groups_elem.click()

            regex_elem = editor_element.find_element_by_css_selector("input.rule-regular-expression")
            regex_elem.clear()
            regex_elem.send_keys(regex)

            filter_input = editor_element.find_element_by_css_selector("input[type='number']")
            filter_input.clear()
            filter_input.send_keys("%s" % group_count)

            if screenshot_name:
                self.screenshot(screenshot_name)

    def rule_builder_add_regex_replacement(self, column_label, regex, replacement, screenshot_name=None):
        rule_builder = self.components.rule_builder
        rule_builder.menu_button_column.wait_for_and_click()
        with self.rule_builder_rule_editor("add-column-regex") as editor_element:

            column_elem = editor_element.find_element_by_css_selector(".rule-column-selector")
            self.select2_set_value(column_elem, column_label)

            groups_elem = editor_element.find_element_by_css_selector("input[type='radio'][value='replacement']")
            groups_elem.click()

            regex_elem = editor_element.find_element_by_css_selector("input.rule-regular-expression")
            regex_elem.clear()
            regex_elem.send_keys(regex)

            filter_input = editor_element.find_element_by_css_selector("input.rule-replacement")
            filter_input.clear()
            filter_input.send_keys("%s" % replacement)

            if screenshot_name:
                self.screenshot(screenshot_name)

    def rule_builder_add_value(self, value, screenshot_name=None):
        rule_builder = self.components.rule_builder
        rule_builder.menu_button_column.wait_for_and_click()
        with self.rule_builder_rule_editor("add-column-value") as editor_element:
            filter_input = editor_element.find_element_by_css_selector("input[type='text']")
            filter_input.clear()
            filter_input.send_keys(value)

            if screenshot_name:
                self.screenshot(screenshot_name)

    def rule_builder_remove_columns(self, column_labels, screenshot_name=None):
        rule_builder = self.components.rule_builder
        rule_builder.menu_button_rules.wait_for_and_click()
        with self.rule_builder_rule_editor("remove-columns") as filter_editor_element:
            column_elem = filter_editor_element.find_element_by_css_selector(".rule-column-selector")
            for column_label in column_labels:
                self.select2_set_value(column_elem, column_label)
            if screenshot_name:
                self.screenshot(screenshot_name)

    def rule_builder_concatenate_columns(self, column_label_1, column_label_2, screenshot_name=None):
        rule_builder = self.components.rule_builder
        rule_builder.menu_button_column.wait_for_and_click()
        with self.rule_builder_rule_editor("add-column-concatenate") as filter_editor_element:
            column_elems = filter_editor_element.find_elements_by_css_selector(".rule-column-selector")
            self.select2_set_value(column_elems[0], column_label_1)
            column_elems = filter_editor_element.find_elements_by_css_selector(".rule-column-selector")
            self.select2_set_value(column_elems[1], column_label_2)
            if screenshot_name:
                self.screenshot(screenshot_name)

    def rule_builder_split_columns(self, column_labels_1, column_labels_2, screenshot_name=None):
        rule_builder = self.components.rule_builder
        rule_builder.menu_button_rules.wait_for_and_click()
        with self.rule_builder_rule_editor("split-columns") as filter_editor_element:
            column_elems = filter_editor_element.find_elements_by_css_selector(".rule-column-selector")
            clear = True
            for column_label_1 in column_labels_1:
                self.select2_set_value(column_elems[0], column_label_1, clear_value=clear)
                clear = False

            column_elems = filter_editor_element.find_elements_by_css_selector(".rule-column-selector")
            clear = True
            for column_label_2 in column_labels_2:
                self.select2_set_value(column_elems[1], column_label_2, clear_value=clear)
                clear = False

            if screenshot_name:
                self.screenshot(screenshot_name)

    def rule_builder_swap_columns(self, column_label_1, column_label_2, screenshot_name):
        rule_builder = self.components.rule_builder
        rule_builder.menu_button_rules.wait_for_and_click()
        with self.rule_builder_rule_editor("swap-columns") as filter_editor_element:
            column_elems = filter_editor_element.find_elements_by_css_selector(".rule-column-selector")
            self.select2_set_value(column_elems[0], column_label_1)
            column_elems = filter_editor_element.find_elements_by_css_selector(".rule-column-selector")
            self.select2_set_value(column_elems[1], column_label_2)
            if screenshot_name:
                self.screenshot(screenshot_name)

    @contextlib.contextmanager
    def rule_builder_rule_editor(self, rule_type):
        rule_builder = self.components.rule_builder
        rule_builder.menu_item_rule_type(rule_type=rule_type).wait_for_and_click()
        filter_editor = rule_builder.rule_editor(rule_type=rule_type)
        filter_editor_element = filter_editor.wait_for_visible()
        yield filter_editor_element
        rule_builder.rule_editor_ok.wait_for_and_click()

    def rule_builder_set_mapping(self, mapping_type, column_label, screenshot_name=None):
        rule_builder = self.components.rule_builder
        rule_builder.menu_button_rules.wait_for_and_click()
        rule_builder.menu_item_rule_type(rule_type="mapping").wait_for_and_click()
        rule_builder.add_mapping_menu.wait_for_and_click()
        rule_builder.add_mapping_button(mapping_type=mapping_type).wait_for_and_click()
        if mapping_type != "list-identifiers" or not isinstance(column_label, list):
            mapping_elem = rule_builder.mapping_edit(mapping_type=mapping_type).wait_for_visible()
            self.select2_set_value(mapping_elem, column_label)
            if screenshot_name:
                self.screenshot(screenshot_name)
        else:
            assert len(column_label) > 0
            column_labels = column_label
            for i, column_label in enumerate(column_labels):
                if i > 0:
                    rule_builder.mapping_add_column(mapping_type=mapping_type).wait_for_and_click()
                mapping_elem = rule_builder.mapping_edit(mapping_type=mapping_type).wait_for_visible()
                self.select2_set_value(mapping_elem, column_label)
            if screenshot_name:
                self.screenshot(screenshot_name)
        rule_builder.mapping_ok.wait_for_and_click()

    def rule_builder_set_source(self, json):
        rule_builder = self.components.rule_builder
        rule_builder.view_source.wait_for_and_click()
        self.rule_builder_enter_source_text(json)
        rule_builder.main_button_ok.wait_for_and_click()
        rule_builder.view_source.wait_for_visible()

    def rule_builder_enter_source_text(self, json):
        rule_builder = self.components.rule_builder
        text_area_elem = rule_builder.source.wait_for_visible()
        text_area_elem.clear()
        text_area_elem.send_keys(json)

    def workflow_editor_click_option(self, option_label):
        self.workflow_editor_click_options()
        menu_element = self.workflow_editor_options_menu_element()
        option_elements = menu_element.find_elements_by_css_selector("a")
        assert len(option_elements) > 0, "Failed to find workflow editor options"
        self.sleep_for(WAIT_TYPES.UX_RENDER)
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

    def admin_open(self):
        self.components.masthead.admin.wait_for_and_click()

    def libraries_open(self):
        self.home()
        self.click_masthead_shared_data()
        self.components.masthead.libraries.wait_for_and_click()
        self.components.libraries.selector.wait_for_visible()

    def libraries_open_with_name(self, name):
        self.libraries_open()
        self.libraries_index_search_for(name)
        self.libraries_index_table_elements()[0].find_element_by_css_selector("td a").click()

    @retry_during_transitions
    def libraries_index_table_elements(self):
        container = self.wait_for_selector_visible(".library_container")
        elements = container.find_elements_by_css_selector("#library_list_body")
        if not elements:
            return []
        else:
            assert len(elements) == 1
            element = elements[0]
            return element.find_elements_by_css_selector("tr")  # [style='display: table-row']

    def libraries_index_click_create_new(self):
        self.wait_for_and_click_selector("#create_new_library_btn")

    def libraries_index_create(self, name):
        self.libraries_index_click_create_new()
        name_text_box = self.wait_for_selector_clickable("input[name='Name']")
        name_text_box.send_keys(name)

        self.wait_for_and_click_selector("#button-0")

    def libraries_index_click_search(self):
        self.sleep_for(WAIT_TYPES.UX_RENDER)
        search_element = self.wait_for_selector_clickable("input.library-search-input")
        search_element.click()
        return search_element

    def libraries_index_sort_selector(self):
        return ".sort-libraries-link"

    def libraries_index_sort_click(self):
        sort_element = self.wait_for_selector_clickable(self.libraries_index_sort_selector())
        sort_element.click()
        return sort_element

    def libraries_index_search_for(self, text):
        self.wait_for_overlays_cleared()
        search_box = self.libraries_index_click_search()
        search_box.clear()
        search_box.send_keys(text)
        value = search_box.get_attribute("value")
        assert value == text, value
        self.driver.execute_script("$(arguments[0]).keyup();", search_box)

    def libraries_folder_create(self, name):
        self.components.libraries.folder.add_folder.wait_for_and_click()

        name_text_box = self.wait_for_selector_clickable("input[name='Name']")
        name_text_box.send_keys(name)

        create_button = self.wait_for_selector_clickable("#button-0")
        create_button.click()

    def libraries_click_dataset_import(self):
        self.wait_for_and_click(self.navigation.libraries.folder.selectors.add_items_button)

    def libraries_dataset_import_from_history(self):
        self.libraries_click_dataset_import()

        self.wait_for_visible(self.navigation.libraries.folder.selectors.add_items_menu)
        self.wait_for_and_click(self.navigation.libraries.folder.labels.from_history)

    def libraries_dataset_import_from_path(self):
        self.libraries_click_dataset_import()

        self.wait_for_visible(self.navigation.libraries.folder.selectors.add_items_menu)
        self.wait_for_and_click(self.navigation.libraries.folder.labels.from_path)

    def libraries_dataset_import_from_history_select(self, to_select_items):
        self.wait_for_visible(self.navigation.libraries.folder.selectors.import_history_content)
        history_elements = self.find_elements(self.navigation.libraries.folder.selectors.import_history_contents_items)
        for to_select_item in to_select_items:
            found = False
            for history_element in history_elements:
                if to_select_item in history_element.text:
                    history_element.find_element_by_css_selector("input").click()
                    found = True
                    break

            if not found:
                raise Exception("Failed to find history item [%s] to select" % to_select_item)

    def libraries_dataset_import_from_history_click_ok(self, wait=True):
        self.wait_for_and_click(self.navigation.libraries.folder.selectors.import_datasets_ok_button)
        if wait:
            # Let the progress bar disappear...
            self.wait_for_absent_or_hidden(self.navigation.libraries.folder.selectors.import_progress_bar)

    def libraries_table_elements(self):
        tbody_element = self.wait_for_selector_visible("#folder_list_body")
        return tbody_element.find_elements_by_css_selector("tr")[1:]

    def wait_for_overlays_cleared(self):
        """Wait for modals and Toast notifications to disappear."""
        self.wait_for_selector_absent_or_hidden(".ui-modal", wait_type=WAIT_TYPES.UX_POPUP)
        self.wait_for_selector_absent_or_hidden(".toast", wait_type=WAIT_TYPES.UX_POPUP)

    def workflow_index_open(self):
        self.home()
        self.click_masthead_workflow()

    def workflow_index_table_elements(self):
        self.wait_for_selector_visible("tbody.workflow-search")
        table_elements = self.driver.find_elements_by_css_selector("tbody.workflow-search > tr:not([style*='display: none'])")
        return table_elements

    def workflow_index_table_row(self, workflow_index=0):
        return self.workflow_index_table_elements()[workflow_index]

    @retry_during_transitions
    def workflow_index_column_text(self, column_index, workflow_index=0):
        row_element = self.workflow_index_table_row()
        columns = row_element.find_elements_by_css_selector("td")
        return columns[column_index].text

    def workflow_index_click_search(self):
        return self.wait_for_and_click_selector("input.search-wf")

    def workflow_index_search_for(self, search_term=None):
        return self._inline_search_for(
            "input.search-wf",
            search_term,
        )

    def workflow_index_click_import(self):
        return self.components.workflows.import_button.wait_for_and_click()

    def workflow_index_rename(self, new_name, workflow_index=0):
        self.workflow_index_click_option("Rename", workflow_index=workflow_index)
        alert = self.driver.switch_to.alert
        alert.send_keys(new_name)
        alert.accept()

    @retry_during_transitions
    def workflow_index_name(self, workflow_index=0):
        """Get workflow name for workflow_index'th row."""
        row_element = self.workflow_index_table_row(workflow_index=workflow_index)
        workflow_button = row_element.find_element_by_css_selector("a.btn.btn-secondary")
        return workflow_button.text

    def workflow_index_click_option(self, option_title, workflow_index=0):

        @retry_during_transitions
        def click_option():
            workflow_row = self.workflow_index_table_row(workflow_index=workflow_index)
            workflow_button = workflow_row.find_element_by_css_selector("button.dropdown-toggle")
            workflow_button.click()

        click_option()

        menu_element = self.wait_for_selector_visible(".dropdown-menu.show")
        menu_options = menu_element.find_elements_by_css_selector("a.dropdown-item")
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

    @retry_during_transitions
    def workflow_index_tags(self, workflow_index=0):
        workflow_row_element = self.workflow_index_table_row(workflow_index)
        tag_display = workflow_row_element.find_element_by_css_selector(".tags-display")
        tag_spans = tag_display.find_elements_by_css_selector("span.badge-tags")
        tags = []
        for tag_span in tag_spans:
            tags.append(tag_span.text)
        return tags

    def workflow_import_submit_url(self, url):
        form_button = self.wait_for_selector_visible("#workflow-import-button")
        url_element = self.wait_for_selector_visible("#workflow-import-url-input")
        url_element.send_keys(url)
        form_button.click()

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

    def tool_open(self, tool_id, outer=False):
        if outer:
            tool_link = self.components.tool_panel.outer_tool_link(tool_id=tool_id)
        else:
            tool_link = self.components.tool_panel.tool_link(tool_id=tool_id)
        tool_element = tool_link.wait_for_present()
        self.driver.execute_script("arguments[0].scrollIntoView(true);", tool_element)
        tool_link.wait_for_and_click()

    def tool_parameter_div(self, expanded_parameter_id):
        return self.components.tool_form.parameter_div(parameter=expanded_parameter_id).wait_for_clickable()

    def tool_parameter_edit_rules(self, expanded_parameter_id="rules"):
        rules_div_element = self.tool_parameter_div("rules")
        edit_button_element = rules_div_element.find_element_by_css_selector("i.fa-edit")
        edit_button_element.click()

    def tool_set_value(self, expanded_parameter_id, value, expected_type=None, test_data_resolver=None):
        div_element = self.tool_parameter_div(expanded_parameter_id)
        assert div_element
        if expected_type in ["data", "data_collection"]:
            div_selector = "div.ui-form-element[tour_id$='%s']" % expanded_parameter_id
            self.select2_set_value(div_selector, value)
        else:
            input_element = div_element.find_element_by_css_selector("input")
            # Clear default value
            input_element.clear()
            input_element.send_keys(value)

    def tool_form_generate_tour(self):
        self.components.tool_form.options.wait_for_and_click()
        self.components.tool_form.generate_tour.wait_for_and_click()

    def tool_form_execute(self):
        self.components.tool_form.execute.wait_for_and_click()

    def click_masthead_user(self):
        self.components.masthead.user.wait_for_and_click()

    def click_masthead_shared_data(self):
        self.components.masthead.shared_data.wait_for_and_click()

    def click_masthead_workflow(self):
        self.components.masthead.workflow.wait_for_and_click()

    def click_button_new_workflow(self):
        self.wait_for_and_click(self.navigation.workflows.selectors.new_button)

    def wait_for_sizzle_selector_clickable(self, selector):
        element = self._wait_on(
            sizzle.sizzle_selector_clickable(selector),
            "sizzle/jQuery selector [%s] to become clickable" % selector,
        )
        return element

    @retry_during_transitions
    def click_history_options(self):
        self.components.history_panel.options_button_icon.wait_for_and_click()

    def click_history_option(self, option_label):
        # Open menu
        self.click_history_options()

        # Click labelled option
        self.wait_for_visible(self.navigation.history_panel.options_menu)
        menu_item_sizzle_selector = '#history-options-button-menu > li > a:contains("%s")' % option_label
        menu_selection_element = self.wait_for_sizzle_selector_clickable(menu_item_sizzle_selector)
        menu_selection_element.click()

    def history_panel_click_copy_elements(self):
        self.click_history_option("Copy Datasets")

    @retry_during_transitions
    def histories_click_advanced_search(self):
        search_selector = '#standard-search .advanced-search-toggle'
        self.wait_for_and_click_selector(search_selector)

    def history_panel_add_tags(self, tags):
        tag_icon_selector = self.components.history_panel.tag_icon
        tag_area_selector = self.components.history_panel.tag_area
        tag_area_input_selector = self.components.history_panel.tag_area_input

        if not tag_area_selector.is_displayed:
            tag_icon_selector.wait_for_and_click()

        tag_area = tag_area_input_selector.wait_for_and_click()

        for tag in tags:
            tag_area.send_keys(tag)
            self.send_enter(tag_area)
            time.sleep(.5)

    def history_panel_rename(self, new_name):
        editable_text_input_element = self.history_panel_click_to_rename()
        editable_text_input_element.send_keys(new_name)
        self.send_enter(editable_text_input_element)

    def history_panel_click_to_rename(self):
        self.wait_for_and_click(self.navigation.history_panel.selectors.name)
        return self.wait_for_visible(self.navigation.history_panel.selectors.name_edit_input)

    def history_panel_refresh_click(self):
        self.wait_for_and_click(self.navigation.history_panel.selectors.refresh_button)

    def history_panel_multi_operations_show(self):
        return self.wait_for_and_click(self.navigation.history_panel.multi_operations.selectors.show_button)

    def history_panel_muli_operation_select_hid(self, hid):
        item_selector = self.history_panel_item_selector(hid, wait=True)
        operation_radio_selector = "%s .selector" % item_selector
        self.wait_for_and_click_selector(operation_radio_selector)

    def history_panel_multi_operation_action_click(self, action):
        # Maybe isn't needed?
        # self.sleep_for(WAIT_TYPES.UX_RENDER)
        self.wait_for_and_click(self.navigation.history_panel.multi_operations.selectors.action_button)

        @retry_during_transitions
        def _click_action_in_menu():
            menu_element = self.wait_for_visible(self.navigation.history_panel.multi_operations.selectors.action_menu)
            menu_element.find_element_by_link_text(action.text).click()

        _click_action_in_menu()

    def history_multi_view_display_collection_contents(self, collection_hid, collection_type="list"):
        self.components.history_panel.multi_view_button.wait_for_and_click()

        selector = self.history_panel_wait_for_hid_state(collection_hid, "ok")
        self.click(selector)
        next_level_element_selector = selector
        for i in range(len(collection_type.split(":")) - 1):
            next_level_element_selector = next_level_element_selector.descendant(".dataset-collection-element")
            self.wait_for_and_click(next_level_element_selector)

        dataset_selector = next_level_element_selector.descendant(".dataset")
        self.wait_for_and_click(dataset_selector)

    def history_panel_item_click_visualization_menu(self, hid):
        viz_button_selector = "%s %s" % (self.history_panel_item_selector(hid), ".visualizations-dropdown")
        self.wait_for_and_click_selector(viz_button_selector)
        self.wait_for_selector_visible("%s %s" % (viz_button_selector, ".dropdown-menu"))

    def history_panel_item_available_visualizations_elements(self, hid):
        # Precondition: viz menu has been opened with history_panel_item_click_visualization_menu
        viz_menu_selectors = "%s %s" % (self.history_panel_item_selector(hid), "a.visualization-link")
        return self.driver.find_elements_by_css_selector(viz_menu_selectors)

    def history_panel_item_get_nametags(self, hid):
        item_component = self.history_panel_item_component(hid=hid)
        item_component.wait_for_visible()
        return [e.text for e in item_component.nametags.all()]

    def history_panel_item_available_visualizations(self, hid):
        # Precondition: viz menu has been opened with history_panel_item_click_visualization_menu
        return [e.text for e in self.history_panel_item_available_visualizations_elements(hid)]

    def history_panel_item_click_visualization(self, hid, visualization_name):
        # Precondition: viz menu has been opened with history_panel_item_click_visualization_menu
        elements = self.history_panel_item_available_visualizations_elements(hid)
        for element in elements:
            if element.text == visualization_name:
                element.click()
                return element

        assert False, "No visualization [%s] found." % visualization_name

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

    def history_panel_item_body_component(self, hid, wait=False):
        details_component = self.history_panel_item_component(hid=hid).details
        if wait:
            details_component.wait_for_visible()
        return details_component

    def hda_click_primary_action_button(self, hid, button_key):
        item_component = self.history_panel_click_item_title(hid=hid, wait=True)
        item_component.primary_action_buttons.wait_for_visible()
        button_component = item_component["%s_button" % button_key]
        button_component.wait_for_and_click()

    def history_panel_click_item_title(self, hid, **kwds):
        item_component = self.history_panel_item_component(hid=hid)
        details_component = item_component.details
        details_displayed = details_component.is_displayed
        item_component.title.wait_for_and_click()
        if kwds.get("wait", False):
            if details_displayed:
                details_component.wait_for_absent_or_hidden()
            else:
                details_component.wait_for_visible()
        return item_component

    def history_panel_ensure_showing_item_details(self, hid):
        if not self.history_panel_item_showing_details(hid):
            self.history_panel_click_item_title(hid=hid, wait=True)

    def history_panel_item_showing_details(self, hid):
        item_component = self.history_panel_item_component(hid=hid)
        return item_component.details.is_displayed

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
            self.wait_for_and_click(self.navigation.masthead.labels.logout)
            self.sleep_for(WAIT_TYPES.UX_TRANSITION)
            assert not self.is_logged_in()

    def run_tour(self, path, skip_steps=None, sleep_on_steps=None, tour_callback=None):
        skip_steps = skip_steps or []
        sleep_on_steps = sleep_on_steps or {}
        if tour_callback is None:
            tour_callback = NullTourCallback()

        self.home()

        with open(path, "r") as f:
            tour_dict = yaml.safe_load(f)
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
        timeout = self.timeout_for(wait_type=WAIT_TYPES.JOB_COMPLETION)
        wait = self.wait(timeout=timeout)
        timeout_message = self._timeout_message("sizzle (jQuery) selector [%s] to become clickable" % selector)
        element = wait.until(
            sizzle.sizzle_selector_clickable(selector),
            timeout_message,
        )
        return element

    def tour_wait_for_element_present(self, selector):
        timeout = self.timeout_for(wait_type=WAIT_TYPES.JOB_COMPLETION)
        wait = self.wait(timeout=timeout)
        timeout_message = self._timeout_message("sizzle (jQuery) selector [%s] to become present" % selector)
        element = wait.until(
            sizzle.sizzle_presence_of_selector(selector),
            timeout_message,
        )
        return element

    def get_tooltip_text(self, element, sleep=0, click_away=True):
        tooltip_balloon = self.components._.tooltip_balloon
        tooltip_balloon.wait_for_absent()

        action_chains = self.action_chains()
        action_chains.move_to_element(element)
        action_chains.perform()

        if sleep > 0:
            time.sleep(sleep)

        tooltip_element = tooltip_balloon.wait_for_visible()
        text = tooltip_element.text
        if click_away:
            self.click_center()
        return text

    @retry_during_transitions
    def assert_selector_absent_or_hidden_after_transitions(self, selector):
        """Variant of assert_selector_absent_or_hidden that retries during transitions.

        In the parent method - the element is found and then it is checked to see
        if it is visible. It may disappear from the page in the middle there
        and cause a StaleElement error. For checks where we care about the final
        resting state after transitions - this method can be used to retry
        during those transitions.
        """
        return self.assert_selector_absent_or_hidden(selector)

    @retry_during_transitions
    def assert_absent_or_hidden_after_transitions(self, selector):
        """Variant of assert_absent_or_hidden that retries during transitions.

        See details above for more information about this.
        """
        return self.assert_absent_or_hidden(selector)

    def assert_tooltip_text(self, element, expected, sleep=0, click_away=True):
        if hasattr(expected, "text"):
            expected = expected.text
        text = self.get_tooltip_text(element, sleep=sleep, click_away=click_away)
        assert text == expected, "Tooltip text [%s] was not expected text [%s]." % (text, expected)

    def assert_error_message(self, contains=None):
        return self._assert_message("error", contains=contains)

    def assert_warning_message(self, contains=None):
        return self._assert_message("warning", contains=contains)

    def _assert_message(self, message_type, contains=None):
        element = self.components._.messages[message_type].wait_for_visible()
        assert element, "No error message found, one expected."
        if contains is not None:
            text = element.text
            if contains not in text:
                message = "Text [%s] expected inside of [%s] but not found." % (contains, text)
                raise AssertionError(message)

    def assert_no_error_message(self):
        self.components._.messages.error.assert_absent_or_hidden()

    def run_tour_step(self, step, step_index, tour_callback):
        preclick = step.get("preclick", [])
        for preclick_selector in preclick:
            print("(Pre)Clicking %s" % preclick_selector)
            self._tour_wait_for_and_click_element(preclick_selector)

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
            self._tour_wait_for_and_click_element(postclick_selector)

    @retry_during_transitions
    def _tour_wait_for_and_click_element(self, selector):
        element = self.tour_wait_for_clickable_element(selector)
        element.click()

    @retry_during_transitions
    def wait_for_and_click_selector(self, selector):
        element = self.wait_for_selector_clickable(selector)
        element.click()
        return element

    @retry_during_transitions
    def wait_for_and_click(self, selector_template):
        element = self.wait_for_clickable(selector_template)
        element.click()
        return element

    def select2_set_value(self, container_selector_or_elem, value, with_click=True, clear_value=False):
        # There are two hacky was to select things from the select2 widget -
        #   with_click=True: This simulates the mouse click after the suggestion contains
        #                    only the selected value.
        #   with_click=False: This presses enter on the selection. Not sure
        #                     why.
        # with_click seems to work in all situtations - the enter methods
        # doesn't seem to work with the tool form for some reason.
        if hasattr(container_selector_or_elem, "selector"):
            container_selector_or_elem = container_selector_or_elem.selector
        if not hasattr(container_selector_or_elem, "find_element_by_css_selector"):
            container_elem = self.wait_for_selector(container_selector_or_elem)
        else:
            container_elem = container_selector_or_elem

        text_element = container_elem.find_element_by_css_selector("input[type='text']")
        if clear_value:
            self.send_backspace(text_element)
            self.send_backspace(text_element)
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

    def snapshot(self, description):
        """Test case subclass overrides this to provide detailed logging."""


class NotLoggedInException(TimeoutException):

    def __init__(self, timeout_exception, user_info):
        template = "Waiting for UI to reflect user logged in but it did not occur. API indicates no user is currently logged in. API response was [%s]. %s"
        msg = template % (user_info, timeout_exception.msg)
        super(NotLoggedInException, self).__init__(
            msg=msg,
            screen=timeout_exception.screen,
            stacktrace=timeout_exception.stacktrace
        )
