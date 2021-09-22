from galaxy.tool_util.linters import general

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

TESTS = [
    (
        WHITESPACE_IN_VERSIONS_AND_NAMES, general.lint_general,
        lambda x:
            "Tool version contains whitespace, this may cause errors: [ 1.0.1 ]." in x.warn_messages
            and "Tool name contains whitespace, this may cause errors: [ BWA Mapper ]." in x.warn_messages
            and "Requirement version contains whitespace, this may cause errors: [ 1.2.5 ]." in x.warn_messages
            and "Tool ID contains whitespace - this is discouraged: [bwa tool]."
            and len(x.warn_messages) == 4 and len(x.error_messages) == 0
    ),
    (
        REQUIREMENT_WO_VERSION, general.lint_general,
        lambda x:
            "Requirement bwa defines no version" in x.warn_messages
            and "Requirement without name found" in x.error_messages
            and len(x.warn_messages) == 1 and len(x.error_messages) == 1
    ),
]

TEST_IDS = [
    'hazardous whitespace',
    'requirement without version',
]
