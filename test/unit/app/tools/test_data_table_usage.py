import json
from typing import Any
from unittest.mock import Mock

import pytest

from galaxy.model import (
    Job,
    JobParameter,
)
from galaxy.model.unittest_utils import GalaxyDataTestApp
from galaxy.tool_util.parser import get_tool_source
from galaxy.tools import create_tool_from_source

CONDITIONAL = """
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
"""
HDA = {"src": "hda", "id": 1}


class ToolApp(GalaxyDataTestApp):
    name = "galaxy"
    biotools_metadata_source = None
    job_search = None
    is_webapp = True
    tool_data_tables: dict[str, Any]


def load_tool(inputs):
    app = ToolApp()
    app.tool_data_tables = {}
    xml = f'<tool id="t" name="t" version="1.0" profile="24.0"><command>x</command><inputs>{inputs}</inputs></tool>'
    source = get_tool_source(tool_source_class="XmlToolSource", raw_tool_source=xml)
    return create_tool_from_source(app, tool_source=source)


def persisted_job(tool, values=None, raw=None):
    """A job with parameters serialized the way Galaxy persists them."""
    job = Job()
    raw = raw if raw is not None else tool.params_to_strings(values, tool.app)
    for name, value in raw.items():
        job.parameters.append(JobParameter(name=name, value=value))
    return job


@pytest.mark.parametrize(
    "reference_source,expected",
    [
        ({"source": "indexed", "reference": "hg38"}, True),
        ({"source": "indexed", "reference": None}, False),
        # A data manager bundle from the history offered as a table entry.
        ({"source": "indexed", "reference": HDA}, False),
        ({"source": "history", "reference": HDA}, False),
    ],
)
def test_active_table_selection(reference_source, expected):
    tool = load_tool(CONDITIONAL)
    assert tool.has_data_table
    assert tool.is_using_data_table(persisted_job(tool, {"reference_source": reference_source})) is expected


def test_nested_repeats_and_sections():
    tool = load_tool(
        '<repeat name="references" title="References"><section name="settings" title="Settings">'
        f"{CONDITIONAL}</section></repeat>"
    )

    def item(index, source, reference):
        return {"__index__": index, "settings": {"reference_source": {"source": source, "reference": reference}}}

    history = item(0, "history", HDA)
    assert not tool.is_using_data_table(persisted_job(tool, {"references": []}))
    assert not tool.is_using_data_table(persisted_job(tool, {"references": [history]}))
    assert tool.is_using_data_table(persisted_job(tool, {"references": [history, item(1, "indexed", "hg38")]}))


def test_data_input_with_table_options_is_not_a_table_select():
    tool = load_tool('<param name="input" type="data" format="txt"><options from_data_table="test_indexes" /></param>')
    assert not tool.has_data_table
    assert not tool.is_using_data_table(persisted_job(tool, {"input": HDA}))


def test_tool_without_tables_does_not_load_parameters():
    tool = load_tool('<param name="input" type="data" format="txt" />')
    job = Mock(spec=Job, raw_param_dict=Mock(side_effect=AssertionError("parameters loaded")))
    assert not tool.has_data_table
    assert not tool.is_using_data_table(job)


@pytest.mark.parametrize("state", ["not json", "[]", '{"source": "removed_case"}'])
def test_stale_state_is_not_table_usage(state):
    tool = load_tool(CONDITIONAL)
    assert not tool.is_using_data_table(persisted_job(tool, raw={"reference_source": state}))


def test_stale_unrelated_state_keeps_table_usage():
    tool = load_tool(f'<section name="extra" title="Extra"><param name="text" type="text" /></section>{CONDITIONAL}')
    raw = {"extra": "[]", "reference_source": json.dumps({"source": "indexed", "reference": "hg38"})}
    assert tool.is_using_data_table(persisted_job(tool, raw=raw))
