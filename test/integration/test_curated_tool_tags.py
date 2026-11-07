import os

from galaxy_test.driver import integration_util
from galaxy_test.driver.driver_util import FRAMEWORK_TOOLS_DIR

TOOL_CONF = f"""<?xml version="1.0"?>
<toolbox tool_path="{FRAMEWORK_TOOLS_DIR}">
  <tool file="simple_constructs.xml" />
  <tool file="empty_select.xml" hidden="true" />
</toolbox>
"""

TOOL_TAG_MAPPINGS = """tool_tags:
  simple_constructs: [Visible Tag]
  empty_select: [Hidden Tag]
"""


class TestCuratedToolTagsVisibility(integration_util.IntegrationTestCase):
    framework_tool_and_types = True

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config_dir = cls._test_driver.mkdtemp()
        tool_conf_path = os.path.join(config_dir, "tool_conf.xml")
        with open(tool_conf_path, "w") as f:
            f.write(TOOL_CONF)
        tool_tag_mappings_path = os.path.join(config_dir, "tool_tag_mappings.yml")
        with open(tool_tag_mappings_path, "w") as f:
            f.write(TOOL_TAG_MAPPINGS)
        config["tool_config_file"] = tool_conf_path
        config["tool_tag_mappings_file"] = tool_tag_mappings_path

    def test_tool_tags_omit_hidden_tools(self):
        response = self._get("tags/tool_tags")
        self._assert_status_code_is(response, 200)
        assert response.json() == {"simple_constructs": ["Visible Tag"]}
