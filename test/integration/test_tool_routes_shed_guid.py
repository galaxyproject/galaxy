import os
import shutil

from galaxy_test.driver import integration_util
from galaxy_test.driver.driver_util import FRAMEWORK_TOOLS_DIR

TOOL_SHED = "toolshed.example.org"
REVISION = "0123456789ab"
GUID = f"{TOOL_SHED}/repos/devteam/gx_int/gx_int/1.0.0"
TOOL_FILE = f"{TOOL_SHED}/repos/devteam/gx_int/{REVISION}/gx_int/gx_int.xml"

TOOL_CONF = f"""<?xml version="1.0"?>
<toolbox tool_path="{{tool_path}}">
  <tool file="{TOOL_FILE}" guid="{GUID}">
    <tool_shed>{TOOL_SHED}</tool_shed>
    <repository_name>gx_int</repository_name>
    <repository_owner>devteam</repository_owner>
    <installed_changeset_revision>{REVISION}</installed_changeset_revision>
    <id>{GUID}</id>
    <version>1.0.0</version>
  </tool>
</toolbox>
"""


class TestToolRoutesWithShedGuid(integration_util.IntegrationTestCase):
    framework_tool_and_types = True

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        tool_path = cls._test_driver.mkdtemp()
        tool_file = os.path.join(tool_path, TOOL_FILE)
        os.makedirs(os.path.dirname(tool_file))
        shutil.copy(os.path.join(FRAMEWORK_TOOLS_DIR, "parameters", "gx_int.xml"), tool_file)
        tool_conf_path = os.path.join(tool_path, "shed_tool_conf.xml")
        with open(tool_conf_path, "w") as f:
            f.write(TOOL_CONF.format(tool_path=tool_path))
        config["tool_config_file"] = tool_conf_path

    def test_inputs(self):
        response = self._get(f"tools/{GUID}/inputs")
        self._assert_status_code_is(response, 200)
        assert_gx_int_parameters(response.json())

    def test_interop(self):
        response = self._get(f"tools/{GUID}/interop")
        self._assert_status_code_is(response, 200)
        assert_gx_int_parsed_tool(response.json())

    def test_versioned_interop(self):
        response = self._get(f"tools/{GUID}/versions/1.0.0/interop")
        self._assert_status_code_is(response, 200)
        assert_gx_int_parsed_tool(response.json())

    def test_parameter_schemas(self):
        for schema in [
            "parameter_request_schema",
            "parameter_landing_request_schema",
            "parameter_test_case_xml_schema",
        ]:
            for path in [f"tools/{GUID}/{schema}", f"tools/{GUID}/versions/1.0.0/{schema}"]:
                response = self._get(path)
                self._assert_status_code_is(response, 200)
                assert "parameter" in response.json()["properties"], path


def assert_gx_int_parameters(parameters):
    assert [(p["name"], p["parameter_type"]) for p in parameters] == [("parameter", "gx_integer")]


def assert_gx_int_parsed_tool(parsed_tool):
    # ParsedTool describes the tool source, so its id is the wrapper's own id.
    assert parsed_tool["id"] == "gx_int"
    assert parsed_tool["version"] == "1.0.0"
    assert_gx_int_parameters(parsed_tool["inputs"])
