import struct
from contextlib import contextmanager

import pytest

from galaxy.datatypes.binary import (
    _read_parquet_file_metadata,
    _read_parquet_footer_metadata,
    Parquet,
)
from galaxy.datatypes.sniff import FilePrefix
from .util import (
    get_input_files,
    MockDataset,
    MockDatasetDataset,
)


def make_parquet_dataset(path):
    dataset = MockDataset(1)
    dataset.set_file_name(path)
    dataset.dataset = MockDatasetDataset(path)
    return dataset


@contextmanager
def get_parquet_dataset(filename):
    """Context manager for parquet tests requiring set_meta and set_peek."""
    with get_input_files(filename) as input_files:
        yield make_parquet_dataset(input_files[0])


def test_parquet_sniff():
    """Test that parquet correctly identifies valid parquet files."""
    parquet = Parquet()
    with get_input_files("example.parquet") as input_files:
        assert parquet.sniff_prefix(FilePrefix(input_files[0])) is True


def test_parquet_sniff_false():
    """Test that parquet returns False for non-parquet files."""
    parquet = Parquet()
    with get_input_files("1.fastq") as input_files:
        assert parquet.sniff_prefix(FilePrefix(input_files[0])) is False


def test_parquet_set_meta_reads_footer_metadata():
    parquet = Parquet()
    with get_parquet_dataset("example.parquet") as dataset:
        parquet.set_meta(dataset)
        assert dataset.metadata.column_names == ["one", "two", "three", "__index_level_0__"]
        assert dataset.metadata.columns == 4
        assert dataset.metadata.data_lines == 3


def test_parquet_set_peek():
    """Test that Parquet correctly sets the peek text."""
    parquet = Parquet()
    with get_parquet_dataset("example.parquet") as dataset:
        parquet.set_meta(dataset)
        parquet.set_peek(dataset)
        assert dataset.peek == "Parquet data"
        assert dataset.blurb is not None
        assert "4 columns" in dataset.blurb
        assert "3 lines" in dataset.blurb


def test_parquet_set_peek_with_utf8_decodable_binary(tmp_path):
    pa = pytest.importorskip("pyarrow")
    pq = pytest.importorskip("pyarrow.parquet")
    source = tmp_path / "boolean.parquet"
    pq.write_table(pa.table({"x": [True]}), source, compression=None, store_schema=False, write_statistics=False)
    # Valid UTF-8 is not sufficient to identify a text file.
    assert source.read_bytes().decode("utf-8").startswith("PAR1")
    dataset = make_parquet_dataset(str(source))

    parquet = Parquet()
    parquet.set_meta(dataset)
    parquet.set_peek(dataset)

    assert dataset.peek == "Parquet data"
    assert "1 column, 1 line" in dataset.blurb


def _varint(value):
    out = bytearray()
    while value > 127:
        out.append((value & 127) | 128)
        value >>= 7
    out.append(value)
    return bytes(out)


@pytest.mark.parametrize(
    "payload",
    [
        pytest.param(b"\x49\xf0" + _varint(2**31 - 1) + b"\x00", id="list_of_stop_elements"),
        pytest.param(b"\x4b" + _varint(2**31 - 1) + b"\x00\x00", id="map_of_stop_elements"),
        pytest.param(b"\x49\xf3" + _varint(2**31 - 1) + b"\x00", id="list_count_exceeds_payload"),
        pytest.param(b"\x15" + b"\xff" * 200_000 + b"\x00\x00", id="oversized_varint"),
        pytest.param(b"\x48" + _varint(2**30) + b"x\x00", id="string_length_exceeds_payload"),
        pytest.param(b"\x4c" + b"\x1c" * 1500 + b"\x00" * 1502, id="deeply_nested_struct"),
        pytest.param(
            b"\x15\x02\x19\xfc" + _varint(100_000) + b"\x00" * 100_000 + b"\x16\x00\x00", id="nameless_schema"
        ),
        pytest.param(b"\x15\x02\x00", id="missing_schema_and_row_count"),
        pytest.param(b"\x4f\x00", id="invalid_field_type"),
    ],
)
def test_read_parquet_file_metadata_rejects_malformed_footer(payload):
    with pytest.raises(ValueError):
        _read_parquet_file_metadata(payload)


def test_read_parquet_file_metadata_limits_decoded_values():
    unknown_list = b"\x49\xf5" + _varint(3_000_000) + b"\x00" * 3_000_000
    with pytest.raises(ValueError, match="too many values"):
        _read_parquet_file_metadata(unknown_list)


def test_parquet_set_meta_ignores_malformed_footer(tmp_path):
    payload = b"\x49\xf0" + _varint(2**31 - 1) + b"\x00"
    source = tmp_path / "malformed.parquet"
    source.write_bytes(b"PAR1" + payload + struct.pack("<I", len(payload)) + b"PAR1")
    dataset = make_parquet_dataset(str(source))

    Parquet().set_meta(dataset)

    assert not hasattr(dataset.metadata, "line_count")


def test_read_parquet_file_metadata_nested_schema(tmp_path):
    pa = pytest.importorskip("pyarrow")
    pq = pytest.importorskip("pyarrow.parquet")
    table = pa.table(
        {
            "id": pa.array([1, 2], pa.int64()),
            "point": pa.array([{"x": 1.0, "y": 2.0}, {"x": 3.0, "y": 4.0}]),
            "tags": pa.array([["a"], ["b", "c"]]),
            "attributes": pa.array([[("k", 1)], []], pa.map_(pa.string(), pa.int32())),
            "flag": pa.array([True, False]),
        }
    )
    source = tmp_path / "nested.parquet"
    pq.write_table(table, source, row_group_size=1)

    num_rows, column_names = _read_parquet_file_metadata(_read_parquet_footer_metadata(str(source)))

    assert num_rows == 2
    assert column_names == ["id", "point", "tags", "attributes", "flag"]
