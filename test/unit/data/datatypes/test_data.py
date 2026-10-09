"""
Unit tests for base DataTypes.
.. seealso:: galaxy.datatypes.data
"""

import os

from galaxy.datatypes.anvio import AnvioStructureDB
from galaxy.datatypes.data import (
    Data,
    Directory,
    get_file_peek,
    ZarrDirectory,
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


class MarkedDirectory(Directory):
    """A directory datatype whose content root holds a MARKER file."""

    def is_content_root(self, path):
        return os.path.isfile(os.path.join(path, "MARKER"))


def test_groom_moves_wrapped_content_to_the_root(tmp_path):
    (tmp_path / "wrapper" / "data").mkdir(parents=True)
    (tmp_path / "wrapper" / "MARKER").write_text("")

    MarkedDirectory().groom_directory_content(str(tmp_path))

    assert sorted(os.listdir(tmp_path)) == ["MARKER", "data"]


def test_groom_leaves_content_already_at_the_root(tmp_path):
    (tmp_path / "MARKER").write_text("")
    (tmp_path / "data").mkdir()

    MarkedDirectory().groom_directory_content(str(tmp_path))

    assert sorted(os.listdir(tmp_path)) == ["MARKER", "data"]


def test_groom_leaves_a_plain_directory_alone(tmp_path):
    (tmp_path / "nested").mkdir()
    (tmp_path / "nested" / "MARKER").write_text("")

    Directory().groom_directory_content(str(tmp_path))

    assert os.listdir(tmp_path) == ["nested"]


def test_groom_leaves_a_symlinked_wrapper_alone(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "MARKER").write_text("")
    extra_files = tmp_path / "extra_files"
    extra_files.mkdir()
    (extra_files / "wrapper").symlink_to(outside)

    MarkedDirectory().groom_directory_content(str(extra_files))

    assert os.listdir(extra_files) == ["wrapper"]
    assert os.listdir(outside) == ["MARKER"]


def test_zarr_store_metadata_marks_its_content_root(tmp_path):
    (tmp_path / "wrapped.zarr" / "0").mkdir(parents=True)
    (tmp_path / "wrapped.zarr" / ".zgroup").write_text('{"zarr_format": 2}')

    ZarrDirectory().groom_directory_content(str(tmp_path))

    assert sorted(os.listdir(tmp_path)) == [".zgroup", "0"]


def test_zarr_format_version_ignores_non_object_metadata(tmp_path):
    (tmp_path / ".zgroup").write_text("[1, 2]")

    assert ZarrDirectory()._get_format_version(str(tmp_path)) is None
