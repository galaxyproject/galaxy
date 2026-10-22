import os

from galaxy.app_unittest_utils import tools_support
from galaxy.job_metrics import JobMetrics
from galaxy.jobs import JobConfiguration
from galaxy.tools import create_tool_from_source
from galaxy.util.unittest import TestCase

GUID = "toolshed.example.org/repos/nate/filter_tool_repo/filter_tool/1.0.0"
RESOURCE_PARAMS_XML = """<parameters>
    <param label="Memory" name="memory" type="integer" min="1" max="8" value="1" />
</parameters>
"""


class TestToolResourceParameters(TestCase, tools_support.UsesTools):
    def setUp(self):
        super().setUp()
        self.setup_app()
        self.app.config.job_resource_params_file = os.path.join(self.test_directory, "job_resource_params_conf.xml")
        with open(self.app.config.job_resource_params_file, "w") as f:
            f.write(RESOURCE_PARAMS_XML)
        self.app.config.default_job_resubmission_condition = ""
        self.app.config.use_tasked_jobs = False
        self.app.job_metrics = JobMetrics()

    def tearDown(self):
        self.tear_down_app()

    def test_full_guid(self):
        self._configure_tools([{"id": GUID, "resources": "memoryonly"}])
        assert self._has_resource_parameters(guid=GUID)

    def test_versionless_guid(self):
        self._configure_tools([{"id": GUID.rsplit("/", 1)[0], "resources": "memoryonly"}])
        assert self._has_resource_parameters(guid=GUID)

    def test_short_id_with_guid(self):
        self._configure_tools([{"id": "filter_tool", "resources": "memoryonly"}])
        assert self._has_resource_parameters(guid=GUID)

    def test_short_id_without_guid(self):
        self._configure_tools([{"id": "filter_tool", "resources": "memoryonly"}])
        assert self._has_resource_parameters()

    def test_guid_entry_without_resources_keeps_short_id_resources(self):
        self._configure_tools(
            [
                {"id": "filter_tool", "resources": "memoryonly"},
                {"id": GUID.rsplit("/", 1)[0], "environment": "local"},
            ]
        )
        assert self._has_resource_parameters(guid=GUID)

    def test_tool_class_resources_ignored(self):
        self._configure_tools([{"class": "requires_galaxy", "resources": "memoryonly"}])
        self.app.config.preserve_python_environment = "always"
        assert not self._has_resource_parameters(guid=GUID)

    def test_other_tool(self):
        self._configure_tools([{"id": "other_tool", "resources": "memoryonly"}])
        assert not self._has_resource_parameters(guid=GUID)

    def _configure_tools(self, tools):
        self.app.config.config_dict["job_config"] = {
            "runners": {"local": {"load": "galaxy.jobs.runners.local:LocalJobRunner"}},
            "execution": {"default": "local", "environments": {"local": {"runner": "local"}}},
            "tools": tools,
            "resources": {"groups": {"memoryonly": ["memory"]}},
        }
        self.app.job_config = JobConfiguration(self.app)

    def _has_resource_parameters(self, guid=None):
        self._init_tool(tool_id="filter_tool")
        tool = create_tool_from_source(self.app, self.tool_source, config_file=self.tool_file, guid=guid)
        return "__job_resource" in tool.inputs
