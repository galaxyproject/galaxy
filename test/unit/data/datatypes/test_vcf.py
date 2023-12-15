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
    vcf_datatype = Vcf()
    vcf_bgzip_datatype = VcfGz()
    with get_input_files("1.vcf_bgzip", "1.vcf", "vcf_gzipped.vcf.gz") as input_files:
        vcf_bgzip, uncompressed, compressed = input_files
        assert vcf_bgzip_datatype.sniff(vcf_bgzip) is True
        assert vcf_bgzip_datatype.sniff(uncompressed) is False
        assert vcf_bgzip_datatype.sniff(compressed) is False
        assert vcf_datatype.sniff(vcf_bgzip) is False
        assert vcf_datatype.sniff(uncompressed) is True
        # Cannot sniff the vcf.gz file as vcf directly, works only when
        # auto_decompress is enabled


def test_vcf_bgzip_set_meta():
    vcf_bgzip_datatype = VcfGz()
    with get_input_files("1.vcf_bgzip") as input_files, get_dataset(
        input_files[0], index_attr="tabix_index"
    ) as dataset:
        vcf_bgzip_datatype.set_meta(dataset)
        f = pysam.VariantFile(dataset.get_file_name(), index_filename=dataset.metadata.tabix_index.get_file_name())
        assert isinstance(f.index, pysam.libcbcf.TabixIndex) is True
