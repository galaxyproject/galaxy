import logging
from typing import (
    cast,
    TYPE_CHECKING,
)
from unittest import mock

import pytest

from galaxy.app_unittest_utils.galaxy_mock import MockApp
from galaxy.model import (
    HistoryDatasetAssociation,
    User,
    WorkflowStepConnection,
)
from galaxy.tools.data import ToolDataTableManager
from galaxy.tools.parameters.basic import SelectToolParameter
from galaxy.tools.wrappers import SelectToolParameterWrapper
from galaxy.util import XML
from galaxy.util.bunch import Bunch
from galaxy.work.context import WorkRequestContext
from galaxy.workflow.modules import (
    InputParameterModule,
    ToolModule,
)

if TYPE_CHECKING:
    from galaxy.tools import Tool


@pytest.fixture
def table_select(tmp_path):
    loc = tmp_path / "refs.loc"
    loc.write_text(
        "hg38\tHuman old\t4.3\t/a/hg38.fa\n"
        "hg38\tHuman current\t5.0\t/b/hg38.fa\n"
        "hg38\tHuman alternate\t5.0\t/c/hg38.fa\n"
        "mm10\tMouse\t5.0\t/mouse.fa\n"
    )
    config = tmp_path / "tables.xml"
    config.write_text(f"""<tables><table name="refs">
        <columns>value, name, version, path</columns><file path="{loc}" />
    </table></tables>""")
    app = MockApp()
    app.tool_data_tables = ToolDataTableManager(tmp_path, str(config))
    trans = WorkRequestContext(app=app)
    tool = cast("Tool", Bunch(app=app, profile=26.1))

    def build(options_xml='<options from_data_table="refs"/>', multiple=False):
        param = SelectToolParameter(
            tool, XML(f'<param name="ref" type="select" multiple="{multiple}">{options_xml}</param>')
        )
        return param, trans

    return build


VERSION_FILTER = '<filter type="static_value" column="version" value="5.0"/>'
REVERSE_PATH_SORT = '<filter type="sort_by" column="path" reverse_sort_order="True"/>'


def _reload_cases(table_select, filters, multiple=False):
    param, trans = table_select(f'<options from_data_table="refs">{filters}</options>', multiple=multiple)
    yield param, trans
    trans.app.tool_data_tables.reload_tables()
    yield param, trans


@pytest.mark.parametrize("multiple", [False, True])
@pytest.mark.parametrize(
    "filters, expected_options, count",
    [
        ("", [("Human old", "hg38", False), ("Mouse", "mm10", False)], 4),
        (VERSION_FILTER, [("Human current", "hg38", False), ("Mouse", "mm10", False)], 3),
        (VERSION_FILTER + REVERSE_PATH_SORT, [("Mouse", "mm10", False), ("Human alternate", "hg38", False)], 3),
    ],
)
def test_table_dropdown_collapses_after_filters(table_select, multiple, filters, expected_options, count):
    for param, trans in _reload_cases(table_select, filters, multiple=multiple):
        assert param.to_dict(trans)["options"] == expected_options
        assert len(param.get_options(trans, {})) == count
        assert len(trans.app.tool_data_tables["refs"].data) == 4


@pytest.mark.parametrize("multiple", [False, True])
@pytest.mark.parametrize(
    "filters, path",
    [("", "/a/hg38.fa"), (VERSION_FILTER, "/b/hg38.fa"), (VERSION_FILTER + REVERSE_PATH_SORT, "/c/hg38.fa")],
)
def test_table_dropdown_hidden_choices_stay_valid(table_select, caplog, multiple, filters, path):
    expected = ["hg38"] if multiple else "hg38"
    for param, trans in _reload_cases(table_select, filters, multiple=multiple):
        # Both labels remain valid aliases, even when hidden in the dropdown.
        for alias in ("Human current", "Human alternate"):
            assert param.from_json([alias] if multiple else alias, trans) == expected
        assert param.from_json(expected, trans) == expected
        caplog.clear()
        with caplog.at_level(logging.WARNING):
            assert SelectToolParameterWrapper(param, expected).fields.path == path
        assert any(
            record.levelno == logging.WARNING and "using the first one" in record.message for record in caplog.records
        )


def test_table_dropdown_uses_configured_value_column(table_select):
    param, trans = table_select("""<options from_data_table="refs">
        <column name="value" index="3"/><column name="name" index="1"/><column name="path" index="3"/>
    </options>""")
    assert [option[1] for option in param.to_dict(trans)["options"]] == [
        "/a/hg38.fa",
        "/b/hg38.fa",
        "/c/hg38.fa",
        "/mouse.fa",
    ]
    assert SelectToolParameterWrapper(param, "/c/hg38.fa").fields.path == "/c/hg38.fa"


def test_table_dropdown_keeps_dataset_choices(table_select, monkeypatch):
    param, trans = table_select()
    trans = WorkRequestContext(app=trans.app, user=User())
    datasets = [HistoryDatasetAssociation(id=1), HistoryDatasetAssociation(id=2)]
    # User bundles append the HDA after the configured table columns.
    monkeypatch.setattr(
        param.options,
        "get_user_options",
        lambda user: [["hg38", f"Bundle {hda.id}", "5.0", "/bundle/hg38.fa", hda] for hda in datasets],
    )
    assert param.to_dict(trans)["options"] == [
        ("Human old", "hg38", False),
        ("Mouse", "mm10", False),
        ("Bundle 1", {"src": "hda", "id": trans.security.encode_id(1)}, False),
        ("Bundle 2", {"src": "hda", "id": trans.security.encode_id(2)}, False),
    ]


def test_non_table_dropdown_keeps_duplicate_values(table_select):
    _, trans = table_select()
    tool = cast("Tool", Bunch(app=trans.app, profile=26.1, ref_lines=["hg38\tFirst\n", "hg38\tSecond\n"]))
    param = SelectToolParameter(
        tool,
        XML("""<param name="ref" type="select"><options from_parameter="tool.ref_lines">
            <column name="value" index="0"/><column name="name" index="1"/>
        </options></param>"""),
    )
    assert param.to_dict(trans)["options"] == [("First", "hg38", False), ("Second", "hg38", False)]


def test_workflow_restricted_options_collapse_table_choices(table_select):
    param, trans = table_select()
    tool_module = mock.Mock(spec=ToolModule)
    tool_module.tool = Bunch(inputs={"ref": param})
    tool_module.state = Bunch(inputs={})
    connection = cast(WorkflowStepConnection, Bunch(input_step=Bunch(module=tool_module), input_name="ref"))
    options = InputParameterModule(trans).restrict_options(None, [connection], "hg38")
    assert options == [
        {"label": "Human old", "value": "hg38", "selected": True},
        {"label": "Mouse", "value": "mm10", "selected": False},
    ]
