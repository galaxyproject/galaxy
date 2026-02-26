"""Shared workflow structure verification methods.

Mixin providing workflow structure assertions shared between API and Selenium tests.
"""

import operator
from json import loads
from typing import (
    Optional,
    TYPE_CHECKING,
)

if TYPE_CHECKING:
    from typing import Any


class WorkflowStructureAssertions:
    """Mixin providing workflow structure verification methods."""

    def assert_steps_of_type(
        self, workflow: "dict[str, Any]", step_type: str, expected_len: Optional[int] = None
    ) -> "list[dict[str, Any]]":
        """Get steps of given type from workflow, optionally asserting count."""
        steps = [s for s in workflow["steps"].values() if s["type"] == step_type]
        if expected_len is not None:
            n = len(steps)
            assert n == expected_len, f"Expected {expected_len} steps of type {step_type}, found {n}"
        return sorted(steps, key=operator.itemgetter("id"))

    def assert_workflow_connected(self, workflow: "dict[str, Any]") -> None:
        """Assert all tool steps have input connections."""
        disconnected = []
        for step in workflow["steps"].values():
            if step["type"] == "tool" and not step.get("input_connections"):
                disconnected.append(step)
        if disconnected:
            template = "%d steps disconnected in extracted workflow - disconnected steps are %s - workflow is %s"
            message = template % (len(disconnected), disconnected, workflow)
            raise AssertionError(message)

    def assert_input_step_collection_type(self, workflow: "dict[str, Any]", expected_type: str) -> None:
        """Assert first collection input step has expected collection type."""
        collection_steps = self.assert_steps_of_type(workflow, "data_collection_input", 1)
        state = loads(collection_steps[0]["tool_state"])
        assert state["collection_type"] == expected_type

    def assert_cat1_workflow_structure(self, workflow: "dict[str, Any]") -> None:
        """Assert workflow matches expected cat1 example structure."""
        assert len(workflow["steps"]) == 3
        input_steps = self.assert_steps_of_type(workflow, "data_input", 2)
        tool_step = self.assert_steps_of_type(workflow, "tool", 1)[0]

        input1 = tool_step["input_connections"]["input1"]
        input2 = tool_step["input_connections"]["queries_0|input2"]
        assert input_steps[0]["id"] == input1["id"]
        assert input_steps[1]["id"] == input2["id"]

    def assert_first_step_is_paired_input(self, workflow: "dict[str, Any]") -> int:
        """Assert first collection input step is paired type and return its id."""
        collection_steps = self.assert_steps_of_type(workflow, "data_collection_input", 1)
        collection_step = collection_steps[0]
        collection_step_state = loads(collection_step["tool_state"])
        assert collection_step_state["collection_type"] == "paired"
        return collection_step["id"]

    def assert_randomlines_mapping_workflow_structure(self, workflow: "dict[str, Any]") -> int:
        """Assert workflow looks like random_lines mapped workflow. Returns collection step id."""
        assert len(workflow["steps"]) == 3
        collection_steps = self.assert_steps_of_type(workflow, "data_collection_input", 1)
        collection_step = collection_steps[0]
        collection_step_state = loads(collection_step["tool_state"])
        assert collection_step_state["collection_type"] == "paired"
        collect_step_idx = collection_step["id"]

        tool_steps = self.assert_steps_of_type(workflow, "tool", 2)
        tool_step_idxs = []
        tool_input_step_idxs = []
        for tool_step in tool_steps:
            assert "input" in tool_step["input_connections"], tool_step
            input_step_idx = tool_step["input_connections"]["input"]["id"]
            tool_step_idxs.append(tool_step["id"])
            tool_input_step_idxs.append(input_step_idx)

        assert collect_step_idx not in tool_step_idxs
        assert tool_input_step_idxs[0] == collect_step_idx
        assert tool_input_step_idxs[1] == tool_step_idxs[0]
        return collect_step_idx

    def check_workflow(
        self,
        workflow: "dict[str, Any]",
        step_count: Optional[int] = None,
        verify_connected: bool = False,
        data_input_count: Optional[int] = None,
        data_collection_input_count: Optional[int] = None,
        tool_ids: "Optional[list[str]]" = None,
    ) -> None:
        """Check workflow against expected structure."""
        steps = workflow["steps"]

        if step_count is not None:
            assert len(steps) == step_count
        if verify_connected:
            self.assert_workflow_connected(workflow)
        if tool_ids is not None:
            tool_steps = self.assert_steps_of_type(workflow, "tool")
            found_steps = set(map(operator.itemgetter("tool_id"), tool_steps))
            expected_steps = set(tool_ids)
            assert found_steps == expected_steps
        if data_input_count is not None:
            self.assert_steps_of_type(workflow, "data_input", expected_len=data_input_count)
        if data_collection_input_count is not None:
            self.assert_steps_of_type(workflow, "data_collection_input", expected_len=data_collection_input_count)
