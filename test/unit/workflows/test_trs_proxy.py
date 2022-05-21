import base64
from os import environ

import pytest
import yaml

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


def test_proxy():
    proxy = TrsProxy()

    assert "dockstore" == proxy.get_servers()[0]["id"]

    tool_id = "#workflow/github.com/jmchilton/galaxy-workflow-dockstore-example-1/mycoolworkflow"
    tool = proxy.get_tool("dockstore", tool_id)
    assert "description" in tool

    b64_tool_id = base64.b64encode(tool_id.encode("UTF-8"))
    tool = proxy.get_tool("dockstore", b64_tool_id, tool_id_b64_encoded=True)
    assert "description" in tool

    versions = proxy.get_versions("dockstore", tool_id)
    assert isinstance(versions, list)
    assert len(versions) >= 1

    version_id = versions[0]["name"]
    version = proxy.get_version("dockstore", tool_id, version_id)
    assert "descriptor_type" in version
    assert GA4GH_GALAXY_DESCRIPTOR in version["descriptor_type"]

    descriptor = proxy.get_version_descriptor("dockstore", tool_id, version_id)
    content = yaml.safe_load(descriptor)
    assert "inputs" in content


@search_test
def test_search():
    proxy = TrsProxy()

    search_kwd = parse_search_kwds("documentation")
    response = proxy.get_tools("dockstore", **search_kwd)
    assert len(response) == 1

    search_kwd = parse_search_kwds("n:example")
    response = proxy.get_tools("dockstore", **search_kwd)
    assert len(response) == 2

    search_kwd = parse_search_kwds("organization:jmchilton")
    response = proxy.get_tools("dockstore", **search_kwd)
    assert len(response) == 2

    search_kwd = parse_search_kwds("organization:jmchiltonx")
    response = proxy.get_tools("dockstore", **search_kwd)
    assert len(response) == 0

    response = proxy.get_tools("dockstore", descriptorType="GALAXY")
    assert len(response) == 2
