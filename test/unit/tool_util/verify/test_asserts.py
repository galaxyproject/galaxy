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

TEXT_HAS_TEXT_ASSERTION = """
    <assert_contents>
        <has_text text="test text"/>
    </assert_contents>
"""

TEXT_HAS_TEXT_ASSERTION_N = """
    <assert_contents>
        <has_text text="test text" n="2"/>
    </assert_contents>
"""

TEXT_NOT_HAS_TEXT_ASSERTION = """
    <assert_contents>
        <not_has_text text="not here"/>
    </assert_contents>
"""

TEXT_HAS_TEXT_MATCHING_ASSERTION = """
    <assert_contents>
        <has_text_matching expression="te[sx]t"/>
    </assert_contents>
"""

TEXT_HAS_TEXT_MATCHING_ASSERTION_N = """
    <assert_contents>
        <has_text_matching expression="te[sx]t" n="4"/>
    </assert_contents>
"""

TEXT_HAS_LINE_ASSERTION = """
    <assert_contents>
        <has_line line="test text"/>
    </assert_contents>
"""
TEXT_HAS_LINE_ASSERTION_N = """
    <assert_contents>
        <has_line line="test text" n="2"/>
    </assert_contents>
"""
TEXT_HAS_N_LINES_ASSERTION = """
    <assert_contents>
        <has_n_lines n="2"/>
    </assert_contents>
"""
TEXT_HAS_N_LINES_ASSERTION_DELTA = """
    <assert_contents>
        <has_n_lines n="3" delta="1"/>
    </assert_contents>
"""
TEXT_HAS_N_LINES_ASSERTION_DELTA_FRAC = """
    <assert_contents>
        <has_n_lines n="3" delta="100" delta_frac="0.334"/>
    </assert_contents>
"""
TEXT_HAS_LINE_MATCHING_ASSERTION = """
    <assert_contents>
        <has_line_matching expression="te[sx]t te[sx]t"/>
    </assert_contents>
"""
TEXT_HAS_LINE_MATCHING_ASSERTION_N = """
    <assert_contents>
        <has_line_matching expression="te[sx]t te[sx]t" n="2"/>
    </assert_contents>
"""

SIZE_HAS_SIZE_ASSERTION = """
    <assert_contents>
        <has_size value="10"/>
    </assert_contents>
"""
SIZE_HAS_SIZE_ASSERTION_DELTA = """
    <assert_contents>
        <has_size value="10" delta="10"/>
    </assert_contents>
"""
SIZE_HAS_SIZE_ASSERTION_DELTA_FRAC = """
    <assert_contents>
        <has_size value="10" delta="100" delta_frac="0.2"/>
    </assert_contents>
"""

TEXT_DATA_HAS_TEXT = """test text
"""

TEXT_DATA_HAS_TEXT_TWO = """test text
test text
"""

TEXT_DATA_HAS_TEXT_NEG = """desired content
is not here
"""

TEXT_DATA_NONE = None

TEXT_DATA_EMPTY = ""

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
    # test has_text
    (
        TEXT_HAS_TEXT_ASSERTION, TEXT_DATA_HAS_TEXT,
        lambda x: len(x) == 0
    ),
    # test has_text .. negative test
    (
        TEXT_HAS_TEXT_ASSERTION, TEXT_DATA_HAS_TEXT_NEG,
        lambda x: "Output file did not contain expected text 'test text' (output 'desired content\nis not here\n')" in x
    ),
    # test has_text with None output
    (
        TEXT_HAS_TEXT_ASSERTION, TEXT_DATA_NONE,
        lambda x: "Checking has_text assertion on empty output (None)" in x
    ),
    # test has_text with empty output
    (
        TEXT_HAS_TEXT_ASSERTION, TEXT_DATA_EMPTY,
        lambda x: "Output file did not contain expected text 'test text' (output '')" in x
    ),
    # test has_text with n
    (
        TEXT_HAS_TEXT_ASSERTION_N, TEXT_DATA_HAS_TEXT_TWO,
        lambda x: len(x) == 0
    ),
    # test has_text with n .. negative test
    (
        TEXT_HAS_TEXT_ASSERTION_N, TEXT_DATA_HAS_TEXT,
        lambda x: "Expected 2 occurences of 'test text' in output file (output 'test text\n'); found 1" in x
    ),
    # test not_has_text
    (
        TEXT_NOT_HAS_TEXT_ASSERTION, TEXT_DATA_HAS_TEXT,
        lambda x: len(x) == 0
    ),
    # test not_has_text .. negative test
    (
        TEXT_NOT_HAS_TEXT_ASSERTION, TEXT_DATA_HAS_TEXT_NEG,
        lambda x: "Output file contains unexpected text 'not here'" in x
    ),
    # test not_has_text with None output
    (
        TEXT_NOT_HAS_TEXT_ASSERTION, TEXT_DATA_NONE,
        lambda x: "Checking not_has_text assertion on empty output (None)" in x
    ),
    # test not_has_text with empty output
    (
        TEXT_NOT_HAS_TEXT_ASSERTION, TEXT_DATA_EMPTY,
        lambda x: len(x) == 0
    ),
    # test has_text_matching
    (
        TEXT_HAS_TEXT_MATCHING_ASSERTION, TEXT_DATA_HAS_TEXT,
        lambda x: len(x) == 0
    ),
    # test has_text_matching .. negative test
    (
        TEXT_HAS_TEXT_MATCHING_ASSERTION, TEXT_DATA_HAS_TEXT_NEG,
        lambda x: "No text matching expression 'te[sx]t' was found in output file" in x
    ),
    # test has_text_matching with n
    (
        TEXT_HAS_TEXT_MATCHING_ASSERTION_N, TEXT_DATA_HAS_TEXT_TWO,
        lambda x: len(x) == 0
    ),
    # test has_text_matching with n .. negative test (using the test text where "te[sx]st" appears twice)
    (
        TEXT_HAS_TEXT_MATCHING_ASSERTION_N, TEXT_DATA_HAS_TEXT,
        lambda x: "Expected 4 (non-overlapping) matches for 'te[sx]t' in output file (output 'test text\n'); found 2" in x
    ),
    # test has_line
    (
        TEXT_HAS_LINE_ASSERTION, TEXT_DATA_HAS_TEXT,
        lambda x: len(x) == 0
    ),
    # test has_line .. negative test
    (
        TEXT_HAS_LINE_ASSERTION, TEXT_DATA_HAS_TEXT_NEG,
        lambda x: "No line of output file was 'test text' (output was 'desired content\nis not here\n')" in x
    ),
    # test has_line with n
    (
        TEXT_HAS_LINE_ASSERTION_N, TEXT_DATA_HAS_TEXT_TWO,
        lambda x: len(x) == 0
    ),
    # test has_line with n .. negative test
    (
        TEXT_HAS_LINE_ASSERTION_N, TEXT_DATA_HAS_TEXT,
        lambda x: "Expected 2 lines matching 'test text' in output file (output was 'test text\n'); found 1" in x
    ),
    # test has_n_lines
    (
        TEXT_HAS_N_LINES_ASSERTION, TEXT_DATA_HAS_TEXT_TWO,
        lambda x: len(x) == 0
    ),
    # test has_n_lines .. negative test
    (
        TEXT_HAS_N_LINES_ASSERTION, TEXT_DATA_HAS_TEXT,
        lambda x: "Expected 2 lines in output, found 1 lines" in x
    ),
    # test has_n_lines ..delta
    (
        TEXT_HAS_N_LINES_ASSERTION_DELTA, TEXT_DATA_HAS_TEXT,
        lambda x: "Expected 3+-1 lines in the output, found 1 lines" in x
    ),
    # test has_n_lines ..delta_frac
    (
        TEXT_HAS_N_LINES_ASSERTION_DELTA_FRAC, TEXT_DATA_HAS_TEXT,
        lambda x: "Expected 3+-1.002 lines in the output, found 1 lines" in x
    ),
    # test has_line_matching
    (
        TEXT_HAS_LINE_MATCHING_ASSERTION, TEXT_DATA_HAS_TEXT,
        lambda x: len(x) == 0
    ),
    # test has_line_matching .. negative test
    (
        TEXT_HAS_LINE_MATCHING_ASSERTION, TEXT_DATA_HAS_TEXT_NEG,
        lambda x: "No line matching expression 'te[sx]t te[sx]t' was found in output file" in x
    ),
    # test has_line_matching n
    (
        TEXT_HAS_LINE_MATCHING_ASSERTION_N, TEXT_DATA_HAS_TEXT_TWO,
        lambda x: len(x) == 0
    ),
    # test has_line_matching n .. negative test
    (
        TEXT_HAS_LINE_MATCHING_ASSERTION_N, TEXT_DATA_HAS_TEXT,
        lambda x: "Expected 2 lines matching for 'te[sx]t te[sx]t' in output file (output 'test text\n'); found 1" in x
    ),
    # test has_size
    (
        SIZE_HAS_SIZE_ASSERTION, TEXT_DATA_HAS_TEXT,
        lambda x: len(x) == 0
    ),
    # test has_size .. negative test
    (
        SIZE_HAS_SIZE_ASSERTION, TEXT_DATA_HAS_TEXT_TWO,
        lambda x: "Expected file size of 10+-0, actual file size is 20" in x
    ),
    # test has_size .. delta
    (
        SIZE_HAS_SIZE_ASSERTION_DELTA, TEXT_DATA_HAS_TEXT_TWO,
        lambda x: len(x) == 0
    ),
    # test has_size .. delta
    (
        SIZE_HAS_SIZE_ASSERTION_DELTA_FRAC, TEXT_DATA_HAS_TEXT_TWO,
        lambda x: "Expected file size of 10+-2.0, actual file size is 20" in x
    ),
]

TEST_IDS = [
    'has_n_columns success',
    'has_n_columns failure',
    'has_n_columns for csv',
    'has_n_columns with comments',
    'has_text success',
    'has_text failure',
    'has_text None output',
    'has_text empty output',
    'has_text n success',
    'has_text n failure',
    'not_has_text success',
    'not_has_text failure',
    'not_has_text None output',
    'not_has_text empty output',
    'has_text_matching success',
    'has_text_matching failure',
    'has_text_matching n success',
    'has_text_matching n failure',
    'has_line success',
    'has_line failure',
    'has_line n success',
    'has_line n failure',
    'has_n_lines success',
    'has_n_lines failure',
    'has_n_lines delta',
    'has_n_lines delta_frac',
    'has_line_matching success',
    'has_line_matching failure',
    'has_line_matching n success',
    'has_line_matching n failure',
    'has_size success',
    'has_size failure',
    'has_size delta',
    'has_size delta_frac',
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
        assert_list = ()
    assert assert_func(assert_list)
