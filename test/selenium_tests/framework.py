"""Basis for Selenium test framework."""
from __future__ import absolute_import
from __future__ import print_function

import datetime
import json
import os
import traceback
import unittest
from functools import partial, wraps

import requests
from gxformat2 import (
    convert_and_import_workflow,
    ImporterGalaxyInterface,
)
try:
    from pyvirtualdisplay import Display
except ImportError:
    Display = None
from six.moves.urllib.parse import urljoin

from base import populators  # noqa: I100,I202
from base.api import UsesApiTestCaseMixin  # noqa: I100
from base.driver_util import classproperty, DEFAULT_WEB_HOST, get_ip_address  # noqa: I100
from base.testcase import FunctionalTestCase  # noqa: I100
from galaxy_selenium import (  # noqa: I100,I201
    driver_factory,
)
from galaxy_selenium.navigates_galaxy import (  # noqa: I100
    NavigatesGalaxy,
    retry_during_transitions
)
from galaxy.util import asbool  # noqa: I201

DEFAULT_TIMEOUT_MULTIPLIER = 1
DEFAULT_TEST_ERRORS_DIRECTORY = os.path.abspath("database/test_errors")
DEFAULT_SELENIUM_BROWSER = "auto"
DEFAULT_SELENIUM_REMOTE = False
DEFAULT_SELENIUM_REMOTE_PORT = "4444"
DEFAULT_SELENIUM_REMOTE_HOST = "127.0.0.1"
DEFAULT_SELENIUM_HEADLESS = "auto"
DEFAULT_ADMIN_USER = "test@bx.psu.edu"
DEFAULT_ADMIN_PASSWORD = "testpass"

TIMEOUT_MULTIPLIER = float(os.environ.get("GALAXY_TEST_TIMEOUT_MULTIPLIER", DEFAULT_TIMEOUT_MULTIPLIER))
GALAXY_TEST_ERRORS_DIRECTORY = os.environ.get("GALAXY_TEST_ERRORS_DIRECTORY", DEFAULT_TEST_ERRORS_DIRECTORY)
GALAXY_TEST_SCREENSHOTS_DIRECTORY = os.environ.get("GALAXY_TEST_SCREENSHOTS_DIRECTORY", None)
# Test browser can be ["CHROME", "FIREFOX", "OPERA", "PHANTOMJS"]
GALAXY_TEST_SELENIUM_BROWSER = os.environ.get("GALAXY_TEST_SELENIUM_BROWSER", DEFAULT_SELENIUM_BROWSER)
GALAXY_TEST_SELENIUM_REMOTE = os.environ.get("GALAXY_TEST_SELENIUM_REMOTE", DEFAULT_SELENIUM_REMOTE)
GALAXY_TEST_SELENIUM_REMOTE_PORT = os.environ.get("GALAXY_TEST_SELENIUM_REMOTE_PORT", DEFAULT_SELENIUM_REMOTE_PORT)
GALAXY_TEST_SELENIUM_REMOTE_HOST = os.environ.get("GALAXY_TEST_SELENIUM_REMOTE_HOST", DEFAULT_SELENIUM_REMOTE_HOST)
GALAXY_TEST_SELENIUM_HEADLESS = os.environ.get("GALAXY_TEST_SELENIUM_HEADLESS", DEFAULT_SELENIUM_HEADLESS)
GALAXY_TEST_EXTERNAL_FROM_SELENIUM = os.environ.get("GALAXY_TEST_EXTERNAL_FROM_SELENIUM", None)
# Auto-retry selenium tests this many times.
GALAXY_TEST_SELENIUM_RETRIES = int(os.environ.get("GALAXY_TEST_SELENIUM_RETRIES", "0"))

GALAXY_TEST_SELENIUM_USER_EMAIL = os.environ.get("GALAXY_TEST_SELENIUM_USER_EMAIL", None)
GALAXY_TEST_SELENIUM_USER_PASSWORD = os.environ.get("GALAXY_TEST_SELENIUM_USER_PASSWORD", None)
GALAXY_TEST_SELENIUM_ADMIN_USER_EMAIL = os.environ.get("GALAXY_TEST_SELENIUM_ADMIN_USER_EMAIL", DEFAULT_ADMIN_USER)
GALAXY_TEST_SELENIUM_ADMIN_USER_PASSWORD = os.environ.get("GALAXY_TEST_SELENIUM_ADMIN_USER_PASSWORD", DEFAULT_ADMIN_PASSWORD)

# JS code to execute in Galaxy JS console to setup localStorage of session for logging and
# logging "flatten" messages because it seems Selenium (with Chrome at least) only grabs
# the first argument to console.XXX when recovering the browser log.
SETUP_LOGGING_JS = '''
window.localStorage && window.localStorage.setItem("galaxy:debug", true);
window.localStorage && window.localStorage.setItem("galaxy:debug:flatten", true);
'''

try:
    from nose.tools import nottest
except ImportError:
    def nottest(x):
        return x


def managed_history(f):
    """Ensure a Selenium test has a distinct, named history.

    Cleanup the history after the job is complete as well unless
    GALAXY_TEST_NO_CLEANUP is set in the environment.
    """

    @wraps(f)
    def func_wrapper(self, *args, **kwds):
        self.home()
        history_name = f.__name__ + datetime.datetime.now().strftime("%Y%m%d%H%M%s")
        self.history_panel_create_new_with_name(history_name)
        try:
            f(self, *args, **kwds)
        finally:
            if "GALAXY_TEST_NO_CLEANUP" not in os.environ:
                current_history_id = self.current_history_id()
                self.dataset_populator.cancel_history_jobs(current_history_id)
                self.api_delete("histories/%s" % current_history_id)

    return func_wrapper


def dump_test_information(self, name_prefix):
    if GALAXY_TEST_ERRORS_DIRECTORY and GALAXY_TEST_ERRORS_DIRECTORY != "0":
        if not os.path.exists(GALAXY_TEST_ERRORS_DIRECTORY):
            os.makedirs(GALAXY_TEST_ERRORS_DIRECTORY)
        result_name = name_prefix + datetime.datetime.now().strftime("%Y%m%d%H%M%s")
        target_directory = os.path.join(GALAXY_TEST_ERRORS_DIRECTORY, result_name)

        def write_file(name, content, raw=False):
            with open(os.path.join(target_directory, name), "wb") as buf:
                buf.write(content.encode("utf-8") if not raw else content)

        os.makedirs(target_directory)
        write_file("stacktrace.txt", traceback.format_exc())
        for snapshot in getattr(self, "snapshots", []):
            snapshot.write_to_error_directory(write_file)

        # Try to use the Selenium driver to recover more debug information, but don't
        # throw an exception if the connection is broken in some way.
        try:
            self.driver.save_screenshot(os.path.join(target_directory, "last.png"))
            write_file("page_source.txt", self.driver.page_source)
            write_file("DOM.txt", self.driver.execute_script("return document.documentElement.outerHTML"))
        except Exception:
            print("Failed to use test driver to recover debug information from Selenium.")
            write_file("selenium_exception.txt", traceback.format_exc())

        for log_type in ["browser", "driver"]:
            try:
                full_log = self.driver.get_log(log_type)
                trimmed_log = [l for l in full_log if l["level"] not in ["DEBUG", "INFO"]]
                write_file("%s.log.json" % log_type, json.dumps(trimmed_log, indent=True))
                write_file("%s.log.verbose.json" % log_type, json.dumps(full_log, indent=True))
            except Exception:
                continue


@nottest
def selenium_test(f):
    test_name = f.__name__

    @wraps(f)
    def func_wrapper(self, *args, **kwds):
        retry_attempts = 0
        while True:
            if retry_attempts > 0:
                self.reset_driver_and_session()
            try:
                return f(self, *args, **kwds)
            except unittest.SkipTest:
                dump_test_information(self, test_name)
                # Don't retry if we have purposely decided to skip the test.
                raise
            except Exception:
                dump_test_information(self, test_name)
                if retry_attempts < GALAXY_TEST_SELENIUM_RETRIES:
                    retry_attempts += 1
                    print("Test function [%s] threw an exception, retrying. Failed attempts - %s." % (test_name, retry_attempts))
                else:
                    raise

    return func_wrapper


retry_assertion_during_transitions = partial(retry_during_transitions, exception_check=lambda e: isinstance(e, AssertionError))


class TestSnapshot(object):

    def __init__(self, driver, index, description):
        self.screenshot_binary = driver.get_screenshot_as_png()
        self.description = description
        self.index = index
        self.exc = traceback.format_exc()
        self.stack = traceback.format_stack()

    def write_to_error_directory(self, write_file_func):
        prefix = "%d-%s" % (self.index, self.description)
        write_file_func("%s-screenshot.png" % prefix, self.screenshot_binary, raw=True)
        write_file_func("%s-traceback.txt" % prefix, self.exc)
        write_file_func("%s-stack.txt" % prefix, str(self.stack))


class SeleniumTestCase(FunctionalTestCase, NavigatesGalaxy, UsesApiTestCaseMixin):
    # If run one-off via nosetests, the next line ensures test
    # tools and datatypes are used instead of configured tools.
    framework_tool_and_types = True

    # Override this in subclasses to ensure a user is logged in
    # before each test. If GALAXY_TEST_SELENIUM_USER_EMAIL and
    # GALAXY_TEST_SELENIUM_USER_PASSWORD are set these values
    # will be used to login.
    ensure_registered = False
    requires_admin = False

    def setUp(self):
        super(SeleniumTestCase, self).setUp()
        # Deal with the case when Galaxy has a different URL when being accessed by Selenium
        # then when being accessed by local API calls.
        if GALAXY_TEST_EXTERNAL_FROM_SELENIUM is not None:
            self.target_url_from_selenium = GALAXY_TEST_EXTERNAL_FROM_SELENIUM
        else:
            self.target_url_from_selenium = self.url
        self.snapshots = []
        self.setup_driver_and_session()
        if self.requires_admin and GALAXY_TEST_SELENIUM_ADMIN_USER_EMAIL == DEFAULT_ADMIN_USER:
            self._setup_interactor()
            self._setup_user(GALAXY_TEST_SELENIUM_ADMIN_USER_EMAIL)
        self._try_setup_with_driver()

    def _try_setup_with_driver(self):
        try:
            self.setup_with_driver()
        except Exception:
            dump_test_information(self, self.__class__.__name__ + "_setup")
            raise

    def setup_with_driver(self):
        """Override point that allows setting up data using self.driver and Selenium connection.

        Overriding this instead of setUp will ensure debug data such as screenshots and stack traces
        are dumped if there are problems with the setup and it will be re-ran on test retries.
        """

    def tearDown(self):
        exception = None
        try:
            super(SeleniumTestCase, self).tearDown()
        except Exception as e:
            exception = e

        try:
            self.tear_down_driver()
        except Exception as e:
            exception = e

        if exception is not None:
            raise exception

    def snapshot(self, description):
        """Create a debug snapshot (DOM, screenshot, etc...) that is written out on tool failure.

        This information will be automatically written to a per-test directory created for all
        failed tests.
        """
        self.snapshots.append(TestSnapshot(self.driver, len(self.snapshots), description))

    def screenshot(self, label):
        """If GALAXY_TEST_SCREENSHOTS_DIRECTORY is set create a screenshot there named <label>.png.

        Unlike the above "snapshot" feature, this will be written out regardless and not in a per-test
        directory. The above method is used for debugging failures within a specific test. This method
        if more for creating a set of images to augment automated testing with manual human inspection
        after a test or test suite has executed.
        """
        target = self._screenshot_path(label)
        if target is None:
            return

        self.driver.save_screenshot(target)

    def write_screenshot_directory_file(self, label, content):
        target = self._screenshot_path(label, ".txt")
        if target is None:
            return

        with open(target, "w") as f:
            f.write(content)

    def _screenshot_path(self, label, extension=".png"):
        if GALAXY_TEST_SCREENSHOTS_DIRECTORY is None:
            return
        if not os.path.exists(GALAXY_TEST_SCREENSHOTS_DIRECTORY):
            os.makedirs(GALAXY_TEST_SCREENSHOTS_DIRECTORY)
        target = os.path.join(GALAXY_TEST_SCREENSHOTS_DIRECTORY, label + extension)
        copy = 1
        while os.path.exists(target):
            # Maybe previously a test re-run - keep the original.
            target = os.path.join(GALAXY_TEST_SCREENSHOTS_DIRECTORY, "%s-%d%s" % (label, copy, extension))
            copy += 1

        return target

    def reset_driver_and_session(self):
        self.tear_down_driver()
        self.setup_driver_and_session()
        self._try_setup_with_driver()

    def setup_driver_and_session(self):
        self.display = driver_factory.virtual_display_if_enabled(use_virtual_display())
        self.driver = get_driver()
        # New workflow index page does not degrade well to smaller sizes, needed
        # to increase this.
        # Needed to up the height for paired list creator being taller in BS4 branch.
        self.driver.set_window_size(1280, 1000)

        self._setup_galaxy_logging()

        if self.ensure_registered:
            self.login()

    def _setup_galaxy_logging(self):
        self.home()
        self.driver.execute_script(SETUP_LOGGING_JS)

    def login(self):
        if GALAXY_TEST_SELENIUM_USER_EMAIL:
            assert GALAXY_TEST_SELENIUM_USER_PASSWORD, "If GALAXY_TEST_SELENIUM_USER_EMAIL is set, a password must be set also with GALAXY_TEST_SELENIUM_USER_PASSWORD"
            self.home()
            self.submit_login(
                email=GALAXY_TEST_SELENIUM_USER_EMAIL,
                password=GALAXY_TEST_SELENIUM_USER_PASSWORD,
                assert_valid=True,
            )
        else:
            self.register()

    def tear_down_driver(self):
        exception = None
        try:
            self.driver.close()
        except Exception as e:
            if "cannot kill Chrome" in str(e):
                print("Ignoring likely harmless error in Selenium shutdown %s" % e)
            else:
                exception = e

        try:
            self.display.stop()
        except Exception as e:
            exception = e

        if exception is not None:
            raise exception

    @classproperty
    def default_web_host(cls):
        return default_web_host_for_selenium_tests()

    @property
    def timeout_multiplier(self):
        return TIMEOUT_MULTIPLIER

    def build_url(self, url, for_selenium=True):
        if for_selenium:
            base = self.target_url_from_selenium
        else:
            base = self.url
        return urljoin(base, url)

    def assert_initial_history_panel_state_correct(self):
        # Move into a TestsHistoryPanel mixin
        unnamed_name = self.components.history_panel.new_name.text

        name_element = self.history_panel_name_element()
        assert name_element.is_displayed()
        assert unnamed_name in name_element.text

        initial_size_str = self.components.history_panel.new_size.text
        size_selector = self.components.history_panel.size
        size_text = size_selector.wait_for_text()
        assert initial_size_str in size_text, "%s not in %s" % (initial_size_str, size_text)

        self.components.history_panel.empty_message.wait_for_visible()

    def admin_login(self):
        self.home()
        self.submit_login(
            GALAXY_TEST_SELENIUM_ADMIN_USER_EMAIL,
            GALAXY_TEST_SELENIUM_ADMIN_USER_PASSWORD
        )
        with self.main_panel():
            self.assert_no_error_message()

    @property
    def dataset_populator(self):
        return SeleniumSessionDatasetPopulator(self)

    @property
    def dataset_collection_populator(self):
        return SeleniumSessionDatasetCollectionPopulator(self)

    @property
    def workflow_populator(self):
        return SeleniumSessionWorkflowPopulator(self)

    def workflow_upload_yaml_with_random_name(self, content, **kwds):
        workflow_populator = self.workflow_populator
        name = self._get_random_name()
        workflow_populator.upload_yaml_workflow(content, name=name, **kwds)
        return name

    def ensure_visualization_available(self, hid, visualization_name):
        """Skip or fail a test if visualization for file doesn't appear.

        Precondition: viz menu has been opened with history_panel_item_click_visualization_menu.
        """
        visualization_names = self.history_panel_item_available_visualizations(hid)
        if visualization_name not in visualization_names:
            raise unittest.SkipTest("Skipping test, visualization [%s] doesn't appear to be configured." % visualization_name)


class SharedStateSeleniumTestCase(SeleniumTestCase):
    """This describes a class Selenium tests that setup class state for all tests.

    This is a bit hacky because we are simulating class level initialization
    with instance level methods. The problem is that super.setUp() works at
    instance level. It might be worth considering having two variants of
    SeleniumTestCase - one that initializes with the class and the other that
    initializes with the instance but all the helpers are instance helpers.
    """

    shared_state_initialized = False
    shared_state_in_error = False

    def setup_with_driver(self):
        if not self.__class__.shared_state_initialized:
            try:
                self.setup_shared_state()
                self.logout_if_needed()
            except Exception:
                self.__class__.shared_state_in_error = True
                raise
            finally:
                self.__class__.shared_state_initialized = True
        else:
            if self.__class__.shared_state_in_error:
                raise unittest.SkipTest("Skipping test, failed to initialize state previously.")

    def setup_shared_state(self):
        """Override this to setup shared data for tests that gets initialized only once."""


class UsesHistoryItemAssertions(object):

    def assert_item_peek_includes(self, hid, expected):
        item_body = self.history_panel_item_component(hid=hid)
        peek_text = item_body.peek.wait_for_text()
        assert expected in peek_text

    def assert_item_info_includes(self, hid, expected):
        item_body = self.history_panel_item_component(hid=hid)
        info_text = item_body.info.wait_for_text()
        assert expected in info_text, "Failed to find expected info text [%s] in info [%s]" % (expected, info_text)

    def assert_item_dbkey_displayed_as(self, hid, dbkey):
        item_body = self.history_panel_item_component(hid=hid)
        dbkey_text = item_body.dbkey.wait_for_text()
        assert dbkey in dbkey_text

    def assert_item_summary_includes(self, hid, expected_text):
        item_body = self.history_panel_item_component(hid=hid)
        summary_text = item_body.summary.wait_for_text()
        assert expected_text in summary_text, "Expected summary [%s] not found in [%s]." % (expected_text, summary_text)

    def assert_item_name(self, hid, expected_name):
        item_body = self.history_panel_item_component(hid=hid)
        name = item_body.name.wait_for_text()
        assert name == expected_name, name

    def assert_item_hid_text(self, hid):
        # Check the text HID matches HID returned from API.
        item_body = self.history_panel_item_component(hid=hid)
        hid_text = item_body.hid.wait_for_text()
        assert hid_text == str(hid), hid_text


def default_web_host_for_selenium_tests():
    if asbool(GALAXY_TEST_SELENIUM_REMOTE):
        try:
            dev_ip = get_ip_address('docker0')
            return dev_ip
        except IOError:
            return DEFAULT_WEB_HOST
    else:
        return DEFAULT_WEB_HOST


def get_driver():
    if asbool(GALAXY_TEST_SELENIUM_REMOTE):
        return get_remote_driver()
    else:
        return get_local_driver()


def headless_selenium():
    if asbool(GALAXY_TEST_SELENIUM_REMOTE):
        return False

    if GALAXY_TEST_SELENIUM_HEADLESS == "auto":
        if driver_factory.is_virtual_display_available() or driver_factory.get_local_browser(GALAXY_TEST_SELENIUM_BROWSER) == "CHROME":
            return True
        else:
            return False
    else:
        return asbool(GALAXY_TEST_SELENIUM_HEADLESS)


def use_virtual_display():
    if asbool(GALAXY_TEST_SELENIUM_REMOTE):
        return False

    if GALAXY_TEST_SELENIUM_HEADLESS == "auto":
        if driver_factory.is_virtual_display_available() and not driver_factory.get_local_browser(GALAXY_TEST_SELENIUM_BROWSER) == "CHROME":
            return True
        else:
            return False
    else:
        return asbool(GALAXY_TEST_SELENIUM_HEADLESS)


def get_local_driver():
    return driver_factory.get_local_driver(
        GALAXY_TEST_SELENIUM_BROWSER,
        headless_selenium()
    )


def get_remote_driver():
    return driver_factory.get_remote_driver(
        host=GALAXY_TEST_SELENIUM_REMOTE_HOST,
        port=GALAXY_TEST_SELENIUM_REMOTE_PORT,
        browser=GALAXY_TEST_SELENIUM_BROWSER,
    )


class SeleniumSessionGetPostMixin(object):
    """Mixin for adapting Galaxy testing populators helpers to Selenium session backed bioblend."""

    def _get(self, route, data={}):
        full_url = self.selenium_test_case.build_url("api/" + route, for_selenium=False)
        response = requests.get(full_url, data=data, cookies=self.selenium_test_case.selenium_to_requests_cookies())
        return response

    def _post(self, route, data={}):
        full_url = self.selenium_test_case.build_url("api/" + route, for_selenium=False)
        response = requests.post(full_url, data=data, cookies=self.selenium_test_case.selenium_to_requests_cookies())
        return response

    def _delete(self, route, data={}):
        full_url = self.selenium_test_case.build_url("api/" + route, for_selenium=False)
        response = requests.delete(full_url, data=data, cookies=self.selenium_test_case.selenium_to_requests_cookies())
        return response

    def __url(self, route):
        return self._gi.url + "/" + route


class SeleniumSessionDatasetPopulator(populators.BaseDatasetPopulator, SeleniumSessionGetPostMixin):

    """Implementation of BaseDatasetPopulator backed by bioblend."""

    def __init__(self, selenium_test_case):
        """Construct a dataset populator from a bioblend GalaxyInstance."""
        self.selenium_test_case = selenium_test_case


class SeleniumSessionDatasetCollectionPopulator(populators.BaseDatasetCollectionPopulator, SeleniumSessionGetPostMixin):

    """Implementation of BaseDatasetCollectionPopulator backed by bioblend."""

    def __init__(self, selenium_test_case):
        """Construct a dataset collection populator from a bioblend GalaxyInstance."""
        self.selenium_test_case = selenium_test_case
        self.dataset_populator = SeleniumSessionDatasetPopulator(selenium_test_case)

    def _create_collection(self, payload):
        create_response = self._post("dataset_collections", data=payload)
        return create_response


class SeleniumSessionWorkflowPopulator(populators.BaseWorkflowPopulator, SeleniumSessionGetPostMixin, ImporterGalaxyInterface):

    """Implementation of BaseWorkflowPopulator backed by bioblend."""

    def __init__(self, selenium_test_case):
        """Construct a workflow populator from a bioblend GalaxyInstance."""
        self.selenium_test_case = selenium_test_case
        self.dataset_populator = SeleniumSessionDatasetPopulator(selenium_test_case)

    def import_workflow(self, workflow, **kwds):
        workflow_str = json.dumps(workflow, indent=4)
        data = {
            'workflow': workflow_str,
        }
        data.update(**kwds)
        upload_response = self._post("workflows", data=data)
        assert upload_response.status_code == 200
        return upload_response.json()

    def upload_yaml_workflow(self, has_yaml, **kwds):
        workflow = convert_and_import_workflow(has_yaml, galaxy_interface=self, **kwds)
        return workflow["id"]
