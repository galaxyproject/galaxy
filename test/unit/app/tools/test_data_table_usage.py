import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from galaxy.model import (
    Job,
    JobParameter,
)
from galaxy.model.unittest_utils import GalaxyDataTestApp
from galaxy.tool_util.parser import get_tool_source
from galaxy.tools import (
    create_tool_from_source,
    Tool,
)

XML_TOOL = """
<tool id="table_usage" name="Table usage" version="1.0" profile="24.0">
  <command>echo reference</command>
  <inputs>
    <conditional name="reference_source">
      <param name="source" type="select">
        <option value="indexed">Installed reference</option>
        <option value="history">History reference</option>
      </param>
      <when value="indexed">
        <param name="reference" type="select">
          <options from_data_table="test_indexes" />
        </param>
      </when>
      <when value="history">
        <param name="reference" type="data" format="fasta" />
      </when>
    </conditional>
  </inputs>
</tool>
"""


class ToolApp(GalaxyDataTestApp):
    name = "galaxy"
    biotools_metadata_source = None
    job_search = None
    is_webapp = True


def load_tool(xml):
    app = ToolApp()
    app.tool_data_tables = {}
    source = get_tool_source(tool_source_class="XmlToolSource", raw_tool_source=xml)
    return create_tool_from_source(app, tool_source=source)


@pytest.fixture
def tool():
    return load_tool(XML_TOOL)


def test_nested_repeats_and_sections():
    xml = XML_TOOL.replace(
        '<conditional name="reference_source">',
        '<repeat name="references" title="References"><section name="settings" title="Settings">'
        '<conditional name="reference_source">',
    ).replace("</conditional>", "</conditional></section></repeat>")
    tool = load_tool(xml)
    history = {
        "settings": {
            "reference_source": {
                "source": "history",
                "reference": {"src": "hda", "id": 1},
            }
        }
    }
    indexed = {"settings": {"reference_source": {"source": "indexed", "reference": "hg38"}}}
    for values, expected in [
        ([], False),
        ([history], False),
        ([history, indexed], True),
    ]:
        job = SimpleNamespace(raw_param_dict=lambda: {"references": json.dumps(values)})
        assert tool.has_data_table
        assert tool.is_using_data_table(job) is expected


@pytest.mark.parametrize(
    "source,selection,expected",
    [
        ("indexed", "hg38", True),
        ("indexed", None, False),
        ("indexed", [], False),
        ("indexed", ["hg38", "mm10"], True),
        ("indexed", {"src": "hda", "id": 1}, False),
        ("history", {"src": "hda", "id": 1}, False),
        ("history", "stale table value", False),
    ],
)
def test_tool_detects_active_table_selection(tool, source, selection, expected):
    job = Job()
    job.parameters.append(
        JobParameter(
            name="reference_source",
            value=json.dumps(
                {
                    "source": source,
                    "reference": selection,
                    "__current_case__": 0,
                }
            ),
        )
    )
    assert tool.has_data_table
    assert tool.is_using_data_table(job) is expected


def test_tree_is_cached_for_tool_instance(tool):
    assert tool.has_data_table
    tree = tool._data_table_parameters
    assert tool.has_data_table
    assert tool._data_table_parameters is tree


def test_tool_without_tables_does_not_load_parameters():
    tool = object.__new__(Tool)
    tool.inputs = {}
    job = SimpleNamespace(raw_param_dict=Mock(side_effect=AssertionError("parameters loaded")))
    assert not tool.has_data_table
    assert not tool.is_using_data_table(job)


def test_job_result_is_not_cached_on_tool(tool):
    state = {"source": "indexed", "reference": "hg38"}
    job = SimpleNamespace(raw_param_dict=lambda: {"reference_source": json.dumps(state)})
    assert tool.is_using_data_table(job)
    state["source"] = "history"
    assert not tool.is_using_data_table(job)


def test_unrelated_parameter_is_not_deserialized(tool):
    job = SimpleNamespace(
        raw_param_dict=lambda: {
            "reference_source": json.dumps({"source": "indexed", "reference": "hg38"}),
            "unrelated_dataset": "not json",
        }
    )
    assert tool.is_using_data_table(job)


@pytest.mark.parametrize("state", ["not json", "[]", "{}", '{"source": "removed_case"}'])
def test_invalid_relevant_state_raises(tool, state):
    job = SimpleNamespace(raw_param_dict=lambda: {"reference_source": state})
    with pytest.raises(ValueError):
        tool.is_using_data_table(job)
