"""
Unit tests for base DataTypes.
.. seealso:: galaxy.datatypes.data
"""

from galaxy.datatypes.data import get_file_peek


def test_get_file_peek( ):
    # should get the first 5 lines of the file without a trailing newline character
    assert get_file_peek('test-data/1.tabular', line_wrap=False) == 'chr22\t1000\tNM_17\nchr22\t2000\tNM_18\nchr10\t2200\tNM_10\nchr10\thap\ttest\nchr10\t1200\tNM_11'
