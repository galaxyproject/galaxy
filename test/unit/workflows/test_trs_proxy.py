import base64
import socket
from os import environ
from unittest import (
    mock,
    SkipTest,
)

import pytest
import yaml

from galaxy.config import GalaxyAppConfiguration
from galaxy.exceptions import (
    ConfigDoesNotAllowException,
    GatewayTimeoutException,
    MessageException,
    UpstreamProxyError,
)
from galaxy.util import requests
from galaxy.util.unittest_utils import (
    skip_if_dockstore_down,
    skip_if_workflowhub_down,
)
from galaxy.workflow import trs_proxy
from galaxy.workflow.trs_proxy import (
    GA4GH_GALAXY_DESCRIPTOR,
    parse_search_kwds,
    parse_trs_version,
    sort_trs_versions,
    trs_upgrade_version_id,
    trs_version_id,
    TrsProxy,
)

# search test is very brittle (depends on production values) and is very slow.
# still good to know search is working though - even if manually
search_test = pytest.mark.skipif(
    not environ.get("GALAXY_TEST_INCLUDE_DOCKSTORE_SEARCH"), reason="GALAXY_TEST_INCLUDE_DOCKSTORE_SEARCH not set"
)


def get_trs_proxy():
    return TrsProxy(GalaxyAppConfiguration(fetch_url_allowlist_ips=[], override_tempdir=False))


@skip_if_dockstore_down
def test_proxy():
    proxy = get_trs_proxy()
    server = proxy.get_server("dockstore")

    assert "dockstore" == proxy.get_servers()[0]["id"]

    assert proxy.get_servers()[0]["api_url"] == server._trs_url

    tool_id = "#workflow/github.com/jmchilton/galaxy-workflow-dockstore-example-1/mycoolworkflow"
    tool = server.get_tool(tool_id)
    assert "description" in tool

    b64_tool_id = base64.b64encode(tool_id.encode("UTF-8"))
    tool = server.get_tool(b64_tool_id, tool_id_b64_encoded=True)
    assert "description" in tool

    versions = server.get_versions(tool_id)
    assert isinstance(versions, list)
    assert len(versions) >= 1

    version_id = versions[0]["name"]
    version = server.get_version(tool_id, version_id)
    assert "descriptor_type" in version
    assert GA4GH_GALAXY_DESCRIPTOR in version["descriptor_type"]

    descriptor = server.get_version_descriptor(tool_id, version_id)
    content = yaml.safe_load(descriptor)
    assert "inputs" in content


def test_match_url():
    proxy = get_trs_proxy()
    valid_dockstore = proxy._match_url(
        "https://dockstore.org/api/ga4gh/trs/v2/tools/"
        "quay.io%2Fcollaboratory%2Fdockstore-tool-bedtools-genomecov/versions/0.3",
    )
    assert valid_dockstore
    assert valid_dockstore["trs_base_url"] == "https://dockstore.org/api"
    # Should unquote
    assert valid_dockstore["tool_id"] == "quay.io/collaboratory/dockstore-tool-bedtools-genomecov"
    assert valid_dockstore["version_id"] == "0.3"

    valid_dockstore_unescaped = proxy._match_url(
        "https://dockstore.org/api/ga4gh/trs/v2/tools/"
        "#workflow/github.com/jmchilton/galaxy-workflow-dockstore-example-1/mycoolworkflow/versions/master",
    )
    assert valid_dockstore_unescaped
    assert valid_dockstore_unescaped["trs_base_url"] == "https://dockstore.org/api"
    assert (
        valid_dockstore_unescaped["tool_id"]
        == "#workflow/github.com/jmchilton/galaxy-workflow-dockstore-example-1/mycoolworkflow"
    )
    assert valid_dockstore_unescaped["version_id"] == "master"

    valid_workflow_hub = proxy._match_url("https://workflowhub.eu/ga4gh/trs/v2/tools/344/versions/1")
    assert valid_workflow_hub
    assert valid_workflow_hub["trs_base_url"] == "https://workflowhub.eu"
    assert valid_workflow_hub["tool_id"] == "344"
    assert valid_workflow_hub["version_id"] == "1"

    valid_arbitrary_trs = proxy._match_url(
        "https://my-trs-server.golf/stuff/ga4gh/trs/v2/tools/hello-world/versions/version-1"
    )
    assert valid_arbitrary_trs
    assert valid_arbitrary_trs["trs_base_url"] == "https://my-trs-server.golf/stuff"
    assert valid_arbitrary_trs["tool_id"] == "hello-world"
    assert valid_arbitrary_trs["version_id"] == "version-1"

    ignore_extra = proxy._match_url(
        "https://workflowhub.eu/ga4gh/trs/v2/tools/344/versions/1/CWL/descriptor/ro-crate-metadata.json",
    )
    assert ignore_extra
    assert ignore_extra["trs_base_url"] == "https://workflowhub.eu"
    assert ignore_extra["tool_id"] == "344"
    assert ignore_extra["version_id"] == "1"

    invalid = proxy._match_url("https://workflowhub.eu/workflows/1")
    assert invalid is None

    missing_version = proxy._match_url("https://workflowhub.eu/ga4gh/trs/v2/tools/344")
    assert missing_version is None

    blank = proxy.match_url("", [])
    assert blank is None

    not_url = proxy.match_url("1234", [])
    assert not_url is None

    expected_exception = None
    try:
        proxy.match_url("https://localhost", [])
    except ConfigDoesNotAllowException as e:
        expected_exception = e
    assert expected_exception, "matching url against localhost should fail"


@skip_if_workflowhub_down
def test_server_from_url():
    proxy = get_trs_proxy()
    server = proxy.server_from_url("https://workflowhub.eu")

    assert "https://workflowhub.eu" == server._trs_url

    tool_id = "138"
    tool = server.get_tool(tool_id)
    assert "description" in tool

    b64_tool_id = base64.b64encode(tool_id.encode("UTF-8"))
    tool = server.get_tool(b64_tool_id, tool_id_b64_encoded=True)
    assert "description" in tool

    versions = server.get_versions(tool_id)
    assert isinstance(versions, list)
    assert len(versions) >= 1

    version_id = versions[0]["id"]  # Dockstore and WorkflowHub differ here! Spec is not clear
    version = server.get_version(tool_id, version_id)
    assert "descriptor_type" in version
    assert GA4GH_GALAXY_DESCRIPTOR in version["descriptor_type"]

    descriptor = server.get_version_descriptor(tool_id, version_id)
    content = yaml.safe_load(descriptor)
    assert "steps" in content


@search_test
@skip_if_dockstore_down
def test_search():
    proxy = get_trs_proxy()
    server = proxy.get_server("dockstore")

    search_kwd = parse_search_kwds("documentation")
    response = server.get_tools(**search_kwd)
    assert len(response) == 1

    search_kwd = parse_search_kwds("n:example")
    response = server.get_tools(**search_kwd)
    assert len(response) == 2

    search_kwd = parse_search_kwds("organization:jmchilton")
    response = server.get_tools(**search_kwd)
    assert len(response) == 2

    search_kwd = parse_search_kwds("organization:jmchiltonx")
    response = server.get_tools(**search_kwd)
    assert len(response) == 0

    response = server.get_tools(descriptorType="GALAXY")
    assert len(response) == 2


def _response(status_code, text, headers=None):
    response = requests.Response()
    response.status_code = status_code
    response._content = text.encode()
    response.headers.update(headers or {})
    return response


def _mock_get(trs_response):
    def get(url, **kwargs):
        if url == "https://workflowhub.eu/":
            return _response(200, "<html>WorkflowHub</html>")
        if isinstance(trs_response, Exception):
            raise trs_response
        return trs_response

    return mock.patch.object(requests, "get", side_effect=get)


def test_non_trs_error_page_reports_status_without_body():
    server = get_trs_proxy().server_from_url("https://workflowhub.eu")
    with _mock_get(_response(503, "<h2>This website is under heavy load (queue full)</h2>")):
        with pytest.raises(MessageException) as exc_info:
            server.get_tool("138")
    assert str(exc_info.value) == "TRS server https://workflowhub.eu responded with HTTP 503."


def test_trs_error_document_is_passed_through():
    server = get_trs_proxy().server_from_url("https://workflowhub.eu")
    with _mock_get(_response(400, '{"code": 400, "message": "bad version"}')):
        with pytest.raises(MessageException, match="^bad version$"):
            server.get_tool("138")


def test_version_with_slash_stays_one_path_segment():
    server = get_trs_proxy().server_from_url("https://workflowhub.eu")
    parts = trs_proxy.parse_trs_url(server.get_trs_url("138", "feature/x"))
    assert parts and parts["version_id"] == "feature/x"
    with _mock_get(_response(200, '{"content": "class: GalaxyWorkflow"}')) as get:
        server.get_version_descriptor("138", parts["version_id"])
    assert get.call_args.args[0].endswith("/tools/138/versions/feature%2Fx/GALAXY/descriptor")


def test_successful_response_without_json_is_upstream_error():
    server = get_trs_proxy().server_from_url("https://workflowhub.eu")
    with _mock_get(_response(200, "<html>Sign in</html>")):
        with pytest.raises(UpstreamProxyError, match="not JSON"):
            server.get_tool("138")


def test_timeout_is_gateway_timeout():
    server = get_trs_proxy().server_from_url("https://workflowhub.eu")
    with _mock_get(requests.exceptions.ReadTimeout("read timed out")):
        with pytest.raises(GatewayTimeoutException):
            server.get_tool("138")


@pytest.mark.parametrize(
    "trs_response",
    [
        _response(403, "<title>Just a moment...</title>", {"cf-mitigated": "challenge", "server": "cloudflare"}),
        _response(503, "<h2>This website is under heavy load (queue full)</h2>"),
        requests.exceptions.ConnectTimeout("connect timed out"),
        requests.exceptions.ConnectionError("connection refused"),
    ],
)
def test_skip_if_workflowhub_down_skips_unavailable_server(trs_response):
    @skip_if_workflowhub_down
    def fetch_tool():
        get_trs_proxy().server_from_url("https://workflowhub.eu").get_tool("138")

    with _mock_get(trs_response):
        with pytest.raises(SkipTest):
            fetch_tool()


def test_skip_if_workflowhub_down_reports_other_failures():
    @skip_if_workflowhub_down
    def fetch_tool():
        tool = get_trs_proxy().server_from_url("https://workflowhub.eu").get_tool("138")
        assert "description" in tool

    with _mock_get(_response(200, '{"id": "138"}')):
        with pytest.raises(AssertionError):
            fetch_tool()


UNRESPONSIVE_SERVER_ERRORS = [
    (
        requests.exceptions.ReadTimeout(
            "HTTPSConnectionPool(host='workflowhub.eu', port=443): Read timed out. (read timeout=30)"
        ),
        "did not respond in time",
    ),
    (
        requests.exceptions.ConnectTimeout(
            "HTTPSConnectionPool(host='workflowhub.eu', port=443): Max retries exceeded with url: "
            "/ga4gh/trs/v2/tools/138 (Caused by ConnectTimeoutError('Connection timed out. (connect timeout=10)'))"
        ),
        "did not respond in time",
    ),
    (
        requests.exceptions.ConnectionError(
            "HTTPSConnectionPool(host='workflowhub.eu', port=443): Max retries exceeded with url: "
            "/ga4gh/trs/v2/tools/138 (Caused by NewConnectionError('Failed to establish a new connection'))"
        ),
        "could not be reached",
    ),
]


def test_trs_requests_use_bounded_timeout():
    with _mock_get(_response(200, '{"id": "138"}')) as get:
        get_trs_proxy().server_from_url("https://workflowhub.eu").get_tool("138")
    assert get.call_args.kwargs["timeout"] == (10, 30)


def test_slow_server_reported_as_timeout():
    # A listening socket that never accepts completes the TCP handshake but never sends a response.
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        host, port = listener.getsockname()
        server = get_trs_proxy().server_from_url(f"http://{host}:{port}")
        with mock.patch.object(trs_proxy, "TRS_REQUEST_TIMEOUT", (1, 0.1)):
            with pytest.raises(MessageException, match=r"did not respond in time"):
                server.get_tool("138")


@pytest.mark.parametrize("trs_error,reason", UNRESPONSIVE_SERVER_ERRORS)
def test_unresponsive_server_reported_as_message_exception(trs_error, reason, caplog):
    with _mock_get(trs_error):
        with pytest.raises(MessageException) as exc_info:
            get_trs_proxy().server_from_url("https://workflowhub.eu").get_tool("138")
    assert exc_info.value.err_msg == f"TRS server https://workflowhub.eu {reason}."
    assert str(trs_error) in caplog.text


def _message_sent_to_client(exception):
    # expose_api sends a MessageException's message to the client and replaces any other
    # exception with a generic message.
    if isinstance(exception, MessageException):
        return exception.err_msg
    return "Uncaught exception in exposed API method:"


@pytest.mark.parametrize("trs_error,reason", UNRESPONSIVE_SERVER_ERRORS)
def test_skip_if_workflowhub_down_skips_unresponsive_server_reported_to_client(trs_error, reason):
    @skip_if_workflowhub_down
    def import_workflow():
        try:
            get_trs_proxy().server_from_url("https://workflowhub.eu").get_tool("138")
        except Exception as e:
            raise AssertionError(f"Errors shown on page: ['Error: {_message_sent_to_client(e)}']")

    with _mock_get(trs_error):
        with pytest.raises(SkipTest, match=reason):
            import_workflow()


DOCKSTORE_TOOL_ID = "#workflow/github.com/iwc-workflows/example/main"


def _dockstore_version(name):
    return {"id": f"{DOCKSTORE_TOOL_ID}:{name}", "name": name}


def test_parse_trs_version():
    assert parse_trs_version("v1.2.3") == (1, 2, 3)
    assert parse_trs_version("v0.10") == (0, 10, 0)
    assert parse_trs_version("2") == (2, 0, 0)
    assert parse_trs_version("main") is None


def test_trs_version_id():
    assert trs_version_id(_dockstore_version("v0.1")) == "v0.1"
    assert trs_version_id({"id": "5", "name": "Version 5"}) == "5"


def test_sort_trs_versions():
    versions = [_dockstore_version(name) for name in ["v0.2", "develop", "v0.10", "Main", "v0.9.1"]]
    assert [v["name"] for v in sort_trs_versions(versions)] == ["v0.10", "v0.9.1", "v0.2", "Main", "develop"]


def test_trs_upgrade_version_id():
    versions = sort_trs_versions([_dockstore_version(name) for name in ["v0.1", "v0.2", "main"]])
    assert trs_upgrade_version_id(versions, "v0.1") == "v0.2"
    assert trs_upgrade_version_id(versions, "v0.2") is None
    # a version newer than the server lists, e.g. one the server has since removed
    assert trs_upgrade_version_id(versions, "v0.3") is None
    assert trs_upgrade_version_id(versions, "main") is None
    assert trs_upgrade_version_id(sort_trs_versions([_dockstore_version("main")]), "main") is None
    with_prereleases = sort_trs_versions(
        [_dockstore_version(name) for name in ["v1.1", "v2.0.0-rc1", "fix-issue-2025"]]
    )
    assert trs_upgrade_version_id(with_prereleases, "v1.0") == "v1.1"
    assert trs_upgrade_version_id(with_prereleases, "v2.0.0-rc1") is None
