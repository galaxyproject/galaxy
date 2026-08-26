"""Selenium tests for custom tool creation and management."""

import platform

from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys

from .framework import (
    selenium_only,
    selenium_test,
    SeleniumTestCase,
)


class TestCustomTools(SeleniumTestCase):
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
        self.perform_upload(test_path, on_current_page=True)
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

    @selenium_test
    def test_authoring_documentation_interactions(self):
        if self.backend_type == "playwright":
            self.page.set_viewport_size({"width": 1600, "height": 1000})
        else:
            self.driver.set_window_size(1600, 1000)
        with self.dataset_populator.user_tool_execute_permissions():
            self.home()
            self.open_tool_editor()
            custom_tools = self.components.custom_tools

            editor_source = custom_tools.editor_content.wait_for_text().replace("\N{NO-BREAK SPACE}", " ")
            assert "class: GalaxyUserTool" in editor_source
            assert "name: Remove Comment Lines" in editor_source
            assert "from_work_dir: output.txt" in editor_source

            with self.accept_alert():
                custom_tools.clear_button.wait_for_and_click()
            self.sleep_for(self.wait_types.UX_RENDER)
            cleared_source = custom_tools.editor_content.wait_for_text().replace("\N{NO-BREAK SPACE}", " ")
            assert "class: GalaxyUserTool" in cleared_source
            assert 'version: "0.1.0"' in cleared_source
            assert "inputs: []" in cleared_source
            assert "outputs: []" in cleared_source
            assert "Remove Comment Lines" not in cleared_source

            documentation_button = custom_tools.documentation_button.wait_for_visible()
            assert documentation_button.get_attribute("aria-expanded") == "false"
            custom_tools.documentation_button.wait_for_and_click()

            custom_tools.documentation_panel.wait_for_visible()
            custom_tools.documentation_content.wait_for_visible()
            custom_tools.editor_pane.wait_for_visible()
            assert documentation_button.get_attribute("aria-expanded") == "true"
            self.screenshot("custom_tool_documentation_split")

            custom_tools.documentation_expand_button.wait_for_and_click()
            custom_tools.editor_pane.wait_for_absent_or_hidden()
            custom_tools.documentation_content.wait_for_visible()

            custom_tools.help_section_toggle(section_id="quick-start").wait_for_and_click()
            custom_tools.example(section_id="quick-start").wait_for_visible()
            assert custom_tools.example_label(section_id="quick-start").wait_for_text() == "Example"

            self.execute_script("""
                window.__authoringHelpCopiedText = null;
                Object.defineProperty(navigator, "clipboard", {
                    configurable: true,
                    value: {
                        writeText: (text) => {
                            window.__authoringHelpCopiedText = text;
                            return Promise.resolve();
                        },
                    },
                });
                """)
            custom_tools.example_copy_button(section_id="quick-start").wait_for_and_click()
            self.sleep_for(self.wait_types.UX_RENDER)
            copied_example = self.execute_script("return window.__authoringHelpCopiedText;")
            assert copied_example.startswith("class: GalaxyUserTool")
            self.screenshot("custom_tool_documentation_example")

            custom_tools.help_section_toggle(section_id="tool-format").wait_for_and_click()
            custom_tools.help_section_link(section_id="tool-format", target_id="outputs").wait_for_and_click()
            custom_tools.help_section(section_id="outputs").wait_for_visible()
            assert (
                custom_tools.help_section_toggle(section_id="outputs").wait_for_visible().get_attribute("aria-expanded")
                == "true"
            )

            custom_tools.documentation_expand_button.wait_for_and_click()
            custom_tools.editor_pane.wait_for_visible()
            custom_tools.documentation_button.wait_for_and_click()
            custom_tools.documentation_panel.wait_for_absent_or_hidden()
            custom_tools.editor_pane.wait_for_visible()

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
