import pysam

from galaxy.datatypes.converters.interval_to_tabix_converter import to_tabix
from ..util import (
    get_input_files,
    get_tmp_path,
)


def test_to_tabix():
    with get_input_files("1.vcf") as input_files:
        with get_tmp_path(suffix=".tbi") as index:
            bgzip_fname = to_tabix(input_files[0], index, preset="vcf")
            f = pysam.TabixFile(bgzip_fname, index=index)
            f.close()
