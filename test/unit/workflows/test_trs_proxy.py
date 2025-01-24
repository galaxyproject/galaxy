import base64
from os import environ

import pytest
import yaml

from galaxy.config import GalaxyAppConfiguration
from galaxy.exceptions import ConfigDoesNotAllowException
from galaxy.workflow.trs_proxy import (
    GA4GH_GALAXY_DESCRIPTOR,
    parse_search_kwds,
    TrsProxy,
)

# search test is very brittle (depends on production values) and is very slow.
# still good to know search is working though - even if manually
search_test = pytest.mark.skipif(
    not environ.get("GALAXY_TEST_INCLUDE_DOCKSTORE_SEARCH"), reason="GALAXY_TEST_INCLUDE_DOCKSTORE_SEARCH not set"
)


def get_trs_proxy():
    return TrsProxy(GalaxyAppConfiguration(fetch_url_allowlist_ips=[], override_tempdir=False))


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
