import base64

import yaml

from galaxy.workflow.trs_proxy import (
    GA4GH_GALAXY_DESCRIPTOR,
    TrsProxy,
)


def test_proxy():
    proxy = TrsProxy()

    assert 'dockstore' == proxy.get_servers()[0]["id"]

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
