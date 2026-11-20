import json
import os
import subprocess
import sys

import pytest

from galaxy.datatypes.sequence import (
    Fasta,
    FastqSanger,
    FastqSolexa,
)
from galaxy.util import galaxy_directory
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
    def __init__(self, file_name, sequences=None, fqtoc=None):
        self.file_name = file_name
        self.metadata = Bunch(sequences=sequences)
        self.copied_from_library_dataset_dataset_association = None
        self.fqtoc = fqtoc

    def get_file_name(self):
        return self.file_name

    def get_converted_files_by_type(self, type):
        return self.fqtoc if type == "fqtoc" else None


def _split_and_extract(tmp_path, input_dataset, parts):
    part_dirs = []

    def new_dir():
        part_dir = tmp_path / f"task_{len(part_dirs)}"
        part_dir.mkdir()
        part_dirs.append(part_dir)
        return str(part_dir)

    FastqSanger.split([input_dataset], new_dir, {"split_mode": "number_of_parts", "split_size": parts})
    name = os.path.basename(input_dataset.get_file_name())
    output = []
    for part_dir in part_dirs:
        with open(part_dir / f"split_info_{name}.json") as f:
            FastqSanger.process_split_file(json.load(f))
        output.append((part_dir / name).read_text())
    return output


READS = [f"@read{i}\nACGT\n+\nIIII\n" for i in range(10)]


@pytest.mark.parametrize("sequences_metadata", [10, None])
@pytest.mark.parametrize("parts", [3, 4, 12])
def test_fastq_split_number_of_parts_keeps_every_read(tmp_path, sequences_metadata, parts):
    input_file = tmp_path / "input.fastqsanger"
    input_file.write_text("".join(READS))
    output = _split_and_extract(tmp_path, _SplitDataset(str(input_file), sequences=sequences_metadata), parts)
    assert len(output) == min(parts, len(READS))
    assert "".join(output) == "".join(READS)


@pytest.mark.parametrize("legacy_float_count", [False, True])
@pytest.mark.parametrize("parts", [1, 4])
def test_fastq_split_with_fqtoc(tmp_path, legacy_float_count, parts):
    input_file = tmp_path / "input.fastqsanger"
    input_file.write_text("".join(READS))
    toc_file = tmp_path / "input.fqtoc"
    if legacy_float_count:
        # what fastq_to_fqtoc.py used to write
        end = input_file.stat().st_size
        toc_file.write_text(f'{{"sections" : [{{"start":"0","end":"{end}","sequences":"10.0"}}]}}\n')
    else:
        converter = os.path.join(galaxy_directory(), "lib/galaxy/datatypes/converters/fastq_to_fqtoc.py")
        subprocess.check_call([sys.executable, converter, str(input_file), str(toc_file)])
    toc = _SplitDataset(str(toc_file))
    output = _split_and_extract(tmp_path, _SplitDataset(str(input_file), sequences=10, fqtoc=toc), parts)
    assert len(output) == parts
    assert "".join(output) == "".join(READS)
