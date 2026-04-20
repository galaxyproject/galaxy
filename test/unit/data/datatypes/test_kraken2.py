import pytest

from galaxy.datatypes.binary import Kraken2DatabaseArchive
from .util import (
    get_input_files,
    MockDataset,
    MockDatasetDataset,
)

@pytest.mark.parametrize(
        "kraken2db_loader, input_file",
        [Kraken2DatabaseArchive, "1.kraken2db.tar.gz"]
)
def test_kraken2dbarchive_sniff(kraken2db_loader, input_file):
    loader = kraken2db_loader()
    with get_input_files(input_file) as input_files:
        assert loader.sniff(input_files[0]) is True


@pytest.mark.parametrize(
        "kraken2db_loader, input_file",
        [Kraken2DatabaseArchive, "1.kraken2db.tar.gz"]
)
def test_kraken2dbarchive_set_peek(kraken2db_loader, input_file):
    loader = kraken2db_loader()
    with get_input_files(input_file) as input_files:
        dataset = MockDataset(1)
        dataset.set_file_name(input_files[0])
        dataset.dataset = MockDatasetDataset(dataset.get_file_name())
        loader.set_peek(dataset)
        assert dataset.peek == loader.peek_text
