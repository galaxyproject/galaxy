"""Basis for Selenium test framework."""

import datetime
import json
import os
import traceback
import unittest
from functools import (
    partial,
    wraps,
)
from typing import (
    Any,
    Dict,
    Optional,
    Tuple,
    TYPE_CHECKING,
)

import requests
import yaml
from gxformat2 import (
    convert_and_import_workflow,
    ImporterGalaxyInterface,
)
from requests.models import Response

from galaxy.selenium import driver_factory
from galaxy.selenium.context import GalaxySeleniumContext
from galaxy.selenium.navigates_galaxy import (
    NavigatesGalaxy,
    retry_during_transitions,
)
from galaxy.tool_util.verify.interactor import prepare_request_params
from galaxy.util import (
    asbool,
    classproperty,
    DEFAULT_SOCKET_TIMEOUT,
)
from galaxy.util.unittest_utils import skip_if_github_down
from galaxy_test.base import populators
from galaxy_test.base.api import (
    UsesApiTestCaseMixin,
    UsesCeleryTasks,
)
from galaxy_test.base.api_util import get_admin_api_key
from galaxy_test.base.decorators import (
    requires_new_history,
    using_requirement,
)
from galaxy_test.base.env import (
    DEFAULT_WEB_HOST,
    get_ip_address,
)
from galaxy_test.base.populators import (
    load_data_dict,
    YamlContentT,
)
from galaxy_test.base.testcase import FunctionalTestCase

try:
    from galaxy_test.driver.driver_util import GalaxyTestDriver
except ImportError:
    GalaxyTestDriver = None  # type: ignore[misc,assignment]

DEFAULT_TIMEOUT_MULTIPLIER = 1
DEFAULT_TEST_ERRORS_DIRECTORY = os.path.abspath("database/test_errors")
DEFAULT_SELENIUM_HEADLESS = "auto"
DEFAULT_ADMIN_USER = "test@bx.psu.edu"
DEFAULT_ADMIN_PASSWORD = "testpass"
DEFAULT_DOWNLOAD_PATH = driver_factory.DEFAULT_DOWNLOAD_PATH


TIMEOUT_MULTIPLIER = float(os.environ.get("GALAXY_TEST_TIMEOUT_MULTIPLIER", DEFAULT_TIMEOUT_MULTIPLIER))
GALAXY_TEST_ERRORS_DIRECTORY = os.environ.get("GALAXY_TEST_ERRORS_DIRECTORY", DEFAULT_TEST_ERRORS_DIRECTORY)
GALAXY_TEST_SCREENSHOTS_DIRECTORY = os.environ.get("GALAXY_TEST_SCREENSHOTS_DIRECTORY", None)
# Test browser can be ["CHROME", "FIREFOX"]
GALAXY_TEST_SELENIUM_BROWSER = os.environ.get("GALAXY_TEST_SELENIUM_BROWSER", driver_factory.DEFAULT_SELENIUM_BROWSER)
GALAXY_TEST_SELENIUM_REMOTE = os.environ.get("GALAXY_TEST_SELENIUM_REMOTE", driver_factory.DEFAULT_SELENIUM_REMOTE)
GALAXY_TEST_SELENIUM_REMOTE_PORT = os.environ.get(
    "GALAXY_TEST_SELENIUM_REMOTE_PORT", driver_factory.DEFAULT_SELENIUM_REMOTE_PORT
)
GALAXY_TEST_SELENIUM_REMOTE_HOST = os.environ.get(
    "GALAXY_TEST_SELENIUM_REMOTE_HOST", driver_factory.DEFAULT_SELENIUM_REMOTE_HOST
)
GALAXY_TEST_SELENIUM_HEADLESS = os.environ.get("GALAXY_TEST_SELENIUM_HEADLESS", DEFAULT_SELENIUM_HEADLESS)
GALAXY_TEST_EXTERNAL_FROM_SELENIUM = os.environ.get("GALAXY_TEST_EXTERNAL_FROM_SELENIUM", None)
# Auto-retry selenium tests this many times.
GALAXY_TEST_SELENIUM_RETRIES = int(os.environ.get("GALAXY_TEST_SELENIUM_RETRIES", "0"))

GALAXY_TEST_SELENIUM_USER_EMAIL = os.environ.get("GALAXY_TEST_SELENIUM_USER_EMAIL", None)
GALAXY_TEST_SELENIUM_USER_PASSWORD = os.environ.get("GALAXY_TEST_SELENIUM_USER_PASSWORD", None)
GALAXY_TEST_SELENIUM_ADMIN_USER_EMAIL = os.environ.get("GALAXY_TEST_SELENIUM_ADMIN_USER_EMAIL", DEFAULT_ADMIN_USER)
GALAXY_TEST_SELENIUM_ADMIN_USER_PASSWORD = os.environ.get(
    "GALAXY_TEST_SELENIUM_ADMIN_USER_PASSWORD", DEFAULT_ADMIN_PASSWORD
)

# JS code to execute in Galaxy JS console to setup localStorage of session for logging and
# logging "flatten" messages because it seems Selenium (with Chrome at least) only grabs
# the first argument to console.XXX when recovering the browser log.
SETUP_LOGGING_JS = """
window.localStorage && window.localStorage.setItem("galaxy:debug", true);
window.localStorage && window.localStorage.setItem("galaxy:debug:flatten", true);
"""


def managed_history(f):
    """Ensure a Selenium test has a distinct, named history.

    Cleanup the history after the job is complete as well unless
    GALAXY_TEST_NO_CLEANUP is set in the environment.
    """
    f = requires_new_history(f)

    @wraps(f)
    def func_wrapper(self, *args, **kwds):
        self.home()
        history_name = f.__name__ + datetime.datetime.now().strftime("%Y%m%d%H%M%s")
        self.history_panel_create_new_with_name(history_name)
        try:
            f(self, *args, **kwds)
        finally:
            if "GALAXY_TEST_NO_CLEANUP" not in os.environ:
                try:
                    current_history_id = self.current_history_id()
                    self.dataset_populator.cancel_history_jobs(current_history_id)
                    self.api_delete(f"histories/{current_history_id}")
                except Exception:
                    print("Faild to cleanup managed history, selenium connection corrupted somehow?")

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
            formatted_exception = traceback.format_exc()
            print(f"Failed to use test driver to recover debug information from Selenium: {formatted_exception}")
            write_file("selenium_exception.txt", formatted_exception)

        for log_type in ["browser", "driver"]:
            try:
                full_log = self.driver.get_log(log_type)
                trimmed_log = [entry for entry in full_log if entry["level"] not in ["DEBUG", "INFO"]]
                write_file(f"{log_type}.log.json", json.dumps(trimmed_log, indent=True))
                write_file(f"{log_type}.log.verbose.json", json.dumps(full_log, indent=True))
            except Exception:
                continue


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
                    print(
                        f"Test function [{test_name}] threw an exception, retrying. Failed attempts - {retry_attempts}."
                    )
                else:
                    raise

    return func_wrapper


retry_assertion_during_transitions = partial(
    retry_during_transitions, exception_check=lambda e: isinstance(e, AssertionError)
)


class TestSnapshot:
    __test__ = False  # Prevent pytest from discovering this class (issue #12071)

    def __init__(self, driver, index, description):
        self.screenshot_binary = driver.get_screenshot_as_png()
        self.description = description
        self.index = index
        self.exc = traceback.format_exc()
        self.stack = traceback.format_stack()

    def write_to_error_directory(self, write_file_func):
        prefix = "%d-%s" % (self.index, self.description)
        write_file_func(f"{prefix}-screenshot.png", self.screenshot_binary, raw=True)
        write_file_func(f"{prefix}-traceback.txt", self.exc)
        write_file_func(f"{prefix}-stack.txt", str(self.stack))


class GalaxyTestSeleniumContext(GalaxySeleniumContext):
    """Extend GalaxySeleniumContext with Selenium-aware galaxy_test.base.populators."""

    @property
    def dataset_populator(self) -> "SeleniumSessionDatasetPopulator":
        """A dataset populator connected to the Galaxy session described by Selenium context."""
        return SeleniumSessionDatasetPopulator(self)

    @property
    def dataset_collection_populator(self) -> populators.BaseDatasetCollectionPopulator:
        """A dataset collection populator connected to the Galaxy session described by Selenium context."""
        return SeleniumSessionDatasetCollectionPopulator(self)

    @property
    def workflow_populator(self) -> populators.BaseWorkflowPopulator:
        """A workflow populator connected to the Galaxy session described by Selenium context."""
        return SeleniumSessionWorkflowPopulator(self)


class TestWithSeleniumMixin(GalaxyTestSeleniumContext, UsesApiTestCaseMixin, UsesCeleryTasks):
    # If run one-off via pytest, the next line ensures test
    # tools and datatypes are used instead of configured tools.
    framework_tool_and_types = True

    # Override this in subclasses to ensure a user is logged in
    # before each test. If GALAXY_TEST_SELENIUM_USER_EMAIL and
    # GALAXY_TEST_SELENIUM_USER_PASSWORD are set these values
    # will be used to login.
    ensure_registered = False

    # Override this in subclasses to annotate that an admin user
    # is required for the test to run properly. Override admin user
    # login info with GALAXY_TEST_SELENIUM_ADMIN_USER_EMAIL /
    # GALAXY_TEST_SELENIUM_ADMIN_USER_PASSWORD
    run_as_admin = False

    def _target_url_from_selenium(self):
        # Deal with the case when Galaxy has a different URL when being accessed by Selenium
        # then when being accessed by local API calls.
        if GALAXY_TEST_EXTERNAL_FROM_SELENIUM is not None:
            target_url_from_selenium = GALAXY_TEST_EXTERNAL_FROM_SELENIUM
        else:
            target_url_from_selenium = self.url
        return target_url_from_selenium

    def setup_selenium(self):
        self.target_url_from_selenium = self._target_url_from_selenium()
        self.snapshots = []
        self.setup_driver_and_session()
        if self.run_as_admin and GALAXY_TEST_SELENIUM_ADMIN_USER_EMAIL == DEFAULT_ADMIN_USER:
            self._setup_interactor()
            self._setup_user(GALAXY_TEST_SELENIUM_ADMIN_USER_EMAIL)
        self._try_setup_with_driver()

    def _try_setup_with_driver(self):
        try:
            self.setup_with_driver()
        except Exception:
            dump_test_information(self, f"{self.__class__.__name__}_setup")
            raise

    def setup_with_driver(self):
        """Override point that allows setting up data using self.driver and Selenium connection.

        Overriding this instead of setUp will ensure debug data such as screenshots and stack traces
        are dumped if there are problems with the setup and it will be re-ran on test retries.
        """
        if self.ensure_registered:
            self.login()

    def tear_down_selenium(self):
        self.tear_down_driver()

    def snapshot(self, description):
        """Create a debug snapshot (DOM, screenshot, etc...) that is written out on tool failure.

        This information will be automatically written to a per-test directory created for all
        failed tests.
        """
        self.snapshots.append(TestSnapshot(self.driver, len(self.snapshots), description))

    def get_download_path(self):
        """Returns default download path"""
        return DEFAULT_DOWNLOAD_PATH

    def api_interactor_for_logged_in_user(self):
        api_key = self.get_api_key(force=True)
        interactor = self._get_interactor(api_key=api_key)
        return interactor

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
        self.target_url_from_selenium = self._target_url_from_selenium()
        self.setup_driver_and_session()
        self._try_setup_with_driver()

    def setup_driver_and_session(self):
        self.display = driver_factory.virtual_display_if_enabled(use_virtual_display())
        self.configured_driver = get_configured_driver()
        self._setup_galaxy_logging()

    def _setup_galaxy_logging(self):
        self.home()
        self.driver.execute_script(SETUP_LOGGING_JS)

    def login(self):
        if GALAXY_TEST_SELENIUM_USER_EMAIL:
            assert (
                GALAXY_TEST_SELENIUM_USER_PASSWORD
            ), "If GALAXY_TEST_SELENIUM_USER_EMAIL is set, a password must be set also with GALAXY_TEST_SELENIUM_USER_PASSWORD"
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
                print(f"Ignoring likely harmless error in Selenium shutdown {e}")
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

    def assert_initial_history_panel_state_correct(self):
        # Move into a TestsHistoryPanel mixin
        unnamed_name = self.components.history_panel.new_name.text
        name_element = self.history_panel_name_element()

        assert name_element.is_displayed()
        assert unnamed_name in name_element.text

        self.components.history_panel.empty_message.wait_for_visible()

    def admin_login(self):
        using_requirement("admin")
        self.home()
        self.submit_login(GALAXY_TEST_SELENIUM_ADMIN_USER_EMAIL, GALAXY_TEST_SELENIUM_ADMIN_USER_PASSWORD)
        with self.main_panel():
            self.assert_no_error_message()
        return GALAXY_TEST_SELENIUM_ADMIN_USER_EMAIL

    @retry_assertion_during_transitions
    def assert_workflow_has_changes_and_save(self):
        save_button = self.components.workflow_editor.save_button
        save_button.wait_for_visible()
        assert not save_button.has_class("disabled")
        save_button.wait_for_and_click()
        self.sleep_for(self.wait_types.UX_RENDER)

    @retry_assertion_during_transitions
    def assert_modal_has_text(self, expected_text):
        modal_element = self.components.workflow_editor.state_modal_body.wait_for_visible()
        text = modal_element.text
        assert expected_text in text, f"Failed to find expected text [{expected_text}] in modal text [{text}]"

    def ensure_visualization_available(self, hid, visualization_name):
        """Skip or fail a test if visualization for file doesn't appear.

        Precondition: viz menu has been opened with history_panel_item_click_visualization_menu.
        """
        visualization_names = self.history_panel_item_available_visualizations(hid)
        if visualization_name not in visualization_names:
            raise unittest.SkipTest(
                f"Skipping test, visualization [{visualization_name}] doesn't appear to be configured."
            )


class SeleniumTestCase(FunctionalTestCase, TestWithSeleniumMixin):
    galaxy_driver_class = GalaxyTestDriver

    def setUp(self):
        super().setUp()
        self.setup_selenium()
        self.admin_api_key = get_admin_api_key()

    def tearDown(self):
        exception = None
        try:
            self.tear_down_selenium()
        except Exception as e:
            exception = e

        try:
            super().tearDown()
        except Exception as e:
            exception = e

        if exception is not None:
            raise exception


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


if TYPE_CHECKING:
    NavigatesGalaxyMixin = NavigatesGalaxy
else:
    NavigatesGalaxyMixin = object


class UsesLibraryAssertions(NavigatesGalaxyMixin):
    @retry_assertion_during_transitions
    def assert_num_displayed_items_is(self, n):
        num_displayed = self.num_displayed_items()
        assert n == num_displayed, f"Expected number of displayed items is {n} but actual was {num_displayed}"

    def num_displayed_items(self) -> int:
        return len(self.libraries_table_elements())


class UsesHistoryItemAssertions(NavigatesGalaxyMixin):
    def assert_item_peek_includes(self, hid, expected):
        item_body = self.history_panel_item_component(hid=hid)
        peek_text = item_body.peek.wait_for_text()
        assert expected in peek_text

    def assert_item_info_includes(self, hid, expected):
        item_body = self.history_panel_item_component(hid=hid)
        info_text = item_body.info.wait_for_text()
        assert expected in info_text, f"Failed to find expected info text [{expected}] in info [{info_text}]"

    def assert_item_dbkey_displayed_as(self, hid, dbkey):
        item_body = self.history_panel_item_component(hid=hid)
        dbkey_text = item_body.dbkey.wait_for_text()
        assert dbkey in dbkey_text

    def assert_item_summary_includes(self, hid, expected_text):
        item_body = self.history_panel_item_component(hid=hid)
        summary_text = item_body.summary.wait_for_text()
        assert expected_text in summary_text, f"Expected summary [{expected_text}] not found in [{summary_text}]."

    def assert_item_name(self, hid, expected_name):
        item_body = self.history_panel_item_component(hid=hid)
        name = item_body.name.wait_for_text()
        assert name == expected_name, name

    def assert_item_hid_text(self, hid):
        # Check the text HID matches HID returned from API.
        item_body = self.history_panel_item_component(hid=hid)
        hid_text = item_body.hid.wait_for_text()
        assert hid_text == str(hid), hid_text


EXAMPLE_WORKFLOW_URL_1 = (
    "https://raw.githubusercontent.com/galaxyproject/galaxy/release_19.09/test/base/data/test_workflow_1.ga"
)


class UsesWorkflowAssertions(NavigatesGalaxyMixin):
    @retry_assertion_during_transitions
    def _assert_showing_n_workflows(self, n):
        actual_count = len(self.workflow_index_table_elements())
        if actual_count != n:
            message = f"Expected {n} workflows to be displayed, based on DOM found {actual_count} workflow rows."
            raise AssertionError(message)

    @skip_if_github_down
    def _workflow_import_from_url(self, url=EXAMPLE_WORKFLOW_URL_1):
        self.workflow_index_click_import()
        self.workflow_import_submit_url(url)


class TestsGalaxyPagers(GalaxyTestSeleniumContext):
    @retry_assertion_during_transitions
    def _assert_current_page_is(self, component, expected_page: int):
        component.pager.wait_for_visible()
        page_from_pager = component.pager_page_active.wait_for_present().text
        assert int(page_from_pager) == expected_page

    def _next_page(self, component):
        component.pager_page_next.wait_for_and_click()

    def _previous_page(self, component):
        component.pager_page_previous.wait_for_and_click()

    def _last_page(self, component):
        component.pager_page_last.wait_for_and_click()

    def _first_page(self, component):
        component.pager_page_first.wait_for_and_click()


class RunsWorkflows(GalaxyTestSeleniumContext):
    def workflow_upload_yaml_with_random_name(self, content: str, **kwds) -> str:
        name = self._get_random_name()
        workflow_populator = self.workflow_populator
        workflow_populator.upload_yaml_workflow(content, name=name, **kwds)
        return name

    def workflow_run_setup_inputs(self, content: Optional[str]) -> Tuple[str, Dict[str, Any]]:
        history_id = self.current_history_id()
        if content:
            yaml_content = yaml.safe_load(content)
            if "test_data" in yaml_content:
                test_data = yaml_content["test_data"]
            else:
                test_data = yaml_content
            inputs, _, _ = load_data_dict(
                history_id, test_data, self.dataset_populator, self.dataset_collection_populator
            )
            self.dataset_populator.wait_for_history(history_id)
        else:
            inputs = {}
        return history_id, inputs

    def workflow_run_open_workflow(self, yaml_content: str):
        name = self.workflow_upload_yaml_with_random_name(yaml_content)
        self.workflow_run_with_name(name)

    def workflow_run_and_submit(
        self,
        workflow_content: str,
        test_data_content: Optional[str] = None,
        landing_screenshot_name=None,
        inputs_specified_screenshot_name: Optional[str] = None,
        ensure_expanded: bool = False,
    ):
        history_id, inputs = self.workflow_run_setup_inputs(test_data_content)
        self.workflow_run_open_workflow(workflow_content)
        if ensure_expanded:
            self.workflow_run_ensure_expanded()
        self.screenshot_if(landing_screenshot_name)
        self.workflow_run_specify_inputs(inputs)
        self.screenshot_if(inputs_specified_screenshot_name)
        self.workflow_run_submit()
        self.sleep_for(self.wait_types.UX_TRANSITION)
        return history_id

    def workflow_run_wait_for_ok(self, hid: int, expand=False):
        timeout = self.wait_length(self.wait_types.JOB_COMPLETION)
        item = self.content_item_by_attributes(hid=hid, state="ok")
        item.wait_for_present(timeout=timeout)
        if expand:
            item.title.wait_for_and_click()


def default_web_host_for_selenium_tests():
    if asbool(GALAXY_TEST_SELENIUM_REMOTE):
        try:
            dev_ip = get_ip_address("docker0")
            return dev_ip
        except OSError:
            return DEFAULT_WEB_HOST
    else:
        return DEFAULT_WEB_HOST


def get_configured_driver():
    return driver_factory.ConfiguredDriver(
        browser=GALAXY_TEST_SELENIUM_BROWSER,
        remote=asbool(GALAXY_TEST_SELENIUM_REMOTE),
        remote_host=GALAXY_TEST_SELENIUM_REMOTE_HOST,
        remote_port=GALAXY_TEST_SELENIUM_REMOTE_PORT,
        headless=headless_selenium(),
    )


def headless_selenium():
    if asbool(GALAXY_TEST_SELENIUM_REMOTE):
        return False

    if GALAXY_TEST_SELENIUM_HEADLESS == "auto":
        if (
            driver_factory.is_virtual_display_available()
            or driver_factory.get_local_browser(GALAXY_TEST_SELENIUM_BROWSER) == "CHROME"
        ):
            return True
        else:
            return False
    else:
        return asbool(GALAXY_TEST_SELENIUM_HEADLESS)


def use_virtual_display():
    if asbool(GALAXY_TEST_SELENIUM_REMOTE):
        return False

    if GALAXY_TEST_SELENIUM_HEADLESS == "auto":
        if (
            driver_factory.is_virtual_display_available()
            and not driver_factory.get_local_browser(GALAXY_TEST_SELENIUM_BROWSER) == "CHROME"
        ):
            return True
        else:
            return False
    else:
        return asbool(GALAXY_TEST_SELENIUM_HEADLESS)


class SeleniumSessionGetPostMixin:
    """Mixin for adapting Galaxy testing populators helpers to Selenium session backed bioblend."""

    selenium_context: GalaxySeleniumContext

    @property
    def _mixin_admin_api_key(self) -> str:
        return getattr(self, "admin_api_key", get_admin_api_key())

    def _get(self, route, data=None, headers=None, admin=False) -> Response:
        data = data or {}
        full_url = self.selenium_context.build_url(f"api/{route}", for_selenium=False)
        cookies = None
        if admin:
            full_url = f"{full_url}?key={self._mixin_admin_api_key}"
        else:
            cookies = self.selenium_context.selenium_to_requests_cookies()
        response = requests.get(full_url, params=data, cookies=cookies, headers=headers, timeout=DEFAULT_SOCKET_TIMEOUT)
        return response

    def _post(self, route, data=None, files=None, headers=None, admin=False, json: bool = False) -> Response:
        full_url = self.selenium_context.build_url(f"api/{route}", for_selenium=False)
        cookies = None
        if admin:
            full_url = f"{full_url}?key={self._mixin_admin_api_key}"
        else:
            cookies = self.selenium_context.selenium_to_requests_cookies()
        request_kwd = prepare_request_params(data=data, files=files, as_json=json, headers=headers, cookies=cookies)
        response = requests.post(full_url, timeout=DEFAULT_SOCKET_TIMEOUT, **request_kwd)
        return response

    def _delete(self, route, data=None, headers=None, admin=False, json: bool = False) -> Response:
        full_url = self.selenium_context.build_url(f"api/{route}", for_selenium=False)
        cookies = None
        if admin:
            full_url = f"{full_url}?key={self._mixin_admin_api_key}"
        else:
            cookies = self.selenium_context.selenium_to_requests_cookies()
        request_kwd = prepare_request_params(data=data, as_json=json, headers=headers, cookies=cookies)
        response = requests.delete(full_url, timeout=DEFAULT_SOCKET_TIMEOUT, **request_kwd)
        return response

    def _put(self, route, data=None, headers=None, admin=False, json: bool = False) -> Response:
        full_url = self.selenium_context.build_url(f"api/{route}", for_selenium=False)
        cookies = None
        if admin:
            full_url = f"{full_url}?key={self._mixin_admin_api_key}"
        else:
            cookies = self.selenium_context.selenium_to_requests_cookies()
        request_kwd = prepare_request_params(data=data, as_json=json, headers=headers, cookies=cookies)
        response = requests.put(full_url, **request_kwd)
        return response


class SeleniumSessionDatasetPopulator(SeleniumSessionGetPostMixin, populators.BaseDatasetPopulator):

    """Implementation of BaseDatasetPopulator backed by bioblend."""

    def __init__(self, selenium_context: GalaxySeleniumContext):
        """Construct a dataset populator from a bioblend GalaxyInstance."""
        self.selenium_context = selenium_context

    def _summarize_history(self, history_id: str) -> None:
        pass


class SeleniumSessionDatasetCollectionPopulator(SeleniumSessionGetPostMixin, populators.BaseDatasetCollectionPopulator):

    """Implementation of BaseDatasetCollectionPopulator backed by bioblend."""

    def __init__(self, selenium_context: GalaxySeleniumContext):
        """Construct a dataset collection populator from a bioblend GalaxyInstance."""
        self.selenium_context = selenium_context
        self.dataset_populator = SeleniumSessionDatasetPopulator(selenium_context)

    def _create_collection(self, payload: dict) -> Response:
        create_response = self._post("dataset_collections", data=payload, json=True)
        return create_response


class SeleniumSessionWorkflowPopulator(
    SeleniumSessionGetPostMixin, populators.BaseWorkflowPopulator, ImporterGalaxyInterface
):

    """Implementation of BaseWorkflowPopulator backed by bioblend."""

    def __init__(self, selenium_context: GalaxySeleniumContext):
        """Construct a workflow populator from a bioblend GalaxyInstance."""
        self.selenium_context = selenium_context
        self.dataset_populator = SeleniumSessionDatasetPopulator(selenium_context)
        self.dataset_collection_populator = SeleniumSessionDatasetCollectionPopulator(selenium_context)

    def import_workflow(self, workflow: dict, **kwds) -> dict:
        workflow_str = json.dumps(workflow, indent=4)
        data = {
            "workflow": workflow_str,
        }
        data.update(**kwds)
        upload_response = self._post("workflows", data=data)
        upload_response.raise_for_status()
        return upload_response.json()

    def upload_yaml_workflow(self, yaml_content: YamlContentT, **kwds) -> str:
        workflow = convert_and_import_workflow(yaml_content, galaxy_interface=self, **kwds)
        return workflow["id"]


__all__ = ("retry_during_transitions",)
