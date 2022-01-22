from inspect import getfullargspec

import pytest

from galaxy.tool_util.lint import LintContext
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
from galaxy.tool_util.parser.xml import XmlToolSource
from galaxy.util import etree

# tests tool xml for citations linter
# tests tool xml for general linter
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
            <validator type="metadata" check="md1,md2" skip="md3,md4" message="cutom validation message" negate="true"/>
            <validator type="unspecified_build" message="cutom validation message" negate="true"/>
            <validator type="dataset_ok_validator" message="cutom validation message" negate="true"/>
            <validator type="dataset_metadata_in_range" min="0" max="100" exclude_min="true" exclude_max="true" message="cutom validation message" negate="true"/>
            <validator type="dataset_metadata_in_file" filename="file.tsv" metadata_column="3" split=","  message="cutom validation message" negate="true"/>
            <validator type="dataset_metadata_in_data_table" table_name="datatable_name" metadata_column="3" message="cutom validation message" negate="true"/>
        </param>
        <param name="collection_param" type="collection">
            <validator type="metadata" check="md1,md2" skip="md3,md4" message="cutom validation message"/>
            <validator type="unspecified_build" message="cutom validation message"/>
            <validator type="dataset_ok_validator" message="cutom validation message"/>
            <validator type="dataset_metadata_in_range" min="0" max="100" exclude_min="true" exclude_max="true" message="cutom validation message"/>
            <validator type="dataset_metadata_in_file" filename="file.tsv" metadata_column="3" split=","  message="cutom validation message"/>
            <validator type="dataset_metadata_in_data_table" table_name="datatable_name" metadata_column="3" message="cutom validation message"/>
        </param>
        <param name="text_param" type="text">
            <validator type="regex">reg.xp</validator>
            <validator type="length" min="0" max="100" message="cutom validation message"/>
            <validator type="empty_field" message="cutom validation message"/>
            <validator type="value_in_data_table" table_name="datatable_name" metadata_column="3" message="cutom validation message"/>
            <validator type="expression" message="cutom validation message">somepythonexpression</validator>
        </param>
        <param name="select_param" type="select">
            <options from_data_table="bowtie2_indexes"/>
            <validator type="no_options" negate="true"/>
            <validator type="regex" negate="true">reg.xp</validator>
            <validator type="length" min="0" max="100" message="cutom validation message" negate="true"/>
            <validator type="empty_field" message="cutom validation message" negate="true"/>
            <validator type="value_in_data_table" table_name="datatable_name" metadata_column="3" message="cutom validation message" negate="true"/>
            <validator type="expression" message="cutom validation message" negate="true">somepythonexpression</validator>
        </param>
        <param name="int_param" type="integer">
            <validator type="in_range" min="0" max="100" exclude_min="true" exclude_max="true" negate="true"/>
            <validator type="expression" message="cutom validation message">somepythonexpression</validator>
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
        <data/>
        <collection name="2output"/>
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
<tool profile="21.09">
    <stdio/>
    <stdio/>
</tool>
"""

STDIO_INVALID_CHILD_OR_ATTRIB = """
<tool profile="21.09">
    <stdio>
        <reqex/>
        <regex descriptio="blah" level="fatal" match="error" source="stdio"/>
        <exit_code descriptio="blah" level="fatal" range="1:"/>
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

# tool xml for xml_order linter
XML_ORDER = """
<tool>
    <wrong_tag/>
    <command/>
    <stdio/>
</tool>
"""

TESTS = [
    (
        CITATIONS_MULTIPLE, citations.lint_citations,
        lambda x:
            "More than one citation section found, behavior undefined." in x.error_messages
            and len(x.info_messages) == 0 and len(x.valid_messages) == 0 and len(x.warn_messages) == 0 and len(x.error_messages) == 1
    ),
    (
        CITATIONS_ABSENT, citations.lint_citations,
        lambda x:
            "No citations found, consider adding citations to your tool." in x.warn_messages
            and len(x.info_messages) == 0 and len(x.valid_messages) == 0 and len(x.warn_messages) == 1 and len(x.error_messages) == 0
    ),
    (
        CITATIONS_ERRORS, citations.lint_citations,
        lambda x:
            "Unknown tag discovered in citations block [nonsense], will be ignored." in x.warn_messages
            and "Unknown citation type discovered [hoerensagen], will be ignored." in x.warn_messages
            and 'Empty doi citation.' in x.error_messages
            and 'Found no valid citations.' in x.warn_messages
            and len(x.info_messages) == 0 and len(x.valid_messages) == 0 and len(x.warn_messages) == 3 and len(x.error_messages) == 1
    ),
    (
        CITATIONS_VALID, citations.lint_citations,
        lambda x:
            'Found 1 likely valid citations.' in x.valid_messages
            and len(x.info_messages) == 0 and len(x.valid_messages) == 1 and len(x.warn_messages) == 0 and len(x.error_messages) == 0
    ),
    (
        COMMAND_MULTIPLE, command.lint_command,
        lambda x:
            'More than one command tag found, behavior undefined.' in x.error_messages
            and len(x.info_messages) == 0 and len(x.valid_messages) == 0 and len(x.warn_messages) == 0 and len(x.error_messages) == 1
    ),
    (
        COMMAND_MISSING, command.lint_command,
        lambda x:
            'No command tag found, must specify a command template to execute.' in x.error_messages
            and len(x.info_messages) == 0 and len(x.valid_messages) == 0 and len(x.warn_messages) == 0 and len(x.error_messages) == 1
    ),
    (
        COMMAND_TODO, command.lint_command,
        lambda x:
            'Tool contains a command.' in x.info_messages
            and 'Command template contains TODO text.' in x.warn_messages
            and len(x.info_messages) == 1 and len(x.valid_messages) == 0 and len(x.warn_messages) == 1 and len(x.error_messages) == 0
    ),
    (
        COMMAND_DETECT_ERRORS_INTERPRETER, command.lint_command,
        lambda x:
            "Command uses deprecated 'interpreter' attribute." in x.warn_messages
            and 'Tool contains a command with interpreter of type [python].' in x.info_messages
            and 'Unknown detect_errors attribute [nonsense]' in x.warn_messages
            and 'Command is empty.' in x.error_messages
            and len(x.info_messages) == 1 and len(x.valid_messages) == 0 and len(x.warn_messages) == 2 and len(x.error_messages) == 1
    ),
    (
        GENERAL_MISSING_TOOL_ID_NAME_VERSION, general.lint_general,
        lambda x:
            'Tool version is missing or empty.' in x.error_messages
            and 'Tool name is missing or empty.' in x.error_messages
            and 'Tool does not define an id attribute.' in x.error_messages
            and 'Tool specifies an invalid profile version [2109].' in x.error_messages
            and len(x.info_messages) == 0 and len(x.valid_messages) == 0 and len(x.warn_messages) == 0 and len(x.error_messages) == 4
    ),
    (
        GENERAL_WHITESPACE_IN_VERSIONS_AND_NAMES, general.lint_general,
        lambda x:
            "Tool version is pre/suffixed by whitespace, this may cause errors: [ 1.0.1 ]." in x.warn_messages
            and "Tool name is pre/suffixed by whitespace, this may cause errors: [ BWA Mapper ]." in x.warn_messages
            and "Requirement version contains whitespace, this may cause errors: [ 1.2.5 ]." in x.warn_messages
            and "Tool ID contains whitespace - this is discouraged: [bwa tool]." in x.warn_messages
            and "Tool targets 16.01 Galaxy profile." in x.valid_messages
            and len(x.info_messages) == 0 and len(x.valid_messages) == 1 and len(x.warn_messages) == 4 and len(x.error_messages) == 0
    ),
    (
        GENERAL_REQUIREMENT_WO_VERSION, general.lint_general,
        lambda x:
            'Tool version [1.0.1blah] is not compliant with PEP 440.' in x.warn_messages
            and "Requirement bwa defines no version" in x.warn_messages
            and "Requirement without name found" in x.error_messages
            and "Tool specifies profile version [20.09]." in x.valid_messages
            and "Tool defines an id [bwa_tool]." in x.valid_messages
            and "Tool defines a name [BWA Mapper]." in x.valid_messages
            and len(x.info_messages) == 0 and len(x.valid_messages) == 3 and len(x.warn_messages) == 2 and len(x.error_messages) == 1
    ),
    (
        GENERAL_VALID, general.lint_general,
        lambda x:
            'Tool defines a version [1.0+galaxy1].' in x.valid_messages
            and "Tool specifies profile version [21.09]." in x.valid_messages
            and "Tool defines an id [valid_id]." in x.valid_messages
            and "Tool defines a name [valid name]." in x.valid_messages
            and len(x.info_messages) == 0 and len(x.valid_messages) == 4 and len(x.warn_messages) == 0 and len(x.error_messages) == 0
    ),
    (
        HELP_MULTIPLE, help.lint_help,
        lambda x:
            'More than one help section found, behavior undefined.' in x.error_messages
            and len(x.info_messages) == 0 and len(x.valid_messages) == 0 and len(x.warn_messages) == 0 and len(x.error_messages) == 1
    ),
    (
        HELP_ABSENT, help.lint_help,
        lambda x:
            'No help section found, consider adding a help section to your tool.' in x.warn_messages
            and len(x.info_messages) == 0 and len(x.valid_messages) == 0 and len(x.warn_messages) == 1 and len(x.error_messages) == 0
    ),
    (
        HELP_EMPTY, help.lint_help,
        lambda x:
            'Help section appears to be empty.' in x.warn_messages
            and len(x.info_messages) == 0 and len(x.valid_messages) == 0 and len(x.warn_messages) == 1 and len(x.error_messages) == 0
    ),
    (
        HELP_TODO, help.lint_help,
        lambda x:
            'Tool contains help section.' in x.valid_messages
            and 'Help contains valid reStructuredText.' in x.valid_messages
            and "Help contains TODO text." in x.warn_messages
            and len(x.info_messages) == 0 and len(x.valid_messages) == 2 and len(x.warn_messages) == 1 and len(x.error_messages) == 0
    ),
    (
        HELP_INVALID_RST, help.lint_help,
        lambda x:
            'Tool contains help section.' in x.valid_messages
            and "Invalid reStructuredText found in help - [<string>:2: (WARNING/2) Inline strong start-string without end-string.\n]." in x.warn_messages
            and len(x.info_messages) == 0 and len(x.valid_messages) == 1 and len(x.warn_messages) == 1 and len(x.error_messages) == 0
    ),
    (
        INPUTS_NO_INPUTS, inputs.lint_inputs,
        lambda x:
            'Found no input parameters.' in x.warn_messages
            and len(x.info_messages) == 0 and len(x.valid_messages) == 0 and len(x.warn_messages) == 1 and len(x.error_messages) == 0
    ),
    (
        INPUTS_NO_INPUTS_DATASOURCE, inputs.lint_inputs,
        lambda x:
            'No input parameters, OK for data sources' in x.info_messages
            and 'display tag usually present in data sources' in x.info_messages
            and 'uihints tag usually present in data sources' in x.info_messages
            and len(x.info_messages) == 3 and len(x.valid_messages) == 0 and len(x.warn_messages) == 0 and len(x.error_messages) == 0
    ),
    (
        INPUTS_VALID, inputs.lint_inputs,
        lambda x:
            "Found 2 input parameters." in x.info_messages
            and len(x.info_messages) == 1 and len(x.valid_messages) == 0 and len(x.warn_messages) == 0 and len(x.error_messages) == 0
    ),
    (
        INPUTS_PARAM_NAME, inputs.lint_inputs,
        lambda x:
            "Found 5 input parameters." in x.info_messages
            and 'Param input [2] is not a valid Cheetah placeholder.' in x.warn_messages
            and 'Found param input with no name specified.' in x.error_messages
            and 'Param input with empty name.' in x.error_messages
            and "Param input [param_name] 'name' attribute is redundant if argument implies the same name." in x.warn_messages
            and len(x.info_messages) == 1 and len(x.valid_messages) == 0 and len(x.warn_messages) == 2 and len(x.error_messages) == 2
    ),
    (
        INPUTS_PARAM_TYPE, inputs.lint_inputs,
        lambda x:
            "Found 2 input parameters." in x.info_messages
            and 'Param input [valid_name] input with no type specified.' in x.error_messages
            and 'Param input [another_valid_name] with empty type specified.' in x.error_messages
            and len(x.info_messages) == 1 and len(x.valid_messages) == 0 and len(x.warn_messages) == 0 and len(x.error_messages) == 2
    ),
    (
        INPUTS_DATA_PARAM, inputs.lint_inputs,
        lambda x:
            "Found 1 input parameters." in x.info_messages
            and "Param input [valid_name] with no format specified - 'data' format will be assumed." in x.warn_messages
            and len(x.info_messages) == 1 and len(x.valid_messages) == 0 and len(x.warn_messages) == 1 and len(x.error_messages) == 0
    ),
    (
        INPUTS_CONDITIONAL, inputs.lint_inputs,
        lambda x:
            'Found 10 input parameters.' in x.info_messages
            and "Conditional without a name" in x.error_messages
            and "Select parameter of a conditional [select] options have to be defined by 'option' children elements." in x.error_messages
            and 'Conditional [cond_wo_param] needs exactly one child <param> found 0' in x.error_messages
            and 'Conditional [cond_w_mult_param] needs exactly one child <param> found 2' in x.error_messages
            and 'Conditional [cond_text] first param should have type="select" (or type="boolean" which is discouraged)' in x.error_messages
            and 'Conditional [cond_boolean] first param of type="boolean" is discouraged, use a select' in x.warn_messages
            and "Conditional [cond_boolean] no truevalue/falsevalue found for when block 'False'" in x.warn_messages
            and 'Conditional [cond_w_optional_select] test parameter cannot be optional="true"' in x.warn_messages
            and 'Conditional [cond_w_multiple_select] test parameter cannot be multiple="true"' in x.warn_messages
            and "Conditional [when_wo_value] when without value" in x.error_messages
            and "Conditional [missing_when] no <when /> block found for select option 'none'" in x.warn_messages
            and len(x.info_messages) == 1 and len(x.valid_messages) == 0 and len(x.warn_messages) == 6 and len(x.error_messages) == 6
    ),
    (
        INPUTS_SELECT_INCOMPATIBLE_DISPLAY, inputs.lint_inputs,
        lambda x:
            'Found 3 input parameters.' in x.info_messages
            and 'Select [radio_select] display="radio" is incompatible with optional="true"' in x.error_messages
            and 'Select [radio_select] display="radio" is incompatible with multiple="true"' in x.error_messages
            and 'Select [checkboxes_select] `display="checkboxes"` is incompatible with `optional="false"`, remove the `display` attribute' in x.error_messages
            and 'Select [checkboxes_select] `display="checkboxes"` is incompatible with `multiple="false"`, remove the `display` attribute' in x.error_messages
            and len(x.info_messages) == 1 and len(x.valid_messages) == 0 and len(x.warn_messages) == 0 and len(x.error_messages) == 4
    ),
    (
        INPUTS_SELECT_DUPLICATED_OPTIONS, inputs.lint_inputs,
        lambda x:
            'Found 1 input parameters.' in x.info_messages
            and 'Select parameter [select] has multiple options with the same text content' in x.error_messages
            and 'Select parameter [select] has multiple options with the same value' in x.error_messages
            and len(x.info_messages) == 1 and len(x.valid_messages) == 0 and len(x.warn_messages) == 0 and len(x.error_messages) == 2
    ),
    (
        SELECT_DUPLICATED_OPTIONS_WITH_DIFF_SELECTED, inputs.lint_inputs,
        lambda x:
            len(x.warn_messages) == 0 and len(x.error_messages) == 0
    ),
    (
        INPUTS_SELECT_DEPRECATIONS, inputs.lint_inputs,
        lambda x:
            'Found 3 input parameters.' in x.info_messages
            and "Select parameter [select_do] uses deprecated 'dynamic_options' attribute." in x.warn_messages
            and "Select parameter [select_ff] options uses deprecated 'from_file' attribute." in x.warn_messages
            and "Select parameter [select_fp] options uses deprecated 'from_parameter' attribute." in x.warn_messages
            and "Select parameter [select_ff] options uses deprecated 'transform_lines' attribute." in x.warn_messages
            and "Select parameter [select_fp] options uses deprecated 'options_filter_attribute' attribute." in x.warn_messages
            and len(x.info_messages) == 1 and len(x.valid_messages) == 0 and len(x.warn_messages) == 5 and len(x.error_messages) == 0
    ),
    (
        INPUTS_SELECT_OPTION_DEFINITIONS, inputs.lint_inputs,
        lambda x:
            'Found 6 input parameters.' in x.info_messages
            and "Select parameter [select_noopt] options have to be defined by either 'option' children elements, a 'options' element or the 'dynamic_options' attribute." in x.error_messages
            and "Select parameter [select_noopts] options tag defines no options. Use 'from_dataset', 'from_data_table', or a filter that adds values." in x.error_messages
            and "Select parameter [select_fd_op] options have to be defined by either 'option' children elements, a 'options' element or the 'dynamic_options' attribute." in x.error_messages
            and "Select parameter [select_fd_op] contains multiple options elements." in x.error_messages
            and "Select parameter [select_fd_fdt] options uses 'from_dataset' and 'from_data_table' attribute." in x.error_messages
            and "Select parameter [select_noval_notext] has option without value" in x.error_messages
            and "Select parameter [select_noval_notext] has option without text" in x.warn_messages
            and "Select parameter [select_meta_file_key_incomp] 'meta_file_key' is only compatible with 'from_dataset'." in x.error_messages
            and len(x.info_messages) == 1 and len(x.valid_messages) == 0 and len(x.warn_messages) == 1 and len(x.error_messages) == 7
    ),
    (
        INPUTS_SELECT_FILTER, inputs.lint_inputs,
        lambda x:
            'Found 1 input parameters.' in x.info_messages
            and "Select parameter [select_filter_types] contains filter without type." in x.error_messages
            and "Select parameter [select_filter_types] contains filter with unknown type 'unknown_filter_type'." in x.error_messages
            and len(x.info_messages) == 1 and len(x.valid_messages) == 0 and len(x.warn_messages) == 0 and len(x.error_messages) == 2
    ),
    (
        INPUTS_VALIDATOR_INCOMPATIBILITIES, inputs.lint_inputs,
        lambda x:
            'Found 2 input parameters.' in x.info_messages
            and "Parameter [param_name]: 'in_range' validators are not expected to contain text (found 'TEXT')" in x.warn_messages
            and "Parameter [param_name]: validator with an incompatible type 'in_range'" in x.error_messages
            and "Parameter [param_name]: 'in_range' validators need to define the 'min' or 'max' attribute(s)" in x.error_messages
            and "Parameter [param_name]: attribute 'filename' is incompatible with validator of type 'regex'" in x.error_messages
            and "Parameter [param_name]: expression validator without content" in x.error_messages
            and "Parameter [another_param_name]: 'metadata' validators need to define the 'check' or 'skip' attribute(s)" in x.error_messages
            and "Parameter [param_name]: 'value_in_data_table' validators need to define the 'table_name' attribute" in x.error_messages
            and len(x.info_messages) == 1 and len(x.valid_messages) == 0 and len(x.warn_messages) == 1 and len(x.error_messages) == 6
    ),
    (
        INPUTS_VALIDATOR_CORRECT, inputs.lint_inputs,
        lambda x:
            'Found 5 input parameters.' in x.info_messages
            and len(x.info_messages) == 1 and len(x.valid_messages) == 0 and len(x.warn_messages) == 0 and len(x.error_messages) == 0
    ),
    (
        OUTPUTS_MISSING, outputs.lint_output,
        lambda x:
            'Tool contains no outputs section, most tools should produce outputs.' in x.warn_messages
            and len(x.info_messages) == 0 and len(x.valid_messages) == 0 and len(x.warn_messages) == 1 and len(x.error_messages) == 0
    ),
    (
        OUTPUTS_MULTIPLE, outputs.lint_output,
        lambda x:
            '0 outputs found.' in x.info_messages
            and 'Tool contains multiple output sections, behavior undefined.' in x.warn_messages
            and len(x.info_messages) == 1 and len(x.valid_messages) == 0 and len(x.warn_messages) == 1 and len(x.error_messages) == 0
    ),
    (
        OUTPUTS_UNKNOWN_TAG, outputs.lint_output,
        lambda x:
            '0 outputs found.' in x.info_messages
            and 'Unknown element found in outputs [output]' in x.warn_messages
            and len(x.info_messages) == 1 and len(x.valid_messages) == 0 and len(x.warn_messages) == 1 and len(x.error_messages) == 0
    ),
    (
        OUTPUTS_UNNAMED_INVALID_NAME, outputs.lint_output,
        lambda x:
            '2 outputs found.' in x.info_messages
            and "Tool output doesn't define a name - this is likely a problem." in x.warn_messages
            and "Tool data output with missing name doesn't define an output format." in x.warn_messages
            and 'Tool output name [2output] is not a valid Cheetah placeholder.' in x.warn_messages
            and "Collection output with undefined 'type' found." in x.warn_messages
            and "Tool collection output 2output doesn't define an output format." in x.warn_messages
            and len(x.info_messages) == 1 and len(x.valid_messages) == 0 and len(x.warn_messages) == 5 and len(x.error_messages) == 0
    ),
    (
        OUTPUTS_FORMAT_INPUT, outputs.lint_output,
        lambda x:
            '1 outputs found.' in x.info_messages
            and "Using format='input' on data, format_source attribute is less ambiguous and should be used instead." in x.warn_messages
            and len(x.info_messages) == 1 and len(x.valid_messages) == 0 and len(x.warn_messages) == 1 and len(x.error_messages) == 0
    ),
    (
        OUTPUTS_COLLECTION_FORMAT_SOURCE, outputs.lint_output,
        lambda x:
            "Tool data output 'reverse' should use either format_source or format/ext" in x.warn_messages
            and len(x.info_messages) == 1 and len(x.valid_messages) == 0 and len(x.warn_messages) == 1 and len(x.error_messages) == 0
    ),
    (
        OUTPUTS_DISCOVER_TOOL_PROVIDED_METADATA, outputs.lint_output,
        lambda x:
            '1 outputs found.' in x.info_messages
            and len(x.info_messages) == 1 and len(x.valid_messages) == 0 and len(x.warn_messages) == 0 and len(x.error_messages) == 0
    ),
    (
        REPEATS, inputs.lint_repeats,
        lambda x:
            "Repeat does not specify name attribute." in x.error_messages
            and "Repeat does not specify title attribute." in x.error_messages
            and len(x.info_messages) == 0 and len(x.valid_messages) == 0 and len(x.warn_messages) == 0 and len(x.error_messages) == 2
    ),
    (
        STDIO_DEFAULT_FOR_DEFAULT_PROFILE, stdio.lint_stdio,
        lambda x:
            "No stdio definition found, tool indicates error conditions with output written to stderr." in x.info_messages
            and len(x.info_messages) == 1 and len(x.valid_messages) == 0 and len(x.warn_messages) == 0 and len(x.error_messages) == 0

    ),
    (
        STDIO_DEFAULT_FOR_NONLEGACY_PROFILE, stdio.lint_stdio,
        lambda x:
            "No stdio definition found, tool indicates error conditions with non-zero exit codes." in x.info_messages
            and len(x.info_messages) == 1 and len(x.valid_messages) == 0 and len(x.warn_messages) == 0 and len(x.error_messages) == 0

    ),
    (
        STDIO_MULTIPLE_STDIO, stdio.lint_stdio,
        lambda x:
            "More than one stdio tag found, behavior undefined." in x.error_messages
            and len(x.info_messages) == 0 and len(x.valid_messages) == 0 and len(x.warn_messages) == 0 and len(x.error_messages) == 1

    ),
    (
        STDIO_INVALID_CHILD_OR_ATTRIB, stdio.lint_stdio,
        lambda x:
            "Unknown stdio child tag discovered [reqex]. Valid options are exit_code and regex." in x.warn_messages
            and "Unknown attribute [descriptio] encountered on exit_code tag." in x.warn_messages
            and "Unknown attribute [descriptio] encountered on regex tag." in x.warn_messages
            and len(x.info_messages) == 0 and len(x.valid_messages) == 0 and len(x.warn_messages) == 3 and len(x.error_messages) == 0

    ),
    (
        TESTS_ABSENT, tests.lint_tsts,
        lambda x:
            'No tests found, most tools should define test cases.' in x.warn_messages
            and len(x.info_messages) == 0 and len(x.valid_messages) == 0 and len(x.warn_messages) == 1 and len(x.error_messages) == 0
    ),
    (
        TESTS_ABSENT_DATA_SOURCE, tests.lint_tsts,
        lambda x:
            'No tests found, that should be OK for data_sources.' in x.info_messages
            and len(x.info_messages) == 1 and len(x.valid_messages) == 0 and len(x.warn_messages) == 0 and len(x.error_messages) == 0
    ),
    (
        TESTS_WO_EXPECTATIONS, tests.lint_tsts,
        lambda x:
            'Test 1: No outputs or expectations defined for tests, this test is likely invalid.' in x.warn_messages
            and 'No valid test(s) found.' in x.warn_messages
            and len(x.info_messages) == 0 and len(x.valid_messages) == 0 and len(x.warn_messages) == 2 and len(x.error_messages) == 0
    ),
    (
        TESTS_PARAM_OUTPUT_NAMES, tests.lint_tsts,
        lambda x:
            '1 test(s) found.' in x.valid_messages
            and "Test 1: Found test param tag without a name defined." in x.error_messages
            and "Test 1: Test param non_existent_test_name not found in the inputs" in x.error_messages
            and "Test 1: Found output tag without a name defined." in x.error_messages
            and "Test 1: Found output tag with unknown name [nonexistent_output], valid names [['existent_output']]" in x.error_messages
            and "Test 1: Found output_collection tag without a name defined." in x.error_messages
            and "Test 1: Found output_collection tag with unknown name [nonexistent_collection], valid names [['existent_collection']]" in x.error_messages
            and len(x.info_messages) == 0 and len(x.valid_messages) == 1 and len(x.warn_messages) == 0 and len(x.error_messages) == 6
    ),
    (
        TESTS_EXPECT_FAILURE_OUTPUT, tests.lint_tsts,
        lambda x:
            'No valid test(s) found.' in x.warn_messages
            and "Test 1: Cannot specify outputs in a test expecting failure." in x.error_messages
            and len(x.info_messages) == 0 and len(x.valid_messages) == 0 and len(x.warn_messages) == 1 and len(x.error_messages) == 1
    ),
    (
        XML_ORDER, xml_order.lint_xml_order,
        lambda x:
            'Unknown tag [wrong_tag] encountered, this may result in a warning in the future.' in x.info_messages
            and 'Best practice violation [stdio] elements should come before [command]' in x.warn_messages
            and len(x.info_messages) == 1 and len(x.valid_messages) == 0 and len(x.warn_messages) == 1 and len(x.error_messages) == 0
    )
]

TEST_IDS = [
    'citations: multiple',
    'citations: absent',
    'citations: errors',
    'citations: valid',
    'command: multiple',
    'command: missing',
    'command: todo',
    'command: detect_errors and interpreter',
    'general: missing tool id, name, version; invalid profile',
    'general: whitespace in version, id, name',
    'general: requirement without version',
    'general: valid name, id, profile',
    'help: multiple',
    'help: absent',
    'help: empty',
    'help: with todo',
    'help: with invalid restructured text',
    'inputs: no inputs sections',
    'inputs: no inputs sections for datasource',
    'inputs: valid',
    'inputs: param name',
    'inputs: param type',
    'inputs: data param',
    'inputs: conditional',
    'inputs: select with incompatible display',
    'inputs: select duplicated options',
    'inputs: select duplicated options with different selected',
    'inputs: select deprecations',
    'inputs: select option definitions',
    'inputs: select filter',
    'inputs: validator incompatibilities',
    'inputs: validator all correct',
    'outputs: missing outputs tag',
    'outputs: multiple outputs tags',
    'outputs: unknow tag in outputs',
    'outputs: unnamed or invalid output',
    'outputs: format="input"',
    'outputs collection static elements with format_source',
    'outputs discover datatsets with tool provided metadata',
    'repeats',
    'stdio: default for default profile',
    'stdio: default for non-legacy profile',
    'stdio: multiple stdio',
    'stdio: invalid tag or attribute',
    'tests: absent',
    'tests: absent data_source',
    'tests: without expectations',
    'tests: param and output names',
    'tests: expecting failure with outputs',
    'xml_order'
]


@pytest.mark.parametrize('tool_xml,lint_func,assert_func', TESTS, ids=TEST_IDS)
def test_tool_xml(tool_xml, lint_func, assert_func):
    lint_ctx = LintContext('all')
    # the general linter gets XMLToolSource and all others
    # an ElementTree
    first_arg = getfullargspec(lint_func).args[0]
    lint_target = etree.ElementTree(element=etree.fromstring(tool_xml))
    if first_arg != "tool_xml":
        lint_target = XmlToolSource(lint_target)
    lint_ctx.lint(name="test_lint", lint_func=lint_func, lint_target=lint_target)
    assert assert_func(lint_ctx), (
        f"Valid: {lint_ctx.valid_messages}\n"
        f"Info: {lint_ctx.info_messages}\n"
        f"Warnings: {lint_ctx.warn_messages}\n"
        f"Errors: {lint_ctx.error_messages}"
    )
