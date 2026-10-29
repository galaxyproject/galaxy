import struct
import tempfile

import pytest
from bx.seq.twobit import TWOBIT_MAGIC_NUMBER

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


def _twobit(order="<", version=0):
    """Rebuild 1.twobit (little-endian, version 0) with the given byte order and version."""
    with open(get_test_fname("1.twobit"), "rb") as f:
        data = f.read()
    count = struct.unpack_from("<L", data, 8)[0]
    names, pos = [], 16
    for _ in range(count):
        end = pos + 1 + data[pos]
        names.append(data[pos:end])
        pos = end + 4
    records = []
    for _ in range(count):
        dna_size, n_blocks = struct.unpack_from("<LL", data, pos)
        ints = list(struct.unpack_from(f"<{2 + 2 * n_blocks}L", data, pos))
        pos += 4 * len(ints)
        mask_blocks = struct.unpack_from("<L", data, pos)[0]
        ints += struct.unpack_from(f"<{2 + 2 * mask_blocks}L", data, pos)
        pos += 4 * (2 + 2 * mask_blocks)
        dna = data[pos : pos + (dna_size + 3) // 4]
        pos += len(dna)
        records.append(struct.pack(f"{order}{len(ints)}L", *ints) + dna)
    offset_format = f"{order}Q" if version == 1 else f"{order}L"
    offset = 16 + sum(len(name) + struct.calcsize(offset_format) for name in names)
    index = b""
    for name, record in zip(names, records):
        index += name + struct.pack(offset_format, offset)
        offset += len(record)
    return struct.pack(f"{order}LLLL", TWOBIT_MAGIC_NUMBER, version, count, 0) + index + b"".join(records)


TWOBIT = _twobit()


@pytest.mark.parametrize("order", ["<", ">"])
@pytest.mark.parametrize("version", [0, 1])
def test_twobit_validation(order, version):
    content = _twobit(order, version)
    _assert_valid("twobit", _bytes(content))
    _assert_invalid("twobit", _bytes(content[:-1]), "TwoBit file is truncated")


@pytest.mark.parametrize(
    "content,message",
    [
        pytest.param(b"", "TwoBit file is 0 bytes", id="empty"),
        pytest.param(b"\0" * 4 + TWOBIT[4:], "magic number not found", id="bad-magic"),
        pytest.param(TWOBIT[:4] + struct.pack("<L", 2) + TWOBIT[8:], "Unsupported TwoBit version 2", id="version-2"),
        pytest.param(TWOBIT[:8] + struct.pack("<L", 0) + TWOBIT[12:], "holds no sequences", id="no-sequences"),
        pytest.param(TWOBIT[:20], "index is truncated", id="index-truncated"),
        pytest.param(TWOBIT[:40], "points past the end", id="offset-past-end"),
        pytest.param(TWOBIT[:80], "record is truncated", id="record-header-truncated"),
        pytest.param(TWOBIT[:-3], "TwoBit file is truncated", id="dna-truncated"),
    ],
)
def test_twobit_validation_rejects(content, message):
    _assert_invalid("twobit", _bytes(content), message)


def test_lav_validation():
    _assert_valid("lav", "alignment.lav")
    _assert_invalid("lav", _truncate("alignment.lav", bytes=8), "does not end with '#:eof'")
    _assert_invalid("lav", _bytes(b""), "does not start with '#:lav'")
    _assert_invalid("lav", "alignment.axt", "does not start with '#:lav'")


def _bytes(content):
    with tempfile.NamedTemporaryFile(delete=False) as o:
        o.write(content)
    return o.name


def _truncate(file_name, bytes=10):
    o = tempfile.NamedTemporaryFile(delete=False)
    with open(get_test_fname(file_name), "rb") as f:
        contents = f.read()
        o.write(contents[0:-bytes])
    return o.name


def _assert_invalid(extension, file_name, message=None):
    validation = _run_validation(extension, file_name)
    assert validation.state == "invalid", validation
    if message is not None:
        assert message in validation.message, validation


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

    def get_file_name(self, sync_cache=True, auth=None):
        return self.file_name_
