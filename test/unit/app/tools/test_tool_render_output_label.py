from typing import Any

import pytest

from galaxy.app_unittest_utils import tools_support
from galaxy.exceptions import ConfigurationError
from galaxy.tool_util.parser.yaml import YamlToolSource
from galaxy.tools import (
    create_tool_from_source,
    Tool,
    UserDefinedTool,
)
from galaxy.util.unittest import TestCase

XML_TOOL = """<tool id="label_tool" name="Label Tool" version="1.0">
    <command>echo hi > $out1</command>
    <inputs>
        <param type="integer" name="n" value="1" />
    </inputs>
    <outputs>
        <data name="out1" format="txt" label="${tool.name} n=${n} on ${on_string}" />
    </outputs>
</tool>
"""
USER_TOOL: dict[str, Any] = {
    "class": "GalaxyUserTool",
    "id": "label_tool",
    "name": "Label Tool",
    "version": "1.0",
    "container": "busybox",
    "shell_command": "echo hi > out.txt",
    "inputs": [{"type": "integer", "name": "n", "value": 1}],
    # Stored rows are not re-validated, so the parser can still hand over a Cheetah label.
    "outputs": [{"type": "data", "name": "out1", "from_work_dir": "out.txt", "label": "n=$(inputs.n) ${1 + 1}"}],
}


class TestToolRenderOutputLabel(TestCase, tools_support.UsesTools):
    def setUp(self):
        self.setup_app()

    def tearDown(self):
        self.tear_down_app()

    def _label(self, tool: Tool) -> str:
        label = tool.outputs["out1"].label
        assert label is not None
        return label

    def test_unprivileged_tool_label_never_cheetah_filled(self):
        tool = self._init_tool(XML_TOOL)
        tool.is_unprivileged_tool = True
        with pytest.raises(ConfigurationError):
            tool.render_output_label(self._label(tool), {"n": 3}, "dataset 1")

    def test_user_tool_label_reads_tool_state_not_cheetah_context(self):
        tool = create_tool_from_source(self.app, YamlToolSource(USER_TOOL))
        assert isinstance(tool, UserDefinedTool)
        cheetah_context: dict[str, Any] = {"n": 3}
        label = tool.render_output_label(self._label(tool), cheetah_context, "dataset 1", tool_state={"n": 4})
        assert label == "n=4 ${1 + 1}"
        assert cheetah_context == {"n": 3}
