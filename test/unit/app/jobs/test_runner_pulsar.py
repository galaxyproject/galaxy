import os
import re
from typing import (
    Any,
    cast,
)

import pytest

from galaxy.app_unittest_utils.tools_support import UsesTools
from galaxy.jobs.runners.pulsar import _tool_provided_metadata_client_outputs
from galaxy.model.store.discover import InvalidDiscoveredFilePathError
from galaxy.util.unittest import TestCase

INTERACTIVE_TOOL = """
<tool id="interactive_tool" name="Interactive Tool" tool_type="interactive" version="$version" profile="$profile">
    <entry_points>
        <entry_point name="Interactive Tool"><port>8080</port></entry_point>
    </entry_points>
    <outputs />
</tool>
"""
TOOL_WITH_EXTERNAL_METADATA_PATH = """
<tool id="external_metadata" name="External Metadata" version="$version" profile="$profile">
    <command>echo test</command>
    <inputs />
    <outputs provided_metadata_file="../outside.json" />
</tool>
"""


class TestPulsarToolProvidedMetadataClientOutputs(TestCase, UsesTools):
    def setUp(self):
        self.setup_app()
        cast(Any, self.app.config).interactivetools_enable = True
        self.tool_working_directory = os.path.join(self.test_directory, "working")
        os.makedirs(self.tool_working_directory)

    def tearDown(self):
        self.tear_down_app()

    def test_only_requests_enabled_tool_provided_metadata(self):
        enabled_tool = self._init_tool(profile="26.1", filename="enabled.xml")
        disabled_tool = self._init_tool(
            INTERACTIVE_TOOL,
            profile="26.1",
            filename="disabled.xml",
        )

        enabled_dynamic_output, enabled_file_sources = _tool_provided_metadata_client_outputs(
            enabled_tool, self.tool_working_directory
        )
        disabled_dynamic_output, disabled_file_sources = _tool_provided_metadata_client_outputs(
            disabled_tool, self.tool_working_directory
        )

        assert enabled_dynamic_output == re.escape("galaxy.json")
        assert enabled_file_sources == [{"path": "galaxy.json", "type": "galaxy"}]
        assert disabled_dynamic_output is None
        assert disabled_file_sources == []

    def test_rejects_metadata_path_outside_working_directory(self):
        tool = self._init_tool(
            TOOL_WITH_EXTERNAL_METADATA_PATH,
            profile="26.1",
            filename="external.xml",
        )

        with pytest.raises(InvalidDiscoveredFilePathError):
            _tool_provided_metadata_client_outputs(tool, self.tool_working_directory)
