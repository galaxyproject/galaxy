from galaxy.app_unittest_utils import tools_support
from galaxy.tools import create_tool_from_source
from galaxy.util.unittest import TestCase


class TestToolResourceParameters(TestCase, tools_support.UsesTools):
    def setUp(self):
        super().setUp()
        self.setup_app()
        self.resource_xml_calls = []

        def get_tool_resource_xml(tool_ids, tool_type):
            self.resource_xml_calls.append(tool_ids)
            return None

        self.app.job_config.get_tool_resource_xml = get_tool_resource_xml

    def tearDown(self):
        self.tear_down_app()

    def test_tool_shed_guid_ids(self):
        self._init_tool(tool_id="filter_tool")
        guid = "toolshed.example.org/repos/nate/filter_tool_repo/filter_tool/1.0.0"
        self.resource_xml_calls.clear()
        create_tool_from_source(self.app, self.tool_source, config_file=self.tool_file, guid=guid)
        assert self.resource_xml_calls == [
            [
                "toolshed.example.org/repos/nate/filter_tool_repo/filter_tool/1.0.0",
                "toolshed.example.org/repos/nate/filter_tool_repo/filter_tool",
                "filter_tool",
            ]
        ]

    def test_tool_without_guid(self):
        self._init_tool(tool_id="filter_tool")
        assert self.resource_xml_calls == [["filter_tool"]]
