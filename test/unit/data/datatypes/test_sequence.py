import json

import pytest

from galaxy.datatypes.sequence import (
    Fasta,
    FastqSanger,
    FastqSolexa,
)
from galaxy.util.bunch import Bunch
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


class _SplitDataset:
    def __init__(self, file_name, sequences):
        self.file_name = file_name
        self.metadata = Bunch(sequences=sequences)
        self.copied_from_library_dataset_dataset_association = None

    def get_file_name(self):
        return self.file_name

    def get_converted_files_by_type(self, type):
        return None


@pytest.mark.parametrize("sequences_metadata", [10, None])
@pytest.mark.parametrize("parts", [3, 4, 12])
def test_fastq_split_number_of_parts_keeps_every_read(tmp_path, sequences_metadata, parts):
    reads = [f"@read{i}\nACGT\n+\nIIII\n" for i in range(10)]
    input_file = tmp_path / "input.fastqsanger"
    input_file.write_text("".join(reads))
    part_dirs = []

    def new_dir():
        part_dir = tmp_path / f"task_{len(part_dirs)}"
        part_dir.mkdir()
        part_dirs.append(part_dir)
        return str(part_dir)

    FastqSanger.split(
        [_SplitDataset(str(input_file), sequences_metadata)],
        new_dir,
        {"split_mode": "number_of_parts", "split_size": parts},
    )
    assert len(part_dirs) == min(parts, len(reads))
    output = ""
    for part_dir in part_dirs:
        with open(part_dir / "split_info_input.fastqsanger.json") as f:
            FastqSanger.process_split_file(json.load(f))
        output += (part_dir / "input.fastqsanger").read_text()
    assert output == "".join(reads)
