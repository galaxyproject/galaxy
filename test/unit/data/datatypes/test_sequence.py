from galaxy.datatypes.sequence import Fasta, FastqSanger, FastqSolexa
from .util import (
    get_dataset,
)


def test_fasta_set_meta():
    b = Fasta()
    with get_dataset("1.fasta") as dataset:
        b.set_meta(dataset=dataset)
        assert dataset.metadata.data_lines == 2
        assert dataset.metadata.sequences == 1


def test_fastagz_set_meta():
    b = Fasta()
    with get_dataset("1.fasta.gz") as dataset:
        b.set_meta(dataset=dataset)
        assert dataset.metadata.data_lines == 2
        assert dataset.metadata.sequences == 1


def test_fastqsanger_set_meta():
    b = FastqSanger()
    with get_dataset("1.fastqsanger") as dataset:
        b.set_meta(dataset=dataset)
        assert dataset.metadata.data_lines == 8
        assert dataset.metadata.sequences == 2


def test_fastqsangergz_set_meta():
    b = FastqSanger()
    with get_dataset("1.fastqsanger.gz") as dataset:
        b.set_meta(dataset=dataset)
        assert dataset.metadata.data_lines == 8
        assert dataset.metadata.sequences == 2


def test_fastqsangerbz2_set_meta():
    b = FastqSanger()
    with get_dataset("1.fastqsanger.bz2") as dataset:
        b.set_meta(dataset=dataset)
        assert dataset.metadata.data_lines == 8
        assert dataset.metadata.sequences == 2


def test_fastqsolexa_set_meta():
    b = FastqSolexa()
    with get_dataset("1.fastqsolexa") as dataset:
        b.set_meta(dataset=dataset)
        assert dataset.metadata.data_lines == 8
        assert dataset.metadata.sequences == 2
