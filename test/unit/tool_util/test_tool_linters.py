import pytest

from galaxy.tool_util.lint import LintContext
from galaxy.tool_util.parser.xml import XmlToolSource
from galaxy.util import etree
from galaxy.util.getargspec import getfullargspec
from . import (
    test_tool_linters_general,
    test_tool_linters_inputs,
    test_tool_linters_outputs
)

TESTS = test_tool_linters_general.TESTS + test_tool_linters_inputs.TESTS + test_tool_linters_outputs.TESTS
TEST_IDS = test_tool_linters_general.TEST_IDS + test_tool_linters_inputs.TEST_IDS + test_tool_linters_outputs.TEST_IDS


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
