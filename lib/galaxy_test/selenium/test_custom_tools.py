"""Selenium tests for custom tool creation and management."""

import platform

from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys

from galaxy.tool_util_models import UserToolSource
from .framework import (
    playwright_only,
    selenium_only,
    selenium_test,
    SeleniumTestCase,
)
from .upload_activity_helpers import UsesUploadActivity


class TestCustomTools(SeleniumTestCase, UsesUploadActivity):
    ensure_registered = True

    def assert_baseline_accessibility(self):
        """Skip accessibility checks for custom tools tests due to Monaco editor issues."""
        pass

    @selenium_only("Not yet migrated to support Playwright backend")
    @selenium_test
    def test_create_custom_tool(self):
        """Test creating a new custom tool through the UI."""
        with self.dataset_populator.user_tool_execute_permissions():
            tool_uuid = self.create_new_custom_tool()
            assert tool_uuid, "Tool UUID should be returned after saving."
            self.components.custom_tools.tool_link(tool_uuid=tool_uuid).wait_for_clickable()

    @selenium_only("Not yet migrated to support Playwright backend")
    @selenium_test
    def test_run_custom_tool(self):
        test_path = self.get_filename("1.fasta")
        self.upload_context("local-file").stage_local_file(test_path).start()
        self.history_panel_wait_for_hid_ok(1)
        with self.dataset_populator.user_tool_execute_permissions():
            tool_uuid = self.create_new_custom_tool()
            assert tool_uuid, "Tool UUID should be returned after saving."
            self.components.custom_tools.tool_link(tool_uuid=tool_uuid).wait_for_and_click()
            self.sleep_for(self.wait_types.UX_RENDER)
            self.components.tool_form.execute.wait_for_and_click()
            self.history_panel_wait_for_hid_ok(2)
            self.hda_click_primary_action_button(2, "rerun")
            self.components.tool_form.execute.wait_for_and_click()
            self.history_panel_wait_for_hid_ok(3)

    @playwright_only("Validates the custom-tool editor workflow with Playwright dialogs and console events.")
    @selenium_test
    def test_new_tool_editor_defaults_and_clear(self):
        console_errors = []
        self.page.on(
            "console", lambda message: console_errors.append(message.text) if message.type == "error" else None
        )

        with self.dataset_populator.user_tool_execute_permissions():
            self.home()
            self.open_tool_editor()

            new_tool_source = self.editor_source()
            assert "class: GalaxyUserTool" in new_tool_source
            assert "name: Remove Comment Lines" in new_tool_source
            assert "from_work_dir: output.txt" in new_tool_source

            self.page.once("dialog", lambda dialog: dialog.dismiss())
            self.components.custom_tools.clear_button.wait_for_and_click()
            assert self.editor_source() == new_tool_source

            self.page.once("dialog", lambda dialog: dialog.accept())
            self.components.custom_tools.clear_button.wait_for_and_click()
            expected_skeleton = """class: GalaxyUserTool
name:
version: "0.1.0"
container:
shell_command:
inputs: []
outputs: []"""
            self._wait_on(
                lambda: self.editor_source() == expected_skeleton,
                "the custom-tool editor to contain the clear-tool skeleton",
            )

            stored_tool = UserToolSource(
                **{
                    "class": "GalaxyUserTool",
                    "id": "stored_editor_tool",
                    "name": "Stored Editor Tool",
                    "version": "2.0.0",
                    "container": "busybox",
                    "shell_command": "echo stored > output.txt",
                    "outputs": [{"name": "output", "type": "data", "from_work_dir": "output.txt"}],
                }
            )
            stored_tool_uuid = self.dataset_populator.create_unprivileged_tool(stored_tool)["uuid"]
            self.get(f"tools/editor/{stored_tool_uuid}")
            self.wait_for_selector_visible(".monaco-editor")
            self._wait_on(
                lambda: "name: Stored Editor Tool" in self.editor_source(),
                "the custom-tool editor to load the stored tool",
            )
            existing_tool_source = self.editor_source()
            assert "version: 2.0.0" in existing_tool_source
            assert "Remove Comment Lines" not in existing_tool_source

        uninitialized_confirm_error = "Confirm dialog component reference not set"
        assert not any(uninitialized_confirm_error in error for error in console_errors), console_errors

    def create_new_custom_tool(self) -> str:
        self.home()
        self.open_tool_editor()
        self.paste_tool()
        return self.save_tool()

    def open_tool_editor(self):
        # Navigate via Custom Tools activity panel
        self.components.custom_tools.activity.wait_for_and_click()
        # Use the component selector for the create button
        self.components.custom_tools.create_button.wait_for_and_click()
        # Wait for the Tool Editor heading to appear
        self.wait_for_selector_visible("h1")
        self.wait_for_selector_visible(".monaco-editor")

    def editor_source(self) -> str:
        source = self.page.locator(".monaco-editor .view-lines").inner_text()
        return source.replace("\N{NO-BREAK SPACE}", " ").strip()

    def save_tool(self) -> str:
        self.components.custom_tools.save_button.wait_for_and_click()
        # Wait for save operation to complete
        self.sleep_for(self.wait_types.UX_TRANSITION)
        # Verify save was successful
        current_url = self.driver.current_url
        return current_url.split("/tools/editor/")[1]

    def paste_tool(self):
        # Define a simple custom tool YAML
        tool_yaml_one = """class: GalaxyUserTool
id: test_cat_tool
name: Test Cat Tool
version: "0.1"
description: Concatenate test files
container: busybox
shell_command: |
  cat $(inputs.datasets.map((input) => input.path).join(' ')) > output.txt

"""

        tool_yaml_two = """
inputs:
- name: datasets
  multiple: true
type: data

"""
        tool_yaml_three = """
outputs:
- name: output1
  type: data
format_source: datasets
from_work_dir: output.txt
"""
        # Try finding Monaco editor and replace skeleton content
        self.sleep_for(self.wait_types.UX_RENDER)  # Allow editor to initialize
        # Use the stable .monaco-editor container, not .view-line which gets re-rendered
        editor_container = self.wait_for_selector_visible(".monaco-editor")

        # Focus the editor by clicking on the stable container
        editor_container.click()
        self.sleep_for(self.wait_types.UX_RENDER)  # Allow editor to focus

        is_mac = platform.system() == "Darwin"
        modifier_key = Keys.COMMAND if is_mac else Keys.CONTROL

        action_chains = ActionChains(self.driver)

        # Select all content
        action_chains.key_down(modifier_key)
        action_chains.send_keys("a")
        action_chains.key_up(modifier_key)
        action_chains.perform()

        # Delete selected content
        action_chains = ActionChains(self.driver)
        action_chains.send_keys(Keys.DELETE)
        action_chains.perform()

        # Now insert the new content
        # yaml is split in funky was to accomodate guided yaml text input in monaco
        action_chains = ActionChains(self.driver)
        action_chains.send_keys(tool_yaml_one)
        action_chains.send_keys(Keys.BACKSPACE)
        action_chains.send_keys(tool_yaml_two)
        action_chains.send_keys(Keys.BACKSPACE)
        action_chains.send_keys(tool_yaml_three)
        action_chains.perform()
