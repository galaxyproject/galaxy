import inspect
import os
import tempfile

import pytest

import galaxy.tool_util.linters
from galaxy.tool_util.lint import (
    lint_tool_source_with,
    lint_tool_source_with_modules,
    LintContext,
    Linter,
    XMLLintMessageLine,
    XMLLintMessageXPath,
)
from galaxy.tool_util.linters import (
    citations,
    command,
    general,
    help,
    inputs,
    output,
    stdio,
    tests,
    xml_order,
    xsd,
)
from galaxy.tool_util.loader_directory import load_tool_sources_from_path
from galaxy.tool_util.parser.interface import ToolSource
from galaxy.tool_util.parser.xml import XmlToolSource
from galaxy.tool_util.unittest_utils import functional_test_tool_path
from galaxy.util import (
    ElementTree,
    submodules,
)
from galaxy.util.unittest_utils import skip_if_site_down
from galaxy.util.xml_macros import load_with_references

# TODO tests tool xml for general linter
# tests tool xml for citations linter
CITATIONS_MULTIPLE = """
<tool id="id" name="name">
    <citations/>
    <citations/>
</tool>
"""

CITATIONS_ABSENT = """
<tool id="id" name="name"/>
"""

CITATIONS_ERRORS = """
<tool id="id" name="name">
    <citations>
        <citation type="doi"> </citation>
    </citations>
</tool>
"""

CITATIONS_VALID = """
<tool id="id" name="name">
    <citations>
        <citation type="doi">DOI</citation>
    </citations>
</tool>
"""

# tests tool xml for command linter
COMMAND_MULTIPLE = """
<tool id="id" name="name">
    <command>ls</command>
    <command>df</command>
</tool>
"""
COMMAND_MISSING = """
<tool id="id" name="name"/>
"""
COMMAND_TODO = """
<tool id="id" name="name">
    <command>
        ## TODO
    </command>
</tool>
"""
COMMAND_DETECT_ERRORS_INTERPRETER = """
<tool id="id" name="name">
    <command detect_errors="nonsense" interpreter="python"/>
</tool>
"""


# tests tool xml for general linter
GENERAL_MISSING_TOOL_ID_NAME_VERSION = """
<tool profile="2109">
</tool>
"""

GENERAL_WHITESPACE_IN_VERSIONS_AND_NAMES = """
<tool name=" BWA Mapper " id="bwa tool" version=" 1.0.1 " display_interface="true" require_login="true" hidden="true">
    <requirements>
        <requirement type="package" version=" 1.2.5 "> bwa </requirement>
    </requirements>
</tool>
"""

GENERAL_REQUIREMENT_WO_VERSION = """
<tool name="BWA Mapper" id="bwa_tool" version="1.0.1blah" display_interface="true" require_login="true" hidden="true" profile="20.09">
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

GENERAL_VALID_NEW_PROFILE_FMT = """
<tool name="valid name" id="valid_id" version="1.0+galaxy1" profile="23.0">
</tool>
"""

GENERAL_VALID_BIOTOOLS = """
<tool name="valid name" id="valid_id" version="1.0+galaxy1" profile="23.0">
    <xrefs>
        <xref type="bio.tools">bwa</xref>
        <xref type="bio.tools">johnscoolbowtie</xref>
    </xrefs>
</tool>
"""

GENERAL_VALID_EDAM = """
<tool name="valid name" id="valid_id" version="1.0+galaxy1" profile="23.0">
    <edam_topics>
        <edam_topic>topic_2269</edam_topic>
        <edam_topic>topic_000</edam_topic>
    </edam_topics>
    <edam_operations>
        <edam_operation>operation_3434</edam_operation>
        <edam_operation>operation_000</edam_operation>
    </edam_operations>
</tool>
"""

# test tool xml for help linter
HELP_MULTIPLE = """
<tool id="id" name="name">
    <help>Help</help>
    <help>More help</help>
</tool>
"""

HELP_ABSENT = """
<tool id="id" name="name">
</tool>
"""

HELP_EMPTY = """
<tool id="id" name="name">
    <help> </help>
</tool>
"""

HELP_TODO = """
<tool id="id" name="name">
    <help>TODO</help>
</tool>
"""

HELP_INVALID_RST = """
<tool id="id" name="name">
    <help>
        **xxl__
    </help>
</tool>
"""

# test tool xml for inputs linter
INPUTS_NO_INPUTS = """
<tool id="id" name="name">
</tool>
"""

INPUTS_NO_INPUTS_DATASOURCE = """
<tool tool_type="data_source">
    <inputs/>
</tool>
"""

INPUTS_VALID = """
<tool id="id" name="name">
    <inputs>
        <param name="txt_param" type="text"/>
        <param name="int_param" type="integer"/>
    </inputs>
</tool>
"""

INPUTS_PARAM_NAME = """
<tool id="id" name="name">
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
<tool id="id" name="name">
    <inputs>
        <param name="valid_name"/>
        <param argument="--another-valid-name" type=""/>
    </inputs>
</tool>
"""

INPUTS_DATA_PARAM = """
<tool id="id" name="name">
    <inputs>
        <param name="valid_name" type="data"/>
    </inputs>
</tool>
"""

INPUTS_DATA_PARAM_OPTIONS = """
<tool id="id" name="name">
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
<tool id="id" name="name">
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
<tool id="id" name="name">
    <inputs>
        <param name="valid_name" type="data" format="txt">
            <options/>
            <options from_file="blah">
                <filter type="regexp"/>
            </options>
        </param>
    </inputs>
</tool>
"""

INPUTS_BOOLEAN_PARAM_SWAPPED_LABELS = """
<tool id="id" name="name">
    <inputs>
        <param name="valid_name" type="boolean" truevalue="false" falsevalue="true" />
    </inputs>
</tool>
"""

INPUTS_BOOLEAN_PARAM_DUPLICATE_LABELS = """
<tool id="id" name="name">
    <inputs>
        <param name="valid_name" type="boolean" truevalue="--foo" falsevalue="--foo" />
    </inputs>
</tool>
"""

INPUTS_CONDITIONAL = """
<tool id="id" name="name">
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
<tool id="id" name="name">
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
<tool id="id" name="name">
    <inputs>
        <param name="select" type="select" optional="true" multiple="true">
            <option value="v">x</option>
            <option value="v">x</option>
        </param>
    </inputs>
</tool>
"""

SELECT_DUPLICATED_OPTIONS_WITH_DIFF_SELECTED = """
<tool id="id" name="name">
    <inputs>
        <param name="select" type="select" optional="true" multiple="true">
            <option value="v">x</option>
            <option value="v" selected="true">x</option>
        </param>
    </inputs>
</tool>
"""

INPUTS_SELECT_DEPRECATIONS = """
<tool id="id" name="name">
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
<tool id="id" name="name">
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
<tool id="id" name="name">
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
<tool id="id" name="name">
    <inputs>
        <param name="param_name" type="text">
            <validator type="in_range">TEXT</validator>
            <validator type="regex" filename="blah"/>
            <validator type="expression"/>
            <validator type="regex">[</validator>
            <validator type="expression">(</validator>
            <validator type="expression">value and "," not in value</validator>
            <validator type="value_in_data_table"/>
        </param>
        <param name="another_param_name" type="data" format="bed">
            <validator type="metadata" value="value"/>
            <validator type="dataset_metadata_equal" value="value" value_json="['1', '2']" metadata_name="columns"/>
        </param>
    </inputs>
</tool>
"""

INPUTS_VALIDATOR_CORRECT = """
<tool id="id" name="name">
    <inputs>
        <param name="data_param" type="data" format="data">
            <validator type="metadata" check="md1,md2" skip="md3,md4" message="custom validation message" negate="true"/>
            <validator type="dataset_metadata_equal" metadata_name="columns" value="xyz" message="custom validation message %s" negate="true"/>
            <validator type="unspecified_build" message="custom validation message" negate="true"/>
            <validator type="dataset_ok_validator" message="custom validation message" negate="true"/>
            <validator type="dataset_metadata_equal" metadata_name="columns" value="8"/>
            <validator type="dataset_metadata_in_range" metadata_name="sequences" min="0" max="100" exclude_min="true" exclude_max="true" message="custom validation message" negate="true"/>
            <validator type="dataset_metadata_in_file" filename="file.tsv" metadata_column="3" split="," metadata_name="dbkey" message="custom validation message" negate="true"/>
            <validator type="dataset_metadata_in_data_table" table_name="datatable_name" metadata_column="3" metadata_name="dbkey" message="custom validation message" negate="true"/>
        </param>
        <param name="collection_param" type="data_collection">
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
<tool id="id" name="name">
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
            <options>
                <column name="x" index="0"/>
            </options>
        </param>
        <param name="int_param" type="integer">
            <options>
                <column name="x" index="0"/>
            </options>
        </param>
    </inputs>
</tool>
"""

INPUTS_DUPLICATE_NAMES = """
<tool id="id" name="name">
    <inputs>
        <param name="dup" type="text"/>
        <param name="dup" type="text"/>
        <param name="dup_in_section" type="text"/>
        <section name="sec" title="">
            <param name="dup_in_section" type="text"/>
        </section>
        <conditional name="cond">
            <param name="dup_in_cond" type="select">
                <option value="a">a</option>
                <option value="b">b</option>
            </param>
            <when value="a">
                <param name="dup_in_cond" type="text"/>
            </when>
            <when value="b">
                <param name="dup_in_cond" type="text"/>
            </when>
        </conditional>
        <param name="dup_in_output" type="text"/>
    </inputs>
    <outputs>
        <data name="dup_in_output"/>
    </outputs>
</tool>
"""

# test tool xml for outputs linter
OUTPUTS_MISSING = """
<tool id="id" name="name"/>
"""
OUTPUTS_MULTIPLE = """
<tool id="id" name="name">
    <outputs/>
    <outputs/>
</tool>
"""
OUTPUTS_UNKNOWN_TAG = """
<tool id="id" name="name">
    <outputs>
        <output name="name"/>
    </outputs>
</tool>
"""
OUTPUTS_UNNAMED_INVALID_NAME = """
<tool id="id" name="name">
    <outputs>
        <data label="data out"/>
        <collection type="list" format="txt" label="collection out"/>
        <collection name="2output" label="coll out"/>
    </outputs>
</tool>
"""
OUTPUTS_FORMAT_INPUT_LEGACY = """
<tool id="id" name="name">
    <outputs>
        <data name="valid_name" format="input"/>
    </outputs>
</tool>
"""
OUTPUTS_FORMAT_INPUT = """
<tool id="id" name="name" profile="16.04">
    <outputs>
        <data name="valid_name" format="input"/>
    </outputs>
</tool>
"""

# check that linter accepts format source for collection elements as means to specify format
# and that the linter warns if format and format_source are used
OUTPUTS_COLLECTION_FORMAT_SOURCE = """
<tool id="id" name="name">
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
<tool id="id" name="name">
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
<tool id="id" name="name">
    <command>galaxy.json</command>
    <outputs>
        <data name="output">
            <discover_datasets/>
        </data>
    </outputs>
</tool>
"""

OUTPUTS_DUPLICATED_NAME_LABEL = """
<tool id="id" name="name">
    <outputs>
        <data name="valid_name" format="fasta"/>
        <data name="valid_name" format="fasta"/>
        <data name="another_valid_name" format="fasta" label="same label may be OK if there is a filter">
            <filter>a and condition</filter>
        </data>
        <data name="yet_another_valid_name" format="fasta" label="same label may be OK if there is a filter">
            <filter>another or condition</filter>
        </data>
    </outputs>
</tool>
"""

# check if filters are valid python expressions
OUTPUTS_FILTER_EXPRESSION = """
<tool id="id" name="name">
    <outputs>
        <data name="another_valid_name" format="fasta" label="a label">
            <filter>an invalid condition</filter>
            <filter>an and condition</filter>
        </data>
        <collection name="yet_another_valid_name" type="list" format="fasta" label="another label">
            <filter>another invalid condition</filter>
            <filter>another or condition</filter>
        </collection>
    </outputs>
</tool>
"""

# tool xml for repeats linter
REPEATS = """
<tool id="id" name="name">
    <inputs>
        <repeat>
            <param name="another_param_name" type="data" format="bed"/>
        </repeat>
    </inputs>
</tool>
"""

# tool xml for stdio linter
STDIO_DEFAULT_FOR_DEFAULT_PROFILE = """
<tool id="id" name="name">
</tool>
"""

STDIO_DEFAULT_FOR_NONLEGACY_PROFILE = """
<tool id="id" name="name" profile="21.09">
</tool>
"""

STDIO_MULTIPLE_STDIO = """
<tool id="id" name="name">
    <stdio/>
    <stdio/>
</tool>
"""

STDIO_INVALID_CHILD_OR_ATTRIB = """
<tool id="id" name="name">
    <stdio>
        <regex descriptio="blah" level="fatal" match="error" source="stdio"/>
        <exit_code descriptio="blah" level="fatal" range="1:"/>
        <reqex/>
    </stdio>
</tool>
"""

STDIO_INVALID_MATCH = """
<tool id="id" name="name">
    <stdio>
        <regex match="["/>
    </stdio>
</tool>
"""

# check that linter does complain about tests wo assumptions
TESTS_ABSENT = """
<tool id="id" name="name"/>
"""
TESTS_ABSENT_YAML = """
class: GalaxyTool
name: name
id: id
"""
TESTS_ABSENT_DATA_SOURCE = """
<tool id="id" name="name" tool_type="data_source"/>
"""
TESTS_WO_EXPECTATIONS = """
<tool id="id" name="name">
    <tests>
        <test>
        </test>
    </tests>
</tool>
"""

TESTS_PARAM_OUTPUT_NAMES = """
<tool id="id" name="name">
    <inputs>
        <param argument="--existent-test-name" type="text"/>
        <conditional name="cond">
            <param name="cond_select" type="select"/>
            <when value="blah">
                <param name="another_existent_test_name" type="text"/>
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
<tool id="id" name="name">
    <outputs>
        <data name="test"/>
    </outputs>
    <tests>
        <test expect_failure="true">
            <output name="test"/>
        </test>
        <test expect_num_outputs="1" expect_failure="true"/>
    </tests>
</tool>
"""

ASSERTS = """
<tool id="id" name="name">
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
                <has_size value="500k" size="50"/>
                <has_text invalid_attrib="blah"/>
            </assert_command>
            <output name="out_archive">
                <assert_contents>
                    <has_size value="500k" delta="1X"/>
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
INVALID_CENTER_OF_MASS = """
<tool id="id" name="name">
    <outputs>
        <data name="out_image"/>
    </outputs>
    <tests>
        <test>
            <output name="out_image">
                <assert_contents>
                    <has_image_center_of_mass center_of_mass="511.07, 223.34, 2.3" />
                </assert_contents>
            </output>
        </test>
    </tests>
</tool>
"""
VALID_CENTER_OF_MASS = """
<tool id="id" name="name">
    <outputs>
        <data name="out_image"/>
    </outputs>
    <tests>
        <test>
            <output name="out_image">
                <assert_contents>
                    <has_image_center_of_mass center_of_mass="511.07, 223.34" />
                </assert_contents>
            </output>
        </test>
    </tests>
</tool>
"""
TESTS_VALID = """
<tool id="id" name="name">
    <outputs>
        <data name="test"/>
    </outputs>
    <tests>
        <test>
            <output name="test" value="empty.txt" />
        </test>
    </tests>
</tool>
"""
TESTS_OUTPUT_TYPE_MISMATCH = """
<tool id="id" name="name">
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
<tool id="id" name="name">
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
        <!-- no count or discovered_dataset/element
             - no outputs can be given
             - consequently also counts and expect_num_output need not to be given -->
        <test expect_failure="true"/>
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

TESTS_EXPECT_NUM_OUTPUTS_FILTER = """
<tool id="id" name="name">
    <outputs>
        <data name="name">
            <filter/>
        </data>
    </outputs>
    <tests>
        <test expect_failure="false">
        </test>
    </tests>
</tool>
"""

TESTS_COMPARE_ATTRIB_INCOMPATIBILITY = """
<tool id="id" name="name">
    <outputs>
        <data name="data_name"/>
        <collection name="collection_name" type="list:list"/>
    </outputs>
    <tests>
        <test>
            <output name="data_name" compare="re_match" decompress="true"/>
            <output_collection name="collection_name">
                <element compare="contains" sort="true" />
            </output_collection>
        </test>
        <test>
            <output name="data_name" compare="diff" lines_diff="2"/>
            <output_collection name="collection_name">
                <element compare="contains" lines_diff="2" />
            </output_collection>
        </test>
    </tests>
</tool>"""

# tool xml for xml_order linter
XML_ORDER = """
<tool id="id" name="name">
    <wrong_tag/>
    <command/>
    <stdio/>
</tool>
"""

TOOL_WITH_COMMENTS = """
<tool id="id" name="name" version="1" profile="22.01">
    <stdio>
        <!-- This is a comment -->
        <regex match="low space" source="both" level="warning" description="Low space on device" />
    </stdio>
    <outputs>
        <!-- This is a comment -->
        <data format="pdf" name="out_file1" />
    </outputs>
</tool>
"""


@pytest.fixture()
def lint_ctx():
    return LintContext("all", lint_message_class=XMLLintMessageLine)


@pytest.fixture()
def lint_ctx_xpath():
    return LintContext("all", lint_message_class=XMLLintMessageXPath)


def get_xml_tree(xml_string: str) -> ElementTree:
    with tempfile.NamedTemporaryFile(mode="w", suffix="tool.xml") as tmp:
        tmp.write(xml_string)
        tmp.flush()
        tool_path = tmp.name
        return load_with_references(tool_path)[0]


def get_xml_tool_source(xml_string: str) -> XmlToolSource:
    return XmlToolSource(get_xml_tree(xml_string))


def get_tool_source(source_contents: str) -> ToolSource:
    if "GalaxyTool" in source_contents:
        with tempfile.NamedTemporaryFile(mode="w", suffix="tool.yml") as tmp:
            tmp.write(source_contents)
            tmp.flush()
            tool_sources = load_tool_sources_from_path(tmp.name)
            assert len(tool_sources) == 1, "Expected 1 tool source"
            tool_source = tool_sources[0][1]
            return tool_source
    else:
        return get_xml_tool_source(source_contents)


def run_lint_module(lint_ctx, lint_module, lint_target):
    lint_tool_source_with_modules(lint_ctx, lint_target, list({lint_module, xsd}))


def run_lint(lint_ctx, lint_func, lint_target):
    lint_ctx.lint(name="test_lint", lint_func=lint_func, lint_target=lint_target)
    # check if the lint messages have the line
    for message in lint_ctx.message_list:
        assert message.line is not None, f"No context found for message: {message.message}"


def test_citations_multiple(lint_ctx):
    tool_source = get_xml_tool_source(CITATIONS_MULTIPLE)
    run_lint_module(lint_ctx, citations, tool_source)
    assert lint_ctx.error_messages == ["Invalid XML: Element 'citations': This element is not expected."]
    assert not lint_ctx.info_messages
    assert not lint_ctx.valid_messages
    assert not lint_ctx.warn_messages


def test_citations_absent(lint_ctx):
    tool_source = get_xml_tool_source(CITATIONS_ABSENT)
    run_lint_module(lint_ctx, citations, tool_source)
    assert lint_ctx.warn_messages == ["No citations found, consider adding citations to your tool."]
    assert not lint_ctx.info_messages
    assert not lint_ctx.valid_messages
    assert not lint_ctx.error_messages


def test_citations_errors(lint_ctx):
    tool_source = get_xml_tool_source(CITATIONS_ERRORS)
    run_lint_module(lint_ctx, citations, tool_source)
    assert lint_ctx.error_messages == ["Empty doi citation."]
    assert not lint_ctx.warn_messages
    assert not lint_ctx.info_messages
    assert len(lint_ctx.valid_messages) == 1


def test_citations_valid(lint_ctx):
    tool_source = get_xml_tool_source(CITATIONS_VALID)
    run_lint_module(lint_ctx, citations, tool_source)
    assert "Found 1 citations." in lint_ctx.valid_messages
    assert len(lint_ctx.valid_messages) == 1
    assert not lint_ctx.info_messages
    assert not lint_ctx.error_messages


def test_command_multiple(lint_ctx):
    tool_source = get_xml_tool_source(COMMAND_MULTIPLE)
    run_lint_module(lint_ctx, command, tool_source)
    assert lint_ctx.error_messages == ["Invalid XML: Element 'command': This element is not expected."]
    assert lint_ctx.info_messages == ["Tool contains a command."]
    assert not lint_ctx.valid_messages
    assert not lint_ctx.warn_messages


def test_command_missing(lint_ctx):
    tool_source = get_xml_tool_source(COMMAND_MISSING)
    run_lint_module(lint_ctx, command, tool_source)
    assert lint_ctx.error_messages == ["No command tag found, must specify a command template to execute."]
    assert not lint_ctx.info_messages
    assert not lint_ctx.valid_messages
    assert not lint_ctx.warn_messages


def test_command_todo(lint_ctx):
    tool_source = get_xml_tool_source(COMMAND_TODO)
    run_lint_module(lint_ctx, command, tool_source)
    assert not lint_ctx.error_messages
    assert lint_ctx.info_messages == ["Tool contains a command."]
    assert lint_ctx.warn_messages == ["Command template contains TODO text."]
    assert not lint_ctx.valid_messages


def test_command_detect_errors_interpreter(lint_ctx):
    tool_source = get_xml_tool_source(COMMAND_DETECT_ERRORS_INTERPRETER)
    run_lint_module(lint_ctx, command, tool_source)
    assert "Command is empty." in lint_ctx.error_messages
    assert (
        "Invalid XML: Element 'command', attribute 'detect_errors': [facet 'enumeration'] The value 'nonsense' is not an element of the set {'default', 'exit_code', 'aggressive'}."
        in lint_ctx.error_messages
    )
    assert lint_ctx.warn_messages == ["Command uses deprecated 'interpreter' attribute."]
    assert lint_ctx.info_messages == ["Tool contains a command with interpreter of type [python]."]
    assert not lint_ctx.valid_messages
    assert len(lint_ctx.error_messages) == 2


def test_general_missing_tool_id_name_version(lint_ctx):
    tool_source = get_xml_tool_source(GENERAL_MISSING_TOOL_ID_NAME_VERSION)
    run_lint_module(lint_ctx, general, tool_source)
    assert "Tool version is missing or empty." in lint_ctx.error_messages
    assert "Tool name is missing or empty." in lint_ctx.error_messages
    assert "Tool does not define an id attribute." in lint_ctx.error_messages
    assert "Tool specifies an invalid profile version [2109]." in lint_ctx.error_messages


def test_general_whitespace_in_versions_and_names(lint_ctx):
    tool_source = get_xml_tool_source(GENERAL_WHITESPACE_IN_VERSIONS_AND_NAMES)
    run_lint_module(lint_ctx, general, tool_source)
    assert "Tool version is pre/suffixed by whitespace, this may cause errors: [ 1.0.1 ]." in lint_ctx.warn_messages
    assert "Tool name is pre/suffixed by whitespace, this may cause errors: [ BWA Mapper ]." in lint_ctx.warn_messages
    assert "Requirement version contains whitespace, this may cause errors: [ 1.2.5 ]." in lint_ctx.warn_messages
    assert "Tool ID contains whitespace - this is discouraged: [bwa tool]." in lint_ctx.warn_messages
    assert "Tool targets 16.01 Galaxy profile." in lint_ctx.valid_messages


def test_general_requirement_without_version(lint_ctx):
    tool_source = get_xml_tool_source(GENERAL_REQUIREMENT_WO_VERSION)
    run_lint_module(lint_ctx, general, tool_source)
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
    run_lint_module(lint_ctx, general, tool_source)
    assert "Tool defines a version [1.0+galaxy1]." in lint_ctx.valid_messages
    assert "Tool specifies profile version [21.09]." in lint_ctx.valid_messages
    assert "Tool defines an id [valid_id]." in lint_ctx.valid_messages
    assert "Tool defines a name [valid name]." in lint_ctx.valid_messages
    assert not lint_ctx.info_messages
    assert len(lint_ctx.valid_messages) == 4
    assert not lint_ctx.warn_messages
    assert not lint_ctx.error_messages


def test_general_valid_new_profile_fmt(lint_ctx):
    tool_source = get_xml_tool_source(GENERAL_VALID_NEW_PROFILE_FMT)
    run_lint_module(lint_ctx, general, tool_source)
    assert "Tool defines a version [1.0+galaxy1]." in lint_ctx.valid_messages
    assert "Tool specifies profile version [23.0]." in lint_ctx.valid_messages
    assert "Tool defines an id [valid_id]." in lint_ctx.valid_messages
    assert "Tool defines a name [valid name]." in lint_ctx.valid_messages
    assert not lint_ctx.info_messages
    assert len(lint_ctx.valid_messages) == 4
    assert not lint_ctx.warn_messages
    assert not lint_ctx.error_messages


@skip_if_site_down("https://bio.tools/")
def test_general_valid_biotools(lint_ctx):
    tool_source = get_xml_tool_source(GENERAL_VALID_BIOTOOLS)
    run_lint_module(lint_ctx, general, tool_source)
    assert "No entry johnscoolbowtie in bio.tools." in lint_ctx.warn_messages
    assert not lint_ctx.info_messages
    assert len(lint_ctx.valid_messages) == 4
    assert len(lint_ctx.warn_messages) == 1
    assert not lint_ctx.error_messages


def test_general_text_spaces_comments(lint_ctx):
    tool_source = get_xml_tool_source(TOOL_WITH_COMMENTS)
    run_lint_module(lint_ctx, general, tool_source)
    assert not lint_ctx.info_messages
    assert len(lint_ctx.valid_messages) == 4
    assert not lint_ctx.warn_messages
    assert not lint_ctx.error_messages


def test_general_valid_edam(lint_ctx):
    tool_source = get_xml_tool_source(GENERAL_VALID_EDAM)
    run_lint_module(lint_ctx, general, tool_source)
    assert "No entry 'operation_000' in EDAM." in lint_ctx.warn_messages
    assert "No entry 'topic_000' in EDAM." in lint_ctx.warn_messages
    assert not lint_ctx.info_messages
    assert len(lint_ctx.valid_messages) == 4
    assert len(lint_ctx.warn_messages) == 2
    # accept 2 xsd errors due to malformed topic/operation ID
    # which should make sure that the id never becomes valid
    assert len(lint_ctx.error_messages) == 2


def test_help_multiple(lint_ctx):
    tool_source = get_xml_tool_source(HELP_MULTIPLE)
    run_lint_module(lint_ctx, help, tool_source)
    assert not lint_ctx.info_messages
    assert len(lint_ctx.valid_messages) == 2  # has help and valid rst
    assert not lint_ctx.warn_messages
    assert lint_ctx.error_messages == ["Invalid XML: Element 'help': This element is not expected."]


def test_help_absent(lint_ctx):
    tool_source = get_xml_tool_source(HELP_ABSENT)
    run_lint_module(lint_ctx, help, tool_source)
    assert "No help section found, consider adding a help section to your tool." in lint_ctx.warn_messages
    assert not lint_ctx.info_messages
    assert not lint_ctx.valid_messages
    assert len(lint_ctx.warn_messages) == 1
    assert not lint_ctx.error_messages


def test_help_empty(lint_ctx):
    tool_source = get_xml_tool_source(HELP_EMPTY)
    run_lint_module(lint_ctx, help, tool_source)
    assert "Help section appears to be empty." in lint_ctx.warn_messages
    assert not lint_ctx.info_messages
    assert not lint_ctx.valid_messages
    assert len(lint_ctx.warn_messages) == 1
    assert not lint_ctx.error_messages


def test_help_todo(lint_ctx):
    tool_source = get_xml_tool_source(HELP_TODO)
    run_lint_module(lint_ctx, help, tool_source)
    assert "Tool contains help section." in lint_ctx.valid_messages
    assert "Help contains valid reStructuredText." in lint_ctx.valid_messages
    assert "Help contains TODO text." in lint_ctx.warn_messages
    assert not lint_ctx.info_messages
    assert len(lint_ctx.valid_messages) == 2
    assert len(lint_ctx.warn_messages) == 1
    assert not lint_ctx.error_messages


def test_help_invalid_rst(lint_ctx):
    tool_source = get_xml_tool_source(HELP_INVALID_RST)
    run_lint_module(lint_ctx, help, tool_source)
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
    run_lint_module(lint_ctx, inputs, tool_source)
    assert "Found no input parameters." in lint_ctx.warn_messages
    assert not lint_ctx.info_messages
    assert not lint_ctx.valid_messages
    assert len(lint_ctx.warn_messages) == 1
    assert not lint_ctx.error_messages


def test_inputs_no_inputs_datasource(lint_ctx):
    tool_source = get_xml_tool_source(INPUTS_NO_INPUTS_DATASOURCE)
    run_lint_module(lint_ctx, inputs, tool_source)
    assert "No input parameters, OK for data sources" in lint_ctx.info_messages
    assert "display tag usually present in data sources" in lint_ctx.info_messages
    assert "uihints tag usually present in data sources" in lint_ctx.info_messages
    assert len(lint_ctx.info_messages) == 3
    assert not lint_ctx.valid_messages
    assert not lint_ctx.warn_messages
    assert not lint_ctx.error_messages


def test_inputs_valid(lint_ctx):
    tool_source = get_xml_tool_source(INPUTS_VALID)
    run_lint_module(lint_ctx, inputs, tool_source)
    assert "Found 2 input parameters." in lint_ctx.info_messages
    assert len(lint_ctx.info_messages) == 1
    assert not lint_ctx.valid_messages
    assert not lint_ctx.warn_messages
    assert not lint_ctx.error_messages


def test_inputs_param_name(lint_ctx):
    tool_source = get_xml_tool_source(INPUTS_PARAM_NAME)
    run_lint_module(lint_ctx, inputs, tool_source)
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
    run_lint_module(lint_ctx, inputs, tool_source)
    assert "Found 2 input parameters." in lint_ctx.info_messages
    assert "Invalid XML: Element 'param': The attribute 'type' is required but missing." in lint_ctx.error_messages
    assert (
        "Invalid XML: Element 'param', attribute 'type': [facet 'enumeration'] The value '' is not an element of the set {'text', 'integer', 'float', 'color', 'boolean', 'genomebuild', 'select', 'data_column', 'hidden', 'hidden_data', 'baseurl', 'file', 'data', 'drill_down', 'group_tag', 'data_collection', 'directory_uri'}."
        in lint_ctx.error_messages
    )
    assert len(lint_ctx.info_messages) == 1
    assert not lint_ctx.valid_messages
    assert not lint_ctx.warn_messages
    assert len(lint_ctx.error_messages) == 2


def test_inputs_data_param(lint_ctx):
    tool_source = get_xml_tool_source(INPUTS_DATA_PARAM)
    run_lint_module(lint_ctx, inputs, tool_source)
    assert "Found 1 input parameters." in lint_ctx.info_messages
    assert (
        "Param input [valid_name] with no format specified - 'data' format will be assumed." in lint_ctx.warn_messages
    )
    assert len(lint_ctx.info_messages) == 1
    assert not lint_ctx.valid_messages
    assert len(lint_ctx.warn_messages) == 1
    assert not lint_ctx.error_messages


def test_inputs_boolean_param(lint_ctx):
    tool_source = get_xml_tool_source(INPUTS_BOOLEAN_PARAM_DUPLICATE_LABELS)
    run_lint_module(lint_ctx, inputs, tool_source)
    assert "Found 1 input parameters." in lint_ctx.info_messages
    assert len(lint_ctx.info_messages) == 1
    assert not lint_ctx.valid_messages
    assert len(lint_ctx.warn_messages) == 1
    assert not lint_ctx.error_messages


def test_inputs_data_param_options(lint_ctx):
    tool_source = get_xml_tool_source(INPUTS_DATA_PARAM_OPTIONS)
    run_lint_module(lint_ctx, inputs, tool_source)
    assert not lint_ctx.valid_messages
    assert "Found 1 input parameters." in lint_ctx.info_messages
    assert len(lint_ctx.info_messages) == 1
    assert not lint_ctx.warn_messages
    assert not lint_ctx.error_messages


def test_inputs_data_param_options_filter_attribute(lint_ctx):
    tool_source = get_xml_tool_source(INPUTS_DATA_PARAM_OPTIONS_FILTER_ATTRIBUTE)
    run_lint_module(lint_ctx, inputs, tool_source)
    assert not lint_ctx.valid_messages
    assert "Found 1 input parameters." in lint_ctx.info_messages
    assert len(lint_ctx.info_messages) == 1
    assert not lint_ctx.warn_messages
    assert not lint_ctx.error_messages


def test_inputs_data_param_invalid_options(lint_ctx):
    tool_source = get_xml_tool_source(INPUTS_DATA_PARAM_INVALIDOPTIONS)
    run_lint_module(lint_ctx, inputs, tool_source)
    assert not lint_ctx.valid_messages
    assert "Found 1 input parameters." in lint_ctx.info_messages
    assert len(lint_ctx.info_messages) == 1
    assert not lint_ctx.warn_messages
    assert "Data parameter [valid_name] contains multiple options elements." in lint_ctx.error_messages
    assert "Data parameter [valid_name] filter needs to define a ref attribute" in lint_ctx.error_messages
    assert (
        'Data parameter [valid_name] for filters only type="data_meta" and key="dbkey" are allowed, found type="regexp" and key="None"'
        in lint_ctx.error_messages
    )
    assert len(lint_ctx.error_messages) == 3


def test_inputs_conditional(lint_ctx):
    tool_source = get_xml_tool_source(INPUTS_CONDITIONAL)
    run_lint_module(lint_ctx, inputs, tool_source)
    assert "Found 10 input parameters." in lint_ctx.info_messages
    assert (
        "Invalid XML: Element 'conditional': The attribute 'name' is required but missing." in lint_ctx.error_messages
    )
    assert (
        "Select parameter of a conditional [select] options have to be defined by 'option' children elements."
        in lint_ctx.error_messages
    )
    assert (
        "Invalid XML: Element 'param': This element is not expected. Expected is ( when )." in lint_ctx.error_messages
    )  # 2x param
    assert (
        "Invalid XML: Element 'conditional': Missing child element(s). Expected is ( param )."
        in lint_ctx.error_messages
    )
    assert 'Conditional [cond_text] first param should have type="select"' in lint_ctx.error_messages
    assert (
        'Conditional [cond_boolean] first param of type="boolean" is discouraged, use a select'
        in lint_ctx.warn_messages
    )
    assert "Conditional [cond_boolean] no truevalue/falsevalue found for when block 'False'" in lint_ctx.warn_messages
    assert 'Conditional [cond_w_optional_select] test parameter cannot be optional="true"' in lint_ctx.warn_messages
    assert 'Conditional [cond_w_multiple_select] test parameter cannot be multiple="true"' in lint_ctx.warn_messages
    assert "Invalid XML: Element 'when': The attribute 'value' is required but missing." in lint_ctx.error_messages
    assert "Conditional [missing_when] no <when /> block found for select option 'none'" in lint_ctx.warn_messages
    assert len(lint_ctx.info_messages) == 1
    assert not lint_ctx.valid_messages
    assert len(lint_ctx.warn_messages) == 6
    assert len(lint_ctx.error_messages) == 6


def test_inputs_select_incompatible_display(lint_ctx):
    tool_source = get_xml_tool_source(INPUTS_SELECT_INCOMPATIBLE_DISPLAY)
    run_lint_module(lint_ctx, inputs, tool_source)
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
    run_lint_module(lint_ctx, inputs, tool_source)
    assert "Found 1 input parameters." in lint_ctx.info_messages
    assert "Select parameter [select] has multiple options with the same text content" in lint_ctx.error_messages
    assert "Select parameter [select] has multiple options with the same value" in lint_ctx.error_messages
    assert len(lint_ctx.info_messages) == 1
    assert not lint_ctx.valid_messages
    assert not lint_ctx.warn_messages
    assert len(lint_ctx.error_messages) == 2


def test_inputs_duplicated_options_with_different_select(lint_ctx):
    tool_source = get_xml_tool_source(SELECT_DUPLICATED_OPTIONS_WITH_DIFF_SELECTED)
    run_lint_module(lint_ctx, inputs, tool_source)
    assert not lint_ctx.warn_messages
    assert not lint_ctx.error_messages


def test_inputs_select_deprecations(lint_ctx):
    tool_source = get_xml_tool_source(INPUTS_SELECT_DEPRECATIONS)
    run_lint_module(lint_ctx, inputs, tool_source)
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
    run_lint_module(lint_ctx, inputs, tool_source)
    run_lint_module(lint_ctx, xsd, tool_source)
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
    assert (
        "Select parameter [select_meta_file_key_incomp] 'meta_file_key' is only compatible with 'from_dataset'."
        in lint_ctx.error_messages
    )
    assert len(lint_ctx.info_messages) == 1
    assert not lint_ctx.valid_messages
    assert not lint_ctx.warn_messages
    assert len(lint_ctx.error_messages) == 7


def test_inputs_select_filter(lint_ctx):
    tool_source = get_xml_tool_source(INPUTS_SELECT_FILTER)
    run_lint_module(lint_ctx, inputs, tool_source)
    assert "Found 1 input parameters." in lint_ctx.info_messages
    assert "Invalid XML: Element 'filter': The attribute 'type' is required but missing." in lint_ctx.error_messages
    assert (
        "Invalid XML: Element 'filter', attribute 'type': [facet 'enumeration'] The value 'unknown_filter_type' is not an element of the set {'data_meta', 'param_value', 'static_value', 'regexp', 'unique_value', 'multiple_splitter', 'attribute_value_splitter', 'add_value', 'remove_value', 'sort_by'}."
        in lint_ctx.error_messages
    )
    assert len(lint_ctx.info_messages) == 1
    assert not lint_ctx.valid_messages
    assert not lint_ctx.warn_messages
    assert len(lint_ctx.error_messages) == 2


def test_inputs_validator_incompatibilities(lint_ctx):
    tool_source = get_xml_tool_source(INPUTS_VALIDATOR_INCOMPATIBILITIES)
    run_lint_module(lint_ctx, inputs, tool_source)
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
    assert "Parameter [param_name]: regex validators are expected to contain text" in lint_ctx.error_messages
    assert (
        "Parameter [param_name]: '[' is no valid regex: unterminated character set at position 0"
        in lint_ctx.error_messages
    )
    assert "Parameter [param_name]: '(' is no valid expression" in lint_ctx.error_messages
    assert (
        "Parameter [another_param_name]: 'metadata' validators need to define the 'check' or 'skip' attribute(s)"
        in lint_ctx.error_messages
    )
    assert (
        "Parameter [param_name]: 'value_in_data_table' validators need to define the 'table_name' attribute"
        in lint_ctx.error_messages
    )
    assert (
        "Parameter [another_param_name]: attribute 'value' is incompatible with validator of type 'metadata'"
        in lint_ctx.error_messages
    )
    assert (
        "Parameter [another_param_name]: 'dataset_metadata_equal' validators must not define the 'value' and the 'value_json' attributes"
        in lint_ctx.error_messages
    )
    assert len(lint_ctx.info_messages) == 1
    assert not lint_ctx.valid_messages
    assert len(lint_ctx.warn_messages) == 1
    assert len(lint_ctx.error_messages) == 11


def test_inputs_validator_correct(lint_ctx):
    tool_source = get_xml_tool_source(INPUTS_VALIDATOR_CORRECT)
    run_lint_module(lint_ctx, inputs, tool_source)
    assert "Found 5 input parameters." in lint_ctx.info_messages
    assert len(lint_ctx.info_messages) == 1
    assert not lint_ctx.valid_messages
    assert not lint_ctx.warn_messages
    assert not lint_ctx.error_messages


def test_inputs_type_child_combinations(lint_ctx):
    tool_source = get_xml_tool_source(INPUTS_TYPE_CHILD_COMBINATIONS)
    run_lint_module(lint_ctx, inputs, tool_source)
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
        "Parameter [int_param] './options' tags are only allowed for parameters of type ['data', 'select', 'drill_down']"
        in lint_ctx.error_messages
    )
    assert (
        "Parameter [int_param] './options/column' tags are only allowed for parameters of type ['data', 'select']"
        in lint_ctx.error_messages
    )
    assert len(lint_ctx.error_messages) == 4


def test_inputs_duplicate_names(lint_ctx):
    tool_source = get_xml_tool_source(INPUTS_DUPLICATE_NAMES)
    run_lint_module(lint_ctx, inputs, tool_source)
    assert len(lint_ctx.info_messages) == 1
    assert not lint_ctx.valid_messages
    assert not lint_ctx.warn_messages
    assert "Tool defines multiple parameters with the same name: 'dup'" in lint_ctx.error_messages
    assert (
        "Tool defines an output with a name equal to the name of an input: 'dup_in_output'" in lint_ctx.error_messages
    )
    assert len(lint_ctx.error_messages) == 2


def test_inputs_repeats(lint_ctx):
    """
    this was previously covered by a linter in inputs
    """
    tool_source = get_xml_tool_source(REPEATS)
    run_lint_module(lint_ctx, inputs, tool_source)
    assert lint_ctx.info_messages == ["Found 1 input parameters."]
    assert not lint_ctx.valid_messages
    assert not lint_ctx.warn_messages
    assert "Invalid XML: Element 'repeat': The attribute 'name' is required but missing." in lint_ctx.error_messages
    assert "Invalid XML: Element 'repeat': The attribute 'title' is required but missing." in lint_ctx.error_messages
    assert len(lint_ctx.error_messages) == 2


def test_outputs_missing(lint_ctx):
    tool_source = get_xml_tool_source(OUTPUTS_MISSING)
    run_lint_module(lint_ctx, output, tool_source)
    assert "Tool contains no outputs section, most tools should produce outputs." in lint_ctx.warn_messages
    assert not lint_ctx.info_messages
    assert not lint_ctx.valid_messages
    assert len(lint_ctx.warn_messages) == 1
    assert not lint_ctx.error_messages


def test_outputs_multiple(lint_ctx):
    tool_source = get_xml_tool_source(OUTPUTS_MULTIPLE)
    run_lint_module(lint_ctx, output, tool_source)
    assert "0 outputs found." in lint_ctx.info_messages
    assert "Invalid XML: Element 'outputs': This element is not expected." in lint_ctx.error_messages
    assert len(lint_ctx.info_messages) == 1
    assert not lint_ctx.valid_messages
    assert not lint_ctx.warn_messages
    assert len(lint_ctx.error_messages) == 1


def test_outputs_unknown_tag(lint_ctx):
    """
    In the past it has been assumed that output tags are not allowed, but only data.
    But, actually they are covered by xsd which is also tested here.
    Still output tags are not covered in the user facing xml schema docs and should
    probably be avoided.
    """
    tool_source = get_xml_tool_source(OUTPUTS_UNKNOWN_TAG)
    lint_tool_source_with_modules(lint_ctx, tool_source, [output, xsd])
    assert "0 outputs found." in lint_ctx.info_messages
    assert "Avoid the use of 'output' and replace by 'data' or 'collection'" in lint_ctx.warn_messages
    assert len(lint_ctx.info_messages) == 1
    assert not lint_ctx.valid_messages
    assert len(lint_ctx.warn_messages) == 1
    assert not lint_ctx.error_messages


def test_outputs_unnamed_invalid_name(lint_ctx):
    tool_source = get_xml_tool_source(OUTPUTS_UNNAMED_INVALID_NAME)
    run_lint_module(lint_ctx, output, tool_source)
    assert "3 outputs found." in lint_ctx.info_messages
    assert "Invalid XML: Element 'data': The attribute 'name' is required but missing." in lint_ctx.error_messages
    assert "Invalid XML: Element 'collection': The attribute 'name' is required but missing." in lint_ctx.error_messages
    assert "Tool data output with missing name doesn't define an output format." in lint_ctx.warn_messages
    assert "Tool output name [2output] is not a valid Cheetah placeholder." in lint_ctx.warn_messages
    assert "Collection output with undefined 'type' found." in lint_ctx.warn_messages
    assert "Tool collection output 2output doesn't define an output format." in lint_ctx.warn_messages
    assert len(lint_ctx.info_messages) == 1
    assert not lint_ctx.valid_messages
    assert len(lint_ctx.warn_messages) == 4
    assert len(lint_ctx.error_messages) == 2


def test_outputs_format_input_legacy(lint_ctx):
    tool_source = get_xml_tool_source(OUTPUTS_FORMAT_INPUT_LEGACY)
    run_lint_module(lint_ctx, output, tool_source)
    assert "1 outputs found." in lint_ctx.info_messages
    assert "Using format='input' on data is deprecated. Use the format_source attribute." in lint_ctx.warn_messages
    assert len(lint_ctx.info_messages) == 1
    assert not lint_ctx.valid_messages
    assert len(lint_ctx.warn_messages) == 1
    assert not lint_ctx.error_messages


def test_outputs_format_input(lint_ctx):
    tool_source = get_xml_tool_source(OUTPUTS_FORMAT_INPUT)
    run_lint_module(lint_ctx, output, tool_source)
    assert "1 outputs found." in lint_ctx.info_messages
    assert "Using format='input' on data is deprecated. Use the format_source attribute." in lint_ctx.error_messages
    assert len(lint_ctx.info_messages) == 1
    assert not lint_ctx.valid_messages
    assert not lint_ctx.warn_messages
    assert len(lint_ctx.error_messages) == 1


def test_outputs_collection_format_source(lint_ctx):
    tool_source = get_xml_tool_source(OUTPUTS_COLLECTION_FORMAT_SOURCE)
    run_lint_module(lint_ctx, output, tool_source)
    assert "Tool data output 'reverse' should use either format_source or format/ext" in lint_ctx.warn_messages
    assert len(lint_ctx.info_messages) == 1
    assert not lint_ctx.valid_messages
    assert len(lint_ctx.warn_messages) == 1
    assert not lint_ctx.error_messages


def test_outputs_format_action(lint_ctx):
    tool_source = get_xml_tool_source(OUTPUTS_FORMAT_ACTION)
    run_lint_module(lint_ctx, output, tool_source)
    assert len(lint_ctx.info_messages) == 1
    assert not lint_ctx.valid_messages
    assert not lint_ctx.warn_messages
    assert not lint_ctx.error_messages


def test_outputs_discover_tool_provided_metadata(lint_ctx):
    tool_source = get_xml_tool_source(OUTPUTS_DISCOVER_TOOL_PROVIDED_METADATA)
    run_lint_module(lint_ctx, output, tool_source)
    assert "1 outputs found." in lint_ctx.info_messages
    assert len(lint_ctx.info_messages) == 1
    assert not lint_ctx.valid_messages
    assert not lint_ctx.warn_messages
    assert not lint_ctx.error_messages


def test_outputs_duplicated_name_label(lint_ctx):
    """ """
    tool_source = get_xml_tool_source(OUTPUTS_DUPLICATED_NAME_LABEL)
    run_lint_module(lint_ctx, output, tool_source)
    assert "4 outputs found." in lint_ctx.info_messages
    assert len(lint_ctx.info_messages) == 1
    assert not lint_ctx.valid_messages
    assert len(lint_ctx.warn_messages) == 2
    assert "Tool output [valid_name] uses duplicated label '${tool.name} on ${on_string}'" in lint_ctx.warn_messages
    assert (
        "Tool output [yet_another_valid_name] uses duplicated label 'same label may be OK if there is a filter', double check if filters imply disjoint cases"
        in lint_ctx.warn_messages
    )
    assert "Tool output [valid_name] has duplicated name" in lint_ctx.error_messages
    assert len(lint_ctx.error_messages) == 1


def test_outputs_filter_expression(lint_ctx):
    """ """
    tool_source = get_xml_tool_source(OUTPUTS_FILTER_EXPRESSION)
    run_lint_module(lint_ctx, output, tool_source)
    assert "2 outputs found." in lint_ctx.info_messages
    assert len(lint_ctx.info_messages) == 1
    assert not lint_ctx.valid_messages
    assert (
        "Filter 'another invalid condition' is no valid expression: invalid syntax (<unknown>, line 1)"
        in lint_ctx.warn_messages
    )
    assert (
        "Filter 'another invalid condition' is no valid expression: invalid syntax (<unknown>, line 1)"
        in lint_ctx.warn_messages
    )
    assert len(lint_ctx.warn_messages) == 2
    assert not lint_ctx.error_messages


def test_stdio_default_for_default_profile(lint_ctx):
    tool_source = get_xml_tool_source(STDIO_DEFAULT_FOR_DEFAULT_PROFILE)
    run_lint_module(lint_ctx, stdio, tool_source)
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
    run_lint_module(lint_ctx, stdio, tool_source)
    assert (
        "No stdio definition found, tool indicates error conditions with non-zero exit codes." in lint_ctx.info_messages
    )
    assert len(lint_ctx.info_messages) == 1
    assert not lint_ctx.valid_messages
    assert not lint_ctx.warn_messages
    assert not lint_ctx.error_messages


def test_stdio_multiple_stdio(lint_ctx):
    tool_source = get_xml_tool_source(STDIO_MULTIPLE_STDIO)
    run_lint_module(lint_ctx, stdio, tool_source)
    assert "Invalid XML: Element 'stdio': This element is not expected." in lint_ctx.error_messages
    assert not lint_ctx.info_messages
    assert not lint_ctx.valid_messages
    assert not lint_ctx.warn_messages
    assert len(lint_ctx.error_messages) == 1


def test_stdio_invalid_child_or_attrib(lint_ctx):
    """
    note the test name is due to that this was previously covered by linting code in stdio
    """
    tool_source = get_xml_tool_source(STDIO_INVALID_CHILD_OR_ATTRIB)
    run_lint_module(lint_ctx, xsd, tool_source)
    assert not lint_ctx.info_messages
    assert not lint_ctx.valid_messages
    assert not len(lint_ctx.warn_messages) == 3
    assert "Invalid XML: Element 'reqex': This element is not expected." in lint_ctx.error_messages
    assert (
        "Invalid XML: Element 'regex', attribute 'source': [facet 'enumeration'] The value 'stdio' is not an element of the set {'stdout', 'stderr', 'both'}."
        in lint_ctx.error_messages
    )
    assert (
        "Invalid XML: Element 'regex', attribute 'descriptio': The attribute 'descriptio' is not allowed."
        in lint_ctx.error_messages
    )
    assert (
        "Invalid XML: Element 'exit_code', attribute 'descriptio': The attribute 'descriptio' is not allowed."
        in lint_ctx.error_messages
    )
    assert len(lint_ctx.error_messages) == 4


def test_stdio_invalid_match(lint_ctx):
    tool_source = get_xml_tool_source(STDIO_INVALID_MATCH)
    run_lint_module(lint_ctx, stdio, tool_source)
    assert (
        "Match '[' is no valid regular expression: unterminated character set at position 0" in lint_ctx.error_messages
    )
    assert not lint_ctx.info_messages
    assert not lint_ctx.valid_messages
    assert not lint_ctx.warn_messages
    assert len(lint_ctx.error_messages) == 1


def test_tests_absent(lint_ctx):
    for test_contents in [TESTS_ABSENT, TESTS_ABSENT_YAML]:
        tool_source = get_tool_source(test_contents)
        run_lint_module(lint_ctx, tests, tool_source)
        assert "No tests found, most tools should define test cases." in lint_ctx.warn_messages
        assert not lint_ctx.info_messages
        assert not lint_ctx.valid_messages
        assert len(lint_ctx.warn_messages) == 1
        assert not lint_ctx.error_messages


def test_tests_data_source(lint_ctx):
    tool_source = get_xml_tool_source(TESTS_ABSENT_DATA_SOURCE)
    run_lint_module(lint_ctx, tests, tool_source)
    assert "No tests found, that should be OK for data_sources." in lint_ctx.info_messages
    assert len(lint_ctx.info_messages) == 1
    assert not lint_ctx.valid_messages
    assert not lint_ctx.warn_messages
    assert not lint_ctx.error_messages


def test_tests_param_output_names(lint_ctx):
    tool_source = get_xml_tool_source(TESTS_PARAM_OUTPUT_NAMES)
    run_lint_module(lint_ctx, tests, tool_source)
    assert "1 test(s) found." in lint_ctx.valid_messages
    assert "Invalid XML: Element 'param': The attribute 'name' is required but missing." in lint_ctx.error_messages
    assert "Test 1: Test param non_existent_test_name not found in the inputs" in lint_ctx.error_messages
    assert "Test 1: Found output tag without a name defined." in lint_ctx.error_messages
    assert (
        "Test 1: Found output tag with unknown name [nonexistent_output], valid names ['existent_output', 'existent_collection']"
        in lint_ctx.error_messages
    )
    assert (
        "Invalid XML: Element 'output_collection': The attribute 'name' is required but missing."
        in lint_ctx.error_messages
    )
    assert (
        "Test 1: Found output_collection tag with unknown name [nonexistent_collection], valid names ['existent_output', 'existent_collection']"
        in lint_ctx.error_messages
    )
    assert not lint_ctx.info_messages
    assert len(lint_ctx.valid_messages) == 1
    assert len(lint_ctx.error_messages) == 6


def test_tests_expect_failure_output(lint_ctx):
    tool_source = get_xml_tool_source(TESTS_EXPECT_FAILURE_OUTPUT)
    run_lint_module(lint_ctx, tests, tool_source)
    assert "No valid test(s) found." in lint_ctx.warn_messages
    assert "Test 1: Cannot specify outputs in a test expecting failure." in lint_ctx.error_messages
    assert (
        "Test 2: Cannot make assumptions on the number of outputs in a test expecting failure."
        in lint_ctx.error_messages
    )
    assert not lint_ctx.info_messages
    assert not lint_ctx.valid_messages
    assert len(lint_ctx.warn_messages) == 3
    assert len(lint_ctx.error_messages) == 2


def test_tests_without_expectations(lint_ctx):
    tool_source = get_xml_tool_source(TESTS_WO_EXPECTATIONS)
    run_lint_module(lint_ctx, tests, tool_source)
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
    run_lint_module(lint_ctx, tests, tool_source)
    assert "1 test(s) found." in lint_ctx.valid_messages
    assert not lint_ctx.info_messages
    assert len(lint_ctx.valid_messages) == 1
    assert not lint_ctx.warn_messages
    assert not lint_ctx.error_messages


def test_tests_asserts(lint_ctx):
    tool_source = get_xml_tool_source(ASSERTS)
    run_lint_module(lint_ctx, tests, tool_source)
    assert "Invalid XML: Element 'invalid': This element is not expected." in lint_ctx.error_messages
    assert (
        "Invalid XML: Element 'has_text', attribute 'invalid_attrib': The attribute 'invalid_attrib' is not allowed."
        in lint_ctx.error_messages
    )
    assert "Invalid XML: Element 'has_text': The attribute 'text' is required but missing." in lint_ctx.error_messages
    assert (
        "Invalid XML: Element 'has_size', attribute 'delta': '1X' is not a valid value of the union type 'Bytes'."
        in lint_ctx.error_messages
    )
    assert (
        "Invalid XML: Element 'not_has_text', attribute 'invalid_attrib_also_checked_in_nested_asserts': The attribute 'invalid_attrib_also_checked_in_nested_asserts' is not allowed."
        in lint_ctx.error_messages
    )
    assert "Test 1: 'has_size' needs to specify 'size', 'min', or 'max'" in lint_ctx.error_messages
    assert "Test 1: 'has_size' must not specify 'value' and 'size'" in lint_ctx.error_messages
    assert "Test 1: 'has_n_columns' needs to specify 'n', 'min', or 'max'" in lint_ctx.error_messages
    assert "Test 1: 'has_n_lines' needs to specify 'n', 'min', or 'max'" in lint_ctx.error_messages
    assert len(lint_ctx.error_messages) == 9


def test_tests_assertion_models_valid(lint_ctx):
    tool_source = get_xml_tool_source(VALID_CENTER_OF_MASS)
    run_lint_module(lint_ctx, tests, tool_source)
    assert len(lint_ctx.error_messages) == 0
    assert len(lint_ctx.warn_messages) == 0


def test_tests_assertion_models_invalid(lint_ctx):
    tool_source = get_xml_tool_source(INVALID_CENTER_OF_MASS)
    run_lint_module(lint_ctx, tests, tool_source)
    assert len(lint_ctx.error_messages) == 0
    assert len(lint_ctx.warn_messages) == 1
    assert "Test 1: failed to validate assertions. Validation errors are " in lint_ctx.warn_messages


def test_tests_output_type_mismatch(lint_ctx):
    tool_source = get_xml_tool_source(TESTS_OUTPUT_TYPE_MISMATCH)
    run_lint_module(lint_ctx, tests, tool_source)
    assert (
        "Test 1: test output collection_name does not correspond to a 'data' output, but a 'collection'"
        in lint_ctx.error_messages
    )
    assert (
        "Test 1: test collection output 'data_name' does not correspond to a 'output_collection' output, but a 'data'"
        in lint_ctx.error_messages
    )
    assert len(lint_ctx.error_messages) == 2


def test_tests_discover_outputs(lint_ctx):
    tool_source = get_xml_tool_source(TESTS_DISCOVER_OUTPUTS)
    run_lint_module(lint_ctx, tests, tool_source)
    assert (
        "Test 3: test output 'data_name' must have a 'count' attribute and/or 'discovered_dataset' children"
        in lint_ctx.error_messages
    )
    assert (
        "Test 3: test collection 'collection_name' must have a 'count' attribute or 'element' children"
        in lint_ctx.error_messages
    )
    assert (
        "Test 3: test collection 'collection_name' must contain nested 'element' tags and/or element children with a 'count' attribute"
        in lint_ctx.error_messages
    )
    assert (
        "Test 5: test collection 'collection_name' must contain nested 'element' tags and/or element children with a 'count' attribute"
        in lint_ctx.error_messages
    )
    assert len(lint_ctx.error_messages) == 4


def test_tests_expect_num_outputs_filter(lint_ctx):
    tool_source = get_xml_tool_source(TESTS_EXPECT_NUM_OUTPUTS_FILTER)
    run_lint_module(lint_ctx, tests, tool_source)
    assert "Test 1: should specify 'expect_num_outputs' if outputs have filters" in lint_ctx.warn_messages
    assert len(lint_ctx.warn_messages) == 1
    assert len(lint_ctx.error_messages) == 0


def test_tests_compare_attrib_incompatibility(lint_ctx):
    tool_source = get_xml_tool_source(TESTS_COMPARE_ATTRIB_INCOMPATIBILITY)
    run_lint_module(lint_ctx, tests, tool_source)
    assert 'Test 1: Attribute decompress is incompatible with compare="re_match".' in lint_ctx.error_messages
    assert 'Test 1: Attribute sort is incompatible with compare="contains".' in lint_ctx.error_messages
    assert not lint_ctx.info_messages
    assert len(lint_ctx.valid_messages) == 1
    assert len(lint_ctx.error_messages) == 2


def test_xml_order(lint_ctx):
    tool_source = get_xml_tool_source(XML_ORDER)
    run_lint_module(lint_ctx, xml_order, tool_source)
    assert not lint_ctx.info_messages
    assert not lint_ctx.valid_messages
    assert lint_ctx.warn_messages == ["Best practice violation [stdio] elements should come before [command]"]
    assert lint_ctx.error_messages == ["Invalid XML: Element 'wrong_tag': This element is not expected."]


DATA_MANAGER = """<tool id="test_dm" name="test dm" version="1" tool_type="manage_data">
    <inputs>
        <param name="select" type="select">
            <option value="a">a</option>
            <option value="a">a</option>
        </param>
    </inputs>
</tool>
"""


def test_data_manager(lint_ctx_xpath, lint_ctx):
    """
    test that all (not really testing 'all', but more than the general linter
    which was the only one applied to data managers until 23.0) linters are applied
    """
    tool_source = get_xml_tool_source(DATA_MANAGER)
    lint_tool_source_with(lint_ctx, tool_source)
    assert "No tests found, most tools should define test cases." in lint_ctx.warn_messages
    assert "Tool contains no outputs section, most tools should produce outputs." in lint_ctx.warn_messages
    assert "No help section found, consider adding a help section to your tool." in lint_ctx.warn_messages
    assert "No citations found, consider adding citations to your tool." in lint_ctx.warn_messages
    assert "Select parameter [select] has multiple options with the same text content" in lint_ctx.error_messages
    assert "Select parameter [select] has multiple options with the same value" in lint_ctx.error_messages
    assert "No command tag found, must specify a command template to execute." in lint_ctx.error_messages
    assert lint_ctx.valid_messages
    assert len(lint_ctx.warn_messages) == 4
    assert len(lint_ctx.error_messages) == 3


COMPLETE = """<tool id="id" name="name">
    <macros>
        <import>macros.xml</import>
        <xml name="test_macro">
            <param name="select" type="select">
                <option value="a">a</option>
                <option value="a">a</option>
            </param>
        </xml>
        <template name="a_template">blah fasel</template>
    </macros>
    <inputs>
        <expand macro="test_macro"/>
        <param type="text"/>
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
        (
            "Select parameter [select] has multiple options with the same value",
            5,
            "/tool/inputs/param[1]",
            "InputsSelectOptionDuplicateValue",
        ),
        ("Found param input with no name specified.", 14, "/tool/inputs/param[2]", "InputsName"),
        (
            "Invalid XML: Element 'param': The attribute 'type' is required but missing.",
            3,
            "/tool/inputs/param[3]",
            "XSD",
        ),
    )
    for a in asserts:
        message, line, xpath, linter = a
        # check message + path combinations
        # found = set([(lint_message.message, lint_message.xpath) for lint_message in lint_ctx_xpath.message_list])
        # path_asserts = set([(a[0], a[2]) for a in asserts])
        found = False
        for lint_message in lint_ctx_xpath.message_list:
            if lint_message.message != message:
                continue
            found = True
            assert (
                lint_message.xpath == xpath
            ), f"Assumed xpath {xpath}; found xpath {lint_message.xpath} for: {message}"
            assert lint_message.linter == linter
        assert found, f"Did not find {message}"
        for lint_message in lint_ctx.message_list:
            if lint_message.message != message:
                continue
            found = True
            assert lint_message.line == line, f"Assumed line {line}; found line {lint_message.line} for: {message}"
            assert lint_message.linter == linter
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
    tool_source = get_tool_source(YAML_TOOL)
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
    assert "Tool defines a name [tool.cwl]." in lint_ctx.valid_messages
    assert "Tool defines an id [tool.cwl]." in lint_ctx.valid_messages
    assert "Tool specifies profile version [17.09]." in lint_ctx.valid_messages
    assert "CWL appears to be valid." in lint_ctx.info_messages
    assert "Description of tool is empty or absent." in lint_ctx.warn_messages
    assert "Tool does not specify a DockerPull source." in lint_ctx.warn_messages
    assert "Modern CWL version [v1.0]." in lint_ctx.info_messages
    assert len(lint_ctx.info_messages) == 2
    assert len(lint_ctx.valid_messages) == 4
    assert len(lint_ctx.warn_messages) == 2
    assert not lint_ctx.error_messages


def test_skip_by_name(lint_ctx):
    # add a linter class name to the skip list
    lint_ctx.skip_types = ["CitationsMissing"]

    tool_source = get_xml_tool_source(CITATIONS_ABSENT)
    run_lint_module(lint_ctx, citations, tool_source)
    assert not lint_ctx.warn_messages
    assert not lint_ctx.info_messages
    assert not lint_ctx.valid_messages
    assert not lint_ctx.error_messages


def test_skip_by_module(lint_ctx):
    # add a module name to the skip list -> all linters in this module are skipped
    lint_ctx.skip_types = ["citations"]

    tool_source = get_xml_tool_source(CITATIONS_ABSENT)
    run_lint_module(lint_ctx, citations, tool_source)
    assert not lint_ctx.warn_messages
    assert not lint_ctx.info_messages
    assert not lint_ctx.valid_messages
    assert not lint_ctx.error_messages


def test_list_linters():
    linter_names = Linter.list_listers()
    # make sure to add/remove a test for new/removed linters if this number changes
    assert len(linter_names) == 135
    assert "Linter" not in linter_names
    # make sure that linters from all modules are available
    for prefix in [
        "Citations",
        "Command",
        "CWL",
        "ToolProfile",
        "Help",
        "Inputs",
        "Outputs",
        "StdIO",
        "Tests",
        "XMLOrder",
        "XSD",
    ]:
        assert len([x for x in linter_names if x.startswith(prefix)])


def test_linting_functional_tool_multi_select(lint_ctx):
    tool_source = functional_test_tool_source("multi_select.xml")
    run_lint_module(lint_ctx, tests, tool_source)
    warn_message = lint_ctx.warn_messages[0]
    assert (
        "Test 2: failed to validate test parameters against inputs - tests won't run on a modern Galaxy tool profile version. Validation errors are [5 validation errors for"
        in str(warn_message)
    )


def functional_test_tool_source(name: str) -> ToolSource:
    tool_sources = load_tool_sources_from_path(functional_test_tool_path(name))
    assert len(tool_sources) == 1, "Expected 1 tool source"
    tool_source = tool_sources[0][1]
    return tool_source


def test_linter_module_list():
    linter_modules = submodules.import_submodules(galaxy.tool_util.linters)
    linter_module_names = [m.__name__.split(".")[-1] for m in linter_modules]
    linter_module_names = [n for n in linter_module_names if not n.startswith("_")]
    assert len(linter_module_names) >= 11

    # until 23.2 the linters were implemented as functions lint_xyz contained in a module named xyz
    # with 24.0 the functions were split in multiple classes (1 per linter message)
    # in order to keep the skip functionality of lint contexts working (which is used eg in planemo)
    # with the old names, we now also check for module name if a linter should be skipped
    # therefore we test here that the module names are not changed
    # the keys of the following dict represent the linter names before the switch and the values give
    # the number of linter classes when we switched
    # so adding new functionality to a linter module is fine. But splitting one or removing functionality
    # should raise an error here to point to the possible consequences of renaming
    old_linters = {
        "citations": 4,
        "command": 5,
        "cwl": 9,
        "general": 17,
        "help": 6,
        "inputs": 52,
        "output": 11,
        "stdio": 3,
        "tests": 21,
        "xml_order": 1,
    }
    assert len(set(linter_module_names).intersection(set(old_linters.keys()))) == len(old_linters.keys())

    for module in linter_modules:
        module_name = module.__name__.split(".")[-1]
        if module_name not in old_linters:
            continue
        linter_cnt = 0
        for name, value in inspect.getmembers(module):
            if callable(value) and name.startswith("lint_"):
                continue
            elif inspect.isclass(value) and issubclass(value, Linter) and not inspect.isabstract(value):
                linter_cnt += 1
        assert linter_cnt >= old_linters[module_name]
