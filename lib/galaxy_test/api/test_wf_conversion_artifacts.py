"""API tests for workflow format2→native conversion artifacts.

The .ga workflows in wf_conversion/ contain tool_state with representation
artifacts from schema-unaware gxformat2 format2→native conversion:

- Multiple select values as JSON lists instead of comma-delimited strings
- Absent sections (all values were None, gxformat2 omitted the key)
- Absent empty repeats (gxformat2 omitted empty lists)
- Lowercase JSON booleans instead of capitalized string booleans

These tests verify Galaxy executes these workflows correctly.
"""

import json
from typing import Any

from galaxy.util.resources import resource_string
from .test_workflows import BaseWorkflowsApiTestCase


def _load_ga_workflow(name: str) -> dict:
    content = resource_string("galaxy_test.base", f"data/wf_conversion/{name}.ga")
    return json.loads(content)


class TestWfConversionArtifacts(BaseWorkflowsApiTestCase):
    """Verify Galaxy executes workflows with format2 conversion artifacts."""

    def _invoke_conversion_workflow(
        self,
        name: str,
        *,
        allow_tool_state_corrections: bool = True,
        history_id: str | None = None,
        inputs: dict[str, Any] | None = None,
        assert_ok: bool = True,
    ) -> str:
        """Import a .ga workflow, invoke it, wait for completion.

        Most cases use allow_tool_state_corrections because gxformat2's
        schema-unaware conversion omits default/None values that Galaxy's
        upgrade checker flags.

        TODO: add a UI/selenium test to verify these workflows can be opened in
        the workflow editor and the upgrade banner is handled correctly.
        """
        workflow_id = self.workflow_populator.create_workflow(_load_ga_workflow(name))
        if history_id is None:
            history_id = self.dataset_populator.new_history()
        request = {"allow_tool_state_corrections": True} if allow_tool_state_corrections else None
        invocation_id = self.workflow_populator.invoke_workflow_and_assert_ok(
            workflow_id,
            history_id=history_id,
            inputs=inputs,
            request=request,
        )
        self.workflow_populator.wait_for_invocation_and_completion(invocation_id, assert_ok=assert_ok)
        return history_id

    def _history_content(self, history_id: str, hid: int) -> str:
        return self.dataset_populator.get_history_dataset_content(history_id, hid=hid, wait=False)

    def _history_dataset_state(self, history_id: str, hid: int) -> str:
        return self.dataset_populator.get_history_dataset_details(history_id, hid=hid, wait=False)["state"]

    def test_multiple_select_list_form(self):
        """Tool with multiple:true select as JSON list in tool_state executes.

        Artifact: tool_state has '["--ex1"]' (JSON list) instead of '"--ex1"'
        (comma-delimited string) for a multiple select parameter.
        """
        history_id = self._invoke_conversion_workflow("multiple_select")
        # Step select_single outputs "--ex1", step select_multi outputs "--ex1,ex2"
        content1 = self._history_content(history_id, hid=1)
        assert "--ex1" in content1
        content2 = self._history_content(history_id, hid=2)
        assert "--ex1" in content2
        assert "ex2" in content2

    def test_absent_allnone_section(self):
        """Tool with absent all-None section in tool_state uses defaults.

        Artifact: the 'parameter' section key is absent from tool_state because
        gxformat2 omitted it (all values were None/default). Galaxy should treat
        the absent section as defaults.
        """
        history_id = self._invoke_conversion_workflow("allnone_section")
        content = self._history_content(history_id, hid=1)
        # Default boolean is false -> "myfalse"
        assert "myfalse" in content

    def test_absent_empty_repeat_without_corrections(self):
        """Absent repeat invokes successfully but job errors at Cheetah rendering.

        Artifact: the 'files' repeat key is absent from tool_state because
        gxformat2 omitted the empty list. Galaxy's upgrade checker does NOT
        flag this (visit_input_values silently defaults missing repeats to []),
        so invocation succeeds without needing allow_tool_state_corrections.
        However the correction to the in-memory state doesn't propagate to
        the persisted tool_state used by the job runner — the Cheetah template
        still can't resolve $files and the job errors.

        This is a workflow-specific problem: direct API tool execution goes
        through populate_state() which initializes all params with defaults
        before processing inputs. Workflow execution goes through
        params_from_strings() which only processes keys present in the stored
        tool_state dict — absent keys are never initialized.
        """
        history_id = self._invoke_conversion_workflow(
            "empty_repeat", allow_tool_state_corrections=False, assert_ok=False
        )
        assert (
            self._history_dataset_state(history_id, hid=1) == "error"
        ), "Expected error — Cheetah can't resolve absent repeat"

    def test_absent_empty_repeat_with_corrections(self):
        """Absent repeat with allow_tool_state_corrections also errors.

        Same outcome as without corrections — the flag makes no difference
        for this artifact because Galaxy doesn't generate an upgrade message
        for the absent repeat in the first place. The job still errors at
        Cheetah template rendering.
        """
        history_id = self._invoke_conversion_workflow("empty_repeat", assert_ok=False)
        assert (
            self._history_dataset_state(history_id, hid=1) == "error"
        ), "Expected error — corrections don't fix absent repeat"

    def test_absent_empty_repeat_safe_template(self):
        """Absent repeat with a well-written template succeeds via workflow.

        Uses gx_repeat_optional which handles empty repeats gracefully (uses
        len() and #for loop, no direct indexing). This isolates the absent-key
        issue from the simple_constructs template bug (dangling &&).

        The job succeeds because visit_input_values defaults the repeat to []
        during check_and_update_param_values, and the Cheetah template can
        handle len($parameter) == 0 and an empty #for loop. The correction
        to in-memory state IS sufficient when the template doesn't directly
        index into the repeat.
        """
        history_id = self._invoke_conversion_workflow("empty_repeat_optional")
        content = self._history_content(history_id, hid=1)
        assert "length: 0" in content

    def test_boolean_case_normalization(self):
        """Tool with lowercase JSON booleans in tool_state executes.

        Artifact: tool_state has 'true'/'false' (lowercase JSON booleans) instead
        of '"True"'/'"False"' (capitalized strings) that some native workflows use.
        """
        history_id = self._invoke_conversion_workflow("boolean_case")
        content_true = self._history_content(history_id, hid=1)
        assert "mytrue" in content_true
        content_false = self._history_content(history_id, hid=2)
        assert "myfalse" in content_false

    def test_connection_only_section_omitted(self):
        """Tool with connection-only section absent from tool_state executes correctly.

        Artifact: the 'parameter' section key is absent from tool_state because
        gxformat2 safely structurally omitted it (as connections are declared in 'in'
        and all native tool_state primitives were connection markers during export).
        Galaxy should resolve the nested connection parameters successfully from
        the step's explicit input_connections metadata.
        """
        history_id = self.dataset_populator.new_history()
        # Create an input dataset to map to the workflow
        input_hda = self.dataset_populator.new_dataset(history_id, content="Connection only test content")
        self._invoke_conversion_workflow(
            "connection_only_section",
            history_id=history_id,
            inputs={"0": {"id": input_hda["id"], "src": "hda"}},
        )

        # Verify the tool executed and emitted our data
        content = self._history_content(history_id, hid=2)
        assert "Connection only test content" in content
