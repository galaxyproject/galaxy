"""
Unit tests for base DataTypes.
.. seealso:: galaxy.datatypes.data
"""

import os

from galaxy.datatypes.anvio import AnvioStructureDB
from galaxy.datatypes.data import (
    Data,
    get_file_peek,
    zarr_v2_store_keys,
    zarr_v3_store_keys,
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


def _zarr_v3_array(shape, chunk_shape, chunk_key_encoding=None):
    metadata = {
        "node_type": "array",
        "shape": shape,
        "chunk_grid": {"name": "regular", "configuration": {"chunk_shape": chunk_shape}},
    }
    if chunk_key_encoding:
        metadata["chunk_key_encoding"] = chunk_key_encoding
    return metadata


def test_zarr_v3_store_keys_follow_consolidated_metadata():
    root = {
        "node_type": "group",
        "consolidated_metadata": {
            "metadata": {
                "group": {"node_type": "group"},
                "group/image": _zarr_v3_array([3, 4], [2, 2]),
                "scalar": _zarr_v3_array([], []),
            }
        },
    }
    metadata_keys, chunk_keys = zarr_v3_store_keys(root)
    assert metadata_keys == ["group/zarr.json", "group/image/zarr.json", "scalar/zarr.json"]
    assert chunk_keys == [
        "group/image/c/0/0",
        "group/image/c/0/1",
        "group/image/c/1/0",
        "group/image/c/1/1",
        "scalar/c",
    ]


def test_zarr_v3_store_keys_with_v2_chunk_key_encoding():
    array = _zarr_v3_array([4, 2], [2, 2], {"name": "v2", "configuration": {"separator": "."}})
    assert zarr_v3_store_keys(array) == ([], ["0.0", "1.0"])


def test_zarr_v2_store_keys_from_consolidated_metadata():
    consolidated = {
        "metadata": {
            ".zgroup": {"zarr_format": 2},
            "labels/.zarray": {"shape": [2, 3], "chunks": [1, 2]},
            "labels/.zattrs": {},
            "nested/.zarray": {"shape": [2], "chunks": [1], "dimension_separator": "/"},
            "scalar/.zarray": {"shape": [], "chunks": []},
        }
    }
    metadata_keys, chunk_keys = zarr_v2_store_keys(consolidated)
    assert metadata_keys == [".zgroup", "labels/.zarray", "labels/.zattrs", "nested/.zarray", "scalar/.zarray"]
    assert chunk_keys == ["labels/0.0", "labels/0.1", "labels/1.0", "labels/1.1", "nested/0", "nested/1", "scalar/0"]
