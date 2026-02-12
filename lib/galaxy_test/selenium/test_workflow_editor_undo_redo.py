from .framework import (
    RunsWorkflows,
    selenium_only,
    selenium_test,
    SeleniumTestCase,
)


class TestWorkflowEditorUndoRedo(SeleniumTestCase, RunsWorkflows):
    ensure_registered = True

    @selenium_only("Not yet migrated to support Playwright backend")
    @selenium_test
    def test_editor_change_stack_inserting_inputs(self):
        editor = self.components.workflow_editor
        annotation = "change_stack_test_inserting_inputs"
        self.workflow_create_new(annotation=annotation)

        self.workflow_editor_add_input(item_name="data_input")
        self.workflow_editor_add_input(item_name="data_collection_input")
        self.workflow_editor_add_input(item_name="parameter_input")

        editor.node.by_id(id=0).wait_for_present()
        editor.node.by_id(id=1).wait_for_present()
        editor.node.by_id(id=2).wait_for_present()

        editor.tool_bar.changes.wait_for_and_click()
        changes = editor.changes

        changes.action_insert_data_input.wait_for_present()
        changes.action_insert_data_collection_input.wait_for_present()
        changes.action_insert_parameter.wait_for_present()

        # Undo all of it by clicking the first node.
        changes.action_insert_data_input.wait_for_and_click()
        editor.node.by_id(id=0).assert_absent_or_hidden_after_transitions()
        editor.node.by_id(id=1).assert_absent_or_hidden_after_transitions()
        editor.node.by_id(id=2).assert_absent_or_hidden_after_transitions()

        # now that same action has become a redo, so we should have a node back afterward.
        changes.action_insert_data_input.wait_for_and_click()
        editor.node.by_id(id=0).wait_for_present()
        editor.node.by_id(id=1).assert_absent_or_hidden_after_transitions()
        editor.node.by_id(id=2).assert_absent_or_hidden_after_transitions()

        changes.action_insert_data_collection_input.wait_for_and_click()
        editor.node.by_id(id=0).wait_for_present()
        editor.node.by_id(id=1).wait_for_present()
        editor.node.by_id(id=2).assert_absent_or_hidden_after_transitions()

        changes.action_insert_parameter.wait_for_and_click()
        editor.node.by_id(id=0).wait_for_present()
        editor.node.by_id(id=1).wait_for_present()
        editor.node.by_id(id=2).wait_for_present()

    @selenium_only("Not yet migrated to support Playwright backend")
    @selenium_test
    def test_editor_change_stack_set_attributes(self):
        editor = self.components.workflow_editor
        annotation = "change_stack_test_set_attributes"
        name = self.workflow_create_new(annotation=annotation)

        assert "Do not specify" in self.workflow_editor_license_text()
        self.workflow_editor_set_license("MIT")
        assert "MIT" in self.workflow_editor_license_text()

        editor.tool_bar.changes.wait_for_and_click()

        changes = editor.changes
        changes.action_set_license.wait_for_and_click()
        # it switches back so this isn't needed per se
        # editor.tool_bar.attributes.wait_for_and_click()
        assert "Do not specify" in self.workflow_editor_license_text()

        # for annotation we want to reset the change stack to dismiss
        # the original setting of the annotation
        name = self.workflow_index_open_with_name(name)

        annotation_modified = "change_stack_test_set_attributes modified!!!"

        self.workflow_editor_set_annotation(annotation_modified)
        self.assert_wf_annotation_is(annotation_modified)

        editor.tool_bar.changes.wait_for_and_click()
        changes.action_set_annotation.wait_for_and_click()

        self.assert_wf_annotation_is(annotation)
