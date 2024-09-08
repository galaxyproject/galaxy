from galaxy.model.dereference import dereference_to_model
from galaxy.tool_util.parameters import DataRequestUri
from .model.test_model_store import setup_fixture_context_with_history

TEST_URI = "gxfiles://test/1.bed"


def test_dereference():
    app, sa_session, user, history = setup_fixture_context_with_history()
    uri_request = DataRequestUri(url=TEST_URI, ext="bed")
    hda = dereference_to_model(sa_session, user, history, uri_request)
    assert hda.name == "1.bed"
    assert hda.dataset.sources[0].source_uri == TEST_URI
