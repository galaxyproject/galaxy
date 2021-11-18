from inspect import getfullargspec

import pytest

from galaxy.tool_util.lint import LintContext
from galaxy.tool_util.linters import (
    general,
    inputs,
    outputs,
    tests,
)
from galaxy.tool_util.parser.xml import XmlToolSource
from galaxy.util import etree

WHITESPACE_IN_VERSIONS_AND_NAMES = """
<tool name=" BWA Mapper " id="bwa tool" version=" 1.0.1 " is_multi_byte="true" display_interface="true" require_login="true" hidden="true">
    <description>The BWA Mapper</description>
    <requirements>
        <requirement type="package" version=" 1.2.5 "> bwa </requirement>
    </requirements>
    <version_command interpreter="python">bwa.py --version</version_command>
    <inputs>
        <param name="select_fd_op" type="select">
            <options from_dataset="xyz"/>
            <options from_data_table="xyz"/>
            <option value="x">x</option>
        </param>
    </inputs>
</tool>
"""

REQUIREMENT_WO_VERSION = """
<tool name="BWA Mapper" id="bwa_tool" version="1.0.1" is_multi_byte="true" display_interface="true" require_login="true" hidden="true">
    <description>The BWA Mapper</description>
    <requirements>
        <requirement type="package">bwa</requirement>
        <requirement type="package" version="1.2.5"></requirement>
    </requirements>
    <version_command interpreter="python">bwa.py --version</version_command>
    <inputs>
        <param name="select_fd_op" type="select">
            <options from_dataset="xyz"/>
            <options from_data_table="xyz"/>
            <option value="x">x</option>
        </param>
    </inputs>
</tool>
"""

NO_SECTIONS_XML = """
<tool name="BWA Mapper" id="bwa" version="1.0.1" is_multi_byte="true" display_interface="true" require_login="true" hidden="true">
    <description>The BWA Mapper</description>
    <version_command interpreter="python">bwa.py --version</version_command>
</tool>
"""

NO_WHEN_IN_CONDITIONAL_XML = """
<tool name="BWA Mapper" id="bwa" version="1.0.1" is_multi_byte="true" display_interface="true" require_login="true" hidden="true">
    <description>The BWA Mapper</description>
    <version_command interpreter="python">bwa.py --version</version_command>
    <inputs>
        <conditional name="labels">
            <param name="label_select" type="select" label="Points to label">
                <option value="none" selected="True">None</option>
            </param>
        </conditional>
    </inputs>
</tool>
"""

RADIO_SELECT_INCOMPATIBILITIES = """
<tool name="BWA Mapper" id="bwa" version="1.0.1" is_multi_byte="true" display_interface="true" require_login="true" hidden="true">
    <description>The BWA Mapper</description>
    <version_command interpreter="python">bwa.py --version</version_command>
    <inputs>
        <param name="radio_select" type="select" display="radio" optional="true" multiple="true">
            <option value="1">1</option>
            <option value="2">2</option>
        </param>
        <param name="radio_checkboxes" type="select" display="checkboxes" optional="false" multiple="false">
            <option value="1">1</option>
            <option value="2">2</option>
        </param>
    </inputs>
</tool>
"""

SELECT_DUPLICATED_OPTIONS = """
<tool>
    <inputs>
        <param name="select" type="select" optional="true" multiple="true">
            <option value="v">x</option>
            <option value="v">x</option>
        </param>
    </inputs>
</tool>
"""

SELECT_DEPRECATIONS = """
<tool name="BWA Mapper" id="bwa" version="1.0.1" is_multi_byte="true" display_interface="true" require_login="true" hidden="true">
    <description>The BWA Mapper</description>
    <version_command interpreter="python">bwa.py --version</version_command>
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

SELECT_OPTION_DEFINITIONS = """
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
    </inputs>
</tool>
"""

VALIDATOR_INCOMPATIBILITIES = """
<tool name="BWA Mapper" id="bwa" version="1.0.1" is_multi_byte="true" display_interface="true" require_login="true" hidden="true">
    <description>The BWA Mapper</description>
    <version_command interpreter="python">bwa.py --version</version_command>
    <inputs>
        <param name="param_name" type="text">
            <validator type="in_range">TEXT</validator>
            <validator type="regex" filename="blah"/>
        </param>
    </inputs>
</tool>
"""

VALIDATOR_CORRECT = """
<tool name="BWA Mapper" id="bwa" version="1.0.1" is_multi_byte="true" display_interface="true" require_login="true" hidden="true">
    <description>The BWA Mapper</description>
    <version_command interpreter="python">bwa.py --version</version_command>
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

# check that linter accepts format source for collection elements as means to specify format
# and that the linter warns if format and format_source are used
OUTPUTS_COLLECTION_FORMAT_SOURCE = """
<tool name="BWA Mapper" id="bwa" version="1.0.1" is_multi_byte="true" display_interface="true" require_login="true" hidden="true">
    <description>The BWA Mapper</description>
    <version_command interpreter="python">bwa.py --version</version_command>
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
<tool name="BWA Mapper" id="bwa" version="1.0.1" is_multi_byte="true" display_interface="true" require_login="true" hidden="true">
    <description>The BWA Mapper</description>
    <version_command interpreter="python">bwa.py --version</version_command>
    <outputs>
        <data name="output">
            <discover_datasets from_tool_provided_metadata="true"/>
        </data>
    </outputs>
</tool>
"""

# check that linter does complain about tests wo assumptions
TESTS_WO_EXPECTATIONS = """
<tool>
    <tests>
        <test>
        </test>
    </tests>
</tool>
"""

TESTS_PARAM = """
<tool>
    <inputs>
        <param argument="--existent-test-name"/>
        <conditional>
            <when>
                <param name="another_existent_test_name"/>
            </when>
        </conditional>
    </inputs>
    <tests>
        <test expect_num_outputs="1">
            <param name="existent_test_name"/>
            <param name="cond_name|another_existent_test_name"/>
            <param name="non_existent_test_name"/>
        </test>
    </tests>
</tool>
"""

TESTS = [
    (
        WHITESPACE_IN_VERSIONS_AND_NAMES, general.lint_general,
        lambda x:
            "Tool version contains whitespace, this may cause errors: [ 1.0.1 ]." in x.warn_messages
            and "Tool name contains whitespace, this may cause errors: [ BWA Mapper ]." in x.warn_messages
            and "Requirement version contains whitespace, this may cause errors: [ 1.2.5 ]." in x.warn_messages
            and "Tool ID contains whitespace - this is discouraged: [bwa tool]." in x.warn_messages
            and len(x.warn_messages) == 4 and len(x.error_messages) == 0
    ),
    (
        REQUIREMENT_WO_VERSION, general.lint_general,
        lambda x:
            "Requirement bwa defines no version" in x.warn_messages
            and "Requirement without name found" in x.error_messages
            and len(x.warn_messages) == 1 and len(x.error_messages) == 1
    ),
    (
        NO_SECTIONS_XML, inputs.lint_inputs,
        lambda x:
            'Found no input parameters.' in x.warn_messages
            and len(x.warn_messages) == 1 and len(x.error_messages) == 0
    ),
    (
        NO_WHEN_IN_CONDITIONAL_XML, inputs.lint_inputs,
        lambda x:
            "Conditional [labels] no <when /> block found for select option 'none'" in x.warn_messages
            and len(x.warn_messages) == 1 and len(x.error_messages) == 0
    ),
    (
        RADIO_SELECT_INCOMPATIBILITIES, inputs.lint_inputs,
        lambda x:
            'Select [radio_select] display="radio" is incompatible with optional="true"' in x.error_messages
            and 'Select [radio_select] display="radio" is incompatible with multiple="true"' in x.error_messages
            and 'Select [radio_checkboxes] `display="checkboxes"` is incompatible with `optional="false"`, remove the `display` attribute' in x.error_messages
            and 'Select [radio_checkboxes] `display="checkboxes"` is incompatible with `multiple="false"`, remove the `display` attribute' in x.error_messages
            and len(x.warn_messages) == 0 and len(x.error_messages) == 4
    ),
    (
        SELECT_DUPLICATED_OPTIONS, inputs.lint_inputs,
        lambda x:
            'Select parameter [select] has multiple options with the same text content' in x.error_messages
            and 'Select parameter [select] has multiple options with the same value' in x.error_messages
            and len(x.warn_messages) == 0 and len(x.error_messages) == 2
    ),
    (
        SELECT_DEPRECATIONS, inputs.lint_inputs,
        lambda x:
            "Select parameter [select_do] uses deprecated 'dynamic_options' attribute." in x.warn_messages
            and "Select parameter [select_ff] options uses deprecated 'from_file' attribute." in x.warn_messages
            and "Select parameter [select_fp] options uses deprecated 'from_parameter' attribute." in x.warn_messages
            and "Select parameter [select_ff] options uses deprecated 'transform_lines' attribute." in x.warn_messages
            and "Select parameter [select_fp] options uses deprecated 'options_filter_attribute' attribute." in x.warn_messages
            and len(x.warn_messages) == 5 and len(x.error_messages) == 0
    ),
    (
        SELECT_OPTION_DEFINITIONS, inputs.lint_inputs,
        lambda x:
            "Select parameter [select_noopt] options have to be defined by either 'option' children elements, a 'options' element or the 'dynamic_options' attribute." in x.error_messages
            and "Select parameter [select_noopts] options tag defines no options. Use 'from_dataset', 'from_data_table', or a filter that adds values." in x.error_messages
            and "Select parameter [select_fd_op] options have to be defined by either 'option' children elements, a 'options' element or the 'dynamic_options' attribute." in x.error_messages
            and "Select parameter [select_fd_op] contains multiple options elements" in x.error_messages
            and "Select parameter [select_fd_fdt] options uses 'from_dataset' and 'from_data_table' attribute." in x.error_messages
            and "Select parameter [select_noval_notext] has option without value" in x.error_messages
            and "Select parameter [select_noval_notext] has option without text" in x.warn_messages
            and len(x.warn_messages) == 1 and len(x.error_messages) == 6
    ),
    (
        VALIDATOR_INCOMPATIBILITIES, inputs.lint_inputs,
        lambda x:
            "Parameter [param_name]: 'in_range' validators are not expected to contain text (found 'TEXT')" in x.warn_messages
            and "Parameter [param_name]: validator with an incompatible type 'in_range'" in x.error_messages
            and "Parameter [param_name]: 'in_range' validators need to define the 'min' or 'max' attribute(s)" in x.error_messages
            and "Parameter [param_name]: attribute 'filename' is incompatible with validator of type 'regex'" in x.error_messages
            and len(x.warn_messages) == 1 and len(x.error_messages) == 3
    ),
    (
        VALIDATOR_CORRECT, inputs.lint_inputs,
        lambda x: len(x.warn_messages) == 0 and len(x.error_messages) == 0
    ),
    (
        OUTPUTS_COLLECTION_FORMAT_SOURCE, outputs.lint_output,
        lambda x:
            "Tool data output reverse should use either format_source or format/ext" in x.warn_messages
            and len(x.warn_messages) == 1 and len(x.error_messages) == 0
    ),
    (
        OUTPUTS_DISCOVER_TOOL_PROVIDED_METADATA, outputs.lint_output,
        lambda x:
            len(x.warn_messages) == 0 and len(x.error_messages) == 0
    ),
    (
        TESTS_WO_EXPECTATIONS, tests.lint_tsts,
        lambda x:
            'No outputs or expectations defined for tests, this test is likely invalid.' in x.warn_messages
            and 'No valid test(s) found.' in x.warn_messages
            and len(x.warn_messages) == 2 and len(x.error_messages) == 0
    ),
    (
        TESTS_PARAM, tests.lint_tsts,
        lambda x:
            "Test param non_existent_test_name not found in the inputs" in x.error_messages
            and len(x.warn_messages) == 0 and len(x.error_messages) == 1
    )
]

TEST_IDS = [
    'hazardous whitespace',
    'requirement without version',
    'lint no sections',
    'lint no when',
    'radio select incompatibilities',
    'select duplicated options',
    'select deprecations',
    'select option definitions',
    'validator imcompatibilities',
    'validator all correct',
    'outputs collection static elements with format_source',
    'outputs discover datatsets with tool provided metadata',
    'test without expectations',
    'test param missing from inputs',
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
        f"Warnings: {lint_ctx.warn_messages}\n"
        f"Errors: {lint_ctx.error_messages}"
    )
