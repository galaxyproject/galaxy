from typing import TYPE_CHECKING

from galaxy_test.driver.uses_shed import UsesShed
from .framework import (
    selenium_test,
    SeleniumIntegrationTestCase,
)

if TYPE_CHECKING:
    from galaxy_test.selenium.framework import SeleniumSessionDatasetPopulator


class TestWorkflowEditorToolUpgradeWithToolShedTool(SeleniumIntegrationTestCase, UsesShed):
    dataset_populator: "SeleniumSessionDatasetPopulator"
    run_as_admin = True

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        cls.configure_shed(config)

    @selenium_test
    def test_tool_shed_tool_update_in_workflow_editor(self):
        self.install_repository("iuc", "compose_text_param", "feb3acba1e0a")  # 0.1.0
        self.install_repository("iuc", "compose_text_param", "e188c9826e0f")  # 0.1.1
        self.login()
        workflow_populator = self.workflow_populator
        workflow_id = workflow_populator.upload_yaml_workflow(
            """class: GalaxyWorkflow
inputs: []
steps:
  - tool_id: compose_text_param
    tool_version: 0.1.0
    label: compose_text_param
        """,
            exact_tools=True,
        )
        self.workflow_index_open()
        self.components.workflows.edit_button.wait_for_and_click()
        editor = self.components.workflow_editor
        editor.node._(label="compose_text_param").wait_for_and_click()
        editor.tool_version_button.wait_for_and_click()
        assert self.select_dropdown_item("Switch to 0.1.1"), "Switch to tool version dropdown item not found"
        self.screenshot("workflow_editor_version_update_tool_shed")
        self.sleep_for(self.wait_types.UX_RENDER)
        self.assert_workflow_has_changes_and_save()
        workflow = self.workflow_populator.download_workflow(workflow_id)
        assert workflow["steps"]["0"]["tool_version"] == "0.1.1"
        assert (
            workflow["steps"]["0"]["tool_id"]
            == "toolshed.g2.bx.psu.edu/repos/iuc/compose_text_param/compose_text_param/0.1.1"
        )

    @selenium_test
    def test_tool_shed_unmatched_version_upgrade(self):
        self.install_repository("iuc", "compose_text_param", "e188c9826e0f")  # 0.1.1
        self.login()
        workflow_id = self.workflow_populator.upload_yaml_workflow(
            """class: GalaxyWorkflow
inputs: []
steps:
  - tool_id: toolshed.g2.bx.psu.edu/repos/iuc/compose_text_param/compose_text_param/0.0.0
    tool_version: 0.0.0
    label: compose_text_param
        """
        )
        self.workflow_index_open()
        self.components.workflows.edit_button.wait_for_and_click()
        self.assert_modal_has_text("Using version '0.1.1' instead of version '0.0.0'")
        self.screenshot("workflow_editor_tool_repository_upgrade")
        self.components.workflow_editor.modal_button_continue.wait_for_and_click()
        self.assert_workflow_has_changes_and_save()
        workflow = self.workflow_populator.download_workflow(workflow_id)
        assert (
            workflow["steps"]["0"]["content_id"]
            == "toolshed.g2.bx.psu.edu/repos/iuc/compose_text_param/compose_text_param/0.1.1"
        )
        assert (
            workflow["steps"]["0"]["tool_id"]
            == "toolshed.g2.bx.psu.edu/repos/iuc/compose_text_param/compose_text_param/0.1.1"
        )
        assert workflow["steps"]["0"]["tool_version"] == "0.1.1"
