import pytest

from galaxy.tool_util.lint import LintContext
from galaxy.tool_util.linters import general
from galaxy.tool_util.parser.xml import XmlToolSource
from galaxy.util import etree


def lint_general(xml_tree, lint_ctx):
    """Wrap calling of lint_general to provide XmlToolSource argument.

    This allows general.lint_general to be called with the other linters which
    take an XmlTree as an argument.
    """
    tool_source = XmlToolSource(xml_tree)
    return general.lint_general(tool_source, lint_ctx)


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
        WHITESPACE_IN_VERSIONS_AND_NAMES, lint_general,
        lambda x:
            "Tool version contains whitespace, this may cause errors: [ 1.0.1 ]." in x.warn_messages
            and "Tool name contains whitespace, this may cause errors: [ BWA Mapper ]." in x.warn_messages
            and "Requirement version contains whitespace, this may cause errors: [ 1.2.5 ]." in x.warn_messages
            and "Tool ID contains whitespace - this is discouraged: [bwa tool]."
            and len(x.warn_messages) == 4 and len(x.error_messages) == 0
    ),
    (
        REQUIREMENT_WO_VERSION, lint_general,
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


@pytest.mark.parametrize('tool_xml,lint_func,assert_func', TESTS, ids=TEST_IDS)
def test_tool_xml(tool_xml, lint_func, assert_func):
    lint_ctx = LintContext('all')
    tree = etree.ElementTree(element=etree.fromstring(tool_xml))
    lint_ctx.lint(name="test_lint", lint_func=lint_func, lint_target=tree)
    assert assert_func(lint_ctx), (
        f"Warnings: {lint_ctx.warn_messages}\n"
        f"Errors: {lint_ctx.error_messages}"
    )
