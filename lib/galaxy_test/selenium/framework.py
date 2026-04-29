"""Basis for Selenium test framework."""

import datetime
import errno
import json
import logging
import os
import traceback
import unittest
from functools import (
    partial,
    wraps,
)
from typing import (
    Any,
    cast,
    Optional,
    TYPE_CHECKING,
)

import requests
import yaml
from requests.models import Response
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By

from galaxy.selenium import driver_factory
from galaxy.selenium.axe_results import assert_baseline_accessible
from galaxy.selenium.context import GalaxySeleniumContext
from galaxy.selenium.has_driver import (
    DEFAULT_AXE_SCRIPT_URL,
    SeleniumTimeoutException,
)
from galaxy.selenium.has_driver_protocol import (
    BackendType,
    HasDriverProtocol,
)
from galaxy.selenium.navigates_galaxy import (
    exception_seems_to_indicate_transition,
    galaxy_timeout_handler,
    NavigatesGalaxy,
    retry_during_transitions,
)
from galaxy.tool_util.verify import (
    verify,
    verify_job_metadata,
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
    stage_inputs,
)
from galaxy_test.base.testcase import FunctionalTestCase

try:
    from galaxy_test.driver.driver_util import GalaxyTestDriver
except ImportError:
    GalaxyTestDriver = None  # type: ignore[assignment, misc, unused-ignore]

logger = logging.getLogger(__name__)


def _load_config_file() -> None:
    """
    Load test configuration from YAML file if GALAXY_TEST_END_TO_END_CONFIG is set.

    This matches the configuration format used for Jupyter-based testing.
    Explicit environment variables take precedence over config file values.
    """
    config_file = os.environ.get("GALAXY_TEST_END_TO_END_CONFIG")
    if not config_file:
        return

    # Expand user paths like ~/config.yml
    config_file = os.path.expanduser(config_file)

    if not os.path.exists(config_file):
        raise FileNotFoundError(
            f"GALAXY_TEST_END_TO_END_CONFIG is set to '{config_file}' but file does not exist. "
            f"Please check the path or unset GALAXY_TEST_END_TO_END_CONFIG."
        )

    try:
        with open(config_file) as f:
            config = yaml.safe_load(f)
    except Exception as e:
        raise ValueError(f"Failed to load GALAXY_TEST_END_TO_END_CONFIG '{config_file}': {e}") from e

    if not isinstance(config, dict):
        raise ValueError(
            f"GALAXY_TEST_END_TO_END_CONFIG '{config_file}' must contain a YAML dictionary, got {type(config)}"
        )

    # Map config keys to environment variables
    # Only set if not already present (explicit env vars take precedence)
    key_mapping = {
        "local_galaxy_url": "GALAXY_TEST_EXTERNAL",
        "login_email": "GALAXY_TEST_SELENIUM_USER_EMAIL",
        "login_password": "GALAXY_TEST_SELENIUM_USER_PASSWORD",
        "admin_api_key": "GALAXY_TEST_SELENIUM_ADMIN_API_KEY",
        "admin_email": "GALAXY_TEST_SELENIUM_ADMIN_USER_EMAIL",
        "admin_password": "GALAXY_TEST_SELENIUM_ADMIN_USER_PASSWORD",
        "selenium_galaxy_url": "GALAXY_TEST_EXTERNAL_FROM_SELENIUM",
    }

    for config_key, env_var in key_mapping.items():
        if config_key in config and config[config_key] is not None:
            if env_var not in os.environ:
                os.environ[env_var] = str(config[config_key])

    os.environ["GALAXY_TEST_ENVIRONMENT_CONFIGURED"] = "1"


# Load config file before reading environment variables
_load_config_file()

DEFAULT_TIMEOUT_MULTIPLIER = 1
DEFAULT_TEST_ERRORS_DIRECTORY = os.path.abspath("database/test_errors")
DEFAULT_SELENIUM_HEADLESS = "auto"
DEFAULT_ADMIN_USER = "test@bx.psu.edu"
DEFAULT_ADMIN_PASSWORD = "testpass"
DEFAULT_DOWNLOAD_PATH = driver_factory.DEFAULT_DOWNLOAD_PATH


TIMEOUT_MULTIPLIER = float(os.environ.get("GALAXY_TEST_TIMEOUT_MULTIPLIER", DEFAULT_TIMEOUT_MULTIPLIER))
GALAXY_TEST_ERRORS_DIRECTORY = os.environ.get("GALAXY_TEST_ERRORS_DIRECTORY", DEFAULT_TEST_ERRORS_DIRECTORY)
GALAXY_TEST_SCREENSHOTS_DIRECTORY = os.environ.get("GALAXY_TEST_SCREENSHOTS_DIRECTORY", None)
# Driver backend can be ["selenium", "playwright"]
GALAXY_TEST_DRIVER_BACKEND = os.environ.get("GALAXY_TEST_DRIVER_BACKEND", "selenium")
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
GALAXY_TEST_AXE_SCRIPT_URL = os.environ.get("GALAXY_TEST_AXE_SCRIPT_URL", DEFAULT_AXE_SCRIPT_URL)
GALAXY_TEST_SKIP_AXE = os.environ.get("GALAXY_TEST_SKIP_AXE", "0") == "1"

# JS code to execute in Galaxy JS console to setup localStorage of session for logging and
# logging "flatten" messages because it seems Selenium (with Chrome at least) only grabs
# the first argument to console.XXX when recovering the browser log.
SETUP_LOGGING_JS = """
window.localStorage && window.localStorage.setItem("galaxy:debug", true);
window.localStorage && window.localStorage.setItem("galaxy:debug:flatten", true);
"""


def selenium_only(reason: str = "Test requires Selenium-specific functionality"):
    """Mark test as Selenium-only, skip if running with Playwright backend.

    Args:
        reason: Explanation for why this test requires Selenium

    Usage:
        @selenium_only("Uses Selenium Select class which requires tag_name attribute")
        def test_custom_select_element(self):
            ...
    """

    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            backend = os.environ.get("GALAXY_TEST_DRIVER_BACKEND", "selenium")
            if backend == "playwright":
                raise unittest.SkipTest(f"Selenium-only test: {reason}")
            return f(*args, **kwargs)

        return wrapper

    return decorator


def playwright_only(reason: str = "Test requires Playwright-specific functionality"):
    """Mark test as Playwright-only, skip if running with Selenium backend.

    Args:
        reason: Explanation for why this test requires Playwright

    Usage:
        @playwright_only("Uses Playwright-specific network interception")
        def test_network_request_logging(self):
            ...
    """

    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            backend = os.environ.get("GALAXY_TEST_DRIVER_BACKEND", "selenium")
            if backend == "selenium":
                raise unittest.SkipTest(f"Playwright-only test: {reason}")
            return f(*args, **kwargs)

        return wrapper

    return decorator


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

        # Try to use the Selenium driver to write a final summary of the accessibility
        # information for the test.
        try:
            self.axe_eval(write_to=os.path.join(target_directory, "last.a11y.json"))
        except Exception as e:
            print(e)
            print("Failed to use test driver to print accessibility information")

        # Try to use the Selenium driver to recover more debug information, but don't
        # throw an exception if the connection is broken in some way.
        try:
            self.save_screenshot(os.path.join(target_directory, "last.png"))
            write_file("page_source.txt", self.page_source)
            write_file("DOM.txt", self.execute_script("return document.documentElement.outerHTML"))
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

        try_symlink(target_directory, os.path.join(GALAXY_TEST_ERRORS_DIRECTORY, "latest"))


def try_symlink(file1, file2):
    try:
        try:
            os.symlink(file1, file2)
        except OSError as e:
            if e.errno == errno.EEXIST:
                os.remove(file2)
                os.symlink(file1, file2)
    except Exception:
        pass


def selenium_test(f):
    test_name = f.__name__

    @wraps(f)
    def func_wrapper(self, *args, **kwds):
        retry_attempts = 0
        while True:
            if retry_attempts > 0:
                self.reset_driver_and_session()
            try:
                rval = f(self, *args, **kwds)
                self.assert_baseline_accessibility()
                return rval
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


def exception_is_assertion_or_transition(e: Exception) -> bool:
    """Drive the retry_assertion_during_transitions decorator.

    Reuse logic for checking for transition exceptions but also retry
    if there is an assertion error.
    """
    return exception_seems_to_indicate_transition(e) or isinstance(e, AssertionError)


retry_assertion_during_transitions = partial(
    retry_during_transitions, exception_check=exception_is_assertion_or_transition
)


class TestSnapshot:
    __test__ = False  # Prevent pytest from discovering this class (issue #12071)

    def __init__(self, has_driver: HasDriverProtocol, index: int, description: str):
        self.screenshot_binary = has_driver.get_screenshot_as_png()
        self.description = description
        self.index = index
        self.exc = traceback.format_exc()
        self.stack = traceback.format_stack()

    def write_to_error_directory(self, write_file_func):
        prefix = f"{self.index}-{self.description}"
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

    # where we pull axe from if enabled
    axe_script_url = GALAXY_TEST_AXE_SCRIPT_URL

    # boolean used to skip axe testing, might be useful to speed up
    # tests or may be required if you have no external internet access
    axe_skip = GALAXY_TEST_SKIP_AXE

    def assert_baseline_accessibility(self):
        axe_results = self.axe_eval()
        assert_baseline_accessible(axe_results)

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
        # Once the driver is allocated, any subsequent failure must still
        # tear it down: pytest does not call tearDown when setUp raises, so
        # without this the Playwright asyncio loop would stay registered as
        # "running" on the main thread and cascade every subsequent test's
        # setUp with "Sync API inside the asyncio loop".
        try:
            if self.run_as_admin and GALAXY_TEST_SELENIUM_ADMIN_USER_EMAIL == DEFAULT_ADMIN_USER:
                self._setup_interactor()
                self._setup_user(GALAXY_TEST_SELENIUM_ADMIN_USER_EMAIL)
            self._try_setup_with_driver()
        except Exception:
            try:
                self.tear_down_driver()
            except Exception:
                logger.exception("Error tearing down driver after setup_selenium failure")
            raise

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

    def snapshot(self, description: str):
        """Create a debug snapshot (DOM, screenshot, etc...) that is written out on tool failure.

        This information will be automatically written to a per-test directory created for all
        failed tests.
        """
        self.snapshots.append(TestSnapshot(self, len(self.snapshots), description))

    def get_download_path(self):
        """Returns default download path"""
        return DEFAULT_DOWNLOAD_PATH

    @property
    def anonymous_galaxy_interactor(self):
        api_key = self.get_api_key(force=False)
        interactor = self._get_interactor(api_key=api_key, allow_anonymous=True)
        return interactor

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
            target = os.path.join(GALAXY_TEST_SCREENSHOTS_DIRECTORY, f"{label}-{copy}{extension}")
            copy += 1

        return target

    def reset_driver_and_session(self):
        self.tear_down_driver()
        self.target_url_from_selenium = self._target_url_from_selenium()
        self.setup_driver_and_session()
        self._try_setup_with_driver()

    def setup_driver_and_session(self):
        virtual_display_enabled = use_virtual_display()
        self.display = driver_factory.virtual_display_if_enabled(virtual_display_enabled)
        self.configured_driver = get_configured_driver()
        self._setup_galaxy_logging()

    def _setup_galaxy_logging(self):
        self.home()
        self.execute_script(SETUP_LOGGING_JS)

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
        if self.backend_type == "playwright":
            try:
                self.quit()
            except Exception as e:
                exception = e
        else:
            try:
                self.close()
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
        modal_element = self.components.workflow_editor.state_upgrade_modal.wait_for_visible()
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
        assert expected in peek_text, f"Expected peek [{expected}] not found in peek [{peek_text}]"

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

    def assert_item_extension(self, hid, expected_extension):
        item_body = self.history_panel_item_component(hid=hid)
        extension = item_body.datatype.wait_for_text()
        assert extension == expected_extension, extension

    def assert_item_hid_text(self, hid):
        # Check the text HID matches HID returned from API.  The hid span includes a colon.
        item_body = self.history_panel_item_component(hid=hid)
        hid_text = item_body.hid.wait_for_text()
        assert hid_text == f"{hid}:", hid_text


class RunsToolTests(NavigatesGalaxyMixin):
    """Mixin that drives tool execution through the browser form using tool test definitions."""

    def run_tool_test(self, tool_id: str, test_index: int = 0, galaxy_interactor=None, dataset_populator=None):
        """Top-level entry point: fetch test def, stage data, fill form, execute, verify."""
        assert galaxy_interactor is not None, "galaxy_interactor is required"
        assert dataset_populator is not None, "dataset_populator is required"
        test_defs = galaxy_interactor.get_tool_tests(tool_id)
        assert len(test_defs) > test_index, f"Tool {tool_id} has {len(test_defs)} tests, requested index {test_index}"
        test_def = test_defs[test_index]
        history_id = self.current_history_id()
        self.home()
        hid_map, required_filenames, collection_hid_map = self._stage_test_data(test_def, history_id, galaxy_interactor)
        pre_job_ids = {j["id"] for j in dataset_populator.history_jobs_for_tool(history_id, tool_id)}
        self.tool_open(tool_id)
        self._fill_tool_test_inputs(test_def, hid_map, required_filenames, collection_hid_map)
        self.tool_form_execute()
        self._verify_tool_test_outputs(test_def, history_id, tool_id, pre_job_ids, dataset_populator)

    # -- Data staging --

    def _stage_test_data(
        self, test_def: dict, history_id: str, galaxy_interactor
    ) -> tuple[dict[str, int], set[str], dict[str, int]]:
        """Stage test data files and collections using stage_inputs().

        Returns (hid_map, required_filenames, collection_hid_map) where:
        - hid_map maps filenames to HIDs for scalar data params
        - required_filenames is the set of filenames from required_files
        - collection_hid_map maps param keys to collection HIDs
        """
        required_files = test_def.get("required_files", [])
        inputs = test_def.get("inputs", {})
        required_filenames = {f[0] for f in required_files}

        file_meta: dict[str, dict] = {}
        for entry in required_files:
            fname = entry[0]
            if len(entry) > 1 and isinstance(entry[1], dict):
                file_meta[fname] = entry[1]

        job: dict = {}
        filename_by_key: dict[str, str] = {}
        collection_keys: set[str] = set()

        for key, value in inputs.items():
            raw = value[0] if isinstance(value, list) and len(value) == 1 else value
            if isinstance(raw, dict) and raw.get("model_class") == "TestCollectionDef":
                job[key] = self._convert_collection_def(raw, file_meta)
                collection_keys.add(key)
            elif isinstance(raw, str) and raw in required_filenames:
                file_entry: dict = {"class": "File", "path": raw}
                ftype = file_meta.get(raw, {}).get("ftype")
                if ftype:
                    file_entry["filetype"] = ftype
                job[key] = file_entry
                filename_by_key[key] = raw

        if not job:
            return {}, required_filenames, {}

        staged_job, datasets = stage_inputs(
            galaxy_interactor,
            history_id,
            job,
            use_path_paste=False,
            tool_or_workflow="tool",
        )

        dataset_id_to_hid = {ds["id"]: ds["hid"] for ds in datasets}
        hid_map: dict[str, int] = {}
        for key, ref in staged_job.items():
            if key in collection_keys:
                continue
            filename = filename_by_key.get(key)
            if filename and ref.get("id") in dataset_id_to_hid:
                hid_map[filename] = dataset_id_to_hid[ref["id"]]

        collection_hid_map: dict[str, int] = {}
        if collection_keys:
            contents = self.api_get(f"histories/{history_id}/contents?type=dataset_collection")
            collection_id_to_hid = {item["id"]: item["hid"] for item in contents}
            for key in collection_keys:
                ref = staged_job.get(key, {})
                if ref.get("id") in collection_id_to_hid:
                    collection_hid_map[key] = collection_id_to_hid[ref["id"]]

        for hid in hid_map.values():
            self.history_panel_wait_for_hid_ok(hid)
        for hid in collection_hid_map.values():
            self.history_panel_wait_for_hid_ok(hid)

        return hid_map, required_filenames, collection_hid_map

    @staticmethod
    def _convert_collection_def(coll_def: dict, file_meta: dict | None = None) -> dict:
        """Convert a TestCollectionDef dict to a CWL-like collection job entry."""
        file_meta = file_meta or {}
        elements = []
        for elem in coll_def["elements"]:
            inner = elem["element_definition"]
            if inner.get("model_class") == "TestCollectionDef":
                converted = RunsToolTests._convert_collection_def(inner, file_meta)
                converted["identifier"] = elem["element_identifier"]
                elements.append(converted)
            else:
                file_entry: dict = {
                    "identifier": elem["element_identifier"],
                    "class": "File",
                    "path": inner["value"],
                }
                ftype = file_meta.get(inner["value"], {}).get("ftype")
                if ftype:
                    file_entry["filetype"] = ftype
                elements.append(file_entry)
        result: dict = {
            "class": "Collection",
            "collection_type": coll_def["collection_type"],
            "elements": elements,
        }
        if coll_def.get("name"):
            result["name"] = coll_def["name"]
        return result

    # -- Form filling --

    def _fill_tool_test_inputs(
        self,
        test_def: dict,
        hid_map: dict,
        required_filenames: set,
        collection_hid_map: dict | None = None,
    ):
        """Fill tool form inputs from test definition.

        Two-pass approach for conditionals: set shallow params first so
        conditionals reveal nested params, then retry deferred ones.
        Data/collection params set last.
        """
        inputs = test_def.get("inputs", {})
        if not inputs:
            return
        collection_hid_map = collection_hid_map or {}

        data_params = []
        collection_params = []
        non_data_params = []
        repeat_counts: dict[str, int] = {}

        for key, value in inputs.items():
            raw_value = value[0] if isinstance(value, list) and len(value) == 1 else value

            repeat_match = self._parse_repeat_key(key)
            if repeat_match:
                repeat_name, repeat_index, _child_key = repeat_match
                if repeat_name not in repeat_counts:
                    repeat_counts[repeat_name] = 0
                repeat_counts[repeat_name] = max(repeat_counts[repeat_name], repeat_index + 1)

            if isinstance(raw_value, dict) and raw_value.get("model_class") == "TestCollectionDef":
                collection_params.append((key, raw_value))
            elif isinstance(raw_value, str) and raw_value in required_filenames:
                data_params.append((key, value))
            else:
                non_data_params.append((key, value))

        for repeat_name, count in repeat_counts.items():
            self._add_repeat_instances(repeat_name, count)

        self._expand_collapsed_sections()

        non_data_params.sort(key=lambda kv: kv[0].count("|"))

        deferred = []
        for key, value in non_data_params:
            try:
                self._set_tool_form_value(key, value, required_filenames)
                self.sleep_for(self.wait_types.UX_RENDER)
            except (NoSuchElementException, SeleniumTimeoutException, AssertionError):
                deferred.append((key, value))

        if deferred:
            self.sleep_for(self.wait_types.UX_RENDER)
            for key, value in deferred:
                expanded_id = key.replace("|", "-")
                if self.components.tool_form.parameter_div(parameter=expanded_id).is_absent:
                    continue
                self._set_tool_form_value(key, value, required_filenames)

        for key, value in data_params:
            if isinstance(value, list) and len(value) == 1:
                value = value[0]
            hid = hid_map.get(value)
            assert hid is not None, f"No staged file for data param {key}={value}"
            is_multiple = self._is_multi_data_param(key)
            if is_multiple:
                self._clear_multiselect_tags(key)
            self.tool_set_value(key, f"{hid}: {value}", expected_type="data", multiple=is_multiple)

        for key, coll_def in collection_params:
            hid = collection_hid_map.get(key)
            assert hid is not None, f"No staged collection for param {key}"
            coll_name = coll_def.get("name", "")
            self.tool_set_value(key, f"{hid}: {coll_name}", expected_type="data")

    def _is_multi_data_param(self, expanded_id: str) -> bool:
        return not self.components.tool_form.parameter_form_selection(parameter=expanded_id).is_absent

    def _clear_multiselect_tags(self, expanded_id: str):
        tag_close = self.components.tool_form.parameter_multiselect_tag_close(parameter=expanded_id)
        for _ in range(20):
            close_buttons = tag_close.all()
            if not close_buttons:
                break
            close_buttons[0].click()
            self.sleep_for(self.wait_types.UX_RENDER)

    @staticmethod
    def _parse_repeat_key(key: str):
        import re

        match = re.match(r"^(.+?)_(\d+)\|(.+)$", key)
        if match:
            return match.group(1), int(match.group(2)), match.group(3)
        return None

    def _add_repeat_instances(self, repeat_name: str, count: int):
        for _ in range(count):
            self.components.tool_form.repeat_insert.wait_for_and_click()
            self.sleep_for(self.wait_types.UX_RENDER)

    def _expand_collapsed_sections(self):
        self.components.tool_form.execute.wait_for_visible()
        for header in self.components.tool_form.section_header.all():
            header.click()
            self.sleep_for(self.wait_types.UX_RENDER)

    # -- Type detection and value setting --

    def _detect_param_type(self, expanded_id: str) -> str:
        """Inspect DOM to determine param type.

        Detection order matters:
        - drilldown before checkbox_select (drilldown also has checkboxes)
        - checkbox_select before boolean (both have input[type='checkbox'])
        """
        tf = self.components.tool_form

        param_div = tf.parameter_div(parameter=expanded_id).wait_for_visible()
        if param_div.find_elements(By.CSS_SELECTOR, tf.drilldown_option.selector):
            return "drilldown"

        checkboxes = tf.parameter_checkbox_input(parameter=expanded_id).all()
        if len(checkboxes) > 1:
            return "checkbox_select"
        if checkboxes:
            return "boolean"

        if not tf.parameter_color_input(parameter=expanded_id).is_absent:
            return "color"
        if not tf.parameter_select(parameter=expanded_id).is_absent:
            return "select"

        return "text"

    def _set_tool_form_value(self, key: str, value, required_filenames: set):
        if isinstance(value, list) and len(value) == 1:
            value = value[0]
        if isinstance(value, str) and value in required_filenames:
            return

        param_type = self._detect_param_type(key)

        if param_type == "drilldown":
            values = value if isinstance(value, list) else [value]
            self._set_drilldown_value(key, values)
        elif param_type == "checkbox_select":
            values = value if isinstance(value, list) else [value]
            self._set_checkbox_select_value(key, values)
        elif param_type == "boolean":
            self._set_boolean_value(key, value)
        elif param_type == "color":
            self._set_color_value(key, value)
        elif param_type == "select":
            self.tool_set_value(key, str(value), expected_type="select")
        else:
            self._set_text_value(key, str(value))

    def _set_boolean_value(self, expanded_id: str, value):
        checkbox = self.components.tool_form.parameter_checkbox_input(parameter=expanded_id).wait_for_present()
        is_checked = checkbox.is_selected()
        want_checked = str(value).lower() in ("true", "1", "yes")
        if is_checked != want_checked:
            self.execute_script("arguments[0].click();", checkbox)

    def _set_checkbox_select_value(self, expanded_id: str, values: list):
        all_checkboxes = self.components.tool_form.parameter_checkbox_input(parameter=expanded_id).all()
        for val in values:
            matched = [cb for cb in all_checkboxes if cb.get_attribute("value") == val]
            assert matched, f"No checkbox with value '{val}' in param {expanded_id}"
            if not matched[0].is_selected():
                self.execute_script("arguments[0].click();", matched[0])

    def _set_drilldown_value(self, expanded_id: str, values: list):
        """Set drill-down param by clicking option checkboxes.

        TODO: DOM id is ``drilldown-option-{option.name}`` but test API returns
        option *values*. Works only when name == value. If a tool has
        ``<option name="Label" value="key">``, the lookup will fail.
        Fixing requires changing FormDrilldownOption.vue (breaks library export)
        or adding a value->name mapping step here.
        """
        for val in values:
            checkbox = self.components.tool_form.parameter_drilldown_option(
                parameter=expanded_id, value=val
            ).wait_for_present()
            if not checkbox.is_selected():
                self.execute_script("arguments[0].click();", checkbox)

    def _set_color_value(self, expanded_id: str, value: str):
        color_input = self.components.tool_form.parameter_color_input(parameter=expanded_id).wait_for_present()
        self._set_input_value_via_js(color_input, value)

    def _set_text_value(self, expanded_id: str, value: str):
        input_element = self.components.tool_form.parameter_text_input(parameter=expanded_id).wait_for_present()
        self._set_input_value_via_js(input_element, value)

    def _set_input_value_via_js(self, element, value):
        self.execute_script(
            "arguments[0].value = arguments[1];"
            "arguments[0].dispatchEvent(new Event('input', {bubbles: true}));"
            "arguments[0].dispatchEvent(new Event('change', {bubbles: true}));",
            element,
            value,
        )

    # -- Output verification --

    def _verify_tool_test_outputs(
        self, test_def: dict, history_id: str, tool_id: str, pre_job_ids: set, dataset_populator
    ):
        expect_failure = test_def.get("expect_failure", False)
        outputs = test_def.get("outputs", [])
        output_collections = test_def.get("output_collections", [])
        expect_num_outputs = test_def.get("expect_num_outputs")
        expect_exit_code = test_def.get("expect_exit_code")
        stdout_assertions = test_def.get("stdout")
        stderr_assertions = test_def.get("stderr")
        command_assertions = test_def.get("command")
        command_version_assertions = test_def.get("command_version")
        has_work = (
            outputs
            or output_collections
            or expect_failure
            or expect_num_outputs is not None
            or expect_exit_code is not None
            or stdout_assertions
            or stderr_assertions
            or command_assertions
            or command_version_assertions
        )
        if not has_work:
            return

        def _find_new_job(driver=None):
            jobs = dataset_populator.history_jobs_for_tool(history_id, tool_id)
            new_jobs = [j for j in jobs if j["id"] not in pre_job_ids]
            if new_jobs:
                return new_jobs[0]
            return None

        new_job = self._wait_on(_find_new_job, "tool job to appear in history")
        assert new_job is not None
        job_id = new_job["id"]

        has_job_checks = (
            expect_exit_code is not None
            or stdout_assertions
            or stderr_assertions
            or command_assertions
            or command_version_assertions
        )

        if expect_failure:
            dataset_populator.wait_for_job(job_id, assert_ok=False)
            job_details = dataset_populator.get_job_details(job_id, full=has_job_checks).json()
            assert job_details["state"] == "error", f"Expected job to fail but state is '{job_details['state']}'"
            if has_job_checks:
                verify_job_metadata(
                    job_details,
                    expect_exit_code,
                    stdout_assertions,
                    stderr_assertions,
                    command_assertions,
                    command_version_assertions,
                )
            return

        dataset_populator.wait_for_job(job_id, assert_ok=True)
        if has_job_checks:
            job_details = dataset_populator.get_job_details(job_id, full=True).json()
            verify_job_metadata(
                job_details,
                expect_exit_code,
                stdout_assertions,
                stderr_assertions,
                command_assertions,
                command_version_assertions,
            )

        all_job_outputs = dataset_populator.job_outputs(job_id)

        if expect_num_outputs is not None:
            actual_count = len([o for o in all_job_outputs if "dataset" in o])
            assert actual_count == int(expect_num_outputs), f"Expected {expect_num_outputs} outputs, got {actual_count}"

        if outputs:
            output_id_by_name = {o["name"]: o["dataset"]["id"] for o in all_job_outputs if "dataset" in o}
            for output_def in outputs:
                output_name = output_def.get("name")
                assert (
                    output_name in output_id_by_name
                ), f"Output '{output_name}' not found in job outputs: {list(output_id_by_name.keys())}"
                dataset_id = output_id_by_name[output_name]
                output_content = dataset_populator.get_history_dataset_content(
                    history_id,
                    dataset_id=dataset_id,
                    type="bytes",
                    wait=False,
                )
                verify(output_name, output_content, output_def.get("attributes", {}))
                primary_datasets = output_def.get("attributes", {}).get("primary_datasets", {})
                for designation, (_primary_outfile, primary_attribs) in primary_datasets.items():
                    primary_key = f"__new_primary_file_{output_name}|{designation}__"
                    assert primary_key in output_id_by_name, (
                        f"Discovered dataset '{designation}' not found for output '{output_name}': "
                        f"{list(output_id_by_name.keys())}"
                    )
                    primary_content = dataset_populator.get_history_dataset_content(
                        history_id,
                        dataset_id=output_id_by_name[primary_key],
                        type="bytes",
                        wait=False,
                    )
                    verify(designation, primary_content, primary_attribs)

        if output_collections:
            collection_id_by_name = {
                o["name"]: o["dataset_collection_instance"]["id"]
                for o in all_job_outputs
                if "dataset_collection_instance" in o
            }
            for oc_def in output_collections:
                oc_name = oc_def["name"]
                assert (
                    oc_name in collection_id_by_name
                ), f"Output collection '{oc_name}' not found in job outputs: {list(collection_id_by_name.keys())}"
                self._verify_output_collection(oc_def, collection_id_by_name[oc_name], history_id, dataset_populator)

    def _verify_output_collection(self, oc_def: dict, collection_id: str, history_id: str, dataset_populator):

        data_collection = dataset_populator.get_history_collection_details(
            history_id,
            content_id=collection_id,
            wait=False,
        )

        expected_type = oc_def.get("attributes", {}).get("type")
        if expected_type:
            actual_type = data_collection["collection_type"]
            assert (
                actual_type == expected_type
            ), f"Collection '{oc_def['name']}': expected type '{expected_type}', got '{actual_type}'"

        expected_count = oc_def.get("attributes", {}).get("count")
        if expected_count is not None:
            actual_count = len(data_collection["elements"])
            assert actual_count == int(
                expected_count
            ), f"Collection '{oc_def['name']}': expected {expected_count} elements, got {actual_count}"

        element_tests = oc_def.get("element_tests", {})
        elements_by_id = {e["element_identifier"]: e for e in data_collection["elements"]}
        for element_id, element_test in element_tests.items():
            assert element_id in elements_by_id, f"Element '{element_id}' not found in collection '{oc_def['name']}'"
            element = elements_by_id[element_id]
            if isinstance(element_test, list):
                _element_outfile, element_attrib = element_test
            else:
                element_attrib = element_test

            if element.get("element_type") == "dataset_collection":
                sub_elements = element["object"]["elements"]
                sub_tests = element_attrib.get("elements", {})
                sub_elements_by_id = {e["element_identifier"]: e for e in sub_elements}
                for sub_id, sub_test in sub_tests.items():
                    assert (
                        sub_id in sub_elements_by_id
                    ), f"Element '{sub_id}' not found in sub-collection '{element_id}'"
                    sub_elem = sub_elements_by_id[sub_id]
                    if isinstance(sub_test, list):
                        _sub_outfile, sub_attrib = sub_test
                    else:
                        sub_attrib = sub_test
                    if sub_elem.get("element_type") == "dataset_collection":
                        sub_oc_def = {
                            "name": f"{oc_def['name']}/{element_id}/{sub_id}",
                            "attributes": {},
                            "element_tests": sub_attrib.get("elements", {}),
                        }
                        self._verify_output_collection(
                            sub_oc_def, sub_elem["object"]["id"], history_id, dataset_populator
                        )
                    else:
                        content = dataset_populator.get_history_dataset_content(
                            history_id,
                            dataset_id=sub_elem["object"]["id"],
                            type="bytes",
                            wait=False,
                        )
                        verify(sub_id, content, sub_attrib if isinstance(sub_attrib, dict) else {})
            else:
                hda_id = element["object"]["id"]
                content = dataset_populator.get_history_dataset_content(
                    history_id,
                    dataset_id=hda_id,
                    type="bytes",
                    wait=False,
                )
                verify(element_id, content, element_attrib if isinstance(element_attrib, dict) else {})


EXAMPLE_WORKFLOW_URL_1 = (
    "https://raw.githubusercontent.com/galaxyproject/galaxy/release_19.09/test/base/data/test_workflow_1.ga"
)


class UsesWorkflowAssertions(NavigatesGalaxyMixin):
    @retry_assertion_during_transitions
    def _assert_showing_n_workflows(self, n):
        if (actual_count := len(self.workflow_card_elements())) != n:
            message = f"Expected {n} workflows to be displayed, based on DOM found {actual_count} workflow rows."
            raise AssertionError(message)

    @skip_if_github_down
    def _workflow_import_from_url(self, url=EXAMPLE_WORKFLOW_URL_1):
        self.workflow_index_click_import()
        self.workflow_import_submit_url(url)

    @retry_assertion_during_transitions
    def assert_wf_annotation_is(self, expected_annotation):
        edit_annotation = self.components.workflow_editor.edit_annotation
        edit_annotation_element = edit_annotation.wait_for_visible()
        actual_annotation = edit_annotation_element.get_attribute("value")
        assert (
            expected_annotation in actual_annotation
        ), f"'{expected_annotation}' unequal annotation '{actual_annotation}'"


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

    def workflow_run_setup_inputs(self, content: Optional[str]) -> tuple[str, dict[str, Any]]:
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
            for input_value in inputs.values():
                if (
                    isinstance(input_value, dict)
                    and (src := input_value.get("src"))
                    and (content_id := input_value.get("id"))
                ):
                    if src == "hda":
                        content_item = self.dataset_populator.get_history_dataset_details(
                            history_id, content_id=content_id
                        )
                        input_value["hid"] = content_item["hid"]
                    elif src == "hdca":
                        content_item = self.dataset_populator.get_history_collection_details(
                            history_id=history_id, content_id=content_id
                        )
                        input_value["hid"] = content_item["hid"]
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
    backend_type = GALAXY_TEST_DRIVER_BACKEND
    assert backend_type in ["selenium", "playwright"], f"Unknown GALAXY_TEST_DRIVER_BACKEND [{backend_type}]"
    return driver_factory.ConfiguredDriver(
        galaxy_timeout_handler(TIMEOUT_MULTIPLIER),
        browser=GALAXY_TEST_SELENIUM_BROWSER,
        remote=asbool(GALAXY_TEST_SELENIUM_REMOTE),
        remote_host=GALAXY_TEST_SELENIUM_REMOTE_HOST,
        remote_port=GALAXY_TEST_SELENIUM_REMOTE_PORT,
        headless=headless_selenium(),
        backend_type=cast(BackendType, backend_type),
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
    using_selenium = GALAXY_TEST_DRIVER_BACKEND == "selenium"
    if asbool(GALAXY_TEST_SELENIUM_REMOTE):
        return False

    if GALAXY_TEST_SELENIUM_HEADLESS == "auto":
        if (
            using_selenium
            and driver_factory.is_virtual_display_available()
            and not driver_factory.get_local_browser(GALAXY_TEST_SELENIUM_BROWSER) == "CHROME"
        ):
            return True
        else:
            return False
    else:
        return using_selenium and asbool(GALAXY_TEST_SELENIUM_HEADLESS)


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

    def _post(
        self, route, data=None, files=None, headers=None, admin=False, json: bool = False, anon: bool = False
    ) -> Response:
        full_url = self.selenium_context.build_url(f"api/{route}", for_selenium=False)
        cookies = None
        if admin:
            full_url = f"{full_url}?key={self._mixin_admin_api_key}"
        elif not anon:
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


class SeleniumSessionWorkflowPopulator(SeleniumSessionGetPostMixin, populators.BaseWorkflowPopulator):
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


__all__ = ("retry_during_transitions",)
