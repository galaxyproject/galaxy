"""
Unit tests for base DataTypes.
.. seealso:: galaxy.datatypes.data
"""

import os
from types import SimpleNamespace
from typing import (
    Any,
    cast,
)

import pytest

from galaxy.datatypes.anvio import AnvioStructureDB
from galaxy.datatypes.data import (
    Data,
    Directory,
    get_file_peek,
    get_params_and_input_name,
    zarr_v2_store_keys,
    zarr_v3_store_keys,
    ZarrDirectory,
)
from galaxy.datatypes.interval import (
    Bed,
    BedStrict,
)
from galaxy.util import galaxy_directory


@pytest.mark.parametrize(
    "resource_context",
    [None, {"__job_resource__select": "no"}, {"__job_resource__select": "yes", "processors": 4}],
)
def test_converter_parameters_with_resource_conditional(resource_context):
    dependency = object()
    converter = SimpleNamespace(
        inputs={
            "source": SimpleNamespace(name="source", type="data"),
            "index": SimpleNamespace(name="index", type="data"),
            "optional": SimpleNamespace(name="optional", type="text", optional=True),
            "required": SimpleNamespace(name="required", type="text", optional=False),
            # Input groups have a name and type but no optional attribute.
            "__job_resource": SimpleNamespace(name="__job_resource", type="conditional"),
        }
    )
    context = None
    expected = {"index": dependency, "optional": None}
    if resource_context is not None:
        context = {
            "__job_resource": resource_context,
            "__target_datatype__": "bam",
            "analysis_parameter": "not a converter parameter",
        }
        expected.update({"__job_resource": resource_context, "__target_datatype__": "bam"})

    params, input_name = get_params_and_input_name(converter, {"index": dependency}, context)

    assert input_name == "source"
    assert params == expected


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


def _zarr_v3_array(
    shape: list[int], chunk_shape: list[int], chunk_key_encoding: dict[str, Any] | None = None
) -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "node_type": "array",
        "shape": shape,
        "chunk_grid": {"name": "regular", "configuration": {"chunk_shape": chunk_shape}},
    }
    if chunk_key_encoding:
        metadata["chunk_key_encoding"] = chunk_key_encoding
    return metadata


def test_zarr_v3_store_keys_follow_consolidated_metadata() -> None:
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
    assert list(chunk_keys) == [
        "group/image/c/0/0",
        "group/image/c/0/1",
        "group/image/c/1/0",
        "group/image/c/1/1",
        "scalar/c",
    ]


def test_zarr_v3_store_keys_with_v2_chunk_key_encoding() -> None:
    array = _zarr_v3_array([4, 2], [2, 2], {"name": "v2", "configuration": {"separator": "."}})
    metadata_keys, chunk_keys = zarr_v3_store_keys(array)
    assert metadata_keys == []
    assert list(chunk_keys) == ["0.0", "1.0"]


def test_zarr_v2_store_keys_from_consolidated_metadata() -> None:
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
    assert list(chunk_keys) == [
        "labels/0.0",
        "labels/0.1",
        "labels/1.0",
        "labels/1.1",
        "nested/0",
        "nested/1",
        "scalar/0",
    ]


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


def _zarr_dataset(extra_files_path, **metadata):
    metadata = {"store_root": None, "zarr_format": None, **metadata}
    return SimpleNamespace(extra_files_path=str(extra_files_path), metadata=SimpleNamespace(**metadata))


def test_zarr_set_meta_records_an_empty_store_root_for_a_store_at_the_root(tmp_path):
    (tmp_path / ".zgroup").write_text('{"zarr_format": 2}')
    dataset = _zarr_dataset(tmp_path)

    ZarrDirectory().set_meta(dataset)

    assert dataset.metadata.store_root == ""
    assert dataset.metadata.zarr_format == 2


def test_zarr_set_meta_leaves_a_wrapped_store_in_place_and_records_it(tmp_path):
    # Metadata is also set on existing datasets, whose files may be shared and are not moved.
    (tmp_path / "wrapped.zarr").mkdir()
    (tmp_path / "wrapped.zarr" / ".zgroup").write_text('{"zarr_format": 2}')
    dataset = _zarr_dataset(tmp_path)

    ZarrDirectory().set_meta(dataset)

    assert os.listdir(tmp_path) == ["wrapped.zarr"]
    assert dataset.metadata.store_root == "wrapped.zarr"
    assert dataset.metadata.zarr_format == 2
    assert ZarrDirectory().content_path(dataset) == str(tmp_path / "wrapped.zarr")


def test_zarr_content_path_stays_inside_the_dataset(tmp_path):
    dataset = _zarr_dataset(tmp_path, store_root="../elsewhere")

    with pytest.raises(ValueError, match="outside"):
        ZarrDirectory().content_path(dataset)


@pytest.mark.parametrize("store_root", ["Bob's store (1).zarr", "..sample.zarr", "...zarr"])
def test_zarr_content_path_of_a_store_named_after_an_upload(tmp_path, store_root):
    # Older datasets record whatever folder name they were uploaded with.
    dataset = _zarr_dataset(tmp_path, store_root=store_root)

    assert ZarrDirectory().content_path(dataset) == str(tmp_path / store_root)


@pytest.mark.parametrize("store_root", ["/etc", "..", "a/../..", "../elsewhere"])
def test_zarr_content_path_rejects_a_store_root_outside_the_dataset(tmp_path, store_root):
    with pytest.raises(ValueError, match="outside"):
        ZarrDirectory().content_path(_zarr_dataset(tmp_path, store_root=store_root))


@pytest.mark.parametrize("store_root", ["link", "link/sub"])
def test_zarr_content_path_rejects_a_store_root_through_a_link_outside(tmp_path, store_root):
    outside = tmp_path / "outside"
    (outside / "sub").mkdir(parents=True)
    extra_files = tmp_path / "extra_files"
    extra_files.mkdir()
    (extra_files / "link").symlink_to(outside)

    with pytest.raises(ValueError, match="outside"):
        ZarrDirectory().content_path(_zarr_dataset(extra_files, store_root=store_root))


def test_zarr_content_path_accepts_a_link_inside_the_dataset(tmp_path):
    (tmp_path / "store.zarr").mkdir()
    (tmp_path / "link").symlink_to(tmp_path / "store.zarr")

    assert ZarrDirectory().content_path(_zarr_dataset(tmp_path, store_root="link")) == str(tmp_path / "link")


def test_zarr_preview_of_a_store_root_outside_the_dataset_falls_back(tmp_path, monkeypatch):
    (tmp_path / ".zgroup").write_text('{"zarr_format": 2}')
    monkeypatch.setattr(Data, "display_data", lambda self, *args, **kwargs: "default display")

    result = ZarrDirectory().display_data(
        cast(Any, None), _zarr_dataset(tmp_path, store_root="../elsewhere"), preview=True
    )

    assert result == "default display"


def test_zarr_set_meta_does_not_record_a_symlinked_wrapper(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / ".zgroup").write_text('{"zarr_format": 2}')
    extra_files = tmp_path / "extra_files"
    extra_files.mkdir()
    (extra_files / "wrapped.zarr").symlink_to(outside)
    dataset = _zarr_dataset(extra_files)

    ZarrDirectory().set_meta(dataset)

    assert dataset.metadata.store_root == ""
    assert ZarrDirectory().content_path(dataset) == str(extra_files)


def test_directory_content_path_is_the_extra_files_path(tmp_path):
    dataset = SimpleNamespace(extra_files_path=str(tmp_path), metadata=SimpleNamespace())

    assert Directory().content_path(dataset) == str(tmp_path)
    assert Directory().content_path(dataset, "/compute/dataset_1_files") == "/compute/dataset_1_files"


def test_directory_without_content_root_does_not_list_the_folder(tmp_path, monkeypatch):
    (tmp_path / "wrapped").mkdir()

    def fail_listdir(path):
        raise AssertionError(f"listed {path}")

    monkeypatch.setattr(os, "listdir", fail_listdir)

    assert Directory().content_wrapper_name(str(tmp_path)) is None
