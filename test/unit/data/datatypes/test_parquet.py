from contextlib import contextmanager

from galaxy.datatypes.binary import Parquet
from galaxy.datatypes.sniff import FilePrefix
from .util import (
    get_input_files,
    MockDataset,
    MockDatasetDataset,
)


@contextmanager
def get_parquet_dataset(filename):
    """Context manager for parquet tests requiring set_meta and set_peek."""
    dataset = MockDataset(1)
    with get_input_files(filename) as input_files:
        dataset.set_file_name(input_files[0])
        dataset.dataset = MockDatasetDataset(input_files[0])
        yield dataset


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
        assert dataset.metadata.column_count == 4
        assert dataset.metadata.line_count == 3


def test_parquet_set_peek():
    """Test that Parquet correctly sets the peek text."""
    parquet = Parquet()
    with get_parquet_dataset("example.parquet") as dataset:
        parquet.set_meta(dataset)
        parquet.set_peek(dataset)
        assert dataset.blurb is not None
        assert "4 columns" in dataset.blurb
        assert "3 lines" in dataset.blurb
