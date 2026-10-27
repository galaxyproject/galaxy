"""Fill an open tool form by parameter path, under Selenium or Playwright."""

from collections.abc import Callable
from functools import cached_property
from typing import (
    Any,
    TYPE_CHECKING,
)

from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By

from .has_driver import (
    exception_indicates_playwright_timeout,
    SeleniumTimeoutException,
)
from .smart_components import SmartTarget
from .tool_form import repeat_instance_candidates
from .web_element_protocol import WebElementProtocol

if TYPE_CHECKING:
    from .navigates_galaxy import NavigatesGalaxy


def _exception_indicates_parameter_not_shown(e: Exception) -> bool:
    """True if setting a tool form parameter failed because the form doesn't show it (yet), on either backend."""
    return isinstance(e, (NoSuchElementException, SeleniumTimeoutException, AssertionError)) or (
        exception_indicates_playwright_timeout(e)
    )


def _button_is_pressed(button: WebElementProtocol) -> bool:
    """True if a toggle button shows as pressed: g-pressed on GButton, active on older servers' BButton."""
    return bool({"g-pressed", "active"} & set((button.get_attribute("class") or "").split()))


class ToolFormFiller:
    """Sets the open tool form's fields by the paths ``tool_form_parameters`` lists."""

    def __init__(self, navigator: "NavigatesGalaxy"):
        self._navigator = navigator
        self._tool_form = navigator.components.tool_form

    def fill(self, values: dict[str, Any] | None = None, data: dict[str, int | str] | None = None) -> None:
        """See ``NavigatesGalaxy.tool_form_fill``."""
        values = values or {}
        data = data or {}
        if not values and not data:
            return
        # The header, not the execute button: a workflow editor step's tool form has no execute button.
        self._tool_form.tool_version.wait_for_visible()

        # Shallow parameters first, so conditionals reveal the nested ones; retry what wasn't there yet.
        deferred = []
        for key, value in sorted(values.items(), key=lambda kv: kv[0].count("|")):
            try:
                self._prepare_parameter(key)
                self.set_parameter(key, value)
                # Nothing signals which parameters a change reveals, so give conditionals time to render.
                self._navigator.sleep_for(self._navigator.wait_types.UX_RENDER)
            except Exception as e:
                if not _exception_indicates_parameter_not_shown(e):
                    raise
                deferred.append((key, value))

        if deferred:
            # Parameters that never appear are skipped, so there is no element to wait for here.
            self._navigator.sleep_for(self._navigator.wait_types.UX_RENDER)
            for key, value in deferred:
                self._prepare_parameter(key)
                if self._tool_form.parameter_div(parameter=key).is_absent:
                    continue
                self.set_parameter(key, value)

        for key, value in data.items():
            self._prepare_parameter(key)
            if isinstance(value, int) or value.isdecimal():
                self._select_data_by_hid(key, int(value))
            else:
                self._select_data(key, value)

    def _select_data_by_hid(self, path: str, hid: int) -> None:
        label = f"{hid}: "
        if hid in self._collection_hids:
            self.enter_collection_mode(path)
        multiple = not self._tool_form.parameter_form_selection(parameter=path).is_absent
        if multiple:
            self._clear_multiselect_tags(path)
        select = self._tool_form.parameter_data_select(parameter=path).wait_for_visible()
        trigger = select.find_element(By.CSS_SELECTOR, ".multiselect__select")
        self._navigator.scroll_into_view(trigger)
        trigger.click()
        search = select.find_element(By.CSS_SELECTOR, "input.multiselect__input")
        search.clear()
        # An all-digit query lets the server find hids outside the first options page.
        search.send_keys(str(hid))
        # Older clients don't rank exact hids first: 13 can appear before 3. Never use Enter here.
        self._tool_form.parameter_data_option_by_hid(parameter=path, hid=hid).wait_for_and_click()
        if multiple:
            self._navigator.send_escape(search)
        self._tool_form.parameter_data_select(parameter=path).wait_for_visible()
        selected = [e.text for e in self._tool_form.parameter_data_selected(parameter=path).all()]
        assert any(text.startswith(label) for text in selected), f"{path} shows {selected}, not hid {hid}"

    def _select_data(self, path: str, label: str) -> None:
        multiple = not self._tool_form.parameter_form_selection(parameter=path).is_absent
        if multiple:
            self._clear_multiselect_tags(path)
        self._navigator.tool_set_value(path, label, expected_type="data", multiple=multiple)

    @cached_property
    def _collection_hids(self) -> set[int]:
        return {
            item["hid"]
            for item in self._navigator.history_contents()
            if item["history_content_type"] == "dataset_collection"
        }

    def enter_collection_mode(self, path: str) -> None:
        # A dataset field lists collections only in its collection (map over) mode.
        collection_mode = self._tool_form.parameter_data_input_collection(parameter=path)
        if collection_mode.is_absent:
            return
        button = collection_mode.wait_for_visible()
        button.click()
        # Wait on the button itself: its tooltip blanks the title the target matches on.
        self._wait_until(lambda: _button_is_pressed(button), f"collection mode for {path}")

    def _clear_multiselect_tags(self, path: str) -> None:
        tag_close = self._tool_form.parameter_multiselect_tag_close(parameter=path)
        for _ in range(20):
            close_buttons = tag_close.all()
            if not close_buttons:
                break
            close_buttons[0].click()
            remaining = len(close_buttons) - 1
            self._wait_until(lambda remaining=remaining: len(tag_close.all()) <= remaining, f"tag removed from {path}")

    def _prepare_parameter(self, path: str) -> None:
        """Expand collapsed sections and add the repeat instances ``path`` needs, outer repeats first."""
        self._expand_collapsed_sections()
        if not self._tool_form.parameter_div(parameter=path).is_absent:
            return
        scope = None
        for repeat_path, index in repeat_instance_candidates(path):
            if self._add_repeat_instances(repeat_path, index, scope):
                scope = f"{repeat_path}_{index}"

    def _add_repeat_instances(self, repeat_path: str, index: int, scope: str | None) -> bool:
        """Add instances of ``repeat_path`` through ``index``, False if ``scope`` shows no such repeat.

        It shows none for a conditional or section named like ``opts_1``, or for a repeat in a conditional case
        not selected yet; setting the parameter then fails, which defers it until the conditional is set.
        """
        count = self._repeat_instance_count(repeat_path)
        if count > index:
            return True
        name = repeat_path.rsplit("|", 1)[-1]
        if scope is None:
            insert = self._tool_form.repeat_insert_top_level(name=name)
        else:
            insert = self._tool_form.repeat_insert_in_instance(instance=scope, name=name)
        if not (buttons := insert.all()):
            return False
        # Same-named repeats in sibling sections or conditionals share a scope; don't guess between them.
        if len(buttons) > 1:
            raise ValueError(f"{len(buttons)} repeat insert buttons match {repeat_path}")
        for n in range(count, index + 1):
            insert.wait_for_and_click()
            self._tool_form.repeat_instance(instance=f"{repeat_path}_{n}").wait_for_present()
        # New instances can hold collapsed sections around the next repeat.
        self._expand_collapsed_sections()
        return True

    def _repeat_instance_count(self, repeat_path: str) -> int:
        count = 0
        while not self._tool_form.repeat_instance(instance=f"{repeat_path}_{count}").is_absent:
            count += 1
        return count

    def _expand_collapsed_sections(self) -> None:
        # Expanding one section can reveal collapsed sections nested in it.
        for _ in range(100):
            if not (headers := self._tool_form.section_header_collapsed.all()):
                return
            content = headers[0].find_element(By.XPATH, self._tool_form.section_header_content.selector)
            headers[0].click()
            self._wait_until(
                lambda content=content: "display: none" not in (content.get_attribute("style") or ""),
                "tool form section expanded",
            )
        # Not an AssertionError, which would read as a parameter not shown yet and defer it.
        raise RuntimeError("tool form sections still collapsed after 100 clicks")

    def _wait_until(self, condition: Callable[..., Any], message: str) -> None:
        self._navigator._wait_on(condition, message, wait_type=self._navigator.wait_types.UX_RENDER)

    def _detect_param_type(self, path: str) -> str:
        """Inspect DOM to determine param type.

        Detection order matters:
        - drilldown before checkbox_select (drilldown also has checkboxes)
        - checkbox_select before boolean (both have input[type='checkbox'])
        """
        tf = self._tool_form

        param_div = tf.parameter_div(parameter=path).wait_for_visible()
        if param_div.find_elements(By.CSS_SELECTOR, tf.drilldown_option.selector):
            return "drilldown"

        checkboxes = tf.parameter_checkbox_input(parameter=path).all()
        if len(checkboxes) > 1:
            return "checkbox_select"
        if checkboxes:
            return "boolean"

        if not tf.parameter_color_input(parameter=path).is_absent:
            return "color"
        if not tf.parameter_select(parameter=path).is_absent:
            return "select"

        return "text"

    def set_parameter(self, path: str, value: Any) -> None:
        """See ``NavigatesGalaxy.tool_form_set_parameter``."""
        if isinstance(value, list) and len(value) == 1:
            value = value[0]

        param_type = self._detect_param_type(path)

        if param_type == "drilldown":
            values = value if isinstance(value, list) else [value]
            self._set_drilldown_value(path, values)
        elif param_type == "checkbox_select":
            values = value if isinstance(value, list) else [value]
            self._set_checkbox_select_value(path, values)
        elif param_type == "boolean":
            self._set_boolean_value(path, value)
        elif param_type == "color":
            self._set_element_value(self._tool_form.parameter_color_input(parameter=path), value)
        elif param_type == "select":
            self._navigator.tool_set_value(path, str(value), expected_type="select")
        else:
            self._set_element_value(self._tool_form.parameter_text_input(parameter=path), str(value))

    def _set_boolean_value(self, path: str, value: Any) -> None:
        checkbox = self._tool_form.parameter_checkbox_input(parameter=path).wait_for_present()
        want_checked = str(value).lower() in ("true", "1", "yes")
        if checkbox.is_selected() != want_checked:
            self._navigator.execute_script("arguments[0].click();", checkbox)

    def _set_checkbox_select_value(self, path: str, values: list[Any]) -> None:
        all_checkboxes = self._tool_form.parameter_checkbox_input(parameter=path).all()
        for val in values:
            matched = [cb for cb in all_checkboxes if cb.get_attribute("value") == val]
            assert matched, f"No checkbox with value '{val}' in param {path}"
            if not matched[0].is_selected():
                self._navigator.execute_script("arguments[0].click();", matched[0])

    def _set_drilldown_value(self, path: str, values: list[Any]) -> None:
        """Set drill-down param by clicking option checkboxes.

        TODO: DOM id is ``drilldown-option-{option.name}`` but test API returns
        option *values*. Works only when name == value. If a tool has
        ``<option name="Label" value="key">``, the lookup will fail.
        Fixing requires changing FormDrilldownOption.vue (breaks library export)
        or adding a value->name mapping step here.
        """
        for val in values:
            checkbox = self._tool_form.parameter_drilldown_option(parameter=path, value=val).wait_for_present()
            if not checkbox.is_selected():
                self._navigator.execute_script("arguments[0].click();", checkbox)

    def _set_element_value(self, target: SmartTarget, value: str) -> None:
        self._navigator.set_element_value(target.wait_for_present(), value)
