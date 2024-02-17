import pysam

from galaxy.datatypes.binary import CRAM
from .util import (
    get_dataset,
    get_input_files,
)


def test_cram():
    c = CRAM()
    with get_input_files("2.cram") as input_files, get_dataset(input_files[0], index_attr="cram_index") as dataset:
        assert c.set_index_file(dataset=dataset, index_file=dataset.metadata.cram_index) is True
        c.set_meta(dataset)
        pysam.AlignmentFile(dataset.get_file_name(), index_filename=dataset.metadata.cram_index.get_file_name())
    assert dataset.metadata.cram_version == "3.0"
