from typing import (
    cast,
    TYPE_CHECKING,
)

from galaxy.app_unittest_utils.galaxy_mock import MockApp
from galaxy.jobs.manager import JobManager
from galaxy.util.bunch import Bunch

if TYPE_CHECKING:
    from galaxy.tools import (
        Tool,
        ToolBox,
    )


def _mock_job():
    return Bunch(id=1, log_str=lambda: "mock job")


def _mock_tool(handler="cfg_from_tool"):
    return cast("Tool", Bunch(id="cat1", get_configured_job_handler=lambda: handler))


def _capture_app():
    """MockApp whose assign_handler records the configured handler it was given."""
    app = MockApp()
    recorded = {}

    def assign_handler(job, configured=None, **kwargs):
        recorded["configured"] = configured
        return "handler0"

    app.job_config = Bunch(assign_handler=assign_handler)
    return app, recorded


def test_enqueue_without_toolbox_does_not_access_toolbox():
    # The async tool-request worker runs without a toolbox (_toolbox is None), so
    # reaching the asserting `app.toolbox` property would raise. enqueue must use
    # `toolbox_or_none` and pass the already-materialized tool through untouched.
    app, recorded = _capture_app()
    assert app.toolbox_or_none is None

    result = JobManager(app).enqueue(_mock_job(), tool=_mock_tool())

    assert result == "handler0"
    assert recorded["configured"] == "cfg_from_tool"


def test_enqueue_with_toolbox_materializes_tool():
    # When a toolbox is configured, the tool is still materialized through it and the
    # materialized tool is what drives handler assignment.
    app, recorded = _capture_app()
    materialized = _mock_tool("cfg_from_materialized")
    calls = []

    def materialize_tool(tool, *, reason):
        calls.append((tool, reason))
        return materialized

    app.toolbox = cast("ToolBox", Bunch(materialize_tool=materialize_tool))

    tool = _mock_tool()
    result = JobManager(app).enqueue(_mock_job(), tool=tool)

    assert result == "handler0"
    assert calls == [(tool, "job_setup")]
    assert recorded["configured"] == "cfg_from_materialized"
