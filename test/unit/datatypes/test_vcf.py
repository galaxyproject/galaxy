import pysam

from galaxy.datatypes.tabular import (
    Vcf,
    VcfGz,
)
from .util import (
    get_dataset,
    get_input_files,
)


def test_vcf_sniff():
    vcf = Vcf()
    vcf_gz = VcfGz()
    with get_input_files('1.vcf_bgzip', '1.vcf') as input_files:
        compressed, uncompressed = input_files
        assert vcf_gz.sniff(compressed) is True
        assert vcf_gz.sniff(uncompressed) is False
        assert vcf.sniff(compressed) is False
        assert vcf.sniff(uncompressed) is True


def test_vcf_gz_set_meta():
    vcf_gz = VcfGz()
    with get_input_files('1.vcf_bgzip') as input_files, get_dataset(input_files[0], index_attr='tabix_index') as dataset:
        vcf_gz.set_meta(dataset)
        f = pysam.VariantFile(dataset.file_name, index_filename=dataset.metadata.tabix_index.file_name)
        assert isinstance(f.index, pysam.libcbcf.TabixIndex) is True
