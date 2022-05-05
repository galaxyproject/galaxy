import os

import pysam

from galaxy.datatypes.binary import CRAM
from .util import (
    get_dataset,
    get_input_files,
)


def test_cram():
    c = CRAM()
    with get_input_files("2.cram") as input_files, get_dataset(input_files[0], index_attr="cram_index") as dataset:
        assert os.path.exists(dataset.metadata_.cram_index.file_name) is False
        c.set_index_file(dataset=dataset, index_file=dataset.metadata_.cram_index)
        assert os.path.exists(dataset.metadata_.cram_index.file_name) is True
        c.set_meta(dataset)
        pysam.AlignmentFile(dataset.file_name, index_filename=dataset.metadata_.cram_index.file_name)
    assert dataset.metadata_.cram_version == "3.0"
