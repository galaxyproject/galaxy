import pytest

from galaxy.datatypes.sequence import (
    Fasta,
    FastqSanger,
    FastqSolexa,
    PearsonFasta,
)
from galaxy.datatypes.sniff import FilePrefix
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


def test_pearson_fasta_set_meta():
    b = PearsonFasta()
    with get_dataset("sequence.pearson_fasta") as dataset:
        b.set_meta(dataset=dataset)
        # the 3 leading ';' lines are not counted
        assert dataset.metadata.data_lines == 5
        assert dataset.metadata.sequences == 2


@pytest.mark.parametrize(
    "content,expected",
    [
        (b";~ fhr: 0.3\n;~ title: t\n>s1 desc\nACGT\n>s2\nGG\n", True),
        (b";LCBO - Prolactin precursor - Bovine\n>LCBO\nMDSKGSSQKGSRLLLLLVVSNLLLCQGVVS\n", True),
        (b"\n;~ a: 1\n\n;~ b: 2\n\n>s1\nACGT\n", True),
        (b";~ a: 1\r\n;~ b: 2\r\n>s1\r\nACGT\r\n", True),
        (b">s1\nACGT\n", False),  # plain FASTA
        (b";~ a: 1\n;~ b: 2\n", False),  # comments only
        (b";~ a: 1\nhello\n>s1\nACGT\n", False),  # text between comments and header
        (b";~ a: 1\n# x\n>s1\nACGT\n", False),
        (b"# x\n;~ a: 1\n>s1\nACGT\n", False),
        (b"  ;~ a: 1\n>s1\nACGT\n", False),  # ';' not in the first column
        (b";~ a: 1\n >s1\nACGT\n", False),  # '>' not in the first column
        (b";~ a: 1\n>s1\n", False),  # header without sequence
        (b";~ a: 1\n>s1\n>s2\nACGT\n", False),
        (b";~ a: 1\n>s1\nGGGAAACCC\n(((...)))\n", False),  # DotBracket
        (b";~ a: 1\n>r1\n40 40 39 38\n", False),  # qual454
        (b";~ a: 1\n>2_15_85_F3\nT2130210130123030023\n", False),  # csfasta
        (b"; zone file\n$TTL 3600\n", False),
    ],
)
def test_pearson_fasta_sniff(tmp_path, content, expected):
    path = tmp_path / "input"
    path.write_bytes(content)
    assert PearsonFasta().sniff_prefix(FilePrefix(str(path))) is expected


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
