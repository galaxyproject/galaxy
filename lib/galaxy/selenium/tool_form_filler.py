"""Fill an open tool form by parameter path, under Selenium or Playwright."""

from typing import (
    Any,
    TYPE_CHECKING,
)

from selenium.common.exceptions import NoSuchElementException

from .has_driver import (
    exception_indicates_playwright_timeout,
    SeleniumTimeoutException,
)
from .tool_form import repeat_instance_counts
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

    def fill(self, values: dict[str, Any] | None = None, data: dict[str, int | str] | None = None) -> None:
        """Fill the open tool form by parameter path, such as ``cond|param`` or ``repeat_0|param``.

        ``values`` sets non-data parameters, detecting each one's widget. ``data`` selects a dataset or
        collection per parameter, by hid or by option label such as ``"3: reads.fq"``. Adds the repeat
        instances the paths need, expands sections, and retries parameters a conditional reveals late.
        """
        values = values or {}
        data = data or {}
        if not values and not data:
            return

        for repeat_name, count in repeat_instance_counts([*values, *data]).items():
            self._add_repeat_instances(repeat_name, count)

        self._expand_collapsed_sections()

        # Shallow parameters first, so conditionals reveal the nested ones; retry what wasn't there yet.
        deferred = []
        for key, value in sorted(values.items(), key=lambda kv: kv[0].count("|")):
            try:
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
                if self._navigator.components.tool_form.parameter_div(parameter=key).is_absent:
                    continue
                self.set_parameter(key, value)

        collection_hids = None
        for key, value in data.items():
            label = f"{value}: " if isinstance(value, int) else value
            if isinstance(value, int):
                if collection_hids is None:
                    collection_hids = {
                        item["hid"]
                        for item in self._navigator.history_contents()
                        if item["history_content_type"] == "dataset_collection"
                    }
                # A dataset field lists collections only in its collection (map over) mode.
                collection_mode = self._navigator.components.tool_form.parameter_data_input_collection(parameter=key)
                if value in collection_hids and not collection_mode.is_absent:
                    button = collection_mode.wait_for_visible()
                    button.click()
                    # Wait on the button itself: its tooltip blanks the title the target matches on.
                    self._navigator._wait_on(
                        lambda button=button: _button_is_pressed(button),
                        f"collection mode for {key}",
                        wait_type=self._navigator.wait_types.UX_RENDER,
                    )
            is_multiple = self._is_multi_data_param(key)
            if is_multiple:
                self._clear_multiselect_tags(key)
            self._navigator.tool_set_value(key, label, expected_type="data", multiple=is_multiple)
            if isinstance(value, int):
                self._assert_data_selected(key, label)

    def _assert_data_selected(self, expanded_id: str, label: str) -> None:
        tool_form = self._navigator.components.tool_form
        tool_form.parameter_data_select(parameter=expanded_id).wait_for_visible()
        selected = [e.text for e in tool_form.parameter_data_selected(parameter=expanded_id).all()]
        assert any(text.startswith(label) for text in selected), f"{expanded_id} shows {selected}, not hid {label}"

    def _is_multi_data_param(self, expanded_id: str) -> bool:
        return not self._navigator.components.tool_form.parameter_form_selection(parameter=expanded_id).is_absent

    def _clear_multiselect_tags(self, expanded_id: str) -> None:
        tag_close = self._navigator.components.tool_form.parameter_multiselect_tag_close(parameter=expanded_id)
        for _ in range(20):
            close_buttons = tag_close.all()
            if not close_buttons:
                break
            close_buttons[0].click()
            remaining = len(close_buttons) - 1
            self._navigator._wait_on(
                lambda remaining=remaining: len(tag_close.all()) <= remaining,
                f"tag removed from {expanded_id}",
                wait_type=self._navigator.wait_types.UX_RENDER,
            )

    def _add_repeat_instances(self, repeat_name: str, count: int) -> None:
        """Make sure ``count`` instances exist; a repeat with a minimum already renders some."""
        tool_form = self._navigator.components.tool_form
        insert = tool_form.repeat_insert_named(name=repeat_name)
        insert.wait_for_visible()
        existing = 0
        while tool_form.repeat_instance_parameter(name=repeat_name, index=existing).all():
            existing += 1
        for index in range(existing, count):
            insert.wait_for_and_click()
            tool_form.repeat_instance_parameter(name=repeat_name, index=index).wait_for_present()

    def _expand_collapsed_sections(self) -> None:
        # The header, not the execute button: a workflow editor step's tool form has no execute button.
        self._navigator.components.tool_form.tool_version.wait_for_visible()
        for header in self._navigator.components.tool_form.section_header.all():
            header.click()
            # Expanding a section has no per-section target to wait on.
            self._navigator.sleep_for(self._navigator.wait_types.UX_RENDER)

    def set_parameter(self, expanded_parameter_id: str, value: Any) -> None:
        """Set a non-data parameter of the open tool form by path, detecting its widget type."""
        if isinstance(value, list) and len(value) == 1:
            value = value[0]
        self._navigator.form_element_set_value(expanded_parameter_id, value)
