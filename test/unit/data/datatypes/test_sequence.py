import pytest

from galaxy.datatypes.sequence import (
    Fasta,
    FastqSanger,
    FastqSolexa,
)
from .util import (
    get_dataset,
    MockDatasetDataset,
)


@pytest.mark.parametrize(
    "input_file",
    [
        "1.fasta",
        "1.fasta.gz",
    ],
)
def test_fasta_set_meta(input_file):
    b = Fasta()
    with get_dataset("1.fasta") as dataset:
        b.set_meta(dataset=dataset)
        assert dataset.metadata.data_lines == 2
        assert dataset.metadata.sequences == 1


@pytest.mark.parametrize(
    "fastq_type,input_file",
    [
        [FastqSanger, "1.fastqsanger"],
        [FastqSanger, "1.fastqsanger.gz"],
        [FastqSanger, "1.fastqsanger.bz2"],
        [FastqSolexa, "1.fastqssolexa"],
    ],
)
def test_fastqsanger_set_meta(fastq_type, input_file):
    b = fastq_type()
    with get_dataset("1.fastqsanger") as dataset:
        dataset.dataset = MockDatasetDataset(dataset.get_file_name())
        b.set_meta(dataset=dataset)
        assert dataset.metadata.data_lines == 8
        assert dataset.metadata.sequences == 2
