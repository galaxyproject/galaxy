import tempfile

from galaxy.datatypes.data import validate
from galaxy.datatypes.registry import example_datatype_registry_for_sample
from galaxy.datatypes.sniff import get_test_fname

datatypes_registry = example_datatype_registry_for_sample()


def test_fastq_validation():
    _assert_valid("fastqsanger", "1.fastqsanger")
    _assert_invalid("fastqcssanger", "1.fastqsanger")

    _assert_invalid("fastqsanger", "1.fastqcssanger")
    _assert_valid("fastqcssanger", "1.fastqcssanger")


def test_bam_validation():
    _assert_valid("bam", "1.bam")
    _assert_invalid("bam", "1.qname_sorted.bam")
    _assert_invalid("bam", "3unsorted.bam")

    _assert_valid("qname_sorted.bam", "1.qname_sorted.bam")

    _assert_invalid("qname_sorted.bam", "3unsorted.bam")
    _assert_valid("unsorted.bam", "3unsorted.bam")


def test_vcf_validation():
    _assert_valid("vcf", "1.vcf")
    _assert_invalid("vcf", _truncate("1.vcf", bytes=30))


def _truncate(file_name, bytes=10):
    o = tempfile.NamedTemporaryFile(delete=False)
    with open(get_test_fname(file_name), "rb") as f:
        contents = f.read()
        o.write(contents[0:-bytes])
    return o.name


def _assert_invalid(extension, file_name):
    validation = _run_validation(extension, file_name)
    assert validation.state == "invalid", validation


def _assert_valid(extension, file_name):
    validation = _run_validation(extension, file_name)
    assert validation.state == "ok", validation


def _run_validation(extension, file_name):
    datatype = datatypes_registry.datatypes_by_extension[extension]
    validation = validate(MockDataset(get_test_fname(file_name), datatype))  # type: ignore[arg-type]
    return validation


class MockDataset:
    def __init__(self, file_name, datatype):
        self.file_name_ = file_name
        self.datatype = datatype

    def get_file_name(self, sync_cache=True):
        return self.file_name_
