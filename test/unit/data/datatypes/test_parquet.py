from contextlib import contextmanager

import pytest

from galaxy.datatypes.binary import Parquet
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
