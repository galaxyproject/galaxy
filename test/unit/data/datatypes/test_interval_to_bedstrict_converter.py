import os
import subprocess
import sys

import pytest

from galaxy.util import galaxy_directory

CONVERTER = os.path.join(galaxy_directory(), "lib/galaxy/datatypes/converters/interval_to_bedstrict_converter.py")

BED12 = (
    "chr1\t100\t500\tgeneA\t0\t.\t150\t450\t0\t2\t100,100,\t0,300,\n"
    "chr1\t600\t900\tgeneB\t0\t-\t650\t850\t0\t1\t300,\t0,\n"
)


def convert(tmp_path, content, extension, force_num_columns=None):
    input_file = tmp_path / f"input.{extension}"
    input_file.write_text(content)
    output_file = tmp_path / "output.bed"
    args = [sys.executable, CONVERTER, str(output_file), str(input_file), "1", "2", "3", "6", "4", extension]
    if force_num_columns is not None:
        args.append(str(force_num_columns))
    subprocess.check_call(args, stdout=subprocess.DEVNULL)
    return output_file.read_text()


@pytest.mark.parametrize("extension,force_num_columns", [("bed", None), ("bed12", 12)])
def test_unstranded_bed12_keeps_strand_and_blocks(tmp_path, extension, force_num_columns):
    assert convert(tmp_path, BED12, extension, force_num_columns) == BED12


def test_unstranded_bed6(tmp_path):
    bed6 = "chr1\t100\t500\tpeak1\t10\t.\nchr2\t5\t50\tpeak2\t20\t+\n"
    assert convert(tmp_path, bed6, "bed6", 6) == bed6
