import os
import tempfile
from typing import cast
from unittest.mock import Mock

import pytest

from galaxy.datatypes.metadata import MetadataSpecCollection
from galaxy.job_execution.compute_environment import ComputeEnvironment
from galaxy.job_execution.datasets import DatasetPath
from galaxy.model import DatasetInstance
from galaxy.tools.parameters.basic import (
    BooleanToolParameter,
    DrillDownSelectToolParameter,
    FloatToolParameter,
    IntegerToolParameter,
    SelectToolParameter,
    TextToolParameter,
    ToolParameter,
)
from galaxy.tools.wrappers import (
    DatasetFilenameWrapper,
    InputValueWrapper,
    RawObjectWrapper,
    SelectToolParameterWrapper,
)
from galaxy.util import XML


def with_mock_tool(func):
    def call():
        test_directory = tempfile.mkdtemp()
        app = MockApp(test_directory)
        tool = MockTool(app)
        return func(tool)

    call.__name__ = func.__name__
    return call


def selectwrapper(tool, value, multiple=False, optional=False):
    optional = 'optional="true"' if optional else ""
    multiple = 'multiple="true"' if multiple else ""
    xml = XML(
        f"""<param name="blah" type="select" {multiple} {optional}>
        <option value="x">I am X</option>
        <option value="y" selected="true">I am Y</option>
        <option value="z">I am Z</option>
    </param>"""
    )
    parameter = SelectToolParameter(tool, xml)
    return SelectToolParameterWrapper(parameter, value)


@with_mock_tool
def test_select_wrapper_simple_options(tool):
    wrapper = selectwrapper(tool, "x")
    assert wrapper.name == "blah"
    assert str(wrapper) == "x"
    assert wrapper.value_label == "I am X"
    wrapper = selectwrapper(tool, None, optional=True)
    assert str(wrapper) == "None"
    assert wrapper == ""
    assert wrapper == "None"


@with_mock_tool
def test_select_wrapper_multiple_options(tool):
    wrapper = selectwrapper(tool, ["x"], multiple=True)
    assert wrapper.name == "blah"
    assert str(wrapper) == "x"
    assert "x" in wrapper
    wrapper = selectwrapper(tool, ["x", "z"], multiple=True)
    assert str(wrapper) == "x,z"
    assert "x" in wrapper
    wrapper = selectwrapper(tool, [], multiple=True)
    assert str(wrapper) == "None"
    assert wrapper == ""
    assert wrapper == "None"
    assert "x" not in wrapper


@with_mock_tool
def test_select_wrapper_with_drilldown(tool):
    parameter = _drilldown_parameter(tool)
    wrapper = SelectToolParameterWrapper(parameter, ["option3"])
    assert str(wrapper) == "option3", str(wrapper)


@with_mock_tool
def test_select_wrapper_option_file(tool):
    parameter = _setup_blast_tool(tool)
    wrapper = SelectToolParameterWrapper(parameter, "val2")
    assert str(wrapper) == "val2"
    assert wrapper.fields.name == "name2"
    assert wrapper.fields.path == "path2"


@with_mock_tool
def test_select_wrapper_multiple(tool):
    parameter = _setup_blast_tool(tool, multiple=True)
    wrapper = SelectToolParameterWrapper(parameter, ["val1", "val2"])
    assert str(wrapper) == "val1,val2"
    assert wrapper.fields.name == "name1,name2"


@with_mock_tool
def test_select_wrapper_with_path_rewritting(tool):
    parameter = _setup_blast_tool(tool, multiple=True)
    compute_environment = cast(ComputeEnvironment, MockComputeEnvironment(None))
    wrapper = SelectToolParameterWrapper(
        parameter, ["val1", "val2"], other_values={}, compute_environment=compute_environment
    )
    assert wrapper.fields.path == "Rewrite<path1>,Rewrite<path2>"


def test_raw_object_wrapper():
    obj = Mock(x=4)
    wrapper = RawObjectWrapper(obj)
    assert wrapper.x == 4
    assert wrapper

    false_wrapper = RawObjectWrapper(False)
    assert not false_wrapper


def valuewrapper(tool, value, paramtype, optional=False):
    parameter: ToolParameter
    if paramtype == "integer":
        optional = 'optional="true"' if optional else 'value="10"'
        parameter = IntegerToolParameter(tool, XML(f'<param name="blah" type="integer" {optional} min="0" />'))
    elif paramtype == "text":
        optional = 'optional="true"' if optional else 'value="foo"'
        parameter = TextToolParameter(tool, XML(f'<param name="blah" type="text" {optional}/>'))
    elif paramtype == "float":
        optional = 'optional="true"' if optional else 'value="10.0"'
        parameter = FloatToolParameter(tool, XML(f'<param name="blah" type="float" {optional}/>'))
    elif paramtype == "boolean":
        optional = 'optional="true"' if optional else 'value=""'
        parameter = BooleanToolParameter(
            tool, XML(f'<param name="blah" type="boolean" truevalue="truevalue" falsevalue="falsevalue" {optional}/>')
        )
    return InputValueWrapper(parameter, value)


@with_mock_tool
def test_input_value_wrapper_comparison(tool):
    wrapper = valuewrapper(tool, 5, "integer")
    assert str(wrapper) == "5"
    assert int(wrapper) == 5
    assert wrapper != "5"
    assert wrapper == 5
    assert wrapper == 5.0
    assert wrapper > 2
    assert wrapper < 10
    assert wrapper < 5.1
    wrapper = valuewrapper(tool, True, "boolean")
    assert bool(wrapper) is True, wrapper
    assert str(wrapper) == "truevalue"
    assert wrapper == "truevalue"
    assert wrapper == "true"
    wrapper = valuewrapper(tool, False, "boolean")
    assert bool(wrapper) is False, wrapper
    assert str(wrapper) == "falsevalue"
    assert wrapper == "falsevalue"
    assert wrapper == "false"


@with_mock_tool
def test_input_value_wrapper_comparison_optional(tool):
    wrapper = valuewrapper(tool, None, "integer", optional=True)
    assert not wrapper
    with pytest.raises(ValueError):
        int(wrapper)
    assert str(wrapper) == ""
    assert wrapper == ""  # for backward-compatibility
    wrapper = valuewrapper(tool, 0, "integer", optional=True)
    assert wrapper == 0
    assert int(wrapper) == 0
    assert str(wrapper)
    assert (
        wrapper != ""
    )  # for backward-compatibility, the correct way to check if an optional integer param is not empty is to use str(wrapper)
    wrapper = valuewrapper(tool, None, "integer", optional=True)
    assert wrapper != 1
    assert str(wrapper) == ""
    assert wrapper == None  # noqa: E711
    wrapper = valuewrapper(tool, None, "boolean", optional=True)
    assert bool(wrapper) is False, wrapper
    assert str(wrapper) == "falsevalue"


@with_mock_tool
def test_input_value_wrapper_input_value_wrapper_comparison(tool):
    wrapper = valuewrapper(tool, 5, "integer")
    assert str(wrapper) == valuewrapper(tool, "5", "text")
    assert int(wrapper) == valuewrapper(tool, "5", "integer")
    assert wrapper != valuewrapper(tool, "5", "text")
    assert wrapper == valuewrapper(tool, "5", "integer")
    assert wrapper == valuewrapper(tool, "5", "float")
    assert wrapper > valuewrapper(tool, "2", "integer")
    assert wrapper < valuewrapper(tool, "10", "integer")
    assert wrapper < valuewrapper(tool, "5.1", "float")


def test_dataset_wrapper():
    dataset = cast(DatasetInstance, MockDataset())
    wrapper = DatasetFilenameWrapper(dataset)
    assert str(wrapper) == MOCK_DATASET_PATH
    assert wrapper.file_name == MOCK_DATASET_PATH

    assert wrapper.ext == MOCK_DATASET_EXT


def test_dataset_wrapper_false_path():
    dataset = cast(DatasetInstance, MockDataset())
    new_path = "/new/path/dataset_123.dat"
    wrapper = DatasetFilenameWrapper(
        dataset, compute_environment=cast(ComputeEnvironment, MockComputeEnvironment(false_path=new_path))
    )
    assert str(wrapper) == new_path
    assert wrapper.file_name == new_path


class MockComputeEnvironment:
    def __init__(self, false_path, false_extra_files_path=None):
        self.false_path = false_path
        self.false_extra_files_path = false_extra_files_path

    def input_path_rewrite(self, dataset):
        return self.false_path

    def input_extra_files_rewrite(self, dataset):
        return self.false_extra_files_path

    def unstructured_path_rewrite(self, path):
        return f"Rewrite<{path}>"


def test_dataset_false_extra_files_path():
    dataset = cast(DatasetInstance, MockDataset())

    wrapper = DatasetFilenameWrapper(dataset)
    assert wrapper.extra_files_path == MOCK_DATASET_EXTRA_FILES_PATH

    new_path = "/new/path/dataset_123.dat"
    dataset_path = DatasetPath(123, MOCK_DATASET_PATH, false_path=new_path)
    wrapper = DatasetFilenameWrapper(
        dataset,
        compute_environment=cast(
            ComputeEnvironment, MockComputeEnvironment(dataset_path, MOCK_DATASET_EXTRA_FILES_PATH)
        ),
    )
    # Setting false_path is not enough to override
    assert wrapper.extra_files_path == MOCK_DATASET_EXTRA_FILES_PATH

    new_files_path = "/new/path/dataset_123_files"
    wrapper = DatasetFilenameWrapper(
        dataset,
        compute_environment=cast(
            ComputeEnvironment, MockComputeEnvironment(false_path=new_path, false_extra_files_path=new_files_path)
        ),
    )
    assert wrapper.extra_files_path == new_files_path


def _drilldown_parameter(tool):
    xml = XML(
        """<param name="some_name" type="drill_down" display="checkbox" hierarchy="recurse" multiple="true">
        <options>
            <option name="Heading 1" value="heading1">
                <option name="Option 1" value="option1"/>
                <option name="Option 2" value="option2"/>
                <option name="Heading 1" value="heading1">
                    <option name="Option 3" value="option3"/>
                    <option name="Option 4" value="option4"/>
               </option>
            </option>
           <option name="Option 5" value="option5"/>
      </options>
    </param>"""
    )
    parameter = DrillDownSelectToolParameter(tool, xml)
    return parameter


def _setup_blast_tool(tool, multiple=False):
    tool.app.write_test_tool_data("blastdb.loc", "val1\tname1\tpath1\nval2\tname2\tpath2\n")
    xml = XML(
        f"""<param name="database" type="select" label="Nucleotide BLAST database" multiple="{multiple}">
        <options from_file="blastdb.loc">
            <column name="value" index="0"/>
            <column name="name" index="1"/>
            <column name="path" index="2"/>
        </options>
    </param>"""
    )
    parameter = SelectToolParameter(tool, xml)
    return parameter


MOCK_DATASET_PATH = "/galaxy/database/files/001/dataset_123.dat"
MOCK_DATASET_EXTRA_FILES_PATH = "/galaxy/database/files/001/dataset_123.dat"
MOCK_DATASET_EXT = "bam"


class MockDataset:
    def __init__(self):
        self.metadata = MetadataSpecCollection({})
        self.extra_files_path = MOCK_DATASET_EXTRA_FILES_PATH
        self.ext = MOCK_DATASET_EXT
        self.tags = []
        self.has_deferred_data = False

    def get_file_name(self, sync_cache=True):
        return MOCK_DATASET_PATH


class MockTool:
    def __init__(self, app):
        self.app = app
        self.options = Mock(sanitize=False)
        self.profile = 23.0


class MockApp:
    def __init__(self, test_directory):
        self.config = Mock(tool_data_path=test_directory)

    def write_test_tool_data(self, name, contents):
        path = os.path.join(self.config.tool_data_path, name)
        open(path, "w").write(contents)
