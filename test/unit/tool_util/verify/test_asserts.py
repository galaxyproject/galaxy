import os
import tarfile
import tempfile
import zipfile

try:
    import h5py
except ImportError:
    h5py = None
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


XML_IS_VALID_XML_ASSERTION = """
    <assert_contents>
        <is_valid_xml/>
    </assert_contents>
"""
XML_HAS_ELEMENT_WITH_PATH = """
    <assert_contents>
        <is_valid_xml/>
        <has_element_with_path path="./elem[1]/more"/>
        <has_element_with_path path="./elem[@name='foo']/more"/>
        <has_element_with_path path=".//more[@name]"/>
    </assert_contents>
"""
XML_HAS_ELEMENT_WITH_PATH = """
    <assert_contents>
        <is_valid_xml/>
        <has_element_with_path path="./elem[1]/more"/>
        <has_element_with_path path="./elem[@name='foo']/more"/>
        <has_element_with_path path=".//more[@name]"/>
    </assert_contents>
"""
XML_HAS_ELEMENT_WITH_PATH_NEGATIVE = """
    <assert_contents>
        <has_element_with_path path="./blah"/>
    </assert_contents>
"""
XML_HAS_N_ELEMENTS_WITH_PATH = """
    <assert_contents>
        <is_valid_xml/>
        <has_n_elements_with_path path="./elem" n="2"/>
        <has_n_elements_with_path path="./elem[1]/more" n="3"/>
        <has_n_elements_with_path path="./elem[@name='foo']/more" n="3"/>
        <has_n_elements_with_path path="./elem[2]/more" n="0"/>
    </assert_contents>
"""
XML_HAS_N_ELEMENTS_WITH_PATH_NEGATIVE = """
    <assert_contents>
        <is_valid_xml/>
        <has_n_elements_with_path path="./elem" n="1"/>
    </assert_contents>
"""
XML_ELEMENT_TEXT_MATCHES = """
    <assert_contents>
        <is_valid_xml/>
        <element_text_matches path="./elem/more" expression="BA(R|Z)"/>
        <element_text_matches path="./elem/more[2]" expression="BA(R|Z)"/>
    </assert_contents>
"""
XML_ELEMENT_TEXT_MATCHES_NEGATIVE = """
    <assert_contents>
        <is_valid_xml/>
        <element_text_matches path="./elem/more" expression="QU(X|Y)"/>
    </assert_contents>
"""
XML_ATTRIBUTE_MATCHES = """
    <assert_contents>
        <is_valid_xml/>
        <attribute_matches path="./elem/more" attribute="name" expression="ba(r|z)"/>
        <attribute_matches path="./elem/more[2]" attribute="name" expression="ba(r|z)"/>
    </assert_contents>
"""
XML_ATTRIBUTE_MATCHES_NEGATIVE = """
    <assert_contents>
        <is_valid_xml/>
        <attribute_matches path="./elem/more" attribute="name" expression="QU(X|Y)"/>
    </assert_contents>
"""
XML_ELEMENT_TEXT = """
    <assert_contents>
        <is_valid_xml/>
        <element_text path="{path}">
            {content_assert}
        </element_text>
    </assert_contents>
"""

VALID_XML = '''<root>
    <elem name="foo">
        <more name="bar">BAR</more>
        <more name="baz">BAZ</more>
        <more name="qux">QUX</more>
    </elem>
    <elem name="baz"/>
</root>
'''
INVALID_XML = '<root><elem name="foo"></root>'

if h5py is not None:
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        h5name = tmp.name
        with h5py.File(tmp.name, "w") as h5fh:
            h5fh.attrs['myfileattr'] = "myfileattrvalue"
            h5fh.attrs['myfileattrint'] = 1
            dset = h5fh.create_dataset("myint", (100,), dtype='i')
            dset.attrs['myintattr'] = "myintattrvalue"
            grp = h5fh.create_group("mygroup")
            grp.attrs['mygroupattr'] = "mygroupattrvalue"
            grp.create_dataset("myfloat", (50,), dtype='f')
            dset.attrs['myfloatattr'] = "myfloatattrvalue"
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

with tempfile.NamedTemporaryFile(delete=False) as ziptmp:
    zipname = ziptmp.name
    with zipfile.ZipFile(ziptmp, mode='w') as zipfh:
        for f in ["file1", "testdir/file1.txt", "testdir/file2.txt", "testdir/dir2/file1.txt"]:
            zipfh.writestr(f, f)
with open(zipname, "rb") as zfh:
    ZIPBYTES = zfh.read()
os.remove(zipname)

with tempfile.NamedTemporaryFile(delete=False) as tartmp:
    tarname = tartmp.name
    with tarfile.open(name=None, mode='w:gz', fileobj=tartmp) as tarfh:
        for f in ["file1", "testdir/file1.txt", "testdir/file2.txt", "testdir/dir2/file1.txt"]:
            with tempfile.NamedTemporaryFile("w") as tmptmp:
                tmptmpname = tmptmp.name
                tmptmp.write(f)
                tarfh.add(tmptmpname, arcname=f)
with open(tarname, "rb") as tfh:
    TARBYTES = tfh.read()
os.remove(tarname)


with tempfile.NamedTemporaryFile(mode="w", delete=False) as nonarchivetmp:
    nonarchivename = nonarchivetmp.name
    nonarchivetmp.write("some text")
with open(nonarchivename, "rb") as ntmp:
    NONARCHIVE = ntmp.read()

ARCHIVE_HAS_ARCHIVE_MEMBER = """
    <assert_contents>
        <has_archive_member path="{path}">
            {content_assert}
        </has_archive_member>
    </assert_contents>
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
        lambda x: 'Expected 3+-0 columns in output found 4' in x
    ),
    # test wrong number of columns for csv data
    (
        TABULAR_CSV_ASSERTION, TABULAR_CSV_DATA,
        lambda x: 'Expected the number of columns in output to be in [3:inf] found 2' in x
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
        lambda x: "Expected text 'test text' in output ('desired content\nis not here\n')" in x
    ),
    # test has_text with None output
    (
        TEXT_HAS_TEXT_ASSERTION, TEXT_DATA_NONE,
        lambda x: "Checking has_text assertion on empty output (None)" in x
    ),
    # test has_text with empty output
    (
        TEXT_HAS_TEXT_ASSERTION, TEXT_DATA_EMPTY,
        lambda x: "Expected text 'test text' in output ('')" in x
    ),
    # test has_text with n
    (
        TEXT_HAS_TEXT_ASSERTION_N, TEXT_DATA_HAS_TEXT_TWO,
        lambda x: len(x) == 0
    ),
    # test has_text with n .. negative test
    (
        TEXT_HAS_TEXT_ASSERTION_N, TEXT_DATA_HAS_TEXT,
        lambda x: "Expected 2+-0 occurences of 'test text' in output ('test text\n') found 1" in x
    ),
    # test has_text with n and delta
    (
        TEXT_HAS_TEXT_ASSERTION_N_DELTA, TEXT_DATA_HAS_TEXT_TWO,
        lambda x: len(x) == 0
    ),
    # test has_text with n and delta .. negative test
    (
        TEXT_HAS_TEXT_ASSERTION_N_DELTA, TEXT_DATA_HAS_TEXT,
        lambda x: "Expected 3+-1 occurences of 'test text' in output ('test text\n') found 1" in x
    ),
    # test has_text with min max
    (
        TEXT_HAS_TEXT_ASSERTION_MIN_MAX, TEXT_DATA_HAS_TEXT_TWO,
        lambda x: len(x) == 0
    ),
    # test has_text with min max .. negative test
    (
        TEXT_HAS_TEXT_ASSERTION_MIN_MAX, TEXT_DATA_HAS_TEXT,
        lambda x: "Expected that the number of occurences of 'test text' in output is in [2:4] ('test text\n') found 1" in x
    ),


    # test has_text negate
    (
        TEXT_HAS_TEXT_ASSERTION_NEGATE, TEXT_DATA_HAS_TEXT_NEG,
        lambda x: len(x) == 0
    ),
    # test has_text negate .. negative test
    (
        TEXT_HAS_TEXT_ASSERTION_NEGATE, TEXT_DATA_HAS_TEXT,
        lambda x: "Did not expect text 'test text' in output ('test text\n')" in x
    ),
    # test has_text negate with None output .. should have the same output as with negate="false"
    (
        TEXT_HAS_TEXT_ASSERTION_NEGATE, TEXT_DATA_NONE,
        lambda x: "Checking has_text assertion on empty output (None)" in x
    ),
    # test has_text negate with empty output
    (
        TEXT_HAS_TEXT_ASSERTION_NEGATE, TEXT_DATA_EMPTY,
        lambda x: len(x) == 0
    ),
    # test has_text negate with n
    (
        TEXT_HAS_TEXT_ASSERTION_N_NEGATE, TEXT_DATA_HAS_TEXT,
        lambda x: len(x) == 0
    ),
    # test has_text negate with n .. negative test
    (
        TEXT_HAS_TEXT_ASSERTION_N_NEGATE, TEXT_DATA_HAS_TEXT_TWO,
        lambda x: "Did not expect 2+-0 occurences of 'test text' in output ('test text\ntest text\n') found 2" in x
    ),
    # test has_text negate with n and delta
    (
        TEXT_HAS_TEXT_ASSERTION_N_DELTA_NEGATE, TEXT_DATA_HAS_TEXT,
        lambda x: len(x) == 0
    ),
    # test has_text negate with n and delta .. negative test
    (
        TEXT_HAS_TEXT_ASSERTION_N_DELTA_NEGATE, TEXT_DATA_HAS_TEXT_TWO,
        lambda x: "Did not expect 3+-1 occurences of 'test text' in output ('test text\ntest text\n') found 2" in x
    ),
    # test has_text negate with min max
    (
        TEXT_HAS_TEXT_ASSERTION_MIN_MAX_NEGATE, TEXT_DATA_HAS_TEXT,
        lambda x: len(x) == 0
    ),
    # test has_text negate with min max .. negative test
    (
        TEXT_HAS_TEXT_ASSERTION_MIN_MAX_NEGATE, TEXT_DATA_HAS_TEXT_TWO,
        lambda x: "Did not expect that the number of occurences of 'test text' in output is in [2:4] ('test text\ntest text\n') found 2" in x
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
        lambda x: "Expected text matching expression 'te[sx]t' in output ('desired content\nis not here\n')" in x
    ),
    # test has_text_matching with n
    (
        TEXT_HAS_TEXT_MATCHING_ASSERTION_N, TEXT_DATA_HAS_TEXT_TWO,
        lambda x: len(x) == 0
    ),
    # test has_text_matching with n .. negative test (using the test text where "te[sx]st" appears twice)
    (
        TEXT_HAS_TEXT_MATCHING_ASSERTION_N, TEXT_DATA_HAS_TEXT,
        lambda x: "Expected 4+-0 (non-overlapping) matches for 'te[sx]t' in output ('test text\n') found 2" in x
    ),
    # test has_text_matching with n
    (
        TEXT_HAS_TEXT_MATCHING_ASSERTION_MINMAX, TEXT_DATA_HAS_TEXT_TWO,
        lambda x: len(x) == 0
    ),
    # test has_text_matching with n .. negative test (using the test text where "te[sx]st" appears twice)
    (
        TEXT_HAS_TEXT_MATCHING_ASSERTION_MINMAX, TEXT_DATA_HAS_TEXT,
        lambda x: "Expected that the number of (non-overlapping) matches for 'te[sx]t' in output is in [3:5] ('test text\n') found 2" in x
    ),
    # test has_line
    (
        TEXT_HAS_LINE_ASSERTION, TEXT_DATA_HAS_TEXT,
        lambda x: len(x) == 0
    ),
    # test has_line .. negative test
    (
        TEXT_HAS_LINE_ASSERTION, TEXT_DATA_HAS_TEXT_NEG,
        lambda x: "Expected line 'test text' in output ('desired content\nis not here\n')" in x
    ),
    # test has_line with n
    (
        TEXT_HAS_LINE_ASSERTION_N, TEXT_DATA_HAS_TEXT_TWO,
        lambda x: len(x) == 0
    ),
    # test has_line with n .. negative test
    (
        TEXT_HAS_LINE_ASSERTION_N, TEXT_DATA_HAS_TEXT,
        lambda x: "Expected 2+-0 lines 'test text' in output ('test text\n') found 1" in x
    ),
    # test has_n_lines
    (
        TEXT_HAS_N_LINES_ASSERTION, TEXT_DATA_HAS_TEXT_TWO,
        lambda x: len(x) == 0
    ),
    # test has_n_lines .. negative test
    (
        TEXT_HAS_N_LINES_ASSERTION, TEXT_DATA_HAS_TEXT,
        lambda x: "Expected 2+-0 lines in the output found 1" in x
    ),
    # test has_n_lines ..delta
    (
        TEXT_HAS_N_LINES_ASSERTION_DELTA, TEXT_DATA_HAS_TEXT,
        lambda x: "Expected 3+-1 lines in the output found 1" in x
    ),
    # test has_line_matching
    (
        TEXT_HAS_LINE_MATCHING_ASSERTION, TEXT_DATA_HAS_TEXT,
        lambda x: len(x) == 0
    ),
    # test has_line_matching .. negative test
    (
        TEXT_HAS_LINE_MATCHING_ASSERTION, TEXT_DATA_HAS_TEXT_NEG,
        lambda x: "Expected line matching expression 'te[sx]t te[sx]t' in output ('desired content\nis not here\n')" in x
    ),
    # test has_line_matching n
    (
        TEXT_HAS_LINE_MATCHING_ASSERTION_N, TEXT_DATA_HAS_TEXT_TWO,
        lambda x: len(x) == 0
    ),
    # test has_line_matching n .. negative test
    (
        TEXT_HAS_LINE_MATCHING_ASSERTION_N, TEXT_DATA_HAS_TEXT,
        lambda x: "Expected 2+-0 lines matching for 'te[sx]t te[sx]t' in output ('test text\n') found 1" in x
    ),
    # test has_size
    (
        SIZE_HAS_SIZE_ASSERTION, TEXT_DATA_HAS_TEXT,
        lambda x: len(x) == 0
    ),
    # test has_size .. negative test
    (
        SIZE_HAS_SIZE_ASSERTION, TEXT_DATA_HAS_TEXT_TWO,
        lambda x: "Expected file size of 10+-0 found 20" in x
    ),
    # test has_size .. delta
    (
        SIZE_HAS_SIZE_ASSERTION_DELTA, TEXT_DATA_HAS_TEXT_TWO,
        lambda x: len(x) == 0
    ),
    # test is_valid_xml
    (
        XML_IS_VALID_XML_ASSERTION, VALID_XML,
        lambda x: len(x) == 0
    ),
    # test is_valid_xml .. negative test
    (
        XML_IS_VALID_XML_ASSERTION, INVALID_XML,
        lambda x: 'Expected valid XML, but could not parse output. Opening and ending tag mismatch: elem line 1 and root, line 1, column 31 (<string>, line 1)' in x
    ),
    # test has_element_with_path
    (
        XML_HAS_ELEMENT_WITH_PATH, VALID_XML,
        lambda x: len(x) == 0
    ),
    # test has_element_with_path .. negative test
    (
        XML_HAS_ELEMENT_WITH_PATH_NEGATIVE, VALID_XML,
        lambda x: 'Expected to find XML element matching expression ./blah, not such match was found.' in x
    ),
    # test has_n_elements_with_path
    (
        XML_HAS_N_ELEMENTS_WITH_PATH, VALID_XML,
        lambda x: len(x) == 0
    ),
    # test has_n_elements_with_path .. negative test
    (
        XML_HAS_N_ELEMENTS_WITH_PATH_NEGATIVE, VALID_XML,
        lambda x: 'Expected to find 1 elements with path ./elem, but 2 were found.' in x
    ),
    # test element_text_matches
    (
        XML_ELEMENT_TEXT_MATCHES, VALID_XML,
        lambda x: len(x) == 0
    ),
    # test element_text_matches .. negative test
    (
        XML_ELEMENT_TEXT_MATCHES_NEGATIVE, VALID_XML,
        lambda x: "Expected element with path './elem/more' to contain text matching 'QU(X|Y)', instead text 'BAR' was found." in x
    ),
    # test element_attribute_matches
    (
        XML_ATTRIBUTE_MATCHES, VALID_XML,
        lambda x: len(x) == 0
    ),
    # test element_attribute_matches .. negative test
    (
        XML_ATTRIBUTE_MATCHES_NEGATIVE, VALID_XML,
        lambda x: "Expected attribute 'name' on element with path './elem/more' to match 'QU(X|Y)', instead attribute value was 'bar'." in x
    ),
    # test element_text
    (
        XML_ELEMENT_TEXT.format(path="./elem/more", content_assert=''), VALID_XML,
        lambda x: len(x) == 0
    ),
    # test element_text .. negative
    (
        XML_ELEMENT_TEXT.format(path="./absent", content_assert=''), VALID_XML,
        lambda x: "Expected path './absent' in xml" in x
    ),
    # test element_text with sub-assertion
    (
        XML_ELEMENT_TEXT.format(path="./elem/more", content_assert='<has_text text="BAR"/>'), VALID_XML,
        lambda x: len(x) == 0
    ),
    # test element_text with sub-assertion .. negative
    (
        XML_ELEMENT_TEXT.format(path="./elem/more", content_assert='<has_text text="NOTBAR"/>'), VALID_XML,
        lambda x: "Expected text 'NOTBAR' in output ('BAR')" in x
    ),
    # test has_archive_member with zip
    (
        ARCHIVE_HAS_ARCHIVE_MEMBER.format(path="testdir/file1.txt", content_assert=""), ZIPBYTES,
        lambda x: len(x) == 0
    ),
    # test has_archive_member with tar
    (
        ARCHIVE_HAS_ARCHIVE_MEMBER.format(path="testdir/file1.txt", content_assert=""), TARBYTES,
        lambda x: len(x) == 0
    ),
    # test has_archive_member with non archive
    (
        ARCHIVE_HAS_ARCHIVE_MEMBER.format(path="irrelevant", content_assert=""), NONARCHIVE,
        lambda x: "Expected path 'irrelevant' to be an archive" in x
    ),
    # test has_archive_member with zip on absent member
    (
        ARCHIVE_HAS_ARCHIVE_MEMBER.format(path="absent", content_assert=""), ZIPBYTES,
        lambda x: "Expected path 'absent' in archive" in x
    ),
    # test has_archive_member with tar on absent member
    (
        ARCHIVE_HAS_ARCHIVE_MEMBER.format(path="absent", content_assert=""), TARBYTES,
        lambda x: "Expected path 'absent' in archive" in x
    ),
    # test has_archive_member with zip on a dir member
    (
        ARCHIVE_HAS_ARCHIVE_MEMBER.format(path="testdir/", content_assert=""), ZIPBYTES,
        lambda x: len(x) == 0
    ),
    # test has_archive_member with tar on a dir member
    (
        ARCHIVE_HAS_ARCHIVE_MEMBER.format(path="testdir/", content_assert=""), TARBYTES,
        lambda x: len(x) == 0
    ),
    # test has_archive_member with zip
    (
        ARCHIVE_HAS_ARCHIVE_MEMBER.format(path="testdir/file1.txt", content_assert='testdir/file1.txt'), ZIPBYTES,
        lambda x: len(x) == 0
    ),
    # test has_archive_member with tar
    (
        ARCHIVE_HAS_ARCHIVE_MEMBER.format(path="testdir/file1.txt", content_assert='testdir/file1.txt'), TARBYTES,
        lambda x: len(x) == 0
    ),
]

if h5py is not None:
    H5PY_TESTS = [
        # test has_h5_keys
        (
            H5_HAS_H5_KEYS, H5BYTES,
            lambda x: len(x) == 0
        ),
        # test has_h5_keys .. negative
        (
            H5_HAS_H5_KEYS_NEGATIVE, H5BYTES,
            lambda x: "Not a HDF5 file or H5 keys missing:\n\t['mygroup', 'mygroup/myfloat', 'myint']\n\t['absent']" in x
        ),
        # test has_attribute
        (
            H5_HAS_ATTRIBUTE, H5BYTES,
            lambda x: len(x) == 0
        ),
        # test has_attribute .. negative
        (
            H5_HAS_ATTRIBUTE_NEGATIVE, H5BYTES,
            lambda x: "Not a HDF5 file or H5 attributes do not match:\n\t[('myfileattr', 'myfileattrvalue'), ('myfileattrint', 1)]\n\n\t(myfileattr : wrong)" in x
        ),
    ]
    TESTS.extend(H5PY_TESTS)


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
    'has_text n delta success',
    'has_text n delta failure',
    'has_text min/max delta success',
    'has_text min/max delta failure',
    'has_text negate success',
    'has_text negate failure',
    'has_text negate None output',
    'has_text negate empty output',
    'has_text negate n success',
    'has_text negate n failure',
    'has_text negate n delta success',
    'has_text negate n delta failure',
    'has_text negate min/max delta success',
    'has_text negate min/max delta failure',
    'not_has_text success',
    'not_has_text failure',
    'not_has_text None output',
    'not_has_text empty output',
    'has_text_matching success',
    'has_text_matching failure',
    'has_text_matching n success',
    'has_text_matching n failure',
    'has_text_matching min/max success',
    'has_text_matching min/max failure',
    'has_line success',
    'has_line failure',
    'has_line n success',
    'has_line n failure',
    'has_n_lines success',
    'has_n_lines failure',
    'has_n_lines delta',
    'has_line_matching success',
    'has_line_matching failure',
    'has_line_matching n success',
    'has_line_matching n failure',
    'has_size success',
    'has_size failure',
    'has_size delta',
    'is_valid_xml success',
    'is_valid_xml failure',
    'has_element_with_path success',
    'has_element_with_path failure',
    'has_n_elements_with_path success',
    'has_n_elements_with_path failure',
    'element_text_matches sucess',
    'element_text_matches failure',
    'attribute_matches sucess',
    'attribute_matches failure',
    'element_text success',
    'element_text failure',
    'element_text with subassertion sucess',
    'element_text with subassertion failure',
    'has_archive_member zip',
    'has_archive_member tar',
    'has_archive_member non-archive',
    'has_archive_member zip absent member',
    'has_archive_member tar absent member',
    'has_archive_member zip non-file member',
    'has_archive_member tar non-file member',
    'has_archive_member zip with content assertion',
    'has_archive_member tar with content assertion',
]

if h5py is not None:
    H5PY_TEST_IDS = [
        'has_h5_keys',
        'has_h5_keys failure',
        'has_h5_attribute',
        'has_h5_attribute failure',
    ]
    TEST_IDS.extend(H5PY_TEST_IDS)


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
