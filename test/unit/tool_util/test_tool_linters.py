import pytest

from galaxy.tool_util.lint import LintContext
from galaxy.tool_util.linters import inputs
from galaxy.util import etree


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

TESTS = [
    (NO_SECTIONS_XML, inputs.lint_inputs, lambda x: 'Found no input parameters.' in x.warn_messages),
    (NO_WHEN_IN_CONDITIONAL_XML, inputs.lint_inputs, lambda x: 'No <when /> block found for select option \'none\' inside conditional \'labels\'' in x.warn_messages),
]


@pytest.mark.parametrize('tool_xml,lint_func,assert_func', TESTS, ids=['Lint no sections', 'lint no when'])
def test_tool_xml(tool_xml, lint_func, assert_func):
    lint_ctx = LintContext('all')
    tree = etree.ElementTree(element=etree.fromstring(tool_xml))
    lint_ctx.lint(name="test_lint", lint_func=lint_func, lint_target=tree)
    assert assert_func(lint_ctx)
