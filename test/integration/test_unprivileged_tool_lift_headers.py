"""Integration tests for lift-status response headers on unprivileged tool endpoints.

Stored tool representations can drift from the strict schema, and the lift
reports every dropped field path. Those paths must never reach response
headers unbounded: header blocks are limited by reverse proxy buffer sizes
(nginx defaults to 4k), and an oversized header turns into a 502 for exactly
the user whose tools drifted -- which the client then misreads as a
permission denial and hides the feature entirely.

These tests seed drifted rows directly in the database (the API validates
strictly on create, so drift can only enter from legacy stored data) and
assert the index endpoint emits no lift headers at all while single-tool
endpoints emit bounded ones.
"""

from sqlalchemy import select

from galaxy.model import DynamicTool
from galaxy.tool_util_models import UserToolSource

from galaxy_test.base.populators import (
    DatasetPopulator,
    TOOL_WITH_SHELL_COMMAND,
)
from galaxy_test.driver import integration_util

# Internal-model fields the strict UserToolSource schema rejects; the lift
# strips them and reports one dropped path per field.
LEGACY_INPUT_EXTRAS = {
    "parameter_type": "gx_text",
    "argument": None,
    "hidden": False,
    "is_dynamic": False,
}

# Mirrors the server-side byte cap on single-tool lift headers.
LIFT_HEADER_MAX_BYTES = 1024

LIFT_HEADERS = ("X-Galaxy-Deprecated-Fields", "X-Galaxy-Schema-Errors", "Warning")


class TestUnprivilegedToolLiftHeaders(integration_util.IntegrationTestCase):
    dataset_populator: DatasetPopulator

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)

    def _seed_drifted_tool(self, drifted_input_count: int) -> str:
        tool = self.dataset_populator.create_unprivileged_tool(UserToolSource(**TOOL_WITH_SHELL_COMMAND))
        uuid = tool["uuid"]
        sa_session = self._app.model.session
        dynamic_tool = sa_session.scalars(select(DynamicTool).where(DynamicTool.uuid == uuid)).one()
        value = dict(dynamic_tool.value or {})
        value["inputs"] = list(value.get("inputs") or []) + [
            {"type": "text", "name": f"param_{i}", "value": "x", **LEGACY_INPUT_EXTRAS}
            for i in range(drifted_input_count)
        ]
        dynamic_tool.value = value
        sa_session.commit()
        return uuid

    def test_index_emits_no_lift_headers(self):
        with self.dataset_populator.user_tool_execute_permissions():
            self._seed_drifted_tool(drifted_input_count=10)
            response = self._get("unprivileged_tools")
            response.raise_for_status()
            for header in LIFT_HEADERS:
                assert header not in response.headers, f"index must not emit {header}"
            # Drift details stay available in the body, per tool.
            listed = response.json()
            assert any(tool["representation_status"] == "lifted" for tool in listed)
            assert any(tool.get("representation_errors") for tool in listed)

    def test_show_lift_headers_are_bounded(self):
        with self.dataset_populator.user_tool_execute_permissions():
            uuid = self._seed_drifted_tool(drifted_input_count=30)
            response = self._get(f"unprivileged_tools/{uuid}")
            response.raise_for_status()
            header = response.headers["X-Galaxy-Deprecated-Fields"]
            # 30 drifted inputs x 4 fields = 120 dropped paths; the header must
            # stay under proxy buffer limits and truncate with a count.
            assert len(header) <= LIFT_HEADER_MAX_BYTES, f"header too large ({len(header)} bytes)"
            assert header.endswith("more"), header
            # The Warning header points at the detail header rather than
            # duplicating the path list.
            warning = response.headers["Warning"]
            assert "X-Galaxy-Deprecated-Fields" in warning
            assert "param_" not in warning
