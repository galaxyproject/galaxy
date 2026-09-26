from contextlib import contextmanager

from galaxy.datatypes.proteomics import (
    MzSpecLibJson,
    MzSpecLibTxt,
)
from galaxy.datatypes.sniff import FilePrefix
from .util import (
    get_input_files,
    MockDataset,
    MockDatasetDataset,
)


@contextmanager
def get_mzspeclib_dataset(filename):
    """Context manager for mzspeclib tests requiring set_meta and set_peek."""
    dataset = MockDataset(1)
    with get_input_files(filename) as input_files:
        dataset.set_file_name(input_files[0])
        dataset.dataset = MockDatasetDataset(input_files[0])
        yield dataset


def test_mzspeclibjson_sniff():
    """Test that MzSpecLibJson correctly identifies valid mzSpeclib JSON files."""
    mzspeclibjson = MzSpecLibJson()
    with get_input_files("test.mzspeclib.json") as input_files:
        assert mzspeclibjson.sniff_prefix(FilePrefix(input_files[0])) is True


def test_mzspeclibjson_sniff_false():
    """Test that MzSpecLibJson returns False for non-JSON files."""
    mzspeclibjson = MzSpecLibJson()
    with get_input_files("test.mzspeclib.txt") as input_files:
        assert mzspeclibjson.sniff_prefix(FilePrefix(input_files[0])) is False


def test_mzspeclibjson_set_meta():
    """Test that MzSpecLibJson correctly sets metadata including spectra count."""
    mzspeclibjson = MzSpecLibJson()
    with get_mzspeclib_dataset("test.mzspeclib.json") as dataset:
        mzspeclibjson.set_meta(dataset)
        assert dataset.metadata.spectra_count == 2


def test_mzspeclibjson_set_peek():
    """Test that MzSpecLibJson correctly sets the peek text."""
    mzspeclibjson = MzSpecLibJson()
    with get_mzspeclib_dataset("test.mzspeclib.json") as dataset:
        mzspeclibjson.set_meta(dataset)
        mzspeclibjson.set_peek(dataset)
        assert dataset.peek is not None
        assert "format_version" in dataset.peek
        assert "2 spectra" in dataset.blurb


def test_mzspeclibtxt_sniff():
    """Test that MzSpecLibTxt correctly identifies valid mzSpeclib TXT files."""
    mzspeclibtxt = MzSpecLibTxt()
    with get_input_files("test.mzspeclib.txt") as input_files:
        assert mzspeclibtxt.sniff_prefix(FilePrefix(input_files[0])) is True


def test_mzspeclibtxt_sniff_false():
    """Test that MzSpecLibTxt returns False for non-TXT files."""
    mzspeclibtxt = MzSpecLibTxt()
    with get_input_files("test.mzspeclib.json") as input_files:
        assert mzspeclibtxt.sniff_prefix(FilePrefix(input_files[0])) is False


def test_mzspeclibtxt_set_meta():
    """Test that MzSpecLibTxt correctly sets metadata including spectra count."""
    mzspeclibtxt = MzSpecLibTxt()
    with get_mzspeclib_dataset("test.mzspeclib.txt") as dataset:
        mzspeclibtxt.set_meta(dataset)
        assert dataset.metadata.spectra_count == 2


def test_mzspeclibtxt_set_peek():
    """Test that MzSpecLibTxt correctly sets the peek text."""
    mzspeclibtxt = MzSpecLibTxt()
    with get_mzspeclib_dataset("test.mzspeclib.txt") as dataset:
        mzspeclibtxt.set_meta(dataset)
        mzspeclibtxt.set_peek(dataset)
        assert dataset.peek is not None
        assert "<mzSpecLib>" in dataset.peek
        assert "2 spectra" in dataset.blurb
