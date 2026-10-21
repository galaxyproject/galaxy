from types import SimpleNamespace
from typing import cast
from unittest import mock

import pytest

from galaxy.agents.operations import AgentOperationsManager
from galaxy.managers.context import ProvidesUserContext
from galaxy.managers.workflows import WorkflowContentsManager
from galaxy.structured_app import MinimalManagerApp


def _make_app(stored_workflow=None, tools=None, toolbox_has=lambda **_: True) -> MinimalManagerApp:
    contents_manager = mock.Mock(spec=WorkflowContentsManager)
    contents_manager.get_or_create_workflow_from_trs.return_value = stored_workflow
    contents_manager.get_all_tools.return_value = tools or []
    toolbox = SimpleNamespace(has_tool=lambda tool_id, **kwargs: toolbox_has(tool_id=tool_id, **kwargs))
    return cast(
        MinimalManagerApp,
        SimpleNamespace(workflow_contents_manager=contents_manager, toolbox=toolbox),
    )


def _make_trans():
    return cast(
        ProvidesUserContext,
        SimpleNamespace(
            user=SimpleNamespace(id=42),
            security=SimpleNamespace(encode_id=lambda value: f"encoded-{value}"),
        ),
    )


def _make_ops(app, trans=None) -> AgentOperationsManager:
    return AgentOperationsManager(app=app, trans=trans or _make_trans())


def test_import_workflow_from_iwc_delegates_to_trs_pipeline():
    trs_id = "#workflow/github.com/iwc-workflows/rna-seq/main"
    stored = SimpleNamespace(id=7, name="rna-seq", latest_workflow=SimpleNamespace())
    app = _make_app(stored_workflow=stored, tools=[])
    ops = _make_ops(app)

    result = ops.import_workflow_from_iwc(trs_id)

    app.workflow_contents_manager.get_or_create_workflow_from_trs.assert_called_once_with(  # type: ignore[attr-defined]
        ops.trans,
        trs_url=None,
        trs_id=trs_id,
        trs_version="main",
        trs_server="dockstore",
    )
    assert result == {
        "id": "encoded-7",
        "name": "rna-seq",
        "trsID": trs_id,
        "missing_tools": [],
    }


def test_import_workflow_from_iwc_surfaces_missing_tools_via_toolbox():
    trs_id = "#workflow/github.com/iwc-workflows/needs-tools/main"
    stored = SimpleNamespace(id=9, name="needs-tools", latest_workflow=SimpleNamespace())
    # Two distinct tool refs (one installed, one not) plus a duplicate of the missing id
    # to confirm de-duplication.
    tools = [
        {"tool_id": "installed/tool", "tool_version": "1.0", "tool_uuid": None},
        {"tool_id": "missing/tool", "tool_version": "2.0", "tool_uuid": None},
        {"tool_id": "missing/tool", "tool_version": "2.0", "tool_uuid": None},
    ]
    app = _make_app(
        stored_workflow=stored,
        tools=tools,
        toolbox_has=lambda tool_id, **_: tool_id == "installed/tool",
    )
    ops = _make_ops(app)

    result = ops.import_workflow_from_iwc(trs_id)

    assert result["missing_tools"] == ["missing/tool"]


def test_import_workflow_from_iwc_handles_no_latest_workflow():
    stored = SimpleNamespace(id=3, name="empty", latest_workflow=None)
    app = _make_app(stored_workflow=stored, tools=[])
    ops = _make_ops(app)

    result = ops.import_workflow_from_iwc("#workflow/github.com/iwc-workflows/empty/main")

    assert result["missing_tools"] == []
    app.workflow_contents_manager.get_all_tools.assert_not_called()  # type: ignore[attr-defined]


def test_import_workflow_from_iwc_requires_authenticated_user():
    app = _make_app()
    trans = cast(ProvidesUserContext, SimpleNamespace(user=None))
    ops = _make_ops(app, trans=trans)

    with pytest.raises(ValueError, match="authenticated"):
        ops.import_workflow_from_iwc("#workflow/anything/main")


def test_import_workflow_from_iwc_rejects_empty_trs_id():
    app = _make_app()
    ops = _make_ops(app)

    with pytest.raises(ValueError, match="trs_id is required"):
        ops.import_workflow_from_iwc("")


def test_import_workflow_from_iwc_propagates_trs_lookup_errors():
    app = _make_app()
    app.workflow_contents_manager.get_or_create_workflow_from_trs.side_effect = RuntimeError("trs lookup blew up")  # type: ignore[attr-defined]
    ops = _make_ops(app)

    with pytest.raises(RuntimeError, match="trs lookup blew up"):
        ops.import_workflow_from_iwc("#workflow/github.com/iwc-workflows/missing/main")
