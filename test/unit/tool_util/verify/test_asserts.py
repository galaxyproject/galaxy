import gzip
import os
import shutil
import tempfile
from typing import Tuple

try:
    import h5py
except ImportError:
    h5py = None

from galaxy.tool_util.parser.xml import parse_assert_list_from_elem
from galaxy.tool_util.verify import asserts
from galaxy.util import parse_xml_string

TABULAR_ASSERTION = """
    <assert_contents>
        <has_n_columns n="3"/>
    </assert_contents>
"""
TABULAR_CSV_ASSERTION = """
    <assert_contents>
        <has_n_columns sep="," min="3"/>
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


def test_has_n_columns_success():
    """test successful assertion"""
    a = run_assertions(TABULAR_ASSERTION, TABULAR_DATA_POS)
    assert len(a) == 0


def test_has_n_columns_failure():
    """test wrong number of columns"""
    a = run_assertions(TABULAR_ASSERTION, TABULAR_DATA_NEG)
    assert "Expected 3+-0 columns in output found 4" in a
    assert len(a) == 1


def test_has_n_columns_for_csv():
    """test wrong number of columns for csv data"""
    a = run_assertions(TABULAR_CSV_ASSERTION, TABULAR_CSV_DATA)
    assert "Expected the number of columns in output to be in [3:inf] found 2" in a
    assert len(a) == 1


def test_has_n_columns_with_comments():
    """test tabular data with comments"""
    a = run_assertions(TABULAR_ASSERTION_COMMENT, TABULAR_DATA_COMMENT)
    assert len(a) == 0


TEXT_DATA_HAS_TEXT = """test text
"""

TEXT_DATA_HAS_TEXT_NEG = """desired content
is not here
"""

TEXT_DATA_NONE = None

TEXT_DATA_EMPTY = ""

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

TEXT_HAS_TEXT_ASSERTION_N_DELTA = """
    <assert_contents>
        <has_text text="test text" n="3" delta="1"/>
    </assert_contents>
"""

TEXT_HAS_TEXT_ASSERTION_MIN_MAX = """
    <assert_contents>
        <has_text text="test text" min="2" max="4"/>
    </assert_contents>
"""

TEXT_HAS_TEXT_ASSERTION_NEGATE = """
    <assert_contents>
        <has_text text="test text" negate="true"/>
    </assert_contents>
"""

TEXT_HAS_TEXT_ASSERTION_N_NEGATE = """
    <assert_contents>
        <has_text text="test text" n="2" negate="true"/>
    </assert_contents>
"""

TEXT_HAS_TEXT_ASSERTION_N_DELTA_NEGATE = """
    <assert_contents>
        <has_text text="test text" n="3" delta="1" negate="true"/>
    </assert_contents>
"""

TEXT_HAS_TEXT_ASSERTION_MIN_MAX_NEGATE = """
    <assert_contents>
        <has_text text="test text" min="2" max="4" negate="true"/>
    </assert_contents>
"""

TEXT_NOT_HAS_TEXT_ASSERTION = """
    <assert_contents>
        <not_has_text text="not here"/>
    </assert_contents>
"""


def test_has_text_success():
    """test has_text"""
    a = run_assertions(TEXT_HAS_TEXT_ASSERTION, TEXT_DATA_HAS_TEXT)
    assert len(a) == 0


def test_has_text_failure():
    """test has_text .. negative test"""
    a = run_assertions(TEXT_HAS_TEXT_ASSERTION, TEXT_DATA_HAS_TEXT_NEG)
    assert "Expected text 'test text' in output ('desired content\nis not here\n')" in a
    assert len(a) == 1


def test_has_text_None_output():
    """test has_text with None output"""
    a = run_assertions(TEXT_HAS_TEXT_ASSERTION, TEXT_DATA_NONE)
    assert "Checking has_text assertion on empty output (None)" in a
    assert len(a) == 1


def test_has_text_empty_output():
    """test has_text with empty output"""
    a = run_assertions(TEXT_HAS_TEXT_ASSERTION, TEXT_DATA_EMPTY)
    assert "Expected text 'test text' in output ('')" in a
    assert len(a) == 1


def test_has_text_n_success():
    """test has_text with n"""
    a = run_assertions(TEXT_HAS_TEXT_ASSERTION_N, TEXT_DATA_HAS_TEXT * 2)
    assert len(a) == 0


def test_has_text_n_failure():
    """test has_text with n .. negative test"""
    a = run_assertions(TEXT_HAS_TEXT_ASSERTION_N, TEXT_DATA_HAS_TEXT)
    assert "Expected 2+-0 occurences of 'test text' in output ('test text\n') found 1" in a
    assert len(a) == 1


def test_has_text_n_delta_success():
    """test has_text with n and delta"""
    a = run_assertions(TEXT_HAS_TEXT_ASSERTION_N_DELTA, TEXT_DATA_HAS_TEXT * 2)
    assert len(a) == 0


def test_has_text_n_delta_failure():
    """test has_text with n and delta .. negative test"""
    a = run_assertions(TEXT_HAS_TEXT_ASSERTION_N_DELTA, TEXT_DATA_HAS_TEXT)
    assert "Expected 3+-1 occurences of 'test text' in output ('test text\n') found 1" in a
    assert len(a) == 1


def test_has_text_minmax_delta_success():
    """test has_text with min max"""
    a = run_assertions(TEXT_HAS_TEXT_ASSERTION_MIN_MAX, TEXT_DATA_HAS_TEXT * 2)
    assert len(a) == 0


def test_has_text_minmax_delta_failure():
    """test has_text with min max .. negative test"""
    a = run_assertions(TEXT_HAS_TEXT_ASSERTION_MIN_MAX, TEXT_DATA_HAS_TEXT)
    assert "Expected that the number of occurences of 'test text' in output is in [2:4] ('test text\n') found 1" in a
    assert len(a) == 1


def test_has_text_negate_success():
    """test has_text negate"""
    a = run_assertions(TEXT_HAS_TEXT_ASSERTION_NEGATE, TEXT_DATA_HAS_TEXT_NEG)
    assert len(a) == 0


def test_has_text_negate_failure():
    """test has_text negate .. negative test"""
    a = run_assertions(TEXT_HAS_TEXT_ASSERTION_NEGATE, TEXT_DATA_HAS_TEXT)
    assert "Did not expect text 'test text' in output ('test text\n')" in a
    assert len(a) == 1


def test_has_text_negate_None_output():
    """test has_text negate with None output .. should have the same output as with negate='false'"""
    a = run_assertions(TEXT_HAS_TEXT_ASSERTION_NEGATE, TEXT_DATA_NONE)
    assert "Checking has_text assertion on empty output (None)" in a
    assert len(a) == 1


def test_has_text_negate_empty_output():
    """test has_text negate with empty output"""
    a = run_assertions(TEXT_HAS_TEXT_ASSERTION_NEGATE, TEXT_DATA_EMPTY)
    assert len(a) == 0


def test_has_text_negate_n_success():
    """test has_text negate with n"""
    a = run_assertions(TEXT_HAS_TEXT_ASSERTION_N_NEGATE, TEXT_DATA_HAS_TEXT)
    assert len(a) == 0


def test_has_text_negate_n_failure():
    """test has_text negate with n .. negative test"""
    a = run_assertions(TEXT_HAS_TEXT_ASSERTION_N_NEGATE, TEXT_DATA_HAS_TEXT * 2)
    assert "Did not expect 2+-0 occurences of 'test text' in output ('test text\ntest text\n') found 2" in a
    assert len(a) == 1


def test_has_text_negate_n_delta_success():
    """test has_text negate with n and delta"""
    a = run_assertions(TEXT_HAS_TEXT_ASSERTION_N_DELTA_NEGATE, TEXT_DATA_HAS_TEXT)
    assert len(a) == 0


def test_has_text_negate_n_delta_failure():
    """test has_text negate with n and delta .. negative test"""
    a = run_assertions(TEXT_HAS_TEXT_ASSERTION_N_DELTA_NEGATE, TEXT_DATA_HAS_TEXT * 2)
    assert "Did not expect 3+-1 occurences of 'test text' in output ('test text\ntest text\n') found 2" in a
    assert len(a) == 1


def test_has_text_negate_minmax_delta_success():
    """test has_text negate with min max"""
    a = run_assertions(TEXT_HAS_TEXT_ASSERTION_MIN_MAX_NEGATE, TEXT_DATA_HAS_TEXT)
    assert len(a) == 0


def test_has_text_negate_minmax_delta_failure():
    """test has_text negate with min max .. negative test"""
    a = run_assertions(TEXT_HAS_TEXT_ASSERTION_MIN_MAX_NEGATE, TEXT_DATA_HAS_TEXT * 2)
    assert (
        "Did not expect that the number of occurences of 'test text' in output is in [2:4] ('test text\ntest text\n') found 2"
        in a
    )
    assert len(a) == 1


def test_not_has_text_success():
    """test not_has_text"""
    a = run_assertions(TEXT_NOT_HAS_TEXT_ASSERTION, TEXT_DATA_HAS_TEXT)
    assert len(a) == 0


def test_not_has_text_failure():
    """test not_has_text .. negative test"""
    a = run_assertions(TEXT_NOT_HAS_TEXT_ASSERTION, TEXT_DATA_HAS_TEXT_NEG)
    assert "Output file contains unexpected text 'not here'" in a
    assert len(a) == 1


def test_not_has_text_None_output():
    """test not_has_text with None output"""
    a = run_assertions(TEXT_NOT_HAS_TEXT_ASSERTION, TEXT_DATA_NONE)
    assert "Checking not_has_text assertion on empty output (None)" in a
    assert len(a) == 1


def test_not_has_text_empty_output():
    """test not_has_text with empty output"""
    a = run_assertions(TEXT_NOT_HAS_TEXT_ASSERTION, TEXT_DATA_EMPTY)
    assert len(a) == 0


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

TEXT_HAS_TEXT_MATCHING_ASSERTION_MINMAX = """
    <assert_contents>
        <has_text_matching expression="te[sx]t" min="3" max="5"/>
    </assert_contents>
"""


def test_has_text_matching_success():
    """test has_text_matching"""
    a = run_assertions(TEXT_HAS_TEXT_MATCHING_ASSERTION, TEXT_DATA_HAS_TEXT)
    assert len(a) == 0


def test_has_text_matching_failure():
    """test has_text_matching .. negative test"""
    a = run_assertions(TEXT_HAS_TEXT_MATCHING_ASSERTION, TEXT_DATA_HAS_TEXT_NEG)
    assert "Expected text matching expression 'te[sx]t' in output ('desired content\nis not here\n')" in a
    assert len(a) == 1


def test_has_text_matching_n_success():
    """test has_text_matching with n"""
    a = run_assertions(TEXT_HAS_TEXT_MATCHING_ASSERTION_N, TEXT_DATA_HAS_TEXT * 2)
    assert len(a) == 0


def test_has_text_matching_n_failure():
    """test has_text_matching with n .. negative test (using the test text where "te[sx]st" appears twice)"""
    a = run_assertions(TEXT_HAS_TEXT_MATCHING_ASSERTION_N, TEXT_DATA_HAS_TEXT)
    assert "Expected 4+-0 (non-overlapping) matches for 'te[sx]t' in output ('test text\n') found 2" in a
    assert len(a) == 1


def test_has_text_matching_minmax_success():
    """test has_text_matching with min/max"""
    a = run_assertions(TEXT_HAS_TEXT_MATCHING_ASSERTION_MINMAX, TEXT_DATA_HAS_TEXT * 2)
    assert len(a) == 0


def test_has_text_matching_minmax_failure():
    """test has_text_matching with n .. negative test (using the test text where "te[sx]st" appears twice)"""
    a = run_assertions(TEXT_HAS_TEXT_MATCHING_ASSERTION_MINMAX, TEXT_DATA_HAS_TEXT)
    assert (
        "Expected that the number of (non-overlapping) matches for 'te[sx]t' in output is in [3:5] ('test text\n') found 2"
        in a
    )
    assert len(a) == 1


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
        <has_n_lines n="{n}"/>
    </assert_contents>
"""
TEXT_HAS_N_LINES_ASSERTION_DELTA = """
    <assert_contents>
        <has_n_lines n="{n}" delta="{delta}"/>
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


def test_has_line_success():
    """test has_line"""
    a = run_assertions(TEXT_HAS_LINE_ASSERTION, TEXT_DATA_HAS_TEXT)
    assert len(a) == 0


def test_has_line_failure():
    """test has_line .. negative test"""
    a = run_assertions(TEXT_HAS_LINE_ASSERTION, TEXT_DATA_HAS_TEXT_NEG)
    assert "Expected line 'test text' in output ('desired content\nis not here\n')" in a
    assert len(a) == 1


def test_has_line_n_success():
    """test has_line with n"""
    a = run_assertions(TEXT_HAS_LINE_ASSERTION_N, TEXT_DATA_HAS_TEXT * 2)
    assert len(a) == 0


def test_has_line_n_failure():
    """test has_line with n .. negative test"""
    a = run_assertions(TEXT_HAS_LINE_ASSERTION_N, TEXT_DATA_HAS_TEXT)
    assert "Expected 2+-0 lines 'test text' in output ('test text\n') found 1" in a
    assert len(a) == 1


def test_has_n_lines_success():
    """test has_n_lines"""
    a = run_assertions(TEXT_HAS_N_LINES_ASSERTION.format(n="2"), TEXT_DATA_HAS_TEXT * 2)
    assert len(a) == 0


def test_has_n_lines_n_as_bytes_success():
    """test has_n_lines .. bytes"""
    a = run_assertions(TEXT_HAS_N_LINES_ASSERTION.format(n="2ki"), TEXT_DATA_HAS_TEXT * 2048)
    assert len(a) == 0


def test_has_n_lines_failure():
    """test has_n_lines .. negative test"""
    a = run_assertions(
        TEXT_HAS_N_LINES_ASSERTION.format(n="2"),
        TEXT_DATA_HAS_TEXT,
    )
    assert "Expected 2+-0 lines in the output found 1" in a
    assert len(a) == 1


def test_has_n_lines_delta():
    """test has_n_lines ..delta"""
    a = run_assertions(TEXT_HAS_N_LINES_ASSERTION_DELTA.format(n="3", delta="1"), TEXT_DATA_HAS_TEXT)
    assert "Expected 3+-1 lines in the output found 1" in a
    assert len(a) == 1


def test_has_line_matching_success():
    """test has_line_matching"""
    a = run_assertions(TEXT_HAS_LINE_MATCHING_ASSERTION, TEXT_DATA_HAS_TEXT)
    assert len(a) == 0


def test_has_line_matching_failure():
    """test has_line_matching .. negative test"""
    a = run_assertions(TEXT_HAS_LINE_MATCHING_ASSERTION, TEXT_DATA_HAS_TEXT_NEG)
    assert "Expected line matching expression 'te[sx]t te[sx]t' in output ('desired content\nis not here\n')" in a
    assert len(a) == 1


def test_has_line_matching_n_success():
    """test has_line_matching n"""
    a = run_assertions(TEXT_HAS_LINE_MATCHING_ASSERTION_N, TEXT_DATA_HAS_TEXT * 2)
    assert len(a) == 0


def test_has_line_matching_n_failure():
    """test has_line_matching n .. negative test"""
    a = run_assertions(TEXT_HAS_LINE_MATCHING_ASSERTION_N, TEXT_DATA_HAS_TEXT)
    assert "Expected 2+-0 lines matching for 'te[sx]t te[sx]t' in output ('test text\n') found 1" in a
    assert len(a) == 1


SIZE_HAS_SIZE_ASSERTION = """
    <assert_contents>
        <has_size {size_attrib}="{value}"/>
    </assert_contents>
"""
SIZE_HAS_SIZE_ASSERTION_DELTA = """
    <assert_contents>
        <has_size {size_attrib}="{value}" delta="{delta}"/>
    </assert_contents>
"""

# create gz test data for use with has_size tests
with tempfile.NamedTemporaryFile(mode="w", delete=False) as txttmp:
    txttmp.write("A" * 100)
    txttmp.flush()
    A100 = open(txttmp.name, "rb").read()
    GZA100 = gzip.compress(A100)


def test_has_size_success():
    """test has_size"""
    a = run_assertions(SIZE_HAS_SIZE_ASSERTION.format(size_attrib="size", value=10), TEXT_DATA_HAS_TEXT)
    assert len(a) == 0


def test_has_size_failure():
    """test has_size .. negative test"""
    a = run_assertions(SIZE_HAS_SIZE_ASSERTION.format(size_attrib="value", value="10"), TEXT_DATA_HAS_TEXT * 2)
    assert "Expected file size of 10+-0 found 20" in a
    assert len(a) == 1


def test_has_size_delta():
    """test has_size .. delta"""
    a = run_assertions(
        SIZE_HAS_SIZE_ASSERTION_DELTA.format(size_attrib="size", value="10", delta="10"), TEXT_DATA_HAS_TEXT * 2
    )
    assert len(a) == 0


def test_has_size_with_bytes_suffix():
    """test has_size .. bytes suffix"""
    a = run_assertions(
        SIZE_HAS_SIZE_ASSERTION_DELTA.format(size_attrib="size", value="1k", delta="0"), TEXT_DATA_HAS_TEXT * 100
    )
    assert len(a) == 0


def test_has_size_with_bytes_suffix_failure():
    """test has_size .. bytes suffix .. negative"""
    a = run_assertions(
        SIZE_HAS_SIZE_ASSERTION_DELTA.format(size_attrib="value", value="1Mi", delta="10k"), TEXT_DATA_HAS_TEXT * 100
    )
    assert "Expected file size of 1Mi+-10k found 1000" in a
    assert len(a) == 1


def test_has_size_decompress_gz():
    """test has_size with gzipped data using decompress=True (which in real life is set int he parent output tag)"""
    a = run_assertions(SIZE_HAS_SIZE_ASSERTION.format(size_attrib="size", value="100"), GZA100, decompress=True)
    assert len(a) == 0


def test_has_size_decompress_txt():
    """
    test has_size with NON-gzipped data using decompress=True
    -> decompress should be ignored - in particular there should be no error
    """
    a = run_assertions(SIZE_HAS_SIZE_ASSERTION.format(size_attrib="size", value="100"), A100, decompress=True)
    assert len(a) == 0


VALID_XML = """<root>
    <elem name="foo">
        <more name="bar">BAR</more>
        <more name="baz">BAZ</more>
        <more name="qux">QUX</more>
    </elem>
    <elem name="baz"/>
</root>
"""

INVALID_XML = '<root><elem name="foo"></root>'

XML_IS_VALID_XML_ASSERTION = """
    <assert_contents>
        <is_valid_xml/>
    </assert_contents>
"""


def test_is_valid_xml_success():
    """test is_valid_xml"""
    a = run_assertions(XML_IS_VALID_XML_ASSERTION, VALID_XML)
    assert len(a) == 0


def test_is_valid_xml_failure():
    """test is_valid_xml .. negative test"""
    a = run_assertions(XML_IS_VALID_XML_ASSERTION, INVALID_XML)
    assert (
        "Expected valid XML, but could not parse output. Opening and ending tag mismatch: elem line 1 and root, line 1, column 31 (<string>, line 1)"
        in a
    )


XML_HAS_ELEMENT_WITH_PATH = """
    <assert_contents>
        <has_element_with_path path="{path}"/>
    </assert_contents>
"""
XML_HAS_N_ELEMENTS_WITH_PATH = """
    <assert_contents>
        <is_valid_xml/>
        <has_n_elements_with_path path="{path}" n="{n}"/>
    </assert_contents>
"""
XML_ELEMENT_TEXT_MATCHES = """
    <assert_contents>
        <element_text_matches path="{path}" expression="{expression}"/>
    </assert_contents>
"""
XML_ELEMENT_TEXT_IS = """
    <assert_contents>
        <element_text_is path="{path}" text="{text}"/>
    </assert_contents>
"""
XML_ATTRIBUTE_MATCHES = """
    <assert_contents>
        <is_valid_xml/>
        <attribute_matches path="{path}" attribute="{attribute}" expression="{expression}"/>
    </assert_contents>
"""
XML_ELEMENT_TEXT = """
    <assert_contents>
        <element_text path="{path}">
            {content_assert}
        </element_text>
    </assert_contents>
"""

XML_XML_ELEMENT = """
    <assert_contents>
        <xml_element path="{path}" attribute="{attribute}" all="{all}" n="{n}" delta="{delta}" min="{min}" max="{max}" negate="{negate}">
            {content_assert}
        </xml_element>
    </assert_contents>
"""


def test_has_element_with_path_success_1():
    """test has_element_with_path"""
    a = run_assertions(XML_HAS_ELEMENT_WITH_PATH.format(path="./elem[1]/more"), VALID_XML)
    assert len(a) == 0


def test_has_element_with_path_success_2():
    """test has_element_with_path"""
    a = run_assertions(XML_HAS_ELEMENT_WITH_PATH.format(path="./elem[@name='foo']"), VALID_XML)
    assert len(a) == 0


def test_has_element_with_path_success_3():
    """test has_element_with_path"""
    a = run_assertions(XML_HAS_ELEMENT_WITH_PATH.format(path=".//more[@name]"), VALID_XML)
    assert len(a) == 0


def test_has_element_with_path_failure():
    """test has_element_with_path .. negative test"""
    a = run_assertions(XML_HAS_ELEMENT_WITH_PATH.format(path="./blah"), VALID_XML)
    assert "Expected path './blah' in xml" in a


def test_has_n_elements_with_path_success_1():
    """test has_n_elements_with_path"""
    a = run_assertions(XML_HAS_N_ELEMENTS_WITH_PATH.format(path="./elem", n="2"), VALID_XML)
    assert len(a) == 0


def test_has_n_elements_with_path_success_2():
    """test has_n_elements_with_path"""
    a = run_assertions(XML_HAS_N_ELEMENTS_WITH_PATH.format(path="./elem[1]/more", n="3"), VALID_XML)
    assert len(a) == 0


def test_has_n_elements_with_path_success_3():
    """test has_n_elements_with_path"""
    a = run_assertions(XML_HAS_N_ELEMENTS_WITH_PATH.format(path="./elem[@name='foo']/more", n="3"), VALID_XML)
    assert len(a) == 0


def test_has_n_elements_with_path_success_4():
    """test has_n_elements_with_path"""
    a = run_assertions(XML_HAS_N_ELEMENTS_WITH_PATH.format(path="./elem[2]/more", n="0"), VALID_XML)
    assert len(a) == 0


def test_has_n_elements_with_path_failure():
    """test has_n_elements_with_path .. negative test"""
    a = run_assertions(XML_HAS_N_ELEMENTS_WITH_PATH.format(path="./elem", n="1"), VALID_XML)
    assert "Expected 1+-0 occurrences of path './elem' in xml found 2" in a
    assert len(a) == 1


def test_element_text_matches_sucess():
    """test element_text_matches"""
    a = run_assertions(XML_ELEMENT_TEXT_MATCHES.format(path="./elem/more", expression="BA(R|Z)"), VALID_XML)
    assert len(a) == 0


def test_element_text_matches_sucess_with_more_specific_path():
    """test element_text_matches more specific path"""
    a = run_assertions(XML_ELEMENT_TEXT_MATCHES.format(path="./elem/more[2]", expression="BA(R|Z)"), VALID_XML)
    assert len(a) == 0


def test_element_text_matches_failure():
    """test element_text_matches .. negative test"""
    a = run_assertions(
        XML_ELEMENT_TEXT_MATCHES.format(path="./elem/more", expression="QU(X|Y)"),
        VALID_XML,
    )
    assert "Text of element with path './elem/more': Expected text matching expression 'QU(X|Y)' in output ('BAR')" in a
    assert len(a) == 1


def test_element_text_is_sucess():
    """test element_text_is"""
    a = run_assertions(XML_ELEMENT_TEXT_IS.format(path="./elem/more", text="BAR"), VALID_XML)
    assert len(a) == 0


def test_element_text_is_sucess_with_more_specific_path():
    """test element_text_is with more specific path"""
    a = run_assertions(XML_ELEMENT_TEXT_IS.format(path="./elem/more[@name='baz']", text="BAZ"), VALID_XML)
    assert len(a) == 0


def test_element_text_is_failure():
    """test element_text_is .. negative test testing that prefix is not accepted"""
    a = run_assertions(XML_ELEMENT_TEXT_IS.format(path="./elem/more", text="BA"), VALID_XML)
    assert "Text of element with path './elem/more': Expected text matching expression 'BA$' in output ('BAR')" in a
    assert len(a) == 1


def test_attribute_matches_sucess():
    """est element_attribute_matches"""
    a = run_assertions(
        XML_ATTRIBUTE_MATCHES.format(path="./elem/more", attribute="name", expression="ba(r|z)"), VALID_XML
    )
    assert len(a) == 0


def test_attribute_matches_sucess_with_more_specific_path():
    """test element_attribute_matches with more specific path"""
    a = run_assertions(
        XML_ATTRIBUTE_MATCHES.format(path="./elem/more[2]", attribute="name", expression="ba(r|z)"), VALID_XML
    )
    assert len(a) == 0


def test_attribute_matches_failure():
    """test element_attribute_matches .. negative test"""
    a = run_assertions(
        XML_ATTRIBUTE_MATCHES.format(path="./elem/more", attribute="name", expression="qu(x|y)"), VALID_XML
    )
    assert (
        "Attribute 'name' on element with path './elem/more': Expected text matching expression 'qu(x|y)' in output ('bar')"
        in a
    )
    assert len(a) == 1


def test_element_text_success():
    """test element_text"""
    a = run_assertions(XML_ELEMENT_TEXT.format(path="./elem/more", content_assert=""), VALID_XML)
    assert len(a) == 0


def test_element_text_failure():
    """test element_text .. negative"""
    a = run_assertions(XML_ELEMENT_TEXT.format(path="./absent", content_assert=""), VALID_XML)
    assert "Expected path './absent' in xml" in a
    assert len(a) == 1


def test_element_text_with_subassertion_sucess():
    """test element_text with sub-assertion"""
    a = run_assertions(XML_ELEMENT_TEXT.format(path="./elem/more", content_assert='<has_text text="BAR"/>'), VALID_XML)
    assert len(a) == 0


def test_element_text_with_subassertion_failure():
    """test element_text with sub-assertion .. negative"""
    a = run_assertions(
        XML_ELEMENT_TEXT.format(path="./elem/more", content_assert='<has_text text="NOTBAR"/>'), VALID_XML
    )
    assert "Text of element with path './elem/more': Expected text 'NOTBAR' in output ('BAR')" in a
    assert len(a) == 1


# note that xml_element is also tested indirectly by the other xml
# assertions which are all implemented by xml_element
def test_xml_element_matching_text_success():
    """test xml_element"""
    a = run_assertions(
        XML_XML_ELEMENT.format(
            path=".//more",
            n="2",
            delta="1",
            min="1",
            max="3",
            attribute="",
            all="false",
            content_assert='<has_text_matching expression="(BA[RZ]|QUX)$"/>',
            negate="false",
        ),
        VALID_XML,
    )
    assert len(a) == 0


def test_xml_element_matching_attribute_success():
    """test xml_element testing attribute matching on all matching elements"""
    a = run_assertions(
        XML_XML_ELEMENT.format(
            path=".//more",
            n="2",
            delta="1",
            min="1",
            max="3",
            attribute="name",
            all="true",
            content_assert='<has_text_matching expression="(ba[rz]|qux)$"/>',
            negate="false",
        ),
        VALID_XML,
    )
    assert len(a) == 0


def test_xml_element_failure_due_to_n():
    """test xml_element .. failing because of n"""
    a = run_assertions(
        XML_XML_ELEMENT.format(
            path=".//more",
            n="2",
            delta="0",
            min="1",
            max="3",
            attribute="",
            all="false",
            content_assert="",
            negate="false",
        ),
        VALID_XML,
    )
    assert "Expected 2+-0 occurrences of path './/more' in xml found 3" in a
    assert len(a) == 1


def test_xml_element_failure_due_to_minmax_in_combination_with_negate():
    """test xml_element .. failing because of n"""
    a = run_assertions(
        XML_XML_ELEMENT.format(
            path=".//more",
            n="10000",
            delta="1",
            min="1",
            max="3",
            attribute="",
            all="false",
            content_assert="",
            negate="true",
        ),
        VALID_XML,
    )
    assert "Did not expect that the number of occurences of path './/more' in xml is in [1:3] found 3" in a
    assert len(a) == 1


def test_xml_element_failure_due_to_subassertion():
    """test xml_element .. failing because of sub assertion"""
    a = run_assertions(
        XML_XML_ELEMENT.format(
            path=".//more",
            n="2",
            delta="1",
            min="1",
            max="3",
            attribute="",
            all="false",
            content_assert='<has_text_matching expression="(BA[RZ]|QUX)$" negate="true"/>',
            negate="false",
        ),
        VALID_XML,
    )
    assert (
        "Text of element with path './/more': Did not expect text matching expression '(BA[RZ]|QUX)$' in output ('BAR')"
        in a
    )
    assert len(a) == 1


# create a test directory structure for zipping
# might also be done directly with the fipfile/tarfile module without creating
# a tmpdir, but its much harder to create empty directories or symlinks
tmpdir = tempfile.mkdtemp()
for f in ["file1.txt", "testdir/file1.txt", "testdir/file2.txt", "testdir/dir2/file1.txt"]:
    tmpfile = os.path.join(tmpdir, f)
    os.makedirs(os.path.dirname(tmpfile), exist_ok=True)
    with open(tmpfile, "w") as fh:
        fh.write(f)
os.makedirs(os.path.join(tmpdir, "emptydir"))
os.symlink("testdir/file1.txt", os.path.join(tmpdir, "symlink"))

with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as ziptmp:
    zipname = ziptmp.name
    shutil.make_archive(zipname[:-4], "zip", tmpdir)
    with open(zipname, "rb") as zfh:
        ZIPBYTES = zfh.read()
with tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False) as ziptmp:
    zipname = ziptmp.name
    shutil.make_archive(zipname[:-7], "gztar", tmpdir)
    with open(zipname, "rb") as zfh:
        TARBYTES = zfh.read()
shutil.rmtree(tmpdir)


with tempfile.NamedTemporaryFile(mode="w", delete=False) as nonarchivetmp:
    nonarchivename = nonarchivetmp.name
    nonarchivetmp.write("some text")
with open(nonarchivename, "rb") as ntmp:
    NONARCHIVE = ntmp.read()

ARCHIVE_HAS_ARCHIVE_MEMBER = """
    <assert_contents>
        <has_archive_member path="{path}" all="{all}">
            {content_assert}
        </has_archive_member>
    </assert_contents>
"""

ARCHIVE_HAS_ARCHIVE_MEMBER_N = """
    <assert_contents>
        <has_archive_member path="{path}" n="{n}" delta="{delta}">
            {content_assert}
        </has_archive_member>
    </assert_contents>
"""

ARCHIVE_HAS_ARCHIVE_MEMBER_MINMAX = """
    <assert_contents>
        <has_archive_member path="{path}" min="{min}" max="{max}">
            {content_assert}
        </has_archive_member>
    </assert_contents>
"""


def test_has_archive_member_1filegzip():
    """test has_archive_member with a single file gz which should fail (has no members anyway)"""
    a = run_assertions(ARCHIVE_HAS_ARCHIVE_MEMBER.format(path="(\\./)?xyz", content_assert="", all="false"), GZA100)
    assert "Expected path '(\\./)?xyz' to be an archive" in a
    assert len(a) == 1


def test_has_archive_member_zip():
    """test has_archive_member with zip"""
    a = run_assertions(
        ARCHIVE_HAS_ARCHIVE_MEMBER.format(path="(\\./)?testdir/file1.txt", content_assert="", all="false"), ZIPBYTES
    )
    assert len(a) == 0


def test_has_archive_member_tar():
    """test has_archive_member with tar"""
    a = run_assertions(
        ARCHIVE_HAS_ARCHIVE_MEMBER.format(path="(\\./)?testdir/file1.txt", content_assert="", all="false"), TARBYTES
    )
    assert len(a) == 0


def test_has_archive_member_nonarchive():
    """test has_archive_member with non archive"""
    a = run_assertions(ARCHIVE_HAS_ARCHIVE_MEMBER.format(path="irrelevant", content_assert="", all="false"), NONARCHIVE)
    assert "Expected path 'irrelevant' to be an archive" in a
    assert len(a) == 1


def test_has_archive_member_zip_absent_member():
    """test has_archive_member with zip on absent member"""
    a = run_assertions(ARCHIVE_HAS_ARCHIVE_MEMBER.format(path="absent", content_assert="", all="false"), ZIPBYTES)
    assert "Expected path 'absent' in archive" in a
    assert len(a) == 1


def test_has_archive_member_tar_absent_member():
    """test has_archive_member with tar on absent member"""
    a = run_assertions(ARCHIVE_HAS_ARCHIVE_MEMBER.format(path="absent", content_assert="", all="false"), TARBYTES)
    assert "Expected path 'absent' in archive" in a
    assert len(a) == 1


def test_has_archive_member_zip_symlink_member():
    """test has_archive_member with zip on symlink"""
    a = run_assertions(
        ARCHIVE_HAS_ARCHIVE_MEMBER.format(
            path="(\\./)?symlink", content_assert='<has_text text="testdir/file1.txt"/>', all="false"
        ),
        ZIPBYTES,
    )
    assert len(a) == 0


def test_has_archive_member_tar_symlink_member():
    """test has_archive_member with tar on symlink"""
    a = run_assertions(
        ARCHIVE_HAS_ARCHIVE_MEMBER.format(
            path="(\\./)?symlink", content_assert='<has_text text="testdir/file1.txt"/>', all="false"
        ),
        TARBYTES,
    )
    assert len(a) == 0


def test_has_archive_member_zip_nonfile_member():
    """test has_archive_member with zip on a dir member (which are treated like empty files)"""
    a = run_assertions(
        ARCHIVE_HAS_ARCHIVE_MEMBER.format(path="(\\./)?testdir/", content_assert='<has_size value="0"/>', all="false"),
        ZIPBYTES,
    )
    assert len(a) == 0


def test_has_archive_member_tar_nonfile_member():
    """test has_archive_member with tar on a dir member (which are treated like empty files)"""
    a = run_assertions(
        ARCHIVE_HAS_ARCHIVE_MEMBER.format(path="(\\./)?testdir/", content_assert='<has_size value="0"/>', all="false"),
        TARBYTES,
    )
    assert len(a) == 0


def test_has_archive_member_zip_with_content_assertion():
    """test has_archive_member with zip with subassertion (note that archive members are sorted therefor file1 in dir2 is tested)"""
    a = run_assertions(
        ARCHIVE_HAS_ARCHIVE_MEMBER.format(
            path="(\\./)?testdir/.*\\.txt", content_assert='<has_text text="testdir/dir2/file1.txt"/>', all="false"
        ),
        ZIPBYTES,
    )
    assert len(a) == 0


def test_has_archive_member_tar_with_content_assertion():
    """test has_archive_member with tar with subassertion (note that archive members are sorted therefor file1 in dir2 is tested)"""
    a = run_assertions(
        ARCHIVE_HAS_ARCHIVE_MEMBER.format(
            path="(\\./)?testdir/.*\\.txt", content_assert='<has_text text="testdir/dir2/file1.txt"/>', all="false"
        ),
        TARBYTES,
    )
    assert len(a) == 0


def test_has_archive_member_zip_with_failing_content_assertion():
    """test has_archive_member with zip with failing subassertion"""
    a = run_assertions(
        ARCHIVE_HAS_ARCHIVE_MEMBER.format(
            path="(\\./)?testdir/file1.txt", content_assert='<has_text text="ABSENT"/>', all="false"
        ),
        ZIPBYTES,
    )
    assert "Archive member '(\\./)?testdir/file1.txt': Expected text 'ABSENT' in output ('testdir/file1.txt')" in a
    assert len(a) == 1


def test_has_archive_member_tar_with_failing_content_assertion():
    """test has_archive_member with tar with failing subassertion"""
    a = run_assertions(
        ARCHIVE_HAS_ARCHIVE_MEMBER.format(
            path="(\\./)?testdir/file1.txt", content_assert='<has_text text="ABSENT"/>', all="false"
        ),
        TARBYTES,
    )
    assert "Archive member '(\\./)?testdir/file1.txt': Expected text 'ABSENT' in output ('testdir/file1.txt')" in a
    assert len(a) == 1


def test_has_archive_member_zip_all_matching_with_content_assertion():
    """test has_archive_member with zip checking all matches with subassertion"""
    a = run_assertions(
        ARCHIVE_HAS_ARCHIVE_MEMBER.format(
            path=".*file.\\.txt", content_assert='<has_text_matching expression="file.\\.txt"/>', all="true"
        ),
        ZIPBYTES,
    )
    assert len(a) == 0


def test_has_archive_member_tar_all_matching_with_content_assertion():
    """test has_archive_member with tar checking all matches with subassertion"""
    a = run_assertions(
        ARCHIVE_HAS_ARCHIVE_MEMBER.format(
            path=".*file.\\.txt", content_assert='<has_text_matching expression="file.\\.txt"/>', all="true"
        ),
        TARBYTES,
    )
    assert len(a) == 0


def test_has_archive_member_zip_all_matching_with_failing_content_assertion():
    """test has_archive_member with zip checking all matches with failing subassertion"""
    a = run_assertions(
        ARCHIVE_HAS_ARCHIVE_MEMBER.format(
            path=".*file.\\.txt", content_assert='<has_text_matching expression="file1\\.txt"/>', all="true"
        ),
        ZIPBYTES,
    )
    assert "Expected text matching expression 'file1\\.txt' in output ('testdir/file2.txt')"
    assert len(a) == 1


def test_has_archive_member_tar_all_matching_with_failing_content_assertion():
    """test has_archive_member with tar checking all matches with failing subassertion"""
    a = run_assertions(
        ARCHIVE_HAS_ARCHIVE_MEMBER.format(
            path=".*file.\\.txt", content_assert='<has_text_matching expression="file1\\.txt"/>', all="true"
        ),
        TARBYTES,
    )

    assert (
        "Archive member '.*file.\\.txt': Expected text matching expression 'file1\\.txt' in output ('testdir/file2.txt')"
        in a
    )
    assert len(a) == 1


def test_has_archive_member_zip_n_delta_and_content_assertion():
    """test has_archive_member with zip n+delta with subassertion"""
    a = run_assertions(
        ARCHIVE_HAS_ARCHIVE_MEMBER_N.format(
            path=".*file.\\.txt", content_assert='<has_text_matching expression="file.\\.txt"/>', n="3", delta="1"
        ),
        ZIPBYTES,
    )
    assert len(a) == 0


def test_has_archive_member_zip_n_delta_failing_and_content_assertion():
    """test has_archive_member with zip n+delta with subassertion .. negative"""
    a = run_assertions(
        ARCHIVE_HAS_ARCHIVE_MEMBER_N.format(
            path=".*file.\\.txt", content_assert='<has_text_matching expression="file.\\.txt"/>', n="1", delta="1"
        ),
        ZIPBYTES,
    )
    assert "Expected 1+-1 matches for path '.*file.\\.txt' in archive found 4" in a
    assert len(a) == 1


def test_has_archive_member_tar_n_delta_and_content_assertion():
    """test has_archive_member with tar n+delta with subassertion"""
    a = run_assertions(
        ARCHIVE_HAS_ARCHIVE_MEMBER_N.format(
            path=".*file.\\.txt", content_assert='<has_text_matching expression="file.\\.txt"/>', n="3", delta="1"
        ),
        TARBYTES,
    )
    assert len(a) == 0


def test_has_archive_member_tar_n_delta_failing_and_content_assertion():
    """test has_archive_member with tar n+delta with subassertion .. negative"""
    a = run_assertions(
        ARCHIVE_HAS_ARCHIVE_MEMBER_N.format(
            path=".*file.\\.txt", content_assert='<has_text_matching expression="file.\\.txt"/>', n="1", delta="1"
        ),
        TARBYTES,
    )
    assert "Expected 1+-1 matches for path '.*file.\\.txt' in archive found 4" in a
    assert len(a) == 1


def test_has_archive_member_zip_min_max_and_content_assertion():
    """test has_archive_member with zip min+max with subassertion"""
    a = run_assertions(
        ARCHIVE_HAS_ARCHIVE_MEMBER_MINMAX.format(
            path=".*file.\\.txt", content_assert='<has_text_matching expression="file.\\.txt"/>', min="2", max="4"
        ),
        ZIPBYTES,
    )
    assert len(a) == 0


def test_has_archive_member_zip_min_max_failing_and_content_assertion():
    """test has_archive_member with zip min+max with subassertion .. negative"""
    a = run_assertions(
        ARCHIVE_HAS_ARCHIVE_MEMBER_MINMAX.format(
            path=".*file.\\.txt", content_assert='<has_text_matching expression="file.\\.txt"/>', min="0", max="2"
        ),
        ZIPBYTES,
    )
    assert "Expected that the number of matches for path '.*file.\\.txt' in archive is in [0:2] found 4" in a
    assert len(a) == 1


def test_has_archive_member_tar_min_max_and_content_assertion():
    """test has_archive_member with tar min+max with subassertion"""
    a = run_assertions(
        ARCHIVE_HAS_ARCHIVE_MEMBER_MINMAX.format(
            path=".*file.\\.txt", content_assert='<has_text_matching expression="file.\\.txt"/>', min="2", max="4"
        ),
        TARBYTES,
    )
    assert len(a) == 0


def test_has_archive_member_tar_min_max_failing_and_content_assertion():
    """test has_archive_member with tar min+max with subassertion .. negative"""
    a = run_assertions(
        ARCHIVE_HAS_ARCHIVE_MEMBER_MINMAX.format(
            path=".*file.\\.txt", content_assert='<has_text_matching expression="file.\\.txt"/>', min="0", max="2"
        ),
        TARBYTES,
    )
    assert "Expected that the number of matches for path '.*file.\\.txt' in archive is in [0:2] found 4" in a
    assert len(a) == 1


JSON_HAS_PROPERTY_WITH_VALUE = """
    <assert_contents>
        <has_json_property_with_value property="{property}" value="{value}" />
    </assert_contents>
"""

JSON_HAS_PROPERTY_WITH_TEXT = """
    <assert_contents>
        <has_json_property_with_text property="{property}" text="{text}" />
    </assert_contents>
"""

VALID_SIMPLE_JSON = """{"foo": 5, "list": [{"textprop": "right"}]}"""


def test_has_json_property_with_value_pos():
    """positive test for has_json_property_with_value"""
    a = run_assertions(
        JSON_HAS_PROPERTY_WITH_VALUE.format(property="foo", value="5"),
        VALID_SIMPLE_JSON,
    )
    assert len(a) == 0


def test_has_json_property_with_value_neg():
    """negative test for has_json_property_with_value"""
    a = run_assertions(
        JSON_HAS_PROPERTY_WITH_VALUE.format(property="foo", value="6"),
        VALID_SIMPLE_JSON,
    )
    assert "Failed to find property [foo] with JSON value [6]" in a
    assert len(a) == 1


def test_has_json_property_with_text_pos():
    """positive test for has_json_property_with_text"""
    a = run_assertions(
        JSON_HAS_PROPERTY_WITH_TEXT.format(property="textprop", text="right"),
        VALID_SIMPLE_JSON,
    )
    assert len(a) == 0


def test_has_json_property_with_text_neg():
    """negative test for has_json_property_with_text"""
    a = run_assertions(
        JSON_HAS_PROPERTY_WITH_TEXT.format(property="textprop", text="wrong"),
        VALID_SIMPLE_JSON,
    )
    assert "Failed to find property [textprop] with text [wrong]" in a
    assert len(a) == 1


if h5py is not None:
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        h5name = tmp.name
        with h5py.File(tmp.name, "w", locking=False) as h5fh:
            h5fh.attrs["myfileattr"] = "myfileattrvalue"
            h5fh.attrs["myfileattrint"] = 1
            dset = h5fh.create_dataset("myint", (100,), dtype="i")
            dset.attrs["myintattr"] = "myintattrvalue"
            grp = h5fh.create_group("mygroup")
            grp.attrs["mygroupattr"] = "mygroupattrvalue"
            grp.create_dataset("myfloat", (50,), dtype="f")
            dset.attrs["myfloatattr"] = "myfloatattrvalue"
    with open(h5name, "rb") as h5fh:
        H5BYTES = h5fh.read()
    os.remove(h5name)

    H5_HAS_H5_KEYS = """
        <assert_contents>
            <has_h5_keys keys="myint,mygroup,mygroup/myfloat"/>
        </assert_contents>
    """
    H5_HAS_H5_KEYS_NEGATIVE = """
        <assert_contents>
            <has_h5_keys keys="absent"/>
        </assert_contents>
    """
    H5_HAS_ATTRIBUTE = """
        <assert_contents>
            <has_h5_attribute key="myfileattr" value="myfileattrvalue" />
            <has_h5_attribute key="myfileattrint" value="1" />
        </assert_contents>
    """
    H5_HAS_ATTRIBUTE_NEGATIVE = """
        <assert_contents>
            <has_h5_attribute key="myfileattr" value="wrong" />
            <has_h5_attribute key="myfileattrint" value="also_wrong" />
        </assert_contents>
    """

    def test_has_h5_keys():
        """test has_h5_keys"""
        a = run_assertions(H5_HAS_H5_KEYS, H5BYTES)
        assert len(a) == 0

    def test_has_h5_keys_failure():
        """test has_h5_keys .. negative"""
        a = run_assertions(H5_HAS_H5_KEYS_NEGATIVE, H5BYTES)
        assert "Not a HDF5 file or H5 keys missing:\n\t['mygroup', 'mygroup/myfloat', 'myint']\n\t['absent']" in a
        assert len(a) == 1

    def test_has_h5_attribute():
        """test has_attribut"""
        a = run_assertions(H5_HAS_ATTRIBUTE, H5BYTES)
        assert len(a) == 0

    def test_has_h5_attribute_failure():
        """test has_attribute .. negative"""
        a = run_assertions(H5_HAS_ATTRIBUTE_NEGATIVE, H5BYTES)
        assert (
            "Not a HDF5 file or H5 attributes do not match:\n\t[('myfileattr', 'myfileattrvalue'), ('myfileattrint', '1')]\n\n\t(myfileattr : wrong)"
            in a
        )
        assert len(a) == 1


def run_assertions(assertion_xml: str, data, decompress=False) -> Tuple:
    assertion = parse_xml_string(assertion_xml)
    assertion_description = parse_assert_list_from_elem(assertion)
    assert assertion_description
    try:
        asserts.verify_assertions(data, assertion_description, decompress=decompress)
    except AssertionError as e:
        assert_list = e.args
    else:
        assert_list = ()
    return assert_list
