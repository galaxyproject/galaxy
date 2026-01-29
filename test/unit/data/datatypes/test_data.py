"""
Unit tests for base DataTypes.
.. seealso:: galaxy.datatypes.data
"""

import os

from galaxy.datatypes.anvio import AnvioStructureDB
from galaxy.datatypes.data import (
    Data,
    get_file_peek,
)
from galaxy.datatypes.interval import (
    Bed,
    BedStrict,
)
from galaxy.util import galaxy_directory


def test_get_file_peek():
    # should get the first 5 lines of the file without a trailing newline character
    assert (
        get_file_peek(os.path.join(galaxy_directory(), "test-data/1.tabular"), line_wrap=False)
        == "chr22\t1000\tNM_17\nchr22\t2000\tNM_18\nchr10\t2200\tNM_10\nchr10\thap\ttest\nchr10\t1200\tNM_11\n"
    )


def test_is_datatype_change_allowed():
    # By default is_datatype_change_allowed() is True if the datatype is not composite
    assert Data.is_datatype_change_allowed()
    assert Bed.is_datatype_change_allowed()
    # AnvioStructureDB is a subclass of a composite datatype
    assert AnvioStructureDB.is_datatype_change_allowed() is False
    # BedStrict explictly disallows datatype change with `allow_datatype_change = False`
    assert BedStrict.is_datatype_change_allowed() is False
