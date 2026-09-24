from types import SimpleNamespace
from typing import cast

from galaxy.app_unittest_utils.tools_support import UsesTools
from galaxy.tool_util.toolbox.base import ToolLike
from galaxy.util.unittest import TestCase
from galaxy.webapps.galaxy.services.tools import (
    dataset_input_match,
    iter_data_inputs,
    latest_tool_versions,
)

NESTED_INPUTS_TOOL = """<tool id="nested_inputs" name="Nested inputs" version="1.0">
    <command>true</command>
    <inputs>
        <param name="top" type="data" format="tabular" />
        <section name="sec" title="Section">
            <param name="in_section" type="data" format="tabular" />
        </section>
        <conditional name="cond">
            <param name="mode" type="select">
                <option value="a">A</option>
                <option value="b">B</option>
            </param>
            <when value="a">
                <param name="in_default_case" type="data" format="tabular" />
            </when>
            <when value="b">
                <param name="in_other_case" type="data" format="tabular" />
                <repeat name="other_rep" title="Repeat in other case">
                    <param name="in_other_case_repeat" type="data" format="tabular" />
                </repeat>
            </when>
        </conditional>
        <repeat name="rep" title="Repeat">
            <param name="in_repeat" type="data" format="tabular" />
        </repeat>
        <param name="collection" type="data_collection" collection_type="list" />
    </inputs>
    <outputs />
</tool>
"""

TIE_TOOL = """<tool id="tie" name="Tie" version="1.0">
    <command>true</command>
    <inputs>
        <conditional name="cond">
            <param name="mode" type="select">
                <option value="a">A</option>
                <option value="b">B</option>
            </param>
            <when value="a" />
            <when value="b">
                <param name="not_prefillable" type="data" format="tabular" />
            </when>
        </conditional>
        <param name="prefillable" type="data" format="tabular" />
    </inputs>
    <outputs />
</tool>
"""

RANK_TOOL = """<tool id="rank" name="Rank" version="1.0">
    <command>true</command>
    <inputs>
        <param name="any" type="data" format="data" />
        <conditional name="cond">
            <param name="mode" type="select">
                <option value="a">A</option>
                <option value="b">B</option>
            </param>
            <when value="a" />
            <when value="b">
                <param name="specific" type="data" format="tabular" />
            </when>
        </conditional>
    </inputs>
    <outputs />
</tool>
"""


class TestInteractiveToolMatching(TestCase, UsesTools):
    def setUp(self):
        self.setup_app()

    def tearDown(self):
        self.tear_down_app()

    def test_iter_data_inputs_names(self):
        tool = self._init_tool(NESTED_INPUTS_TOOL)
        assert [(name, param.name) for name, param in iter_data_inputs(tool.inputs)] == [
            ("top", "top"),
            ("sec|in_section", "in_section"),
            ("cond|in_default_case", "in_default_case"),
            (None, "in_other_case"),
            (None, "in_other_case_repeat"),
            ("rep_0|in_repeat", "in_repeat"),
        ]

    def test_match_prefers_prefillable_input_on_equal_rank(self):
        tool = self._init_tool(TIE_TOOL)
        assert dataset_input_match(self.app.datatypes_registry, "tabular", tool.inputs) == ("prefillable", "direct")

    def test_match_prefers_better_rank_over_prefillable_input(self):
        tool = self._init_tool(RANK_TOOL)
        assert dataset_input_match(self.app.datatypes_registry, "tabular", tool.inputs) == (None, "direct")
        assert dataset_input_match(self.app.datatypes_registry, "bam", tool.inputs) == ("any", "generic")

    def test_no_match(self):
        tool = self._init_tool(TIE_TOOL)
        assert dataset_input_match(self.app.datatypes_registry, "bam", tool.inputs) is None


def test_latest_tool_versions_keeps_newest_per_lineage():
    tools = [
        SimpleNamespace(id="toolshed.example.org/repos/o/r/tool_x/1.0", version="1.0"),
        SimpleNamespace(id="toolshed.example.org/repos/o/r/tool_x/10.0", version="10.0"),
        SimpleNamespace(id="toolshed.example.org/repos/o/r/tool_x/2.0", version="2.0"),
        SimpleNamespace(id="local_tool", version="0.1"),
    ]
    latest = latest_tool_versions(cast(list[ToolLike], tools))
    assert [tool.id for tool in latest] == ["toolshed.example.org/repos/o/r/tool_x/10.0", "local_tool"]
