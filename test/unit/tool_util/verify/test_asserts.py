import pytest

from galaxy.tool_util.parser.xml import __parse_assert_list_from_elem
from galaxy.tool_util.verify import asserts
from galaxy.util import etree

TABULAR_ASSERTION = """
    <assert_contents>
        <has_n_columns n="3"/>
    </assert_contents>
"""
TABULAR_CSV_ASSERTION = """
    <assert_contents>
        <has_n_columns n="3" sep=","/>
    </assert_contents>
"""
TABULAR_ASSERTION_COMMENT = """
    <assert_contents>
        <has_n_columns n="3" comment="#$"/>
    </assert_contents>
"""

TABULAR_DATA_POS = """1\t2\t3
"""

TABULAR_DATA_NEG = """1\t2\t3\t4
"""

TABULAR_CSV_DATA = """1,2
"""

TABULAR_DATA_COMMENT = """# comment
$ more comment (using a char with meaning wrt regexp)
1\t2\t3
"""


TESTS = [
    # test successful assertion
    (
        TABULAR_ASSERTION, TABULAR_DATA_POS,
        lambda x: len(x) == 0
    ),
    # test wrong number of columns
    (
        TABULAR_ASSERTION, TABULAR_DATA_NEG,
        lambda x: 'Expected 3 columns in output, found 4 columns' in x
    ),
    # test wrong number of columns for csv data
    (
        TABULAR_CSV_ASSERTION, TABULAR_CSV_DATA,
        lambda x: 'Expected 3 columns in output, found 2 columns' in x
    ),
    # test tabular data with comments
    (
        TABULAR_ASSERTION_COMMENT, TABULAR_DATA_COMMENT,
        lambda x: len(x) == 0
    ),
]

TEST_IDS = [
    'tabular assertion success',
    'tabular assertion failure',
    'tabular csv assertion',
    'tabular with comments assertion',
]


@pytest.mark.parametrize('assertion_xml,data,assert_func', TESTS, ids=TEST_IDS)
def test_assertions(assertion_xml, data, assert_func):
    assertion = etree.fromstring(assertion_xml)
    assertion_description = __parse_assert_list_from_elem(assertion)
    try:
        asserts.verify_assertions(data, assertion_description)
    except AssertionError as e:
        assert_list = e.args
    else:
        assert_list = []
    assert assert_func(assert_list)
