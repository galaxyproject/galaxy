"""Selenium tests for custom tool creation and management."""

import platform

from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains

from .framework import (
    selenium_test,
    SeleniumTestCase,
)


class TestCustomTools(SeleniumTestCase):
    ensure_registered = True

    def assert_baseline_accessibility(self):
        """Skip accessibility checks for custom tools tests due to Monaco editor issues."""
        pass

    @selenium_test
    def test_create_custom_tool(self):
        """Test creating a new custom tool through the UI."""
        with self.dataset_populator.user_tool_execute_permissions():
            self.home()
            # Navigate via Custom Tools activity panel
            self.components.custom_tools.activity.wait_for_and_click()
            # Use the component selector for the create button
            self.components.custom_tools.create_button.wait_for_and_click()
            # Wait for the Tool Editor heading to appear
            self.wait_for_selector_visible("h1")
            self.wait_for_selector_visible(".monaco-editor")
            self.paste_tool()
            # Save the tool and verify it actually saved
            save_button = self.wait_for_selector_visible("button.btn.btn-primary")
            # Record the initial URL to detect changes
            initial_url = self.driver.current_url
            save_button.click()
            # Wait for save operation to complete
            self.sleep_for(self.wait_types.UX_TRANSITION)
            # Verify save was successful
            current_url = self.driver.current_url
            # Method 1: URL changed to include UUID
            assert current_url != initial_url and "/tools/editor/" in current_url

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
        tool_yaml_three = (
            """
outputs:
- name: output1
  type: data
format_source: datasets
from_work_dir: output.txt
"""
            ""
        )
        # Try finding Monaco editor textarea and replace skeleton content
        self.sleep_for(self.wait_types.UX_RENDER)  # Allow editor to focus
        editor = self.wait_for_selector_visible(".monaco-editor div.view-line")

        # Focus the editor first
        editor.click()
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
