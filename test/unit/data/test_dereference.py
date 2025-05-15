from base64 import b64encode

from galaxy.model.dereference import dereference_to_model
from galaxy.tool_util.parameters import DataRequestUri
from .model.test_model_store import setup_fixture_context_with_history

B64_FOR_1_2_3 = b64encode(b"1 2 3").decode("utf-8")
TEST_URI = "gxfiles://test/1.bed"
TEST_BASE64_URI = f"base64://{B64_FOR_1_2_3}"


def test_dereference():
    app, sa_session, user, history = setup_fixture_context_with_history()
    uri_request = DataRequestUri(url=TEST_URI, ext="bed")
    hda = dereference_to_model(sa_session, user, history, uri_request)
    assert hda.name == "1.bed"
    assert hda.dataset.sources[0].source_uri == TEST_URI
    assert hda.ext == "bed"


def test_dereference_dbkey():
    app, sa_session, user, history = setup_fixture_context_with_history()
    uri_request = DataRequestUri(url=TEST_URI, ext="bed", dbkey="hg19")
    hda = dereference_to_model(sa_session, user, history, uri_request)
    assert hda.name == "1.bed"
    assert hda.dataset.sources[0].source_uri == TEST_URI
    assert hda.dbkey == "hg19"


def test_dereference_md5():
    app, sa_session, user, history = setup_fixture_context_with_history()
    md5 = "f2b33fb7b3d0eb95090a16060e6a24f9"
    uri_request = DataRequestUri.model_validate(
        {
            "url": TEST_BASE64_URI,
            "name": "foobar.txt",
            "ext": "txt",
            "hashes": [{"hash_function": "MD5", "hash_value": md5}],
        }
    )
    hda = dereference_to_model(sa_session, user, history, uri_request)
    assert hda.name == "foobar.txt"
    assert hda.dataset.sources[0].source_uri == TEST_BASE64_URI
    assert hda.dataset.sources[0].hashes[0]
    assert hda.dataset.sources[0].hashes[0].hash_function == "MD5"
    assert hda.dataset.sources[0].hashes[0].hash_value == md5


def test_dereference_to_posix():
    app, sa_session, user, history = setup_fixture_context_with_history()
    uri_request = DataRequestUri.model_validate(
        {"url": TEST_BASE64_URI, "name": "foobar.txt", "ext": "txt", "space_to_tab": True}
    )
    hda = dereference_to_model(sa_session, user, history, uri_request)
    assert hda.name == "foobar.txt"
    assert hda.dataset.sources[0].source_uri == TEST_BASE64_URI
    assert hda.dataset.sources[0].transform[0]["action"] == "spaces_to_tabs"
