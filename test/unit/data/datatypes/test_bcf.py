from galaxy.datatypes.binary import (
    Bcf,
    BcfUncompressed,
)
from .util import (
    get_dataset,
    get_input_files,
)


def test_bcf_sniff():
    bcf = Bcf()
    bcfu = BcfUncompressed()
    with get_input_files("1.bcf", "1.bcf_uncompressed") as input_files:
        compressed, uncompressed = input_files
        assert bcf.sniff(compressed) is True
        assert bcf.sniff(uncompressed) is False
        assert bcfu.sniff(compressed) is False
        assert bcfu.sniff(uncompressed) is True


def test_bcf_set_meta():
    bcf = Bcf()
    with get_input_files("1.bcf") as input_files, get_dataset(input_files[0], index_attr="bcf_index") as dataset:
        bcf.set_meta(dataset)
