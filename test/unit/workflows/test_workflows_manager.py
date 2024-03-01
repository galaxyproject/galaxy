from galaxy import model

from .workflow_support import MockApp

TRS_TOOL_ID = "#the_id"
TRS_TOOL_VERSION = "v1"


def test_find_workflow_by_trs_id():
    app = MockApp()
    with app.model.session.begin():
        w = model.Workflow()

        w.stored_workflow = model.StoredWorkflow()
        w.stored_workflow.latest_workflow = w
        u = model.User("test@test.com", "test", "test")
        w.stored_workflow.user = u
        w.source_metadata = {"trs_server": "dockstore", "trs_tool_id": TRS_TOOL_ID, "trs_version_id": TRS_TOOL_VERSION}
        app.model.session.add(w)
        app.model.session.commit()
        app.model.session.flush()
    assert app.workflow_manager.get_workflow_by_trs_id_and_version(app.model.session, TRS_TOOL_ID, TRS_TOOL_VERSION, u.id) == w
