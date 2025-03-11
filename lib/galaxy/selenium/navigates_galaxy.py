"""A mixin that extends a HasDriver class with Galaxy-specific utilities.

Implementer must provide a self.build_url method to target Galaxy.
"""

import collections
import contextlib
import random
import string
import time
from abc import abstractmethod
from dataclasses import (
    dataclass,
    field,
)
from functools import (
    partial,
    wraps,
)
from typing import (
    Any,
    cast,
    Dict,
    List,
    Literal,
    NamedTuple,
    Optional,
    Tuple,
    Union,
)

import yaml
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as ec

from galaxy.navigation.components import (
    Component,
    HasText,
)
from galaxy.navigation.data import load_root_component
from galaxy.util import (
    DEFAULT_SOCKET_TIMEOUT,
    requests,
)
from . import sizzle
from .has_driver import (
    exception_indicates_click_intercepted,
    exception_indicates_not_clickable,
    exception_indicates_stale_element,
    HasDriver,
    SeleniumTimeoutException,
)
from .smart_components import SmartComponent

# Test case data
DEFAULT_PASSWORD = "123456"

RETRY_DURING_TRANSITIONS_SLEEP_DEFAULT = 0.1
RETRY_DURING_TRANSITIONS_ATTEMPTS_DEFAULT = 10

GALAXY_MAIN_FRAME_ID = "galaxy_main"
GALAXY_VISUALIZATION_FRAME_ID = "galaxy_visualization"

WaitType = collections.namedtuple("WaitType", ["name", "default_length"])


class HistoryEntry(NamedTuple):
    id: str
    hid: str
    history_content_type: str


# Default wait times should make sense for a development server under low
# load. Wait times for production servers can be scaled up with a multiplier.
class WAIT_TYPES:
    # Rendering a form and registering callbacks, etc...
    UX_RENDER = WaitType("ux_render", 1)
    # Fade in, fade out, etc...
    UX_TRANSITION = WaitType("ux_transition", 5)
    # Toastr popup and dismissal, etc...
    UX_POPUP = WaitType("ux_popup", 15)
    # Creating a new history and loading it into the panel.
    DATABASE_OPERATION = WaitType("database_operation", 10)
    # Wait time for jobs to complete in default environment.
    JOB_COMPLETION = WaitType("job_completion", 30)
    # Wait time for a GIE to spawn.
    GIE_SPAWN = WaitType("gie_spawn", 30)
    # Wait time for toolshed search
    SHED_SEARCH = WaitType("shed_search", 30)
    # Wait time for repository installation
    REPO_INSTALL = WaitType("repo_install", 60)
    # History Polling Duration
    HISTORY_POLL = WaitType("history_poll", 3)


# Choose a moderate wait type for operations that don't specify a type.
DEFAULT_WAIT_TYPE = WAIT_TYPES.DATABASE_OPERATION


class NullTourCallback:
    def handle_step(self, step, step_index: int):
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
    return (
        exception_indicates_stale_element(e)
        or exception_indicates_not_clickable(e)
        or exception_indicates_click_intercepted(e)
    )


def retry_call_during_transitions(
    f,
    attempts=RETRY_DURING_TRANSITIONS_ATTEMPTS_DEFAULT,
    sleep=RETRY_DURING_TRANSITIONS_SLEEP_DEFAULT,
    exception_check=exception_seems_to_indicate_transition,
):
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


def retry_during_transitions(
    f,
    attempts=RETRY_DURING_TRANSITIONS_ATTEMPTS_DEFAULT,
    sleep=RETRY_DURING_TRANSITIONS_SLEEP_DEFAULT,
    exception_check=exception_seems_to_indicate_transition,
):
    @wraps(f)
    def _retry(*args, **kwds):
        return retry_call_during_transitions(
            partial(f, *args, **kwds), attempts=attempts, sleep=sleep, exception_check=exception_check
        )

    return _retry


def retry_index_during_transitions():

    def exception_check(e):
        return exception_seems_to_indicate_transition(e) or isinstance(e, IndexError)

    return partial(retry_during_transitions, exception_check=exception_check)


def edit_details(f, scope=".history-index"):
    """Open the editor, run the edits, hit the save button"""

    @wraps(f)
    def func_wrapper(self, *args, **kwds):
        # open editor
        self.open_history_editor(scope=scope)
        # run edits
        result = f(self, *args, **kwds)
        # save edits
        self.history_click_editor_save()
        return result

    return func_wrapper


@dataclass
class ConfigTemplateParameter:
    form_element_type: Literal["string", "boolean", "integer"]
    name: str
    value: Any


@dataclass
class FileSourceInstance:
    template_id: str
    name: str
    description: Optional[str]
    parameters: List[ConfigTemplateParameter] = field(default_factory=list)


@dataclass
class ObjectStoreInstance:
    template_id: str
    name: str
    description: Optional[str]
    parameters: List[ConfigTemplateParameter] = field(default_factory=list)


class NavigatesGalaxy(HasDriver):
    """Class with helpers methods for driving components of the Galaxy interface.

    In most cases, methods for interacting with Galaxy components that appear in
    multiple tests or applications should be refactored into this class for now.
    Keep in mind that this class is used outside the context of ``TestCase`` s as
    well - so some methods more explicitly related to test data or assertion checking
    may make more sense in SeleniumTestCase for instance.

    Some day this class will likely be split up into smaller mixins for particular
    components of Galaxy, but until that day the best practice is to prefix methods
    for driving or querying the interface with the name of the component or page
    the method operates on. These serve as pseudo-namespaces until we decompose this
    class. For instance, the method for clicking an option in the workflow editor is
    workflow_editor_click_option instead of click_workflow_editor_option.
    """

    timeout_multiplier: float
    driver: WebDriver

    @abstractmethod
    def build_url(self, url: str, for_selenium: bool = True) -> str:
        """Build URL to the target Galaxy."""

    @abstractmethod
    def screenshot(self, label: str) -> None:
        """Take a screenshot of the current browser with the specified label."""

    def screenshot_if(self, label: Optional[str]) -> Optional[str]:
        target = None
        if label:
            target = self.screenshot(label)
        return target

    default_password = DEFAULT_PASSWORD
    wait_types = WAIT_TYPES
    # set to True to reload each invocation (good for interactive test building)
    _interactive_components: bool = False
    _root_component: Component = load_root_component()

    def get(self, url: str = ""):
        """Expand supplied relative URL and navigate to page using Selenium driver."""
        full_url = self.build_url(url)
        return self.driver.get(full_url)

    @property
    def navigation(self) -> Component:
        if self._interactive_components:
            return load_root_component()
        else:
            return self._root_component

    @property
    def components(self) -> SmartComponent:
        """Fetch root component describing the Galaxy DOM."""
        return SmartComponent(self.navigation, self)

    def wait_length(self, wait_type: WaitType) -> float:
        """Return the wait time specified by wait_type after applying `timeout_multipler`.

        `timeout_multiplier` is used in production CI tests to reduce transient failures
        in a uniform way across test suites to expand waiting.
        """
        return wait_type.default_length * self.timeout_multiplier

    def sleep_for(self, wait_type: WaitType) -> None:
        """Sleep on the Python client side for the specified wait_type.

        This method uses `wait_length` to apply any `timeout_multiplier`.
        """
        self.sleep_for_seconds(self.wait_length(wait_type))

    def sleep_for_seconds(self, duration: float) -> None:
        """Sleep in the local thread for specified number of seconds.

        Ideally, we would be sleeping on the Selenium server instead of in the local client
        (e.g. test) thread.
        """
        time.sleep(duration)

    def timeout_for(self, wait_type: WaitType = DEFAULT_WAIT_TYPE, **kwd) -> float:
        return self.wait_length(wait_type)

    def home(self) -> None:
        """Return to root Galaxy page and wait for some basic widgets to appear."""
        self.get()
        try:
            self.components.masthead._.wait_for_visible()
        except SeleniumTimeoutException as e:
            raise ClientBuildException(e)

    def go_to_workflow_landing(self, uuid: str, public: Literal["false", "true"], client_secret: Optional[str]):
        path = f"workflow_landings/{uuid}?public={public}"
        if client_secret:
            path = f"{path}&client_secret={client_secret}"
        self.driver.get(self.build_url(path))
        self.components.workflow_run.run_workflow.wait_for_visible()

    def go_to_trs_search(self) -> None:
        self.driver.get(self.build_url("workflows/trs_search"))
        self.components.masthead._.wait_for_visible()

    def go_to_trs_by_id(self) -> None:
        self.driver.get(self.build_url("workflows/trs_import"))
        self.components.masthead._.wait_for_visible()

    def go_to_workflow_sharing(self, workflow_id: str) -> None:
        self.driver.get(self.build_url(f"workflows/sharing?id={workflow_id}"))

    def go_to_workflow_export(self, workflow_id: str) -> None:
        self.driver.get(self.build_url(f"workflows/export?id={workflow_id}"))

    def go_to_history_sharing(self, history_id: str) -> None:
        self.driver.get(self.build_url(f"histories/sharing?id={history_id}"))

    def switch_to_main_panel(self):
        self.driver.switch_to.frame(GALAXY_MAIN_FRAME_ID)

    @contextlib.contextmanager
    def local_storage(self, key: str, value: Union[float, str]):
        """Method decorator to modify localStorage for the scope of the supplied context."""
        self.driver.execute_script(f"""window.localStorage.setItem("{key}", {value});""")
        try:
            yield
        finally:
            self.driver.execute_script(f"""window.localStorage.removeItem("{key}");""")

    @contextlib.contextmanager
    def main_panel(self):
        """Decorator to operate within the context of Galaxy's main frame."""
        try:
            self.switch_to_main_panel()
            yield
        finally:
            self.driver.switch_to.default_content()

    @contextlib.contextmanager
    def visualization_panel(self):
        """Decorator to operate within the context of Galaxy's visualization frame."""
        try:
            self.driver.switch_to.frame(GALAXY_VISUALIZATION_FRAME_ID)
            yield
        finally:
            self.driver.switch_to.default_content()

    def api_get(self, endpoint, data=None, raw=False):
        data = data or {}
        full_url = self.build_url(f"api/{endpoint}", for_selenium=False)
        response = requests.get(
            full_url, data=data, cookies=self.selenium_to_requests_cookies(), timeout=DEFAULT_SOCKET_TIMEOUT
        )
        return self._handle_response(response, raw)

    def api_post(self, endpoint, data=None):
        data = data or {}
        full_url = self.build_url(f"api/{endpoint}", for_selenium=False)
        response = requests.post(
            full_url, data=data, cookies=self.selenium_to_requests_cookies(), timeout=DEFAULT_SOCKET_TIMEOUT
        )
        return response.json()

    def api_delete(self, endpoint, raw=False):
        full_url = self.build_url(f"api/{endpoint}", for_selenium=False)
        response = requests.delete(
            full_url, cookies=self.selenium_to_requests_cookies(), timeout=DEFAULT_SOCKET_TIMEOUT
        )
        return self._handle_response(response, raw)

    def _handle_response(self, response: requests.Response, raw: bool = False):
        if raw:
            return response
        else:
            return response.json() if response.content else None

    def get_galaxy_session(self):
        for cookie in self.driver.get_cookies():
            if cookie["name"] == "galaxysession":
                return cookie["value"]

    def selenium_to_requests_cookies(self):
        return {"galaxysession": self.get_galaxy_session()}

    def history_panel_name_element(self):
        component = self.history_element("name display")
        return component.wait_for_present()

    @retry_during_transitions
    def history_panel_name(self):
        return self.history_panel_name_element().text

    def history_panel_collection_rename(self, hid: int, new_name: str, assert_old_name: Optional[str] = None):
        toggle = self.history_element("editor toggle")
        toggle.wait_for_and_click()
        self.history_panel_rename(new_name)

    def history_panel_expand_collection(self, collection_hid: int) -> SmartComponent:
        self.history_panel_click_item_title(collection_hid)
        collection_view = self.components.history_panel.collection_view
        collection_view._.wait_for_present()
        return collection_view

    def history_panel_collection_name_element(self):
        title_element = self.history_element("collection name display").wait_for_present()
        return title_element

    def make_accessible_and_publishable(self):
        self.components.histories.sharing.make_accessible.wait_for_and_click()
        self.components.histories.sharing.make_publishable.wait_for_and_click()

    def history_contents(self, history_id=None, view="summary", datasets_only=True):
        if history_id is None:
            history_id = self.current_history_id()
        histories = self.api_get("histories?keys=id")
        if history_id not in [h["id"] for h in histories]:
            return {}
        if datasets_only:
            endpoint = f"histories/{history_id}/contents?view={view}"
        else:
            endpoint = f"histories/{history_id}?view={view}"
        return self.api_get(endpoint)

    def current_history(self) -> Dict[str, Any]:
        full_url = self.build_url("history/current_history_json", for_selenium=False)
        response = requests.get(full_url, cookies=self.selenium_to_requests_cookies(), timeout=DEFAULT_SOCKET_TIMEOUT)
        return response.json()

    def current_history_id(self) -> str:
        return self.current_history()["id"]

    def current_history_publish(self):
        self.click_history_option_sharing()
        self.make_accessible_and_publishable()

    def latest_history_entry(self):
        entry_dict = self._latest_history_item()
        if entry_dict is None:
            return None
        else:
            return HistoryEntry(
                id=entry_dict["id"],
                hid=entry_dict["hid"],
                history_content_type=entry_dict["history_content_type"],
            )

    def latest_history_item(self) -> Dict[str, Any]:
        return_value = self._latest_history_item()
        assert return_value, "Attempted to get latest history item on empty history."
        return return_value

    def _latest_history_item(self) -> Optional[Dict[str, Any]]:
        history_contents = self.history_contents()
        if len(history_contents) > 0:
            entry_dict = history_contents[-1]
            return entry_dict
        else:
            return None

    def wait_for_history(self, assert_ok=True):
        def history_becomes_terminal(driver):
            current_history_id = self.current_history_id()
            state = self.api_get(f"histories/{current_history_id}")["state"]
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
        self.history_click_create_new()
        self.sleep_for(WAIT_TYPES.UX_RENDER)

    def history_panel_wait_for_hid_ok(self, hid, allowed_force_refreshes=0):
        return self.history_panel_wait_for_hid_state(hid, "ok", allowed_force_refreshes=allowed_force_refreshes)

    def history_panel_wait_for_hid_deferred(self, hid, allowed_force_refreshes=0):
        return self.history_panel_wait_for_hid_state(hid, "deferred", allowed_force_refreshes=allowed_force_refreshes)

    def wait_for_hid_ok_and_open_details(self, hid):
        self.history_panel_wait_for_hid_ok(hid, allowed_force_refreshes=1)
        self.history_panel_click_item_title(hid=hid)
        self.history_panel_item_view_dataset_details(hid)

    def history_panel_item_component(self, history_item=None, hid=None, multi_history_panel=False):
        assert hid
        return self.content_item_by_attributes(hid=hid, multi_history_panel=multi_history_panel)

    def wait_for_history_to_have_hid(self, history_id, hid):
        def get_hids():
            contents = self.api_get(f"histories/{history_id}/contents")
            return [d["hid"] for d in contents]

        def history_has_hid(driver):
            hids = get_hids()
            return any(h == hid for h in hids)

        timeout = self.timeout_for(wait_type=WAIT_TYPES.JOB_COMPLETION)
        try:
            self.wait(timeout).until(history_has_hid)
        except SeleniumTimeoutException as e:
            hids = get_hids()
            message = f"Timeout waiting for history {history_id} to have hid {hid} - have hids {hids}"
            raise self.prepend_timeout_message(e, message)

    def history_panel_wait_for_hid_visible(self, hid, allowed_force_refreshes=0, multi_history_panel=False):
        current_history_id = self.current_history_id()
        self.wait_for_history_to_have_hid(current_history_id, hid)
        # TODO: just use HID and stop resolving history_item -or- place history item in DOM.
        # I think Mason thought the first was cleaner based on recent changes, but I think duplicated
        # HIDs due to conversions and such make using the actual history item ID more robust.
        history_item = self.hid_to_history_item(hid, current_history_id=current_history_id)
        history_item_selector = self.history_panel_item_component(
            history_item, hid=hid, multi_history_panel=multi_history_panel
        )
        try:
            self.history_item_wait_for(history_item_selector, allowed_force_refreshes)
        except SeleniumTimeoutException as e:
            selector = self.navigation.history_panel.selectors.contents
            contents_elements = self.find_elements(selector)
            div_ids = [f"#{d.get_attribute('id')}" for d in contents_elements]
            template = "Failed waiting on history item %d to become visible, visible datasets include [%s]."
            message = template % (hid, ",".join(div_ids))
            raise self.prepend_timeout_message(e, message)
        return history_item_selector

    def hid_to_history_item(self, hid, current_history_id=None):
        if current_history_id is None:
            current_history_id = self.current_history_id()
        contents = self.api_get(f"histories/{current_history_id}/contents")
        history_item = [d for d in contents if d["hid"] == hid][0]
        return history_item

    def history_item_wait_for(self, history_item_selector, allowed_force_refreshes):
        attempt = 0
        while True:
            try:
                rval = self.wait_for_visible(history_item_selector, wait_type=WAIT_TYPES.JOB_COMPLETION)
                break
            except SeleniumTimeoutException:
                if attempt >= allowed_force_refreshes:
                    raise

            attempt += 1
            self.history_panel_refresh_click()
        return rval

    def history_panel_wait_for_history_loaded(self):
        # Verify that the history has been loaded and is empty.
        self.wait_for_visible(
            self.navigation.history_panel.selectors.empty_message, wait_type=WAIT_TYPES.DATABASE_OPERATION
        )

    def history_panel_wait_for_hid_hidden(self, hid, multi_history_panel=False):
        history_item_selector = self.history_panel_item_component(hid=hid, multi_history_panel=multi_history_panel)
        self.wait_for_absent_or_hidden(history_item_selector, wait_type=WAIT_TYPES.JOB_COMPLETION)
        return history_item_selector

    def history_panel_wait_for_hid_state(self, hid, state, allowed_force_refreshes=0, multi_history_panel=False):
        history_item_selector = self.history_panel_wait_for_hid_visible(
            hid, allowed_force_refreshes=allowed_force_refreshes, multi_history_panel=multi_history_panel
        )
        history_item_selector_state = self.content_item_by_attributes(
            hid=hid, state=state, multi_history_panel=multi_history_panel
        )
        try:
            self.history_item_wait_for(history_item_selector_state, allowed_force_refreshes)
        except SeleniumTimeoutException as e:
            history_item = self.wait_for_visible(history_item_selector)
            current_state = "UNKNOWN"
            raw_class_str = history_item.get_attribute("class") or ""
            classes = raw_class_str.split(" ")
            for clazz in classes:
                if clazz.startswith("state-"):
                    current_state = clazz[len("state-") :]
            template = "Failed waiting on history item %d state to change to [%s] current state [%s]. "
            message = template % (hid, state, current_state)
            raise self.prepend_timeout_message(e, message)
        return history_item_selector_state

    @retry_during_transitions
    def get_grid_entry_names(self, selector):
        self.sleep_for(self.wait_types.UX_RENDER)
        names = []
        grid = self.wait_for_selector(selector)
        for row in grid.find_elements(By.TAG_NAME, "tr"):
            td = row.find_elements(By.TAG_NAME, "td")
            name = td[1].text if td[0].text == "" else td[0].text
            names.append(name)
        return names

    def select_grid_operation(self, item_name, option_label):
        target_item = None
        grid = self.components.grids.body.wait_for_visible()
        for row in grid.find_elements(By.TAG_NAME, "tr"):
            for name_column in range(2):
                name_cell = row.find_elements(By.TAG_NAME, "td")[name_column]
                if item_name in name_cell.text:
                    target_item = name_cell
                    break
            if target_item is not None:
                break

        if target_item is None:
            raise AssertionError(f"Failed to find item with name [{item_name}]")

        popup_menu_button = target_item.find_element(By.CSS_SELECTOR, "button")
        popup_menu_button.click()
        popup_option = target_item.find_element(
            By.CSS_SELECTOR, f"[data-description='grid operation {option_label.lower()}'"
        )
        popup_option.click()

    def select_grid_cell(self, grid_name, item_name, column_index=3):
        cell = None
        grid = self.wait_for_selector(f"{grid_name} table")
        for row in grid.find_elements(By.TAG_NAME, "tr"):
            td = row.find_elements(By.TAG_NAME, "td")
            print(td[0].text)
            print(td[1].text)
            if item_name in [td[0].text, td[1].text]:
                cell = td[column_index]
                break

        if cell is None:
            raise AssertionError(f"Failed to find cell for item with name [{item_name}]")

        return cell

    def check_grid_rows(self, grid_name, item_names):
        grid = self.wait_for_selector(grid_name)
        for row in grid.find_elements(By.TAG_NAME, "tr"):
            td = row.find_elements(By.TAG_NAME, "td")
            item_name = td[1].text
            if item_name in item_names:
                checkbox = td[0].find_element(self.by.TAG_NAME, "input")
                # bootstrap vue checkbox seems to be hidden by label, but the label is not interactable
                self.driver.execute_script("$(arguments[0]).click();", checkbox)

    def check_advanced_search_filter(self, filter_name):
        filter_div = self.wait_for_selector(f"[data-description='filter {filter_name}']")
        checkbox = filter_div.find_element(self.by.CSS_SELECTOR, "input")
        # bootstrap vue checkbox seems to be hidden by label, but the label is not interactable
        self.driver.execute_script("$(arguments[0]).click();", checkbox)

    def published_grid_search_for(self, search_term=None):
        return self._inline_search_for(
            self.navigation.grids.free_text_search,
            search_term,
        )

    def get_logged_in_user(self) -> Optional[Dict[str, Any]]:
        # for user's not logged in - this just returns a {} so lets
        # key this on an id being available?
        if "id" in (user_dict := self.api_get("users/current")):
            return user_dict
        else:
            return None

    def get_api_key(self, force=False) -> Optional[str]:
        user_id = self.get_user_id()
        if user_id is None:
            if force:
                raise Exception("Attempting to get_api_key but no user logged in.")
            else:
                return None
        elif not force:
            response = self.api_get(f"users/{user_id}/api_key/detailed")
            return response["key"] if response else None
        else:
            return self.api_post(f"users/{user_id}/api_key")

    def get_user_id(self) -> Optional[str]:
        if (user := self.get_logged_in_user()) is not None:
            return user["id"]
        else:
            return None

    def get_user_email(self) -> str:
        user = self.get_logged_in_user()
        if user is None:
            raise Exception("No user is logged in, cannot fetch user e-mail.")
        else:
            return user["email"]

    def is_logged_in(self) -> bool:
        user_object = self.get_logged_in_user()
        if not user_object:
            return False
        else:
            return "email" in user_object

    @retry_during_transitions
    def _inline_search_for(self, selector, search_term=None, escape_to_clear=False):
        # Clear tooltip resulting from clicking on the masthead to get here.
        self.clear_tooltips()
        search_box = self.wait_for_and_click(selector)
        if escape_to_clear:
            # The combination of DebouncedInput+b-input doesn't seem to uniformly respect
            # .clear() below. We use escape handling a lot - and that does cauase to the input
            # to reset correctly and fire the required re-active events/handlers.
            self.send_escape(search_box)
        search_box.clear()
        if search_term is not None:
            search_box.send_keys(search_term)
        self.send_enter(search_box)
        return search_box

    def _get_random_name(self, prefix=None, suffix=None, len=10):
        return "{}{}{}".format(
            prefix or "",
            "".join(random.choice(string.ascii_lowercase + string.digits) for _ in range(len)),
            suffix or "",
        )

    def _get_random_email(self, username=None, domain=None):
        username = username or "test"
        domain = domain or "test.test"
        return self._get_random_name(prefix=username, suffix=f"@{domain}")

    # Creates a random password of length len by creating an array with all ASCII letters and the numbers 0 to 9,
    # then using the random number generator to pick one elemenent to concatinate it to the end of the password string until
    # we have a password of length len.
    def _get_random_password(self, len=6):
        return "".join(random.SystemRandom().choice(string.ascii_letters + string.digits) for _ in range(len))

    def submit_login(self, email, password=None, assert_valid=True, retries=0):
        self.components.masthead.register_or_login.wait_for_and_click()
        self.sleep_for(WAIT_TYPES.UX_RENDER)
        self.fill_login_and_submit(email, password=password)
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

    def fill_login_and_submit(self, email, password=None):
        if password is None:
            password = self.default_password
        login_info = {
            "login": email,
            "password": password,
        }
        login = self.components.login
        self.fill(login.form.wait_for_visible(), login_info)
        self.snapshot("logging-in")
        login.submit.wait_for_and_click()
        self.snapshot("login-submitted")

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
        self.components.masthead.register_or_login.wait_for_and_click()
        registration = self.components.registration
        registration.toggle.wait_for_and_click()
        form = registration.form.wait_for_visible()
        self.fill(form, dict(email=email, password=password, username=username, confirm=confirm))
        registration.submit.wait_for_and_click()
        if assert_valid is False:
            self.assert_error_message()
        elif assert_valid:
            self.wait_for_logged_in()

    def wait_for_logged_in(self):
        try:
            self.components.masthead.logged_in_only.wait_for_visible()
        except SeleniumTimeoutException as e:
            ui_logged_out = self.components.masthead.logged_out_only.is_displayed
            if ui_logged_out:
                dom_message = "Element a.loggedout-only is present in DOM, indicating Log in or Register button still in masthead."
            else:
                dom_message = "Element a.loggedout-only is *not* present in DOM."
            user_info = self.api_get("users/current")
            if "username" in user_info:
                template = "Failed waiting for masthead to update for login, but user API response indicates [%s] is logged in. This seems to be a bug in Galaxy. %s logged API response was [%s]. "
                message = template % (user_info["username"], dom_message, user_info)
                raise self.prepend_timeout_message(e, message)
            else:
                raise NotLoggedInException(e, user_info, dom_message)

    def click_center(self):
        action_chains = self.action_chains()
        center_element = self.driver.find_element(By.CSS_SELECTOR, "#center")
        action_chains.move_to_element(center_element).click().perform()

    def hover_over(self, target):
        action_chains = self.action_chains()
        action_chains.move_to_element(target).perform()

    def perform_single_upload(self, test_path, **kwd) -> HistoryEntry:
        before_latest_history_item = self.latest_history_entry()
        self._perform_upload(test_path=test_path, **kwd)
        after_latest_history_item = self.latest_history_entry()
        assert after_latest_history_item
        if before_latest_history_item is not None:
            assert before_latest_history_item.id != after_latest_history_item.id
        return after_latest_history_item

    def perform_upload(self, test_path, **kwd):
        self._perform_upload(test_path=test_path, **kwd)

    def perform_upload_of_pasted_content(self, paste_data, **kwd):
        self._perform_upload(paste_data=paste_data, **kwd)

    def _perform_upload(
        self, test_path=None, paste_data=None, ext=None, genome=None, ext_all=None, genome_all=None, deferred=None
    ):
        self.home()
        self.upload_start_click()

        self.upload_set_footer_extension(ext_all)
        self.upload_set_footer_genome(genome_all)

        if test_path:
            self.upload_queue_local_file(test_path)
        else:
            assert paste_data is not None
            if isinstance(paste_data, dict):
                for name, value in paste_data.items():
                    self.upload_paste_data(value)
                    name_input = self.wait_for_selector("div#regular .upload-row:last-of-type .upload-title")
                    name_input.clear()
                    name_input.send_keys(name)
            else:
                self.upload_paste_data(paste_data)

        if ext is not None:
            self.wait_for_selector_visible(".upload-extension")
            self.select_set_value(".upload-extension", ext)

        if genome is not None:
            self.wait_for_selector_visible(".upload-genome")
            self.select_set_value(".upload-genome", genome)

        if deferred is not None:
            upload = self.components.upload
            upload.settings_button(n=0).wait_for_and_click()
            upload.settings.wait_for_visible()
            setting = upload.setting_deferred.wait_for_visible()
            classes = setting.get_attribute("class").split(" ")
            if deferred is True and "fa-check-square-o" not in classes:
                setting.click()
            elif deferred is False and "fa-check-square-o" in classes:
                setting.click()

        self.upload_start()

        self.components.upload.close_button.wait_for_and_click()

    def perform_upload_of_composite_dataset_pasted_data(self, ext, paste_content):
        self.home()
        self.upload_start_click()
        self.components.upload.tab(tab="composite").wait_for_and_click()
        self.upload_set_footer_extension(ext, tab_id="composite")

        for i in range(len(paste_content)):
            self.components.upload.source_button(n=i).wait_for_and_click()
            self.components.upload.paste_option(n=i).wait_for_and_click()
            textarea = self.components.upload.paste_content(n=i).wait_for_visible()
            textarea.send_keys(paste_content[i])

        self.upload_start(tab_id="composite")
        self.components.upload.composite_close_button.wait_for_and_click()

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

        self.ensure_collection_builder_filters_cleared()
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
            selector = f"div#{tab_id} .upload-footer-extension"
            self.wait_for_selector_visible(selector)
            self.select_set_value(selector, ext)

    @retry_during_transitions
    def upload_set_footer_genome(self, genome, tab_id="regular"):
        if genome is not None:
            selector = f"div#{tab_id} .upload-footer-genome"
            self.wait_for_selector_visible(selector)
            self.select_set_value(selector, genome)

    @retry_during_transitions
    def upload_set_collection_type(self, collection_type):
        self.wait_for_selector_visible(".upload-footer-collection-type")
        self.select_set_value(".upload-footer-collection-type", collection_type)

    def upload_start(self, tab_id="regular"):
        self.wait_for_and_click_selector(f"div#{tab_id} button#btn-start")

    @retry_during_transitions
    def upload_build(self, tab="collection"):
        build_selector = f"div#{tab} button#btn-build"
        # Pause a bit to let the callback on the build button be registered.
        time.sleep(0.5)
        # Click the Build button and make sure it disappears.
        self.wait_for_and_click_selector(build_selector)
        try:
            self.wait_for_selector_absent_or_hidden(build_selector)
        except SeleniumTimeoutException:
            # Sometimes the callback in the JS hasn't be registered by the
            # time that the build button is clicked. By the time the timeout
            # has been registered - it should have been.
            self.wait_for_and_click_selector(build_selector)
            self.wait_for_selector_absent_or_hidden(build_selector)

    def upload_queue_local_file(self, test_path, tab_id="regular"):
        self.wait_for_and_click_selector(f"div#{tab_id} button#btn-local")

        file_upload = self.wait_for_selector(f'div#{tab_id} input[type="file"]')
        file_upload.send_keys(test_path)

    def upload_paste_data(self, pasted_content, tab_id="regular"):
        tab_locator = f"div#{tab_id}"
        self.wait_for_and_click_selector(f"{tab_locator} button#btn-new")

        textarea = self.wait_for_selector(f"{tab_locator} .upload-row:last-of-type .upload-text-content")
        textarea.send_keys(pasted_content)

    def upload_uri(self, uri, wait=False):
        upload = self.components.upload
        upload.start.wait_for_and_click()
        upload.file_dialog.wait_for_and_click()
        scheme, uri_rest = uri.split("://", 1)
        parts = uri_rest.split("/")

        root = f"{scheme}://{parts[0]}"
        upload.file_source_selector(path=root).wait_for_and_click()
        rest_parts = parts[1:]
        path = root
        for part in rest_parts:
            path = f"{path}/{part}"
            upload.file_source_selector(path=path).wait_for_and_click()
        upload.file_dialog_ok.wait_for_and_click()
        self.upload_start()
        if wait:
            self.sleep_for(self.wait_types.UX_RENDER)
            self.wait_for_history()

    def upload_rule_start(self):
        self.upload_start_click()
        self.upload_tab_click("rule-based")

    def upload_rule_build(self):
        self.upload_build(tab="rule-based")

    def upload_rule_dataset_dialog(self):
        upload = self.components.upload
        upload.rule_dataset_dialog.wait_for_and_click()

    def upload_rule_set_data_type(self, type_description):
        upload = self.components.upload
        data_type_element = upload.rule_select_data_type.wait_for_visible()
        self.select_set_value(data_type_element, type_description)

    def upload_rule_set_dataset(self, row=1):
        upload = self.components.upload
        upload.rule_dataset_selector.wait_for_visible()
        upload.rule_dataset_selector_row(rowindex=row).wait_for_and_click()

    def rule_builder_set_collection_name(self, name):
        rule_builder = self.components.rule_builder
        name_element = rule_builder.collection_name_input.wait_for_and_click()
        name_element.send_keys(name)
        self.sleep_for(WAIT_TYPES.UX_RENDER)

    def rule_builder_set_extension(self, extension):
        self.select2_set_value(self.navigation.rule_builder.selectors.extension_select, extension)

    def rule_builder_filter_count(self, count=1):
        rule_builder = self.components.rule_builder
        rule_builder.menu_button_filter.wait_for_and_click()
        with self.rule_builder_rule_editor("add-filter-count") as editor_element:
            filter_input = editor_element.find_element(By.CSS_SELECTOR, "input[type='number']")
            filter_input.clear()
            filter_input.send_keys(f"{count}")

    def rule_builder_sort(self, column_label, screenshot_name=None):
        rule_builder = self.components.rule_builder
        rule_builder.menu_button_rules.wait_for_and_click()
        with self.rule_builder_rule_editor("sort") as editor_element:
            column_elem = editor_element.find_element(By.CSS_SELECTOR, ".rule-column-selector")
            self.select2_set_value(column_elem, column_label)
            self.screenshot_if(screenshot_name)

    def rule_builder_add_regex_groups(self, column_label, group_count, regex, screenshot_name):
        rule_builder = self.components.rule_builder
        rule_builder.menu_button_column.wait_for_and_click()
        with self.rule_builder_rule_editor("add-column-regex") as editor_element:
            column_elem = editor_element.find_element(By.CSS_SELECTOR, ".rule-column-selector")
            self.select2_set_value(column_elem, column_label)

            groups_elem = editor_element.find_element(By.CSS_SELECTOR, "input[type='radio'][value='groups']")
            groups_elem.click()

            regex_elem = editor_element.find_element(By.CSS_SELECTOR, "input.rule-regular-expression")
            regex_elem.clear()
            regex_elem.send_keys(regex)

            filter_input = editor_element.find_element(By.CSS_SELECTOR, "input[type='number']")
            filter_input.clear()
            filter_input.send_keys(f"{group_count}")

            self.screenshot_if(screenshot_name)

    def rule_builder_add_regex_replacement(self, column_label, regex, replacement, screenshot_name=None):
        rule_builder = self.components.rule_builder
        rule_builder.menu_button_column.wait_for_and_click()
        with self.rule_builder_rule_editor("add-column-regex") as editor_element:
            column_elem = editor_element.find_element(By.CSS_SELECTOR, ".rule-column-selector")
            self.select2_set_value(column_elem, column_label)

            groups_elem = editor_element.find_element(By.CSS_SELECTOR, "input[type='radio'][value='replacement']")
            groups_elem.click()

            regex_elem = editor_element.find_element(By.CSS_SELECTOR, "input.rule-regular-expression")
            regex_elem.clear()
            regex_elem.send_keys(regex)

            filter_input = editor_element.find_element(By.CSS_SELECTOR, "input.rule-replacement")
            filter_input.clear()
            filter_input.send_keys(f"{replacement}")

            self.screenshot_if(screenshot_name)

    def rule_builder_add_value(self, value, screenshot_name=None):
        rule_builder = self.components.rule_builder
        rule_builder.menu_button_column.wait_for_and_click()
        with self.rule_builder_rule_editor("add-column-value") as editor_element:
            filter_input = editor_element.find_element(By.CSS_SELECTOR, "input[type='text']")
            filter_input.clear()
            filter_input.send_keys(value)

            self.screenshot_if(screenshot_name)

    def rule_builder_remove_columns(self, column_labels, screenshot_name=None):
        rule_builder = self.components.rule_builder
        rule_builder.menu_button_rules.wait_for_and_click()
        with self.rule_builder_rule_editor("remove-columns") as filter_editor_element:
            column_elem = filter_editor_element.find_element(By.CSS_SELECTOR, ".rule-column-selector")
            for column_label in column_labels:
                self.select2_set_value(column_elem, column_label)
            self.screenshot_if(screenshot_name)

    def rule_builder_concatenate_columns(self, column_label_1, column_label_2, screenshot_name=None):
        rule_builder = self.components.rule_builder
        rule_builder.menu_button_column.wait_for_and_click()
        with self.rule_builder_rule_editor("add-column-concatenate") as filter_editor_element:
            column_elems = filter_editor_element.find_elements(By.CSS_SELECTOR, ".rule-column-selector")
            self.select2_set_value(column_elems[0], column_label_1)
            column_elems = filter_editor_element.find_elements(By.CSS_SELECTOR, ".rule-column-selector")
            self.select2_set_value(column_elems[1], column_label_2)
            self.screenshot_if(screenshot_name)

    def rule_builder_split_columns(self, column_labels_1, column_labels_2, screenshot_name=None):
        rule_builder = self.components.rule_builder
        rule_builder.menu_button_rules.wait_for_and_click()
        with self.rule_builder_rule_editor("split-columns") as filter_editor_element:
            column_elems = filter_editor_element.find_elements(By.CSS_SELECTOR, ".rule-column-selector")
            clear = True
            for column_label_1 in column_labels_1:
                self.select2_set_value(column_elems[0], column_label_1, clear_value=clear)
                clear = False

            column_elems = filter_editor_element.find_elements(By.CSS_SELECTOR, ".rule-column-selector")
            clear = True
            for column_label_2 in column_labels_2:
                self.select2_set_value(column_elems[1], column_label_2, clear_value=clear)
                clear = False

            self.screenshot_if(screenshot_name)

    def rule_builder_swap_columns(self, column_label_1, column_label_2, screenshot_name):
        rule_builder = self.components.rule_builder
        rule_builder.menu_button_rules.wait_for_and_click()
        with self.rule_builder_rule_editor("swap-columns") as filter_editor_element:
            column_elems = filter_editor_element.find_elements(By.CSS_SELECTOR, ".rule-column-selector")
            self.select2_set_value(column_elems[0], column_label_1)
            column_elems = filter_editor_element.find_elements(By.CSS_SELECTOR, ".rule-column-selector")
            self.select2_set_value(column_elems[1], column_label_2)
            self.screenshot_if(screenshot_name)

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
            self.screenshot_if(screenshot_name)
        else:
            assert len(column_label) > 0
            column_labels = column_label
            for i, column_label in enumerate(column_labels):
                if i > 0:
                    rule_builder.mapping_add_column(mapping_type=mapping_type).wait_for_and_click()
                mapping_elem = rule_builder.mapping_edit(mapping_type=mapping_type).wait_for_visible()
                self.select2_set_value(mapping_elem, column_label)
            self.screenshot_if(screenshot_name)
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

    def workflow_editor_add_input(self, item_name="data_input"):
        editor = self.components.workflow_editor

        # Make sure we're on the workflow editor and not clicking the main tool panel.
        editor.canvas_body.wait_for_visible()

        if editor.inputs.activity_panel.is_absent:
            editor.inputs.activity_button.wait_for_and_click()

        editor.inputs.input(id=item_name).wait_for_and_click()
        self.sleep_for(self.wait_types.UX_RENDER)

    def workflow_editor_set_license(self, license: str) -> None:
        license_selector = self.components.workflow_editor.license_selector
        license_selector.wait_for_and_click()
        license_selector.wait_for_and_send_keys(license)

        license_selector_option = self.components.workflow_editor.license_selector_option
        license_selector_option.wait_for_and_click()

    def workflow_editor_click_option(self, option_label):
        self.workflow_editor_click_options()
        menu_element = self.workflow_editor_options_menu_element()
        option_elements = menu_element.find_elements(By.CSS_SELECTOR, "button")
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
            raise Exception(f"Failed to find workflow editor option with label [{option_label}]")

    def workflow_editor_click_options(self):
        return self.wait_for_and_click_selector("#activity-settings")

    def workflow_editor_options_menu_element(self):
        return self.wait_for_selector_visible(".activity-settings")

    def workflow_editor_click_run(self):
        return self.wait_for_and_click_selector("#workflow-run-button")

    def workflow_editor_click_save(self):
        self.wait_for_and_click_selector("#workflow-save-button")
        self.sleep_for(self.wait_types.DATABASE_OPERATION)

    def workflow_editor_search_for_workflow(self, name: str):
        self.wait_for_and_click(self.components.workflow_editor.workflow_activity)
        self.sleep_for(self.wait_types.UX_RENDER)

        input = self.wait_for_selector(".activity-panel input")
        input.send_keys(name)

        self.sleep_for(self.wait_types.UX_RENDER)

    def workflow_editor_add_steps(self, name: str):
        self.workflow_editor_search_for_workflow(name)

        insert_button = self.components.workflows.workflow_card_button(name=name, title="Copy steps into workflow")
        insert_button.wait_for_and_click()

        self.sleep_for(self.wait_types.UX_RENDER)

    def workflow_editor_add_subworkflow(self, name: str):
        self.workflow_editor_search_for_workflow(name)

        insert_button = self.components.workflows.workflow_card_button(name=name, title="Insert as sub-workflow")
        insert_button.wait_for_and_click()

        self.components.workflow_editor.node._(label=name).wait_for_present()

        self.sleep_for(self.wait_types.UX_RENDER)

    def navigate_to_histories_page(self):
        self.home()
        self.components.histories.activity.wait_for_and_click()
        self.components.histories.histories.wait_for_present()

    def navigate_to_histories_shared_with_me_page(self):
        self.home()
        self.components.histories.activity.wait_for_and_click()
        self.components.shared_histories.tab.wait_for_and_click()

    def navigate_to_user_preferences(self):
        self.home()
        self.components.masthead.user.wait_for_and_click()
        self.components.masthead.preferences.wait_for_and_click()

    def navigate_to_invocations_grid(self):
        self.home()
        self.components.invocations.activity.wait_for_and_click()
        self.components.invocations.activity_expand.wait_for_and_click()

    def navigate_to_pages(self):
        self.home()
        self.components.pages.activity.wait_for_and_click()

    def navigate_to_published_workflows(self):
        self.home()
        self.components.workflows.activity.wait_for_and_click()
        self.components.workflows.published_tab.wait_for_and_click()

    def navigate_to_published_histories(self):
        self.home()
        self.components.histories.activity.wait_for_and_click()
        self.components.published_histories.tab.wait_for_and_click()

    def navigate_to_tools(self):
        self.home()
        self.components.tools.activity.wait_for_and_click()

    def admin_open(self):
        self.components.admin.activity.wait_for_and_click()

    def create_quota(
        self,
        name: Optional[str] = None,
        description: Optional[str] = None,
        amount: Optional[str] = None,
        quota_source_label: Optional[str] = None,
        user: Optional[str] = None,
    ):
        admin_component = self.components.admin

        self.admin_open()
        quota_link = admin_component.index.quotas
        quota_link.wait_for_and_click()
        quota_component = admin_component.quota

        quota_component.add_new.wait_for_and_click()
        form = quota_component.add_form.wait_for_visible()

        name = name or self._get_random_name()
        description = description or f"quota description for {name}"
        amount = amount or ""
        self.fill(
            form,
            {
                "name": name,
                "description": description,
                "amount": amount,
            },
        )
        if quota_source_label:
            self.select_set_value("#quota_source_label", quota_source_label)
        if user:
            self.select_set_value("#in_users", user, multiple=True)
        quota_component.add_form_submit.wait_for_and_click()

    def select_dataset_from_lib_import_modal(self, filenames):
        for name in filenames:
            self.components.libraries.folder.select_import_dir_item(name=name).wait_for_and_click()
        self.components.libraries.folder.import_dir_btn.wait_for_and_click()

    def create_new_library(self):
        self.libraries_open()
        self.name = self._get_random_name(prefix="testcontents")
        self.libraries_index_create(self.name)

    def libraries_open(self):
        self.home()
        self.components.libraries.activity.wait_for_and_click()
        self.components.libraries.selector.wait_for_visible()

    def libraries_open_with_name(self, name):
        self.libraries_open()
        self.libraries_index_search_for(name)
        self.libraries_index_table_elements()[0].find_element(By.CSS_SELECTOR, "td a").click()

    def page_open_and_screenshot(self, page_name, screenshot_name):
        self.home()
        self.navigate_to_pages()
        self.select_grid_operation(page_name, "View")
        if screenshot_name:
            self.sleep_for(self.wait_types.UX_RENDER)
            self.screenshot(screenshot_name)

    @retry_during_transitions
    def libraries_index_table_elements(self):
        container = self.components.libraries._.wait_for_visible()

        elements = container.find_elements(By.CSS_SELECTOR, "tbody")
        if not elements:
            return []
        else:
            assert len(elements) == 1
            element = elements[0]
            return element.find_elements(By.CSS_SELECTOR, "tr")  # [style='display: table-row']

    def libraries_index_create(self, name):
        self.components.libraries.create_new_library_btn.wait_for_and_click()
        name_input_field = self.components.libraries.new_library_name_input.wait_for_visible()
        input_field = self.components.libraries.new_library_description_input.wait_for_visible()

        name_input_field.send_keys(name)
        input_field.send_keys(self._get_random_name(prefix="description"))
        self.components.libraries.save_new_library_btn.wait_for_and_click()

    def libraries_index_click_search(self):
        self.sleep_for(WAIT_TYPES.UX_RENDER)
        search_element = self.components.libraries.search_field.wait_for_visible()
        search_element.click()
        return search_element

    def libraries_index_sort_selector(self):
        return "th[aria-sort]"

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

    def libraries_folder_create(self, name):
        self.components.libraries.folder.add_folder.wait_for_and_click()
        self.components.libraries.folder.input_folder_name.wait_for_and_send_keys(name)
        self.components.libraries.folder.save_folder_btn.wait_for_and_click()

    def libraries_click_dataset_import(self):
        self.wait_for_and_click(self.navigation.libraries.folder.selectors.add_items_button)
        self.wait_for_visible(self.navigation.libraries.folder.selectors.add_items_menu)

    def libraries_dataset_import(self, btn):
        self.libraries_click_dataset_import()
        self.wait_for_and_click(btn)

    def libraries_dataset_import_from_history_search_for(self, search_term=None):
        return self._inline_search_for(
            self.navigation.libraries.folder.selectors.import_datasets_from_history_modal_history_search,
            search_term,
        )

    def libraries_dataset_import_from_history_select(self, to_select_items):
        self.wait_for_visible(
            self.navigation.libraries.folder.selectors.import_datasets_from_history_modal_list_is_ready
        )
        for to_select_item in to_select_items:
            found = False
            self._inline_search_for(
                self.navigation.libraries.folder.selectors.import_datasets_from_history_modal_dataset_search,
                to_select_item,
            )
            self.components.libraries.folder.import_datasets_from_history_modal_select_list_item_by_index(
                row_index=1
            ).wait_for_and_click()
            found = True
        if not found:
            raise Exception(f"Failed to find history item [{to_select_item}] to select")

    def libraries_dataset_import_from_history_click_ok(self, wait=True):
        self.wait_for_and_click(self.navigation.libraries.folder.selectors.import_datasets_from_history_modal_ok)
        if wait:
            # Let the progress bar disappear...
            self.wait_for_absent_or_hidden(
                self.navigation.libraries.folder.selectors.import_datasets_from_history_modal
            )

    def libraries_table_elements(self):
        tbody_element = self.wait_for_selector_visible("#folder_list_body > tbody")
        return tbody_element.find_elements(By.CSS_SELECTOR, "tr:not(.b-table-empty-row)")

    def populate_library_folder_from_import_dir(self, library_name, filenames):
        self.libraries_open_with_name(library_name)
        self.libraries_dataset_import(self.navigation.libraries.folder.labels.from_import_dir)
        self.select_dataset_from_lib_import_modal(filenames)

    def navigate_to_new_library(self):
        self.create_new_library()
        self.libraries_open_with_name(self.name)

    def wait_for_overlays_cleared(self):
        """Wait for modals and Toast notifications to disappear."""
        self.wait_for_selector_absent_or_hidden(".ui-modal", wait_type=WAIT_TYPES.UX_POPUP)
        self.wait_for_selector_absent_or_hidden(".toast", wait_type=WAIT_TYPES.UX_POPUP)

    def clear_tooltips(self):
        action_chains = self.action_chains()
        center_element = self.driver.find_element(By.CSS_SELECTOR, "#center")
        action_chains.move_to_element(center_element).perform()
        self.wait_for_selector_absent_or_hidden(".b-tooltip", wait_type=WAIT_TYPES.UX_POPUP)

    def pages_index_table_elements(self):
        pages = self.components.pages
        pages.index_table.wait_for_visible()
        return pages.index_rows.all()

    def workflow_index_open(self):
        self.home()
        self.click_activity_workflow()

    def workflow_shared_with_me_open(self):
        self.workflow_index_open()
        self.components.workflows.shared_with_me_tab.wait_for_and_click()

    def workflow_card_elements(self):
        self.components.workflows.workflow_cards.wait_for_visible()
        return self.components.workflows.workflow_card.all()

    def workflow_card_element(self, workflow_index=0):

        @retry_index_during_transitions()
        def fetch():
            return self.workflow_card_elements()[workflow_index]

        return fetch()

    @retry_during_transitions
    def workflow_index_column_text(self, column_index, workflow_index=0):
        row_element = self.workflow_card_element(workflow_index=workflow_index)
        columns = row_element.find_elements(By.CSS_SELECTOR, "td")
        return columns[column_index].text

    def workflow_index_click_search(self):
        return self.wait_for_and_click_selector(
            '.workflows-list input.search-query[data-description="filter text input"]'
        )

    def workflow_index_get_current_filter(self):
        filter_element = self.components.workflows.search_box.wait_for_and_click()
        return filter_element.get_attribute("value")

    def workflow_index_search_for(self, search_term=None):
        return self._inline_search_for(
            self.navigation.workflows.search_box,
            search_term,
            escape_to_clear=True,
        )

    def workflow_index_click_import(self):
        return self.components.workflows.import_button.wait_for_and_click()

    def workflow_rename(self, new_name, workflow_index=0):
        workflow = self.workflow_card_element(workflow_index=workflow_index)
        workflow.find_element(By.CSS_SELECTOR, "[data-workflow-rename]").click()
        self.components.workflows.rename_input.wait_for_visible().clear()
        self.components.workflows.rename_input.wait_for_and_send_keys(new_name)
        self.components.workflows.rename_input.wait_for_and_send_keys(self.keys.ENTER)

    def workflow_delete_by_name(self, name):
        self.workflow_index_search_for(name)
        self.components.workflows.workflow_drop_down.wait_for_and_click()
        self.components.workflows.delete_button.wait_for_and_click()
        self.sleep_for(self.wait_types.UX_RENDER)
        self.components._.confirm_button(name="Delete").wait_for_and_click()

    @retry_during_transitions
    def workflow_index_name(self, workflow_index=0):
        workflow = self.workflow_card_element(workflow_index=workflow_index)
        return workflow.find_element(By.CSS_SELECTOR, ".workflow-name").text

    def select_dropdown_item(self, option_title):
        menu_element = self.wait_for_selector_visible(".dropdown-menu.show")
        menu_options = menu_element.find_elements(By.CSS_SELECTOR, "a.dropdown-item")
        for menu_option in menu_options:
            if option_title in menu_option.text:
                menu_option.click()
                return True

    def workflow_share_click(self):
        self.components.workflows.share_button.wait_for_and_click()

    def workflow_index_view_external_link(self, workflow_index=0):
        self.components.workflows.workflow_drop_down.wait_for_and_click()
        self.components.workflows.view_external_link.wait_for_and_click()

    def workflow_index_click_tag_display(self, workflow_index=0):
        workflow_element = self.workflow_card_element(workflow_index=workflow_index)
        workflow_element.find_element(By.CSS_SELECTOR, ".stateless-tags .headless-multiselect .toggle-button").click()

    def workflow_index_add_tag(self, tag: str, workflow_index: int = 0):
        self.workflow_index_click_tag_display(workflow_index=workflow_index)
        self.tagging_add([tag])

    @retry_during_transitions
    def workflow_index_tags(self, workflow_index=0):
        tag_spans = self.workflow_index_tag_elements(workflow_index=workflow_index)
        tags = []
        for tag_span in tag_spans:
            tags.append(tag_span.text)
        return tags

    @retry_during_transitions
    def workflow_index_tag_elements(self, workflow_index=0):
        workflow_row_element = self.workflow_card_element(workflow_index)
        tag_display = workflow_row_element.find_element(By.CSS_SELECTOR, ".stateless-tags")
        tag_spans = tag_display.find_elements(By.CSS_SELECTOR, ".tag")
        return tag_spans

    @retry_during_transitions
    def workflow_index_click_tag(self, tag, workflow_index=0):
        tag_spans = self.workflow_index_tag_elements(workflow_index=workflow_index)
        clicked = False
        for tag_span in tag_spans:
            if tag_span.text == tag:
                tag_span.click()
                clicked = True
                break
        if not clicked:
            raise KeyError(f"Failed to find tag {tag} on workflow with index {workflow_index}")

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
                tag_area_selector = f"{parent_selector}.headless-multiselect input[type='text']"
                tag_area = self.wait_for_selector_clickable(tag_area_selector)
                tag_area.click()

            tag_area.send_keys(tag)
            self.send_enter(tag_area)
        self.send_escape(tag_area)

    def workflow_run_with_name(self, name: str):
        self.workflow_index_open()
        self.workflow_index_search_for(name)
        self.components.workflows.run_button.wait_for_and_click()
        self.sleep_for(self.wait_types.UX_RENDER)

    def workflow_run_specify_inputs(self, inputs: Dict[str, Any]):
        workflow_run = self.components.workflow_run
        for label, value in inputs.items():
            input_div_element = workflow_run.input_data_div(label=label).wait_for_visible()
            self.select_set_value(input_div_element, "{}: ".format(value["hid"]))

    def workflow_run_submit(self):
        self.components.workflow_run.run_workflow.wait_for_and_click()

    def workflow_run_ensure_expanded(self):
        workflow_run = self.components.workflow_run
        if workflow_run.expanded_form.is_absent:
            workflow_run.runtime_setting_button.wait_for_and_click()
            workflow_run.expand_form_link.wait_for_and_click()
            workflow_run.expanded_form.wait_for_visible()

    def workflow_create_new(
        self, annotation: Optional[str] = None, clear_placeholder: bool = False, save_workflow: bool = True
    ):
        self.workflow_index_open()
        self.sleep_for(self.wait_types.UX_RENDER)
        self.click_button_new_workflow()
        self.sleep_for(self.wait_types.UX_RENDER)
        name = self._get_random_name()
        name_component = self.components.workflow_editor.edit_name
        if clear_placeholder:
            name_component.wait_for_visible().clear()
        name_component.wait_for_and_send_keys(name)
        annotation = annotation or self._get_random_name()
        self.components.workflow_editor.edit_annotation.wait_for_and_send_keys(annotation)
        if save_workflow:
            save_button = self.components.workflow_editor.save_button
            save_button.wait_for_visible()
            assert not save_button.has_class("disabled")
            save_button.wait_for_and_click()
            self.sleep_for(self.wait_types.UX_RENDER)
        return name

    def invocation_index_table_elements(self):
        invocations = self.components.invocations
        invocations.invocations_table.wait_for_visible()
        return invocations.invocations_table_rows.all()

    def open_toolbox(self):
        self.sleep_for(self.wait_types.UX_RENDER)

        if self.element_absent(self.components.tools.tools_activity_workflow_editor):
            if self.element_absent(self.components._.toolbox_panel):
                self.components.tools.activity.wait_for_and_click()
        else:
            if self.element_absent(self.components._.toolbox_panel):
                self.components.tools.tools_activity_workflow_editor.wait_for_and_click()

        self.sleep_for(self.wait_types.UX_RENDER)

    def swap_to_tool_panel(self, panel_id: str) -> None:
        tool_panel = self.components.tool_panel
        tool_panel.views_button.wait_for_and_click()
        tool_panel.views_menu_item(panel_id=panel_id).wait_for_and_click()

    def swap_to_tool_panel_edam_operations(self) -> None:
        self.swap_to_tool_panel("ontology:edam_operations")

    def tool_open(self, tool_id, outer=False):
        self.open_toolbox()

        self.components.tools.clear_search.wait_for_and_click()
        self.sleep_for(self.wait_types.UX_RENDER)

        self.components.tools.search.wait_for_and_send_keys(f"id:{tool_id}")

        if outer:
            tool_link = self.components.tool_panel.outer_tool_link(tool_id=tool_id)
        else:
            tool_link = self.components.tool_panel.tool_link(tool_id=tool_id)
        tool_element = tool_link.wait_for_present()
        self.driver.execute_script("arguments[0].scrollIntoView(true);", tool_element)
        tool_link.wait_for_and_click()

    def datasource_tool_open(self, tool_id):
        tool_link = self.components.tool_panel.data_source_tool_link(tool_id=tool_id)
        tool_element = tool_link.wait_for_present()
        self.driver.execute_script("arguments[0].scrollIntoView(true);", tool_element)
        tool_link.wait_for_and_click()

    def run_environment_test_tool(self, inttest_value="42", select_storage: Optional[str] = None):
        self.home()
        self.tool_open("environment_variables")
        if select_storage:
            self.components.tool_form.storage_options.wait_for_and_click()
            self.select_storage(select_storage)
        self.tool_set_value("inttest", inttest_value)
        self.tool_form_execute()

    def select_storage(self, storage_id: str) -> None:
        selection_component = self.components.preferences.object_store_selection
        selection_component.option_buttons.wait_for_present()
        button = selection_component.option_button(object_store_id=storage_id)
        button.wait_for_and_click()
        selection_component.option_buttons.wait_for_absent_or_hidden()

    def create_page_and_edit(self, name=None, slug=None, screenshot_name=None):
        name = self.create_page(name=name, slug=slug, screenshot_name=screenshot_name)
        self.select_grid_operation(name, "Edit content")
        self.components.pages.editor.markdown_editor.wait_for_visible()
        return name

    def create_page(self, name=None, slug=None, screenshot_name=None):
        name = name or self._get_random_name(prefix="page")
        slug = slug = self._get_random_name(prefix="pageslug")
        self.components.pages.create.wait_for_and_click()
        self.sleep_for(self.wait_types.UX_TRANSITION)
        self.screenshot("before_title_input")
        self.components.pages.create_title_input.wait_for_and_send_keys(name)
        self.sleep_for(self.wait_types.UX_RENDER)
        self.screenshot("before_slug_input")
        self.components.pages.create_slug_input.wait_for_and_send_keys(slug)
        self.sleep_for(self.wait_types.UX_RENDER)
        self.screenshot_if(screenshot_name)
        self.components.pages.submit.wait_for_and_click()
        self.sleep_for(self.wait_types.UX_RENDER)
        return name

    def tool_parameter_div(self, expanded_parameter_id):
        return self.components.tool_form.parameter_div(parameter=expanded_parameter_id).wait_for_clickable()

    def tool_parameter_edit_rules(self):
        rules_div_element = self.tool_parameter_div("rules")
        edit_button_element = rules_div_element.find_element(By.CSS_SELECTOR, ".form-rules-edit button")
        edit_button_element.click()

    def tool_set_value(self, expanded_parameter_id, value, expected_type=None):
        div_element = self.tool_parameter_div(expanded_parameter_id)
        assert div_element
        if expected_type in ["select", "data", "data_collection"]:
            select_field = self.components.tool_form.parameter_data_select(
                parameter=expanded_parameter_id
            ).wait_for_visible()
            self.select_set_value(select_field, value)
        else:
            input_element = div_element.find_element(By.CSS_SELECTOR, "input")
            # Clear default value
            input_element.clear()
            input_element.send_keys(value)

    def tool_form_generate_tour(self):
        self.components.tool_form.options.wait_for_and_click()
        self.components.tool_form.generate_tour.wait_for_and_click()

    def tool_form_execute(self):
        self.components.tool_form.execute.wait_for_and_click()

    def click_activity_workflow(self):
        self.components.workflows.activity.wait_for_and_click()

    def click_button_new_workflow(self):
        self.wait_for_and_click(self.navigation.workflows.selectors.new_button)

    def wait_for_sizzle_selector_clickable(self, selector):
        element = self._wait_on(
            sizzle.sizzle_selector_clickable(selector),
            f"sizzle/jQuery selector [{selector}] to become clickable",
        )
        return element

    @retry_during_transitions
    def click_history_options(self):
        component = self.components.history_panel.options_button_icon
        component.wait_for_and_click()

    def click_history_option_export_to_file(self):
        self.use_bootstrap_dropdown(option="export to file", menu="history options")

    def click_history_option_sharing(self):
        self.use_bootstrap_dropdown(option="share or publish", menu="history options")

    def click_history_option(self, option_label_or_component):
        # Open menu
        self.click_history_options()

        if isinstance(option_label_or_component, str):
            option_label = option_label_or_component
            # Click labeled option
            self.wait_for_visible(self.navigation.history_panel.options_menu)
            menu_item_sizzle_selector = self.navigation.history_panel.options_menu_item(
                option_label=option_label
            ).selector
            menu_selection_element = self.wait_for_sizzle_selector_clickable(menu_item_sizzle_selector)
            menu_selection_element.click()
        else:
            option_component = option_label_or_component
            option_component.wait_for_and_click()

    # avoids problematic ID and classes on markup
    def history_element(self, attribute_value, attribute_name="data-description", scope=".history-index"):
        return self.components._.by_attribute(name=attribute_name, value=attribute_value, scope=scope)

    # join list of attrs into css attribute selectors and append to base item selector
    def content_item_by_attributes(self, multi_history_panel=False, **attrs):
        suffix_list = [f'[data-{k}="{v}"]' for (k, v) in attrs.items() if v is not None]
        suffix = "".join(suffix_list)
        selector = self.components.history_panel.content_item.selector
        if multi_history_panel:
            selector = self.components.multi_history_panel.selector(suffix=suffix)
        return selector(suffix=suffix)

    def history_click_create_new(self):
        self.components.history_panel.new_history_button.wait_for_and_click()

    def history_click_editor_save(self):
        option = self.history_element("editor save button")
        option.wait_for_and_click()
        self.sleep_for(self.wait_types.UX_RENDER)

    def history_panel_click_copy_elements(self):
        self.use_bootstrap_dropdown(option="copy datasets", menu="history action menu")

    def use_bootstrap_dropdown(self, option=None, menu=None):
        """uses bootstrap dropdown by data-description attributes"""
        if option is None:
            raise TypeError
        if menu is None:
            raise TypeError
        toggle = self.history_element(menu).descendant("button")
        self.wait_for_and_click(toggle)
        return self.history_element(option).wait_for_and_click()

    @retry_during_transitions
    def histories_click_advanced_search(self):
        search_selector = "#standard-search .advanced-search-toggle"
        self.wait_for_and_click_selector(search_selector)

    @edit_details
    def history_panel_add_tags(self, tags):
        tag_area_button = self.components.history_panel.tag_area_button

        tag_area_button.wait_for_and_click()
        input_element = self.components.history_panel.tag_area_input.wait_for_visible()

        for tag in tags:
            input_element.send_keys(tag)
            self.send_enter(input_element)
            self.sleep_for(self.wait_types.UX_RENDER)

        self.send_escape(input_element)

    @edit_details
    def history_panel_rename(self, new_name):
        editable_text_input_element = self.history_panel_name_input()
        editable_text_input_element.clear()
        editable_text_input_element.send_keys(new_name)
        return editable_text_input_element

    def history_panel_name_input(self):
        history_panel = self.components.history_panel
        edit = history_panel.name_edit_input
        editable_text_input_element = edit.wait_for_visible()
        return editable_text_input_element

    def history_panel_click_to_rename(self):
        history_panel = self.components.history_panel
        name = history_panel.name
        edit = history_panel.name_edit_input
        name.wait_for_and_click()
        return edit.wait_for_visible()

    def history_panel_refresh_click(self):
        self.wait_for_and_click(self.navigation.history_panel.selectors.refresh_button)

    def history_panel_multi_operations_show(self):
        return self.wait_for_and_click(self.navigation.history_panel.multi_operations.selectors.show_button)

    def history_panel_muli_operation_select_hid(self, hid):
        item_selector = self.history_panel_item_selector(hid, wait=True)
        operation_radio_selector = f"{item_selector} .selector"
        self.wait_for_and_click_selector(operation_radio_selector)

    def history_panel_multi_operation_action_click(self, action):
        # Maybe isn't needed?
        # self.sleep_for(WAIT_TYPES.UX_RENDER)
        self.wait_for_and_click(self.navigation.history_panel.multi_operations.selectors.action_button)

        @retry_during_transitions
        def _click_action_in_menu():
            menu_element = self.wait_for_visible(self.navigation.history_panel.multi_operations.selectors.action_menu)
            menu_element.find_element(By.LINK_TEXT, action.text).click()

        _click_action_in_menu()

    def open_history_multi_view(self):
        self.components.history_panel.histories_operation_menu.wait_for_and_click()
        self.components.history_panel.multi_view_button.wait_for_and_click()

    def history_multi_view_display_collection_contents(self, collection_hid, collection_type="list"):
        self.open_history_multi_view()

        selector = self.history_panel_wait_for_hid_state(collection_hid, "ok", multi_history_panel=True)
        self.click(selector)
        for _ in range(len(collection_type.split(":")) - 1):
            selector = self.history_panel_wait_for_hid_state(1, "ok", multi_history_panel=True)
            self.click(selector)

        dataset_selector = self.history_panel_wait_for_hid_state(1, "ok", multi_history_panel=True)
        self.wait_for_and_click(dataset_selector)
        self.history_panel_wait_for_hid_state(1, "ok", multi_history_panel=True)

    def history_panel_item_edit(self, hid):
        item = self.history_panel_item_component(hid=hid)
        item.edit_button.wait_for_and_click()
        self.components.edit_dataset_attributes._.wait_for_visible()

    def history_panel_item_view_dataset_details(self, hid):
        item = self.history_panel_item_component(hid=hid)
        item.dataset_operations.wait_for_visible()
        item.info_button.wait_for_and_click()
        self.components.dataset_details._.wait_for_visible()

    def history_panel_item_click_visualization_menu(self, hid):
        viz_button_selector = f"{self.history_panel_item_selector(hid)} .visualizations-dropdown"
        self.wait_for_and_click_selector(viz_button_selector)
        self.wait_for_selector_visible(f"{viz_button_selector} .dropdown-menu")

    def history_panel_item_available_visualizations_elements(self, hid):
        # Precondition: viz menu has been opened with history_panel_item_click_visualization_menu
        viz_menu_selectors = f"{self.history_panel_item_selector(hid)} a.visualization-link"
        return self.driver.find_elements(By.CSS_SELECTOR, viz_menu_selectors)

    def history_panel_item_get_tags(self, hid):
        item_component = self.history_panel_item_component(hid=hid)
        item_component.wait_for_visible()
        return [e.text for e in item_component.alltags.all()]

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

        raise ValueError(f"No visualization [{visualization_name}] found.")

    def history_panel_item_selector(self, hid, wait=False):
        current_history_id = self.current_history_id()
        contents = self.api_get(f"histories/{current_history_id}/contents")
        try:
            history_item = [d for d in contents if d["hid"] == hid][0]
        except IndexError:
            raise Exception(f"Could not find history item with hid [{hid}] in contents [{contents}]")
        history_item_selector = f"#{history_item['history_content_type']}-{history_item['id']}"
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

    def hda_click_primary_action_button(self, hid: int, button_key: str):
        self.history_panel_ensure_showing_item_details(hid)
        item_component = self.history_panel_item_component(hid=hid)
        button_component = item_component[f"{button_key}_button"]
        button_component.wait_for_and_click()

    def hda_click_details(self, hid: int):
        self.hda_click_primary_action_button(hid, "info")

    def history_panel_click_item_title(self, hid, **kwds):
        item_component = self.history_panel_item_component(hid=hid)
        details_component = item_component.details
        details_displayed = not details_component.is_absent and details_component.is_displayed
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
        item_component.wait_for_present()
        if item_component.details.is_absent:
            return False
        return item_component.details.is_displayed

    def collection_builder_set_name(self, name):
        # small sleep here seems to be needed in the case of the
        # collection builder even though we wait for the component
        # to be clickable - which should make it enabled and should
        # allow send_keys to work. The send_keys occasionally doesn't
        # result in the name being filled out in the UI without this.
        self.sleep_for(WAIT_TYPES.UX_RENDER)
        self._wait_for_input_text_component_and_fill(self.components.collection_builders.name, name)

    def _wait_for_input_text_component_and_fill(self, component, text):
        target_element = component.wait_for_clickable()
        target_element.send_keys(text)

    def collection_builder_hide_originals(self):
        self.wait_for_and_click_selector('[data-description="hide original elements"]')

    def collection_builder_create(self):
        self.wait_for_and_click_selector("button.create-collection")

    def ensure_collection_builder_filters_cleared(self):
        clear_filters = self.components.collection_builders.clear_filters
        element = clear_filters.wait_for_present()
        if "disabled" not in element.get_attribute("class").split(" "):
            self.collection_builder_clear_filters()

    def collection_builder_clear_filters(self):
        clear_filters = self.components.collection_builders.clear_filters
        clear_filters.wait_for_and_click()

    def collection_builder_click_paired_item(self, forward_or_reverse, item):
        assert forward_or_reverse in ["forward", "reverse"]
        forward_column = self.wait_for_selector_visible(f".{forward_or_reverse}-column .column-datasets")
        first_datset_forward = forward_column.find_elements(By.CSS_SELECTOR, "li")[item]
        first_datset_forward.click()

    def logout_if_needed(self):
        if self.is_logged_in():
            self.home()
            self.logout()

    def logout(self):
        self.components.masthead.logged_in_only.wait_for_visible()
        self.components.masthead.user.wait_for_and_click()
        self.components.masthead.logout.wait_for_and_click()
        try:
            self.components.masthead.logged_out_only.wait_for_visible()
        except SeleniumTimeoutException as e:
            message = "Clicked logout button but waiting for 'Log in or Registration' button failed, perhaps the logout button was clicked before the handler was setup?"
            raise self.prepend_timeout_message(e, message)
        assert (
            not self.is_logged_in()
        ), "Clicked to logged out and UI reflects a logout, but API still thinks a user is logged in."

    def run_tour(self, path, skip_steps=None, sleep_on_steps=None, tour_callback=None):
        skip_steps = skip_steps or []
        sleep_on_steps = sleep_on_steps or {}
        if tour_callback is None:
            tour_callback = NullTourCallback()
        self.home()
        with open(path) as f:
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
        timeout_message = self._timeout_message(f"Tour CSS selector [{selector}] to become clickable")
        element = wait.until(
            ec.element_to_be_clickable((By.CSS_SELECTOR, selector)),
            timeout_message,
        )
        return element

    def tour_wait_for_element_present(self, selector):
        timeout = self.timeout_for(wait_type=WAIT_TYPES.JOB_COMPLETION)
        wait = self.wait(timeout=timeout)
        timeout_message = self._timeout_message(f"Tour CSS selector [{selector}] to become present")
        element = wait.until(
            ec.presence_of_element_located((By.CSS_SELECTOR, selector)),
            timeout_message,
        )
        return element

    def _clear_tooltip(self, tooltip_component):
        last_timeout: Optional[SeleniumTimeoutException] = None
        for _ in range(2):
            if not tooltip_component.is_absent:
                move_away_chain = self.action_chains()
                move_away_chain.move_by_offset(100, 100)
                move_away_chain.perform()
            try:
                tooltip_component.wait_for_absent()
                return
            except SeleniumTimeoutException as e:
                last_timeout = e

        assert last_timeout
        message = "Failed to force current tool tip off screen, cannot test next tooltip."
        raise self.prepend_timeout_message(last_timeout, message)

    def get_tooltip_text(self, element, sleep=0, click_away=True):
        tooltip_balloon = self.components._.tooltip_balloon
        self._clear_tooltip(tooltip_balloon)
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

    def assert_tooltip_text(self, element, expected: Union[str, HasText], sleep: int = 0, click_away: bool = True):
        if hasattr(expected, "text"):
            expected = cast(HasText, expected).text
        text = self.get_tooltip_text(element, sleep=sleep, click_away=click_away)
        assert text == expected, f"Tooltip text [{text}] was not expected text [{expected}]."

    def assert_tooltip_text_contains(
        self, element, expected: Union[str, HasText], sleep: int = 0, click_away: bool = True
    ):
        if hasattr(expected, "text"):
            expected = cast(HasText, expected).text
        text = self.get_tooltip_text(element, sleep=sleep, click_away=click_away)
        assert expected in text, f"Tooltip text [{text}] was not expected text [{expected}]."

    def assert_error_message(self, contains=None):
        self.components._.messages.error.wait_for_visible()
        elements = self.find_elements(self.components._.messages.selectors.error)
        return self.assert_message(elements, contains=contains)

    def assert_warning_message(self, contains=None):
        element = self.components._.messages["warning"]
        return self.assert_message(element, contains=contains)

    def assert_success_message(self, contains=None):
        element = self.components._.messages["done"]
        return self.assert_message(element, contains=contains)

    def assert_message(self, element, contains=None):
        if contains is not None:
            if isinstance(element, list):
                assert any(
                    contains in el.text for el in element
                ), f"{contains} was not found in {[el.text for el in element]}"
                return

            element = element.wait_for_visible()
            text = element.text
            if contains not in text:
                message = f"Text [{contains}] expected inside of [{text}] but not found."
                raise AssertionError(message)

    def assert_no_error_message(self):
        self.components._.messages.error.assert_absent_or_hidden()

    def run_tour_step(self, step, step_index: int, tour_callback):
        element_str = step.get("element", None)
        if element_str is None:
            component = step.get("component", None)
            if component is not None:
                element_str = self.components.resolve_component_locator(component).locator

        preclick = step.get("preclick", [])
        if preclick is True:
            preclick = [element_str]

        for preclick_selector in preclick:
            print(f"(Pre)Clicking {preclick_selector}")
            self._tour_wait_for_and_click_element(preclick_selector)

        if element_str is not None:
            print(f"Waiting for element {element_str}")
            element = self.tour_wait_for_element_present(element_str)
            assert element is not None

        if (textinsert := step.get("textinsert", None)) is not None:
            element.send_keys(textinsert)

        tour_callback.handle_step(step, step_index)

        postclick = step.get("postclick", [])
        if postclick is True:
            postclick = [element_str]
        for postclick_selector in postclick:
            print(f"(Post)Clicking {postclick_selector}")
            self._tour_wait_for_and_click_element(postclick_selector)

    @retry_during_transitions
    def _tour_wait_for_and_click_element(self, selector):
        element = self.tour_wait_for_clickable_element(selector)
        self.driver.execute_script("arguments[0].click();", element)

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

    def set_history_annotation(self, annotation, clear_text=False):
        toggle = self.history_element("editor toggle")
        toggle.wait_for_and_click()
        annotation_input = self.history_element("annotation input").wait_for_visible()
        if clear_text:
            annotation_input.clear()
        annotation_input.send_keys(annotation)
        self.history_click_editor_save()

    def ensure_history_annotation_area_displayed(self):
        annotation_area = self.components.history_panel.annotation_area
        annotation_icon = self.components.history_panel.annotation_icon

        if annotation_area.is_absent or not annotation_area.is_displayed:
            annotation_icon.wait_for_and_click()

    def select_set_value(self, container_selector_or_elem, value, multiple=False):
        if hasattr(container_selector_or_elem, "selector"):
            container_selector_or_elem = container_selector_or_elem.selector
        if not hasattr(container_selector_or_elem, "find_element"):
            container_elem = self.wait_for_selector(container_selector_or_elem)
        else:
            container_elem = container_selector_or_elem
        container_elem.click()
        try:
            text_input = container_elem.find_element(By.CSS_SELECTOR, "input[class='multiselect__input']")
        except Exception:
            text_input = None
        if text_input:
            text_input.send_keys(value)
            self.send_enter(text_input)
            if multiple:
                self.send_escape(text_input)
        else:
            self.sleep_for(WAIT_TYPES.UX_RENDER)
            elems = container_elem.find_elements(By.CSS_SELECTOR, "[role='option'] .multiselect__option span")
            discovered_options = []
            found = False
            for elem in elems:
                elem_value = elem.text
                discovered_options.append(elem_value)
                if elem_value == value:
                    elem.click()
                    found = True
            assert found, f"Failed to find specified select value [{value}] in browser options [{discovered_options}]"

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
        if not hasattr(container_selector_or_elem, "find_element"):
            container_elem = self.wait_for_selector(container_selector_or_elem)
        else:
            container_elem = container_selector_or_elem

        text_element = container_elem.find_element(By.CSS_SELECTOR, "input[type='text']")
        if clear_value:
            self.send_backspace(text_element)
            self.send_backspace(text_element)
        text_element.send_keys(value)
        # Wait for select2 options to load and then click to add this one.
        drop_elem = self.wait_for_selector_visible("#select2-drop")
        # Sleep seems to be needed - at least for send_enter.
        time.sleep(0.5)
        if not with_click:
            # Wait for select2 options to load and then click to add this one.
            self.send_enter(text_element)
        else:
            candidate_elements = drop_elem.find_elements(By.CSS_SELECTOR, ".select2-result-label")
            # try to find exact match
            for elem in candidate_elements:
                if elem.text == value:
                    select_elem = elem
                    break
            else:
                # Pick first match. We're replacing select2 anyway ...
                select_elem = candidate_elements[0]
            action_chains = self.action_chains()
            action_chains.move_to_element(select_elem).click().perform()
        self.wait_for_selector_absent_or_hidden("#select2-drop")

    def snapshot(self, description):
        """Test case subclass overrides this to provide detailed logging."""

    def open_history_editor(self, scope=".history-index"):
        panel = self.components.history_panel.editor.selector(scope=scope)
        if panel.name_input.is_absent:
            toggle = panel.toggle
            toggle.wait_for_and_click()
            editor = panel.form
            editor.wait_for_present()

    def close_history_editor(self, scope=".history-index"):
        toggle = self.components.history_panel.edit_toggle
        toggle.wait_for_and_click()
        editor = self.components.history_panel.editor.selector(scope=scope)
        self.assert_absent_or_hidden(editor)

    def share_ensure_by_user_available(self, sharing_component):
        sharing_component.share_with_multiselect.wait_for_visible()

    def share_unshare_with_user(self, sharing_component, email):
        self.share_ensure_by_user_available(sharing_component)
        unshare_user_button = self.components.histories.sharing.unshare_with_user_button(email=email)
        unshare_user_button.wait_for_and_click()
        self.components.histories.sharing.submit_sharing_with.wait_for_and_click()
        unshare_user_button.wait_for_absent_or_hidden()

    def share_with_user(
        self,
        sharing_component,
        user_id=None,
        user_email=None,
        screenshot_before_submit=None,
        screenshot_after_submit=None,
        assert_valid=False,
    ):
        self.share_ensure_by_user_available(sharing_component)
        multiselect = sharing_component.share_with_multiselect.wait_for_and_click()
        sharing_component.share_with_input.wait_for_and_send_keys(user_id or user_email)
        self.send_enter(multiselect)

        self.screenshot_if(screenshot_before_submit)
        sharing_component.submit_sharing_with.wait_for_and_click()

        if assert_valid:
            self.assert_no_error_message()

            xpath = f'//span[contains(text(), "{user_email}")]'
            self.wait_for_xpath_visible(xpath)
        self.screenshot_if(screenshot_after_submit)

    def create_file_source_template(self, instance: FileSourceInstance) -> str:
        self.navigate_to_user_preferences()
        template_id = instance.template_id
        preferences = self.components.preferences
        preferences.manage_file_sources.wait_for_and_click()
        file_source_instances = self.components.file_source_instances
        file_source_instances.index.create_button.wait_for_and_click()

        select_template = file_source_instances.create.select(template_id=template_id)
        select_template.wait_for_present()
        self.screenshot(f"user_file_source_select_{template_id}")
        select_template.wait_for_and_click()

        file_source_instances.create._.wait_for_present()
        self.screenshot(f"user_file_source_form_empty_{template_id}")
        self._fill_configuration_template(instance.name, instance.description, instance.parameters)
        self.screenshot(f"user_file_source_form_full_{template_id}")
        file_source_instances.create.submit.wait_for_and_click()

        file_source_instances = self.components.file_source_instances
        file_source_instances.index._.wait_for_present()
        self.screenshot(f"user_file_source_created_{template_id}")
        instances = self.api_get("file_source_instances")
        newest_instance = instances[-1]
        uri_root = newest_instance["uri_root"]
        return uri_root

    def create_object_store_template(self, instance: ObjectStoreInstance) -> str:
        self.navigate_to_user_preferences()
        template_id = instance.template_id
        preferences = self.components.preferences
        preferences.manage_object_stores.wait_for_and_click()
        object_store_instances = self.components.object_store_instances
        object_store_instances.index.create_button.wait_for_and_click()

        select_template = object_store_instances.create.select(template_id=template_id)
        select_template.wait_for_present()
        self.screenshot(f"user_object_store_select_{template_id}")
        select_template.wait_for_and_click()

        object_store_instances.create._.wait_for_present()
        self.screenshot(f"user_object_store_form_empty_{template_id}")
        self._fill_configuration_template(instance.name, instance.description, instance.parameters)
        self.screenshot(f"user_object_store_form_full_{template_id}")
        object_store_instances.create.submit.wait_for_and_click()
        object_store_instances.index._.wait_for_present()
        self.screenshot(f"user_object_store_created_{template_id}")
        instances = self.api_get("object_store_instances")
        newest_instance = instances[-1]
        object_store_id = newest_instance["object_store_id"]
        return object_store_id

    def _fill_configuration_template(
        self, name: str, description: Optional[str], parameters: List[ConfigTemplateParameter]
    ):
        self.components.tool_form.parameter_input(parameter="_meta_name").wait_for_and_send_keys(
            name,
        )
        if description:
            self.components.tool_form.parameter_input(parameter="_meta_description").wait_for_and_send_keys(
                description,
            )

        for parameter in parameters:
            form_type = parameter.form_element_type
            if form_type in ["integer", "string"]:
                self.components.tool_form.parameter_input(parameter=parameter.name).wait_for_and_send_keys(
                    str(parameter.value),
                )
            else:
                raise NotImplementedError("Configuration templates of type {form_type} not yet implemented")

    def tutorial_mode_activate(self):
        search_selector = "#gtn a"
        self.wait_for_and_click_selector(search_selector)
        self.wait_for_selector_visible("#gtn-screen")

    def mouse_drag(
        self,
        from_element: WebElement,
        to_element: Optional[WebElement] = None,
        from_offset=(0, 0),
        to_offset=(0, 0),
        via_offsets: Optional[List[Tuple[int, int]]] = None,
    ):
        chain = self.action_chains().move_to_element(from_element).move_by_offset(*from_offset)
        chain = chain.click_and_hold().pause(self.wait_length(self.wait_types.UX_RENDER))

        if via_offsets is not None:
            for offset in via_offsets:
                chain = chain.move_by_offset(*offset).pause(self.wait_length(self.wait_types.UX_RENDER))

        if to_element is not None:
            chain = chain.move_to_element(to_element)

        chain = chain.move_by_offset(*to_offset).pause(self.wait_length(self.wait_types.UX_RENDER)).release()
        chain.perform()


class NotLoggedInException(SeleniumTimeoutException):
    def __init__(self, timeout_exception, user_info, dom_message):
        template = "Waiting for UI to reflect user logged in but it did not occur. API indicates no user is currently logged in. %s API response was [%s]. %s"
        msg = template % (dom_message, user_info, timeout_exception.msg)
        super().__init__(msg=msg, screen=timeout_exception.screen, stacktrace=timeout_exception.stacktrace)


class ClientBuildException(SeleniumTimeoutException):
    def __init__(self, timeout_exception: SeleniumTimeoutException):
        msg = f"Error waiting for Galaxy masthead to appear, this frequently means there is a problem with the client build and the Galaxy client is broken. {timeout_exception.msg}"
        super().__init__(msg=msg, screen=timeout_exception.screen, stacktrace=timeout_exception.stacktrace)
