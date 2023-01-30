import os
import tempfile

import pytest

from galaxy.tool_util.lint import (
    lint_tool_source_with,
    lint_xml_with,
    LintContext,
    XMLLintMessageLine,
    XMLLintMessageXPath,
)
from galaxy.tool_util.linters import (
    citations,
    command,
    general,
    help,
    inputs,
    outputs,
    stdio,
    tests,
    xml_order,
)
from galaxy.tool_util.loader_directory import load_tool_sources_from_path
from galaxy.tool_util.parser.xml import XmlToolSource
from galaxy.util import parse_xml
from galaxy.util.xml_macros import load_with_references

# TODO tests tool xml for general linter
# tests tool xml for citations linter
CITATIONS_MULTIPLE = """
<tool>
    <citations/>
    <citations/>
</tool>
"""

CITATIONS_ABSENT = """
<tool/>
"""

CITATIONS_ERRORS = """
<tool>
    <citations>
        <nonsense/>
        <citation type="hoerensagen"/>
        <citation type="doi"> </citation>
    </citations>
</tool>
"""

CITATIONS_VALID = """
<tool>
    <citations>
        <citation type="doi">DOI</citation>
    </citations>
</tool>
"""

# tests tool xml for command linter
COMMAND_MULTIPLE = """
<tool>
    <command/>
    <command/>
</tool>
"""
COMMAND_MISSING = """
<tool/>
"""
COMMAND_TODO = """
<tool>
    <command>
        ## TODO
    </command>
</tool>
"""
COMMAND_DETECT_ERRORS_INTERPRETER = """
<tool>
    <command detect_errors="nonsense" interpreter="python"/>
</tool>
"""


# tests tool xml for general linter
GENERAL_MISSING_TOOL_ID_NAME_VERSION = """
<tool profile="2109">
</tool>
"""

GENERAL_WHITESPACE_IN_VERSIONS_AND_NAMES = """
<tool name=" BWA Mapper " id="bwa tool" version=" 1.0.1 " is_multi_byte="true" display_interface="true" require_login="true" hidden="true">
    <requirements>
        <requirement type="package" version=" 1.2.5 "> bwa </requirement>
    </requirements>
</tool>
"""

GENERAL_REQUIREMENT_WO_VERSION = """
<tool name="BWA Mapper" id="bwa_tool" version="1.0.1blah" is_multi_byte="true" display_interface="true" require_login="true" hidden="true" profile="20.09">
    <requirements>
        <requirement type="package">bwa</requirement>
        <requirement type="package" version="1.2.5"></requirement>
    </requirements>
</tool>
"""

GENERAL_VALID = """
<tool name="valid name" id="valid_id" version="1.0+galaxy1" profile="21.09">
</tool>
"""

# test tool xml for help linter
HELP_MULTIPLE = """
<tool>
    <help>Help</help>
    <help>More help</help>
</tool>
"""

HELP_ABSENT = """
<tool>
</tool>
"""

HELP_EMPTY = """
<tool>
    <help> </help>
</tool>
"""

HELP_TODO = """
<tool>
    <help>TODO</help>
</tool>
"""

HELP_INVALID_RST = """
<tool>
    <help>
        **xxl__
    </help>
</tool>
"""

# test tool xml for inputs linter
INPUTS_NO_INPUTS = """
<tool>
</tool>
"""

INPUTS_NO_INPUTS_DATASOURCE = """
<tool tool_type="data_source">
    <inputs/>
</tool>
"""

INPUTS_VALID = """
<tool>
    <inputs>
        <param name="txt_param" type="text"/>
        <param name="int_param" type="integer"/>
    </inputs>
</tool>
"""

INPUTS_PARAM_NAME = """
<tool>
    <inputs>
        <param type="text"/>
        <param name="" type="text"/>
        <param name="2" type="text"/>
        <param argument="--valid" type="text"/>
        <param name="param_name" argument="--param-name" type="text"/>
    </inputs>
</tool>
"""

INPUTS_PARAM_TYPE = """
<tool>
    <inputs>
        <param name="valid_name"/>
        <param argument="--another-valid-name" type=""/>
    </inputs>
</tool>
"""

INPUTS_DATA_PARAM = """
<tool>
    <inputs>
        <param name="valid_name" type="data"/>
    </inputs>
</tool>
"""

INPUTS_DATA_PARAM_OPTIONS = """
<tool>
    <inputs>
        <param name="valid_name" type="data" format="txt">
            <options>
                <filter type="data_meta" key="dbkey" ref="input"/>
            </options>
        </param>
    </inputs>
</tool>
"""

INPUTS_DATA_PARAM_OPTIONS_FILTER_ATTRIBUTE = """
<tool>
    <inputs>
        <param name="valid_name" type="data" format="txt">
            <options options_filter_attribute="metadata.foo">
                <filter type="data_meta" key="foo" ref="input"/>
            </options>
        </param>
    </inputs>
</tool>
"""

INPUTS_DATA_PARAM_INVALIDOPTIONS = """
<tool>
    <inputs>
        <param name="valid_name" type="data" format="txt">
            <options/>
            <options from_file="blah">
                <filter type="expression"/>
            </options>
        </param>
    </inputs>
</tool>
"""

INPUTS_CONDITIONAL = """
<tool>
    <inputs>
        <conditional>
            <param name="select" type="select"/>
        </conditional>
        <conditional name="cond_wo_param">
        </conditional>
        <conditional name="cond_w_mult_param">
            <param name="select3" type="select"><option value="A">A</option><option value="B">B</option></param>
            <param name="select4" type="select"><option value="A">A</option><option value="B">B</option></param>
            <when value="A"/>
            <when value="B"/>
        </conditional>
        <conditional name="cond_boolean">
            <param name="bool" type="boolean"/>
            <when value="true"/>
            <when value="false"/>
            <when value="False"/>
        </conditional>
        <conditional name="cond_text">
            <param name="text" type="text"/>
        </conditional>
        <conditional name="cond_w_optional_select">
            <param name="optionalselect" type="select" optional="true"><option value="A">A</option><option value="B">B</option></param>
            <when value="A"/>
            <when value="B"/>
        </conditional>
        <conditional name="cond_w_multiple_select">
            <param name="multipleselect" type="select" multiple="true"><option value="A">A</option><option value="B">B</option></param>
            <when value="A"/>
            <when value="B"/>
        </conditional>
        <conditional name="when_wo_value">
            <param name="select3" type="select"><option value="A">A</option><option value="B">B</option></param>
            <when/>
            <when value="A"/>
            <when value="B"/>
        </conditional>
        <conditional name="missing_when">
            <param name="label_select" type="select">
                <option value="none" selected="True">None</option>
            </param>
        </conditional>
        <conditional name="missing_option">
            <param name="missing_option" type="select">
                <option value="none" selected="True">None</option>
            </param>
            <when value="none"/>
            <when value="absent"/>
        </conditional>
    </inputs>
</tool>
"""

INPUTS_SELECT_INCOMPATIBLE_DISPLAY = """
<tool>
    <inputs>
        <param name="radio_select" type="select" display="radio" optional="true" multiple="true">
            <option value="1">1</option>
            <option value="2">2</option>
        </param>
        <param name="checkboxes_select" type="select" display="checkboxes" optional="false" multiple="false">
            <option value="1">1</option>
            <option value="2">2</option>
        </param>
        <!-- this must not raise any warning/error since multiple=true implies true as default for optional -->
        <param name="checkboxes_select_correct" type="select" display="checkboxes" multiple="true">
            <option value="1">1</option>
            <option value="2">2</option>
        </param>
    </inputs>
</tool>
"""

INPUTS_SELECT_DUPLICATED_OPTIONS = """
<tool>
    <inputs>
        <param name="select" type="select" optional="true" multiple="true">
            <option value="v">x</option>
            <option value="v">x</option>
        </param>
    </inputs>
</tool>
"""

SELECT_DUPLICATED_OPTIONS_WITH_DIFF_SELECTED = """
<tool>
    <inputs>
        <param name="select" type="select" optional="true" multiple="true">
            <option value="v">x</option>
            <option value="v" selected="true">x</option>
        </param>
    </inputs>
</tool>
"""

INPUTS_SELECT_DEPRECATIONS = """
<tool>
    <inputs>
        <param name="select_do" type="select" dynamic_options="blah()"/>
        <param name="select_ff" type="select">
            <options from_file="file.tsv" transform_lines="narf()"/>
        </param>
        <param name="select_fp" type="select">
            <options from_parameter="select_do" options_filter_attribute="fasel"/>
        </param>
    </inputs>
</tool>
"""

INPUTS_SELECT_OPTION_DEFINITIONS = """
<tool>
    <inputs>
        <param name="select_noopt" type="select"/>
        <param name="select_noopts" type="select">
            <options/>
        </param>
        <param name="select_fd_op" type="select">
            <options from_dataset="xyz"/>
            <options from_data_table="xyz"/>
            <option value="x">x</option>
        </param>
        <param name="select_fd_fdt" type="select">
            <options from_dataset="xyz" from_data_table="xyz"/>
        </param>
        <param name="select_noval_notext" type="select">
            <option>option wo value</option>
            <option value="value"/>
        </param>
        <param name="select_meta_file_key_incomp" type="select">
            <options from_data_table="xyz" meta_file_key="dbkey"/>
        </param>
    </inputs>
</tool>
"""

INPUTS_SELECT_FILTER = """
<tool>
    <inputs>
        <param name="select_filter_types" type="select">
            <options from_data_table="xyz">
                <filter/>
                <filter type="unknown_filter_type"/>
            </options>
        </param>
    </inputs>
</tool>
"""

INPUTS_VALIDATOR_INCOMPATIBILITIES = """
<tool>
    <inputs>
        <param name="param_name" type="text">
            <validator type="in_range">TEXT</validator>
            <validator type="regex" filename="blah"/>
            <validator type="expression"/>
            <validator type="expression">[</validator>
            <validator type="value_in_data_table"/>
        </param>
        <param name="another_param_name" type="data" format="bed">
            <validator type="metadata"/>
        </param>
    </inputs>
</tool>
"""

INPUTS_VALIDATOR_CORRECT = """
<tool>
    <inputs>
        <param name="data_param" type="data" format="data">
            <validator type="metadata" check="md1,md2" skip="md3,md4" message="custom validation message" negate="true"/>
            <validator type="unspecified_build" message="custom validation message" negate="true"/>
            <validator type="dataset_ok_validator" message="custom validation message" negate="true"/>
            <validator type="dataset_metadata_in_range" metadata_name="sequences" min="0" max="100" exclude_min="true" exclude_max="true" message="custom validation message" negate="true"/>
            <validator type="dataset_metadata_in_file" filename="file.tsv" metadata_column="3" split="," metadata_name="dbkey" message="custom validation message" negate="true"/>
            <validator type="dataset_metadata_in_data_table" table_name="datatable_name" metadata_column="3" metadata_name="dbkey" message="custom validation message" negate="true"/>
        </param>
        <param name="collection_param" type="collection">
            <validator type="metadata" check="md1,md2" skip="md3,md4" message="custom validation message"/>
            <validator type="unspecified_build" message="custom validation message"/>
            <validator type="dataset_ok_validator" message="custom validation message"/>
            <validator type="dataset_metadata_in_range" metadata_name="sequences" min="0" max="100" exclude_min="true" exclude_max="true" message="custom validation message"/>
            <validator type="dataset_metadata_in_file" filename="file.tsv" metadata_column="3" split="," metadata_name="dbkey" message="custom validation message"/>
            <validator type="dataset_metadata_in_data_table" table_name="datatable_name" metadata_column="3" metadata_name="dbkey" message="custom validation message"/>
        </param>
        <param name="text_param" type="text">
            <validator type="regex">reg.xp</validator>
            <validator type="length" min="0" max="100" message="custom validation message"/>
            <validator type="empty_field" message="custom validation message"/>
            <validator type="value_in_data_table" table_name="datatable_name" metadata_column="3" message="custom validation message"/>
            <validator type="expression" message="custom validation message">somepythonexpression</validator>
        </param>
        <param name="select_param" type="select">
            <options from_data_table="bowtie2_indexes"/>
            <validator type="no_options" negate="true"/>
            <validator type="regex" negate="true">reg.xp</validator>
            <validator type="length" min="0" max="100" message="custom validation message" negate="true"/>
            <validator type="empty_field" message="custom validation message" negate="true"/>
            <validator type="value_in_data_table" table_name="datatable_name" metadata_column="3" message="custom validation message" negate="true"/>
            <validator type="expression" message="custom validation message" negate="true">somepythonexpression</validator>
        </param>
        <param name="int_param" type="integer">
            <validator type="in_range" min="0" max="100" exclude_min="true" exclude_max="true" negate="true"/>
            <validator type="expression" message="custom validation message">somepythonexpression</validator>
        </param>
    </inputs>
</tool>
"""

INPUTS_TYPE_CHILD_COMBINATIONS = """
<tool>
    <inputs>
        <param name="text_param" type="text">
            <options/>
        </param>
        <param name="select_param" type="select">
            <options from_data_table="data_table">
                <option name="x" value="y"/>
            </options>
        </param>
        <param name="data_param" type="data" format="tabular">
            <column/>
        </param>
    </inputs>
</tool>
"""


# test tool xml for outputs linter
OUTPUTS_MISSING = """
<tool/>
"""
OUTPUTS_MULTIPLE = """
<tool>
    <outputs/>
    <outputs/>
</tool>
"""
OUTPUTS_UNKNOWN_TAG = """
<tool>
    <outputs>
        <output/>
    </outputs>
</tool>
"""
OUTPUTS_UNNAMED_INVALID_NAME = """
<tool>
    <outputs>
        <data label="data out"/>
        <collection name="2output" label="coll out"/>
    </outputs>
</tool>
"""
OUTPUTS_FORMAT_INPUT = """
<tool>
    <outputs>
        <data name="valid_name" format="input"/>
    </outputs>
</tool>
"""

# check that linter accepts format source for collection elements as means to specify format
# and that the linter warns if format and format_source are used
OUTPUTS_COLLECTION_FORMAT_SOURCE = """
<tool>
    <outputs>
        <collection name="output_collection" type="paired">
            <data name="forward" format_source="input_readpair" />
            <data name="reverse" format_source="input_readpair" format="fastq"/>
        </collection>
    </outputs>
</tool>
"""

# check that setting format with actions is supported
OUTPUTS_FORMAT_ACTION = """
<tool>
    <outputs>
        <data name="output">
            <actions>
                <conditional name="library.type">
                    <when value="paired">
                        <action type="format">
                            <option type="from_param" name="library.input_2" param_attribute="ext" />
                        </action>
                    </when>
                </conditional>
            </actions>
        </data>
    </outputs>
</tool>
"""

# check that linter does not complain about missing format if from_tool_provided_metadata is used
OUTPUTS_DISCOVER_TOOL_PROVIDED_METADATA = """
<tool>
    <outputs>
        <data name="output">
            <discover_datasets from_tool_provided_metadata="true"/>
        </data>
    </outputs>
</tool>
"""
OUTPUTS_DUPLICATED_NAME_LABEL = """
<tool>
    <outputs>
        <data name="valid_name" format="fasta"/>
        <data name="valid_name" format="fasta"/>
    </outputs>
</tool>
"""

# tool xml for repeats linter
REPEATS = """
<tool>
    <inputs>
        <repeat>
            <param name="another_param_name" type="data" format="bed"/>
        </repeat>
    </inputs>
</tool>
"""

# tool xml for stdio linter
STDIO_DEFAULT_FOR_DEFAULT_PROFILE = """
<tool>
</tool>
"""

STDIO_DEFAULT_FOR_NONLEGACY_PROFILE = """
<tool profile="21.09">
</tool>
"""

STDIO_MULTIPLE_STDIO = """
<tool>
    <stdio/>
    <stdio/>
</tool>
"""

STDIO_INVALID_CHILD_OR_ATTRIB = """
<tool>
    <stdio>
        <reqex/>
        <regex descriptio="blah" level="fatal" match="error" source="stdio"/>
        <exit_code descriptio="blah" level="fatal" range="1:"/>
    </stdio>
</tool>
"""

STDIO_INVALID_MATCH = """
<tool>
    <stdio>
        <regex match="["/>
    </stdio>
</tool>
"""

# check that linter does complain about tests wo assumptions
TESTS_ABSENT = """
<tool/>
"""
TESTS_ABSENT_DATA_SOURCE = """
<tool tool_type="data_source"/>
"""
TESTS_WO_EXPECTATIONS = """
<tool>
    <tests>
        <test>
        </test>
    </tests>
</tool>
"""

TESTS_PARAM_OUTPUT_NAMES = """
<tool>
    <inputs>
        <param argument="--existent-test-name"/>
        <conditional>
            <when>
                <param name="another_existent_test_name"/>
            </when>
        </conditional>
    </inputs>
    <outputs>
        <data name="existent_output"/>
        <collection name="existent_collection"/>
    </outputs>
    <tests>
        <test expect_num_outputs="1">
            <param/>
            <param name="existent_test_name"/>
            <param name="cond_name|another_existent_test_name"/>
            <param name="non_existent_test_name"/>
            <output/>
            <output name="existent_output"/>
            <output name="nonexistent_output"/>
            <output_collection/>
            <output_collection name="existent_collection"/>
            <output_collection name="nonexistent_collection"/>
        </test>
    </tests>
</tool>
"""

TESTS_EXPECT_FAILURE_OUTPUT = """
<tool>
    <outputs>
        <data name="test"/>
    </outputs>
    <tests>
        <test expect_failure="true">
            <output name="test"/>
        </test>
    </tests>
</tool>
"""

ASSERTS = """
<tool>
    <outputs>
        <data name="out_archive"/>
        <data name="out_tabular"/>
    </outputs>
    <tests>
        <test>
            <assert_stdout>
                <has_text text="blah" n="1"/>
                <has_line line="blah"/>
            </assert_stdout>
            <assert_stderr>
                <invalid/>
            </assert_stderr>
            <assert_command>
                <has_text invalid_attrib="blah"/>
            </assert_command>
            <output name="out_archive">
                <assert_contents>
                    <has_size value="500k" delta="1O"/>
                    <has_archive_member path=".*/my-file.txt">
                        <not_has_text invalid_attrib_also_checked_in_nested_asserts="Blah" text="EDK72998.1" />
                    </has_archive_member>
                </assert_contents>
            </output>
            <output name="out_tabular">
                <assert_contents>
                    <has_size/>
                    <has_n_columns/>
                    <has_n_lines/>
                </assert_contents>
            </output>
        </test>
    </tests>
</tool>
"""
TESTS_VALID = """
<tool>
    <outputs>
        <data name="test"/>
    </outputs>
    <tests>
        <test>
            <output name="test"/>
        </test>
    </tests>
</tool>
"""
TESTS_OUTPUT_TYPE_MISMATCH = """
<tool>
    <outputs>
        <data name="data_name"/>
        <collection name="collection_name" type="list:list"/>
    </outputs>
    <tests>
        <test>
            <output_collection name="data_name"/>
            <output name="collection_name"/>
        </test>
    </tests>
</tool>
"""
TESTS_DISCOVER_OUTPUTS = """
<tool>
    <outputs>
        <data name="data_name">
            <discover_datasets/>
        </data>
        <collection name="collection_name" type="list:list">
            <discover_datasets/>
        </collection>
    </outputs>
    <tests>
        <!-- this should be fine -->
        <test>
            <output name="data_name">
                <discovered_dataset/>
            </output>
            <output_collection name="collection_name">
                <element count="2"/>
            </output_collection>
        </test>
        <!-- this should be fine as well -->
        <test>
            <output name="data_name" count="2"/>
            <output_collection name="collection_name">
                <element>
                    <element/>
                </element>
            </output_collection>
        </test>
        <!-- no count or discovered_dataset/element  -->
        <test>
            <output name="data_name"/>
            <output_collection name="collection_name"/>
        </test>
        <!-- no nested element and count at element -->
        <test>
            <output name="data_name" count="1"/>
            <output_collection name="collection_name" count="1">
                <element/>
            </output_collection>
        </test>
    </tests>
</tool>
"""

# tool xml for xml_order linter
XML_ORDER = """
<tool>
    <wrong_tag/>
    <command/>
    <stdio/>
</tool>
"""

TOOL_WITH_COMMENTS = """
<tool>
    <stdio>
    <!-- This is a comment -->
    </stdio>
    <outputs>
    <!-- This is a comment -->
    </outputs>
</tool>
"""


@pytest.fixture()
def lint_ctx():
    return LintContext("all", lint_message_class=XMLLintMessageLine)


@pytest.fixture()
def lint_ctx_xpath():
    return LintContext("all", lint_message_class=XMLLintMessageXPath)


def get_xml_tool_source(xml_string):
    with tempfile.NamedTemporaryFile(mode="w", suffix="tool.xml") as tmp:
        tmp.write(xml_string)
        tmp.flush()
        tool_path = tmp.name
        return load_with_references(tool_path)[0]


def get_tool_xml_exact(xml_string):
    """Returns the tool XML as it is, without stripping comments or anything else."""
    with tempfile.NamedTemporaryFile(mode="w", suffix="tool.xml") as tmp:
        tmp.write(xml_string)
        tmp.flush()
        tool_path = tmp.name
        return parse_xml(tool_path, strip_whitespace=False, remove_comments=False)


def failed_assert_print(lint_ctx):
    return (
        f"Valid: {lint_ctx.valid_messages}\n"
        f"Info: {lint_ctx.info_messages}\n"
        f"Warnings: {lint_ctx.warn_messages}\n"
        f"Errors: {lint_ctx.error_messages}"
    )


def run_lint(lint_ctx, lint_func, lint_target):
    lint_ctx.lint(name="test_lint", lint_func=lint_func, lint_target=lint_target)
    # check if the lint messages have the line
    for message in lint_ctx.message_list:
        if lint_func != general.lint_general:
            assert message.line is not None, f"No context found for message: {message.message}"


def test_citations_multiple(lint_ctx):
    tool_source = get_xml_tool_source(CITATIONS_MULTIPLE)
    run_lint(lint_ctx, citations.lint_citations, tool_source)
    assert "More than one citation section found, behavior undefined." in lint_ctx.error_messages
    assert not lint_ctx.info_messages
    assert not lint_ctx.valid_messages
    assert not lint_ctx.warn_messages
    assert len(lint_ctx.error_messages) == 1


def test_citations_absent(lint_ctx):
    tool_source = get_xml_tool_source(CITATIONS_ABSENT)
    run_lint(lint_ctx, citations.lint_citations, tool_source)
    assert lint_ctx.warn_messages == ["No citations found, consider adding citations to your tool."]
    assert not lint_ctx.info_messages
    assert not lint_ctx.valid_messages
    assert not lint_ctx.error_messages


def test_citations_errors(lint_ctx):
    tool_source = get_xml_tool_source(CITATIONS_ERRORS)
    run_lint(lint_ctx, citations.lint_citations, tool_source)
    assert "Unknown tag discovered in citations block [nonsense], will be ignored." in lint_ctx.warn_messages
    assert "Unknown citation type discovered [hoerensagen], will be ignored." in lint_ctx.warn_messages
    assert "Empty doi citation." in lint_ctx.error_messages
    assert "Found no valid citations." in lint_ctx.warn_messages
    assert len(lint_ctx.warn_messages) == 3
    assert not lint_ctx.info_messages
    assert not lint_ctx.valid_messages


def test_citations_valid(lint_ctx):
    tool_source = get_xml_tool_source(CITATIONS_VALID)
    run_lint(lint_ctx, citations.lint_citations, tool_source)
    assert "Found 1 likely valid citations." in lint_ctx.valid_messages
    assert len(lint_ctx.valid_messages) == 1
    assert not lint_ctx.info_messages
    assert not lint_ctx.error_messages


def test_command_multiple(lint_ctx):
    tool_source = get_xml_tool_source(COMMAND_MULTIPLE)
    run_lint(lint_ctx, command.lint_command, tool_source)
    assert "More than one command tag found, behavior undefined." in lint_ctx.error_messages
    assert len(lint_ctx.error_messages) == 1
    assert not lint_ctx.info_messages
    assert not lint_ctx.valid_messages
    assert not lint_ctx.warn_messages


def test_command_missing(lint_ctx):
    tool_source = get_xml_tool_source(COMMAND_MISSING)
    run_lint(lint_ctx, command.lint_command, tool_source)
    assert "No command tag found, must specify a command template to execute." in lint_ctx.error_messages


def test_command_todo(lint_ctx):
    tool_source = get_xml_tool_source(COMMAND_TODO)
    run_lint(lint_ctx, command.lint_command, tool_source)
    assert "Tool contains a command." in lint_ctx.info_messages
    assert "Command template contains TODO text." in lint_ctx.warn_messages


def test_command_detect_errors_interpreter(lint_ctx):
    tool_source = get_xml_tool_source(COMMAND_DETECT_ERRORS_INTERPRETER)
    run_lint(lint_ctx, command.lint_command, tool_source)
    assert "Command uses deprecated 'interpreter' attribute." in lint_ctx.warn_messages
    assert "Tool contains a command with interpreter of type [python]." in lint_ctx.info_messages
    assert "Unknown detect_errors attribute [nonsense]" in lint_ctx.warn_messages
    assert "Command is empty." in lint_ctx.error_messages


def test_general_missing_tool_id_name_version(lint_ctx):
    tool_source = get_xml_tool_source(GENERAL_MISSING_TOOL_ID_NAME_VERSION)
    run_lint(lint_ctx, general.lint_general, XmlToolSource(tool_source))
    assert "Tool version is missing or empty." in lint_ctx.error_messages
    assert "Tool name is missing or empty." in lint_ctx.error_messages
    assert "Tool does not define an id attribute." in lint_ctx.error_messages
    assert "Tool specifies an invalid profile version [2109]." in lint_ctx.error_messages


def test_general_whitespace_in_versions_and_names(lint_ctx):
    tool_source = get_xml_tool_source(GENERAL_WHITESPACE_IN_VERSIONS_AND_NAMES)
    run_lint(lint_ctx, general.lint_general, XmlToolSource(tool_source))
    assert "Tool version is pre/suffixed by whitespace, this may cause errors: [ 1.0.1 ]." in lint_ctx.warn_messages
    assert "Tool name is pre/suffixed by whitespace, this may cause errors: [ BWA Mapper ]." in lint_ctx.warn_messages
    assert "Requirement version contains whitespace, this may cause errors: [ 1.2.5 ]." in lint_ctx.warn_messages
    assert "Tool ID contains whitespace - this is discouraged: [bwa tool]." in lint_ctx.warn_messages
    assert "Tool targets 16.01 Galaxy profile." in lint_ctx.valid_messages


def test_general_requirement_without_version(lint_ctx):
    tool_source = get_xml_tool_source(GENERAL_REQUIREMENT_WO_VERSION)
    run_lint(lint_ctx, general.lint_general, XmlToolSource(tool_source))
    assert "Tool version [1.0.1blah] is not compliant with PEP 440." in lint_ctx.warn_messages
    assert "Requirement bwa defines no version" in lint_ctx.warn_messages
    assert "Requirement without name found" in lint_ctx.error_messages
    assert "Tool specifies profile version [20.09]." in lint_ctx.valid_messages
    assert "Tool defines an id [bwa_tool]." in lint_ctx.valid_messages
    assert "Tool defines a name [BWA Mapper]." in lint_ctx.valid_messages
    assert not lint_ctx.info_messages
    assert len(lint_ctx.valid_messages) == 3
    assert len(lint_ctx.warn_messages) == 2
    assert len(lint_ctx.error_messages) == 1


def test_general_valid(lint_ctx):
    tool_source = get_xml_tool_source(GENERAL_VALID)
    run_lint(lint_ctx, general.lint_general, XmlToolSource(tool_source))
    assert "Tool defines a version [1.0+galaxy1]." in lint_ctx.valid_messages
    assert "Tool specifies profile version [21.09]." in lint_ctx.valid_messages
    assert "Tool defines an id [valid_id]." in lint_ctx.valid_messages
    assert "Tool defines a name [valid name]." in lint_ctx.valid_messages
    assert not lint_ctx.info_messages
    assert len(lint_ctx.valid_messages) == 4
    assert not lint_ctx.warn_messages
    assert not lint_ctx.error_messages


def test_help_multiple(lint_ctx):
    tool_source = get_xml_tool_source(HELP_MULTIPLE)
    run_lint(lint_ctx, help.lint_help, tool_source)
    assert "More than one help section found, behavior undefined." in lint_ctx.error_messages
    assert not lint_ctx.info_messages
    assert not lint_ctx.valid_messages
    assert not lint_ctx.warn_messages
    assert len(lint_ctx.error_messages) == 1


def test_help_absent(lint_ctx):
    tool_source = get_xml_tool_source(HELP_ABSENT)
    run_lint(lint_ctx, help.lint_help, tool_source)
    assert "No help section found, consider adding a help section to your tool." in lint_ctx.warn_messages
    assert not lint_ctx.info_messages
    assert not lint_ctx.valid_messages
    assert len(lint_ctx.warn_messages) == 1
    assert not lint_ctx.error_messages


def test_help_empty(lint_ctx):
    tool_source = get_xml_tool_source(HELP_EMPTY)
    run_lint(lint_ctx, help.lint_help, tool_source)
    assert "Help section appears to be empty." in lint_ctx.warn_messages
    assert not lint_ctx.info_messages
    assert not lint_ctx.valid_messages
    assert len(lint_ctx.warn_messages) == 1
    assert not lint_ctx.error_messages


def test_help_todo(lint_ctx):
    tool_source = get_xml_tool_source(HELP_TODO)
    run_lint(lint_ctx, help.lint_help, tool_source)
    assert "Tool contains help section." in lint_ctx.valid_messages
    assert "Help contains valid reStructuredText." in lint_ctx.valid_messages
    assert "Help contains TODO text." in lint_ctx.warn_messages
    assert not lint_ctx.info_messages
    assert len(lint_ctx.valid_messages) == 2
    assert len(lint_ctx.warn_messages) == 1
    assert not lint_ctx.error_messages


def test_help_invalid_rst(lint_ctx):
    tool_source = get_xml_tool_source(HELP_INVALID_RST)
    run_lint(lint_ctx, help.lint_help, tool_source)
    assert "Tool contains help section." in lint_ctx.valid_messages
    assert (
        "Invalid reStructuredText found in help - [<string>:2: (WARNING/2) Inline strong start-string without end-string.\n]."
        in lint_ctx.warn_messages
    )
    assert not lint_ctx.info_messages
    assert len(lint_ctx.valid_messages) == 1
    assert len(lint_ctx.warn_messages) == 1
    assert not lint_ctx.error_messages


def test_inputs_no_inputs(lint_ctx):
    tool_source = get_xml_tool_source(INPUTS_NO_INPUTS)
    run_lint(lint_ctx, inputs.lint_inputs, tool_source)
    assert "Found no input parameters." in lint_ctx.warn_messages
    assert not lint_ctx.info_messages
    assert not lint_ctx.valid_messages
    assert len(lint_ctx.warn_messages) == 1
    assert not lint_ctx.error_messages


def test_inputs_no_inputs_datasource(lint_ctx):
    tool_source = get_xml_tool_source(INPUTS_NO_INPUTS_DATASOURCE)
    run_lint(lint_ctx, inputs.lint_inputs, tool_source)
    assert "No input parameters, OK for data sources" in lint_ctx.info_messages
    assert "display tag usually present in data sources" in lint_ctx.info_messages
    assert "uihints tag usually present in data sources" in lint_ctx.info_messages
    assert len(lint_ctx.info_messages) == 3
    assert not lint_ctx.valid_messages
    assert not lint_ctx.warn_messages
    assert not lint_ctx.error_messages


def test_inputs_valid(lint_ctx):
    tool_source = get_xml_tool_source(INPUTS_VALID)
    run_lint(lint_ctx, inputs.lint_inputs, tool_source)
    assert "Found 2 input parameters." in lint_ctx.info_messages
    assert len(lint_ctx.info_messages) == 1
    assert not lint_ctx.valid_messages
    assert not lint_ctx.warn_messages
    assert not lint_ctx.error_messages


def test_inputs_param_name(lint_ctx):
    tool_source = get_xml_tool_source(INPUTS_PARAM_NAME)
    run_lint(lint_ctx, inputs.lint_inputs, tool_source)
    assert "Found 5 input parameters." in lint_ctx.info_messages
    assert "Param input [2] is not a valid Cheetah placeholder." in lint_ctx.warn_messages
    assert "Found param input with no name specified." in lint_ctx.error_messages
    assert "Param input with empty name." in lint_ctx.error_messages
    assert (
        "Param input [param_name] 'name' attribute is redundant if argument implies the same name."
        in lint_ctx.warn_messages
    )
    assert len(lint_ctx.info_messages) == 1
    assert not lint_ctx.valid_messages
    assert len(lint_ctx.warn_messages) == 2
    assert len(lint_ctx.error_messages) == 2


def test_inputs_param_type(lint_ctx):
    tool_source = get_xml_tool_source(INPUTS_PARAM_TYPE)
    run_lint(lint_ctx, inputs.lint_inputs, tool_source)
    assert "Found 2 input parameters." in lint_ctx.info_messages
    assert "Param input [valid_name] input with no type specified." in lint_ctx.error_messages
    assert "Param input [another_valid_name] with empty type specified." in lint_ctx.error_messages
    assert len(lint_ctx.info_messages) == 1
    assert not lint_ctx.valid_messages
    assert not lint_ctx.warn_messages
    assert len(lint_ctx.error_messages) == 2


def test_inputs_data_param(lint_ctx):
    tool_source = get_xml_tool_source(INPUTS_DATA_PARAM)
    run_lint(lint_ctx, inputs.lint_inputs, tool_source)
    assert "Found 1 input parameters." in lint_ctx.info_messages
    assert (
        "Param input [valid_name] with no format specified - 'data' format will be assumed." in lint_ctx.warn_messages
    )
    assert len(lint_ctx.info_messages) == 1
    assert not lint_ctx.valid_messages
    assert len(lint_ctx.warn_messages) == 1
    assert not lint_ctx.error_messages


def test_inputs_data_param_options(lint_ctx):
    tool_source = get_xml_tool_source(INPUTS_DATA_PARAM_OPTIONS)
    run_lint(lint_ctx, inputs.lint_inputs, tool_source)
    assert not lint_ctx.valid_messages
    assert "Found 1 input parameters." in lint_ctx.info_messages
    assert len(lint_ctx.info_messages) == 1
    assert not lint_ctx.warn_messages
    assert not lint_ctx.error_messages


def test_inputs_data_param_options_filter_attribute(lint_ctx):
    tool_source = get_xml_tool_source(INPUTS_DATA_PARAM_OPTIONS_FILTER_ATTRIBUTE)
    run_lint(lint_ctx, inputs.lint_inputs, tool_source)
    assert not lint_ctx.valid_messages
    assert "Found 1 input parameters." in lint_ctx.info_messages
    assert len(lint_ctx.info_messages) == 1
    assert not lint_ctx.warn_messages
    assert not lint_ctx.error_messages


def test_inputs_data_param_invalid_options(lint_ctx):
    tool_source = get_xml_tool_source(INPUTS_DATA_PARAM_INVALIDOPTIONS)
    run_lint(lint_ctx, inputs.lint_inputs, tool_source)
    assert not lint_ctx.valid_messages
    assert "Found 1 input parameters." in lint_ctx.info_messages
    assert len(lint_ctx.info_messages) == 1
    assert not lint_ctx.warn_messages
    assert "Data parameter [valid_name] contains multiple options elements." in lint_ctx.error_messages
    assert "Data parameter [valid_name] filter needs to define a ref attribute" in lint_ctx.error_messages
    assert (
        'Data parameter [valid_name] for filters only type="data_meta" and key="dbkey" are allowed, found type="expression" and key="None"'
        in lint_ctx.error_messages
    )
    assert len(lint_ctx.error_messages) == 3


def test_inputs_conditional(lint_ctx):
    tool_source = get_xml_tool_source(INPUTS_CONDITIONAL)
    run_lint(lint_ctx, inputs.lint_inputs, tool_source)
    assert "Found 10 input parameters." in lint_ctx.info_messages
    assert "Conditional without a name" in lint_ctx.error_messages
    assert (
        "Select parameter of a conditional [select] options have to be defined by 'option' children elements."
        in lint_ctx.error_messages
    )
    assert "Conditional [cond_wo_param] needs exactly one child <param> found 0" in lint_ctx.error_messages
    assert "Conditional [cond_w_mult_param] needs exactly one child <param> found 2" in lint_ctx.error_messages
    assert 'Conditional [cond_text] first param should have type="select"' in lint_ctx.error_messages
    assert (
        'Conditional [cond_boolean] first param of type="boolean" is discouraged, use a select'
        in lint_ctx.warn_messages
    )
    assert "Conditional [cond_boolean] no truevalue/falsevalue found for when block 'False'" in lint_ctx.warn_messages
    assert 'Conditional [cond_w_optional_select] test parameter cannot be optional="true"' in lint_ctx.warn_messages
    assert 'Conditional [cond_w_multiple_select] test parameter cannot be multiple="true"' in lint_ctx.warn_messages
    assert "Conditional [when_wo_value] when without value" in lint_ctx.error_messages
    assert "Conditional [missing_when] no <when /> block found for select option 'none'" in lint_ctx.warn_messages
    assert len(lint_ctx.info_messages) == 1
    assert not lint_ctx.valid_messages
    assert len(lint_ctx.warn_messages) == 6
    assert len(lint_ctx.error_messages) == 6


def test_inputs_select_incompatible_display(lint_ctx):
    tool_source = get_xml_tool_source(INPUTS_SELECT_INCOMPATIBLE_DISPLAY)
    run_lint(lint_ctx, inputs.lint_inputs, tool_source)
    assert "Found 3 input parameters." in lint_ctx.info_messages
    assert 'Select [radio_select] display="radio" is incompatible with optional="true"' in lint_ctx.error_messages
    assert 'Select [radio_select] display="radio" is incompatible with multiple="true"' in lint_ctx.error_messages
    assert (
        'Select [checkboxes_select] `display="checkboxes"` is incompatible with `optional="false"`, remove the `display` attribute'
        in lint_ctx.error_messages
    )
    assert (
        'Select [checkboxes_select] `display="checkboxes"` is incompatible with `multiple="false"`, remove the `display` attribute'
        in lint_ctx.error_messages
    )
    assert len(lint_ctx.info_messages) == 1
    assert not lint_ctx.valid_messages
    assert not lint_ctx.warn_messages
    assert len(lint_ctx.error_messages) == 4


def test_inputs_duplicated_options(lint_ctx):
    tool_source = get_xml_tool_source(INPUTS_SELECT_DUPLICATED_OPTIONS)
    run_lint(lint_ctx, inputs.lint_inputs, tool_source)
    assert "Found 1 input parameters." in lint_ctx.info_messages
    assert "Select parameter [select] has multiple options with the same text content" in lint_ctx.error_messages
    assert "Select parameter [select] has multiple options with the same value" in lint_ctx.error_messages
    assert len(lint_ctx.info_messages) == 1
    assert not lint_ctx.valid_messages
    assert not lint_ctx.warn_messages
    assert len(lint_ctx.error_messages) == 2


def test_inputs_duplicated_options_with_different_select(lint_ctx):
    tool_source = get_xml_tool_source(SELECT_DUPLICATED_OPTIONS_WITH_DIFF_SELECTED)
    run_lint(lint_ctx, inputs.lint_inputs, tool_source)
    assert not lint_ctx.warn_messages
    assert not lint_ctx.error_messages


def test_inputs_select_deprections(lint_ctx):
    tool_source = get_xml_tool_source(INPUTS_SELECT_DEPRECATIONS)
    run_lint(lint_ctx, inputs.lint_inputs, tool_source)
    assert "Found 3 input parameters." in lint_ctx.info_messages
    assert "Select parameter [select_do] uses deprecated 'dynamic_options' attribute." in lint_ctx.warn_messages
    assert "Select parameter [select_ff] options uses deprecated 'from_file' attribute." in lint_ctx.warn_messages
    assert "Select parameter [select_fp] options uses deprecated 'from_parameter' attribute." in lint_ctx.warn_messages
    assert "Select parameter [select_ff] options uses deprecated 'transform_lines' attribute." in lint_ctx.warn_messages
    assert (
        "Select parameter [select_fp] options uses deprecated 'options_filter_attribute' attribute."
        in lint_ctx.warn_messages
    )
    assert len(lint_ctx.info_messages) == 1
    assert not lint_ctx.valid_messages
    assert len(lint_ctx.warn_messages) == 5
    assert not lint_ctx.error_messages


def test_inputs_select_option_definitions(lint_ctx):
    tool_source = get_xml_tool_source(INPUTS_SELECT_OPTION_DEFINITIONS)
    run_lint(lint_ctx, inputs.lint_inputs, tool_source)
    assert "Found 6 input parameters." in lint_ctx.info_messages
    assert (
        "Select parameter [select_noopt] options have to be defined by either 'option' children elements, a 'options' element or the 'dynamic_options' attribute."
        in lint_ctx.error_messages
    )
    assert (
        "Select parameter [select_noopts] options tag defines no options. Use 'from_dataset', 'from_data_table', or a filter that adds values."
        in lint_ctx.error_messages
    )
    assert (
        "Select parameter [select_fd_op] options have to be defined by either 'option' children elements, a 'options' element or the 'dynamic_options' attribute."
        in lint_ctx.error_messages
    )
    assert "Select parameter [select_fd_op] contains multiple options elements." in lint_ctx.error_messages
    assert (
        "Select parameter [select_fd_fdt] options uses 'from_dataset' and 'from_data_table' attribute."
        in lint_ctx.error_messages
    )
    assert "Select parameter [select_noval_notext] has option without value" in lint_ctx.error_messages
    assert "Select parameter [select_noval_notext] has option without text" in lint_ctx.warn_messages
    assert (
        "Select parameter [select_meta_file_key_incomp] 'meta_file_key' is only compatible with 'from_dataset'."
        in lint_ctx.error_messages
    )
    assert len(lint_ctx.info_messages) == 1
    assert not lint_ctx.valid_messages
    assert len(lint_ctx.warn_messages) == 1
    assert len(lint_ctx.error_messages) == 7


def test_inputs_select_filter(lint_ctx):
    tool_source = get_xml_tool_source(INPUTS_SELECT_FILTER)
    run_lint(lint_ctx, inputs.lint_inputs, tool_source)
    assert "Found 1 input parameters." in lint_ctx.info_messages
    assert "Select parameter [select_filter_types] contains filter without type." in lint_ctx.error_messages
    assert (
        "Select parameter [select_filter_types] contains filter with unknown type 'unknown_filter_type'."
        in lint_ctx.error_messages
    )
    assert len(lint_ctx.info_messages) == 1
    assert not lint_ctx.valid_messages
    assert not lint_ctx.warn_messages
    assert len(lint_ctx.error_messages) == 2


def test_inputs_validator_incompatibilities(lint_ctx):
    tool_source = get_xml_tool_source(INPUTS_VALIDATOR_INCOMPATIBILITIES)
    run_lint(lint_ctx, inputs.lint_inputs, tool_source)
    assert "Found 2 input parameters." in lint_ctx.info_messages
    assert (
        "Parameter [param_name]: 'in_range' validators are not expected to contain text (found 'TEXT')"
        in lint_ctx.warn_messages
    )
    assert "Parameter [param_name]: validator with an incompatible type 'in_range'" in lint_ctx.error_messages
    assert (
        "Parameter [param_name]: 'in_range' validators need to define the 'min' or 'max' attribute(s)"
        in lint_ctx.error_messages
    )
    assert (
        "Parameter [param_name]: attribute 'filename' is incompatible with validator of type 'regex'"
        in lint_ctx.error_messages
    )
    assert "Parameter [param_name]: expression validators are expected to contain text" in lint_ctx.error_messages
    assert (
        "Parameter [param_name]: '[' is no valid regular expression: unterminated character set at position 0"
        in lint_ctx.error_messages
    )
    assert (
        "Parameter [another_param_name]: 'metadata' validators need to define the 'check' or 'skip' attribute(s)"
        in lint_ctx.error_messages
    )
    assert (
        "Parameter [param_name]: 'value_in_data_table' validators need to define the 'table_name' attribute"
        in lint_ctx.error_messages
    )
    assert len(lint_ctx.info_messages) == 1
    assert not lint_ctx.valid_messages
    assert len(lint_ctx.warn_messages) == 1
    assert len(lint_ctx.error_messages) == 7


def test_inputs_validator_correct(lint_ctx):
    tool_source = get_xml_tool_source(INPUTS_VALIDATOR_CORRECT)
    run_lint(lint_ctx, inputs.lint_inputs, tool_source)
    assert "Found 5 input parameters." in lint_ctx.info_messages
    assert len(lint_ctx.info_messages) == 1
    assert not lint_ctx.valid_messages
    assert not lint_ctx.warn_messages
    assert not lint_ctx.error_messages


def test_inputs_type_child_combinations(lint_ctx):
    tool_source = get_xml_tool_source(INPUTS_TYPE_CHILD_COMBINATIONS)
    run_lint(lint_ctx, inputs.lint_inputs, tool_source)
    assert len(lint_ctx.info_messages) == 1
    assert not lint_ctx.valid_messages
    assert not lint_ctx.warn_messages
    assert (
        "Parameter [text_param] './options' tags are only allowed for parameters of type ['data', 'select', 'drill_down']"
        in lint_ctx.error_messages
    )
    assert (
        "Parameter [select_param] './options/option' tags are only allowed for parameters of type ['drill_down']"
        in lint_ctx.error_messages
    )
    assert (
        "Parameter [data_param] './column' tags are only allowed for parameters of type ['data_column']"
        in lint_ctx.error_messages
    )
    assert len(lint_ctx.error_messages) == 3


def test_inputs_repeats(lint_ctx):
    tool_source = get_xml_tool_source(REPEATS)
    run_lint(lint_ctx, inputs.lint_repeats, tool_source)
    assert "Repeat does not specify name attribute." in lint_ctx.error_messages
    assert "Repeat does not specify title attribute." in lint_ctx.error_messages
    assert not lint_ctx.info_messages
    assert not lint_ctx.valid_messages
    assert not lint_ctx.warn_messages
    assert len(lint_ctx.error_messages) == 2


def test_outputs_missing(lint_ctx):
    tool_source = get_xml_tool_source(OUTPUTS_MISSING)
    run_lint(lint_ctx, outputs.lint_output, tool_source)
    assert "Tool contains no outputs section, most tools should produce outputs." in lint_ctx.warn_messages
    assert not lint_ctx.info_messages
    assert not lint_ctx.valid_messages
    assert len(lint_ctx.warn_messages) == 1
    assert not lint_ctx.error_messages


def test_outputs_multiple(lint_ctx):
    tool_source = get_xml_tool_source(OUTPUTS_MULTIPLE)
    run_lint(lint_ctx, outputs.lint_output, tool_source)
    assert "0 outputs found." in lint_ctx.info_messages
    assert "Tool contains multiple output sections, behavior undefined." in lint_ctx.warn_messages
    assert len(lint_ctx.info_messages) == 1
    assert not lint_ctx.valid_messages
    assert len(lint_ctx.warn_messages) == 1
    assert not lint_ctx.error_messages


def test_outputs_unknown_tag(lint_ctx):
    tool_source = get_xml_tool_source(OUTPUTS_UNKNOWN_TAG)
    run_lint(lint_ctx, outputs.lint_output, tool_source)
    assert "0 outputs found." in lint_ctx.info_messages
    assert "Unknown element found in outputs [output]" in lint_ctx.warn_messages
    assert len(lint_ctx.info_messages) == 1
    assert not lint_ctx.valid_messages
    assert len(lint_ctx.warn_messages) == 1
    assert not lint_ctx.error_messages


def test_outputs_unnamed_invalid_name(lint_ctx):
    tool_source = get_xml_tool_source(OUTPUTS_UNNAMED_INVALID_NAME)
    run_lint(lint_ctx, outputs.lint_output, tool_source)
    assert "2 outputs found." in lint_ctx.info_messages
    assert "Tool output doesn't define a name - this is likely a problem." in lint_ctx.warn_messages
    assert "Tool data output with missing name doesn't define an output format." in lint_ctx.warn_messages
    assert "Tool output name [2output] is not a valid Cheetah placeholder." in lint_ctx.warn_messages
    assert "Collection output with undefined 'type' found." in lint_ctx.warn_messages
    assert "Tool collection output 2output doesn't define an output format." in lint_ctx.warn_messages
    assert len(lint_ctx.info_messages) == 1
    assert not lint_ctx.valid_messages
    assert len(lint_ctx.warn_messages) == 5
    assert not lint_ctx.error_messages


def test_outputs_format_input(lint_ctx):
    tool_source = get_xml_tool_source(OUTPUTS_FORMAT_INPUT)
    run_lint(lint_ctx, outputs.lint_output, tool_source)
    assert "1 outputs found." in lint_ctx.info_messages
    assert (
        "Using format='input' on data, format_source attribute is less ambiguous and should be used instead."
        in lint_ctx.warn_messages
    )
    assert len(lint_ctx.info_messages) == 1
    assert not lint_ctx.valid_messages
    assert len(lint_ctx.warn_messages) == 1
    assert not lint_ctx.error_messages


def test_outputs_collection_format_source(lint_ctx):
    tool_source = get_xml_tool_source(OUTPUTS_COLLECTION_FORMAT_SOURCE)
    run_lint(lint_ctx, outputs.lint_output, tool_source)
    assert "Tool data output 'reverse' should use either format_source or format/ext" in lint_ctx.warn_messages
    assert len(lint_ctx.info_messages) == 1
    assert not lint_ctx.valid_messages
    assert len(lint_ctx.warn_messages) == 1
    assert not lint_ctx.error_messages


def test_outputs_format_action(lint_ctx):
    tool_source = get_xml_tool_source(OUTPUTS_FORMAT_ACTION)
    run_lint(lint_ctx, outputs.lint_output, tool_source)
    assert len(lint_ctx.info_messages) == 1
    assert not lint_ctx.valid_messages
    assert not lint_ctx.warn_messages
    assert not lint_ctx.error_messages


def test_outputs_discover_tool_provided_metadata(lint_ctx):
    tool_source = get_xml_tool_source(OUTPUTS_DISCOVER_TOOL_PROVIDED_METADATA)
    run_lint(lint_ctx, outputs.lint_output, tool_source)
    assert "1 outputs found." in lint_ctx.info_messages
    assert len(lint_ctx.info_messages) == 1
    assert not lint_ctx.valid_messages
    assert not lint_ctx.warn_messages
    assert not lint_ctx.error_messages


def test_outputs_duplicated_name_label(lint_ctx):
    tool_source = get_xml_tool_source(OUTPUTS_DUPLICATED_NAME_LABEL)
    run_lint(lint_ctx, outputs.lint_output, tool_source)
    assert "2 outputs found." in lint_ctx.info_messages
    assert len(lint_ctx.info_messages) == 1
    assert not lint_ctx.valid_messages
    assert not lint_ctx.warn_messages
    assert "Tool output [valid_name] has duplicated name" in lint_ctx.error_messages
    assert "Tool output [valid_name] uses duplicated label '${tool.name} on ${on_string}'" in lint_ctx.error_messages
    assert len(lint_ctx.error_messages) == 2


def test_stdio_default_for_default_profile(lint_ctx):
    tool_source = get_xml_tool_source(STDIO_DEFAULT_FOR_DEFAULT_PROFILE)
    run_lint(lint_ctx, stdio.lint_stdio, XmlToolSource(tool_source))
    assert (
        "No stdio definition found, tool indicates error conditions with output written to stderr."
        in lint_ctx.info_messages
    )
    assert len(lint_ctx.info_messages) == 1
    assert not lint_ctx.valid_messages
    assert not lint_ctx.warn_messages
    assert not lint_ctx.error_messages


def test_stdio_default_for_nonlegacy_profile(lint_ctx):
    tool_source = get_xml_tool_source(STDIO_DEFAULT_FOR_NONLEGACY_PROFILE)
    run_lint(lint_ctx, stdio.lint_stdio, XmlToolSource(tool_source))
    assert (
        "No stdio definition found, tool indicates error conditions with non-zero exit codes." in lint_ctx.info_messages
    )
    assert len(lint_ctx.info_messages) == 1
    assert not lint_ctx.valid_messages
    assert not lint_ctx.warn_messages
    assert not lint_ctx.error_messages


def test_stdio_multiple_stdio(lint_ctx):
    tool_source = get_xml_tool_source(STDIO_MULTIPLE_STDIO)
    run_lint(lint_ctx, stdio.lint_stdio, XmlToolSource(tool_source))
    assert "More than one stdio tag found, behavior undefined." in lint_ctx.error_messages
    assert not lint_ctx.info_messages
    assert not lint_ctx.valid_messages
    assert not lint_ctx.warn_messages
    assert len(lint_ctx.error_messages) == 1


def test_stdio_invalid_child_or_attrib(lint_ctx):
    tool_source = get_xml_tool_source(STDIO_INVALID_CHILD_OR_ATTRIB)
    run_lint(lint_ctx, stdio.lint_stdio, XmlToolSource(tool_source))
    assert (
        "Unknown stdio child tag discovered [reqex]. Valid options are exit_code and regex." in lint_ctx.warn_messages
    )
    assert "Unknown attribute [descriptio] encountered on exit_code tag." in lint_ctx.warn_messages
    assert "Unknown attribute [descriptio] encountered on regex tag." in lint_ctx.warn_messages
    assert not lint_ctx.info_messages
    assert not lint_ctx.valid_messages
    assert len(lint_ctx.warn_messages) == 3
    assert not lint_ctx.error_messages


def test_stdio_invalid_match(lint_ctx):
    tool_source = get_xml_tool_source(STDIO_INVALID_MATCH)
    run_lint(lint_ctx, stdio.lint_stdio, XmlToolSource(tool_source))
    assert (
        "Match '[' is no valid regular expression: unterminated character set at position 0" in lint_ctx.error_messages
    )
    assert not lint_ctx.info_messages
    assert not lint_ctx.valid_messages
    assert not lint_ctx.warn_messages
    assert len(lint_ctx.error_messages) == 1


def test_tests_absent(lint_ctx):
    tool_source = get_xml_tool_source(TESTS_ABSENT)
    run_lint(lint_ctx, tests.lint_tsts, tool_source)
    assert "No tests found, most tools should define test cases." in lint_ctx.warn_messages
    assert not lint_ctx.info_messages
    assert not lint_ctx.valid_messages
    assert len(lint_ctx.warn_messages) == 1
    assert not lint_ctx.error_messages


def test_tests_data_source(lint_ctx):
    tool_source = get_xml_tool_source(TESTS_ABSENT_DATA_SOURCE)
    run_lint(lint_ctx, tests.lint_tsts, tool_source)
    assert "No tests found, that should be OK for data_sources." in lint_ctx.info_messages
    assert len(lint_ctx.info_messages) == 1
    assert not lint_ctx.valid_messages
    assert not lint_ctx.warn_messages
    assert not lint_ctx.error_messages


def test_tests_param_output_names(lint_ctx):
    tool_source = get_xml_tool_source(TESTS_PARAM_OUTPUT_NAMES)
    run_lint(lint_ctx, tests.lint_tsts, tool_source)
    assert "1 test(s) found." in lint_ctx.valid_messages
    assert "Test 1: Found test param tag without a name defined." in lint_ctx.error_messages
    assert "Test 1: Test param non_existent_test_name not found in the inputs" in lint_ctx.error_messages
    assert "Test 1: Found output tag without a name defined." in lint_ctx.error_messages
    assert (
        "Test 1: Found output tag with unknown name [nonexistent_output], valid names ['existent_output', 'existent_collection']"
        in lint_ctx.error_messages
    )
    assert "Test 1: Found output_collection tag without a name defined." in lint_ctx.error_messages
    assert (
        "Test 1: Found output_collection tag with unknown name [nonexistent_collection], valid names ['existent_output', 'existent_collection']"
        in lint_ctx.error_messages
    )
    assert not lint_ctx.info_messages
    assert len(lint_ctx.valid_messages) == 1
    assert not lint_ctx.warn_messages
    assert len(lint_ctx.error_messages) == 6


def test_tests_expect_failure_output(lint_ctx):
    tool_source = get_xml_tool_source(TESTS_EXPECT_FAILURE_OUTPUT)
    run_lint(lint_ctx, tests.lint_tsts, tool_source)
    assert "No valid test(s) found." in lint_ctx.warn_messages
    assert "Test 1: Cannot specify outputs in a test expecting failure." in lint_ctx.error_messages
    assert not lint_ctx.info_messages
    assert not lint_ctx.valid_messages
    assert len(lint_ctx.warn_messages) == 1
    assert len(lint_ctx.error_messages) == 1


def test_tests_without_expectations(lint_ctx):
    tool_source = get_xml_tool_source(TESTS_WO_EXPECTATIONS)
    run_lint(lint_ctx, tests.lint_tsts, tool_source)
    assert (
        "Test 1: No outputs or expectations defined for tests, this test is likely invalid." in lint_ctx.warn_messages
    )
    assert "No valid test(s) found." in lint_ctx.warn_messages
    assert not lint_ctx.info_messages
    assert not lint_ctx.valid_messages
    assert len(lint_ctx.warn_messages) == 2
    assert not lint_ctx.error_messages


def test_tests_valid(lint_ctx):
    tool_source = get_xml_tool_source(TESTS_VALID)
    run_lint(lint_ctx, tests.lint_tsts, tool_source)
    assert "1 test(s) found." in lint_ctx.valid_messages
    assert not lint_ctx.info_messages
    assert len(lint_ctx.valid_messages) == 1
    assert not lint_ctx.warn_messages
    assert not lint_ctx.error_messages


def test_tests_asserts(lint_ctx):
    tool_source = get_xml_tool_source(ASSERTS)
    run_lint(lint_ctx, tests.lint_tsts, tool_source)
    assert "Test 1: unknown assertion 'invalid'" in lint_ctx.error_messages
    assert "Test 1: unknown attribute 'invalid_attrib' for 'has_text'" in lint_ctx.error_messages
    assert "Test 1: missing attribute 'text' for 'has_text'" in lint_ctx.error_messages
    assert "Test 1: attribute 'value' for 'has_size' needs to be 'int' got '500k'" in lint_ctx.error_messages
    assert "Test 1: attribute 'delta' for 'has_size' needs to be 'int' got '1O'" in lint_ctx.error_messages
    assert (
        "Test 1: unknown attribute 'invalid_attrib_also_checked_in_nested_asserts' for 'not_has_text'"
        in lint_ctx.error_messages
    )
    assert "Test 1: 'has_size' needs to specify 'n', 'min', or 'max'" in lint_ctx.error_messages
    assert "Test 1: 'has_n_columns' needs to specify 'n', 'min', or 'max'" in lint_ctx.error_messages
    assert "Test 1: 'has_n_lines' needs to specify 'n', 'min', or 'max'" in lint_ctx.error_messages
    assert not lint_ctx.warn_messages
    assert len(lint_ctx.error_messages) == 9


def test_tests_output_type_mismatch(lint_ctx):
    tool_source = get_xml_tool_source(TESTS_OUTPUT_TYPE_MISMATCH)
    run_lint(lint_ctx, tests.lint_tsts, tool_source)
    assert (
        "Test 1: test output collection_name does not correspond to a 'data' output, but a 'collection'"
        in lint_ctx.error_messages
    )
    assert (
        "Test 1: test collection output 'data_name' does not correspond to a 'output_collection' output, but a 'data'"
        in lint_ctx.error_messages
    )
    assert not lint_ctx.warn_messages
    assert len(lint_ctx.error_messages) == 2


def test_tests_discover_outputs(lint_ctx):
    tool_source = get_xml_tool_source(TESTS_DISCOVER_OUTPUTS)
    run_lint(lint_ctx, tests.lint_tsts, tool_source)
    assert (
        "Test 3: test output 'data_name' must have a 'count' attribute and/or 'discovered_dataset' children"
        in lint_ctx.error_messages
    )
    assert (
        "Test 3: test collection 'collection_name' must have a 'count' attribute or 'element' children"
        in lint_ctx.error_messages
    )
    assert (
        "Test 3: test collection 'collection_name' must contain nested 'element' tags and/or element childen with a 'count' attribute"
        in lint_ctx.error_messages
    )
    assert (
        "Test 4: test collection 'collection_name' must contain nested 'element' tags and/or element childen with a 'count' attribute"
        in lint_ctx.error_messages
    )
    assert not lint_ctx.warn_messages
    assert len(lint_ctx.error_messages) == 4


def test_xml_order(lint_ctx):
    tool_source = get_xml_tool_source(XML_ORDER)
    run_lint(lint_ctx, xml_order.lint_xml_order, tool_source)
    assert "Unknown tag [wrong_tag] encountered, this may result in a warning in the future." in lint_ctx.info_messages
    assert "Best practice violation [stdio] elements should come before [command]" in lint_ctx.warn_messages
    assert len(lint_ctx.info_messages) == 1
    assert not lint_ctx.valid_messages
    assert len(lint_ctx.warn_messages) == 1
    assert not lint_ctx.error_messages


COMPLETE = """<tool>
    <macros>
        <import>macros.xml</import>
        <xml name="test_macro">
            <param name="select" type="select">
                <option value="a">a</option>
                <option value="a">a</option>
            </param>
        </xml>
    </macros>
    <inputs>
        <expand macro="test_macro"/>
        <param/>
        <expand macro="test_macro2"/>
    </inputs>
</tool>
"""

COMPLETE_MACROS = """<macros>
    <xml name="test_macro2">
        <param name="No_type"/>
    </xml>
</macros>
"""


def test_tool_and_macro_xml(lint_ctx_xpath, lint_ctx):
    """
    test linters (all of them via lint_tool_source_with) on a tool and macro xml file
    checking a list of asserts, where each assert is a 4-tuple:
    - expected message
    - filename suffix (tool.xml or macro.xml)
    - line number (1 based)
    - xpath
    """
    with tempfile.TemporaryDirectory() as tmp:
        tool_path = os.path.join(tmp, "tool.xml")
        macros_path = os.path.join(tmp, "macros.xml")
        with open(tool_path, "w") as tmpf:
            tmpf.write(COMPLETE)
        with open(macros_path, "w") as tmpf:
            tmpf.write(COMPLETE_MACROS)
        tool_xml, _ = load_with_references(tool_path)

    tool_source = XmlToolSource(tool_xml)
    # lint once with the lint context using XMLLintMessageXPath and XMLLintMessageLine
    lint_tool_source_with(lint_ctx_xpath, tool_source)
    lint_tool_source_with(lint_ctx, tool_source)

    asserts = (
        ("Select parameter [select] has multiple options with the same value", 5, "/tool/inputs/param[1]"),
        ("Found param input with no name specified.", 13, "/tool/inputs/param[2]"),
        ("Param input [No_type] input with no type specified.", 3, "/tool/inputs/param[3]"),
    )
    for a in asserts:
        message, line, xpath = a
        found = False
        for lint_message in lint_ctx_xpath.message_list:
            if lint_message.message != message:
                continue
            found = True
            assert (
                lint_message.xpath == xpath
            ), f"Assumed xpath {xpath}; found xpath {lint_message.xpath} for: {message}"
        assert found, f"Did not find {message}"
        for lint_message in lint_ctx.message_list:
            if lint_message.message != message:
                continue
            found = True
            assert lint_message.line == line, f"Assumed line {line}; found line {lint_message.line} for: {message}"
        assert found, f"Did not find {message}"


# TODO COPIED from test/unit/app/tools/test_tool_deserialization.py
CWL_TOOL = """
cwlVersion: v1.0
class: CommandLineTool
baseCommand: echo
inputs:
  message:
    type: string
    inputBinding:
      position: 1
outputs: []
"""

YAML_TOOL = """
class: GalaxyTool
id: simple_constructs_y
name: simple_constructs_y
version: 1.0
command:
  >
    echo "$booltest"  >> $out_file1;
inputs:
- name: booltest
  type: boolean
  truevalue: booltrue
  falsevalue: boolfalse
  checked: false
outputs:
  out_file1:
    format: txt
"""


def test_linting_yml_tool(lint_ctx):
    with tempfile.TemporaryDirectory() as tmp:
        tool_path = os.path.join(tmp, "tool.yml")
        with open(tool_path, "w") as tmpf:
            tmpf.write(YAML_TOOL)
        tool_sources = load_tool_sources_from_path(tmp)
        assert len(tool_sources) == 1, "Expected 1 tool source"
        tool_source = tool_sources[0][1]
        lint_tool_source_with(lint_ctx, tool_source)
    assert "Tool defines a version [1.0]." in lint_ctx.valid_messages
    assert "Tool defines a name [simple_constructs_y]." in lint_ctx.valid_messages
    assert "Tool defines an id [simple_constructs_y]." in lint_ctx.valid_messages
    assert "Tool specifies profile version [16.04]." in lint_ctx.valid_messages
    assert not lint_ctx.info_messages
    assert len(lint_ctx.valid_messages) == 4
    assert not lint_ctx.warn_messages
    assert not lint_ctx.error_messages


def test_linting_cwl_tool(lint_ctx):
    with tempfile.TemporaryDirectory() as tmp:
        tool_path = os.path.join(tmp, "tool.cwl")
        with open(tool_path, "w") as tmpf:
            tmpf.write(CWL_TOOL)
        tool_sources = load_tool_sources_from_path(tmp)
        assert len(tool_sources) == 1, "Expected 1 tool source"
        tool_source = tool_sources[0][1]
        lint_tool_source_with(lint_ctx, tool_source)
    assert "Tool defines a version [0.0.1]." in lint_ctx.valid_messages
    assert "Tool defines a name [tool]." in lint_ctx.valid_messages
    assert "Tool defines an id [tool]." in lint_ctx.valid_messages
    assert "Tool specifies profile version [16.04]." in lint_ctx.valid_messages
    assert "CWL appears to be valid." in lint_ctx.info_messages
    assert "Description of tool is empty or absent." in lint_ctx.warn_messages
    assert "Tool does not specify a DockerPull source." in lint_ctx.warn_messages
    assert "Modern CWL version [v1.0]." in lint_ctx.info_messages
    assert len(lint_ctx.info_messages) == 2
    assert len(lint_ctx.valid_messages) == 4
    assert len(lint_ctx.warn_messages) == 2
    assert not lint_ctx.error_messages


def test_xml_comments_are_ignored(lint_ctx: LintContext):
    tool_xml = get_tool_xml_exact(TOOL_WITH_COMMENTS)
    lint_xml_with(lint_ctx, tool_xml)
    for lint_message in lint_ctx.message_list:
        assert "Comment" not in lint_message.message
