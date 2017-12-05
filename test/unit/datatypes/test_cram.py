from galaxy.datatypes.binary import CRAM

from .util import (
    get_dataset,
    get_input_files,
)


def test_cram():
    c = CRAM()
    with get_input_files('2.cram') as input_files, get_dataset(input_files[0], index_attr='cram_index') as dataset:
        c.set_meta(dataset)
    assert dataset.metadata.cram_version == '3.0'
