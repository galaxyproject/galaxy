import bz2
import gzip
import lzma
import os.path
import tempfile
import zipfile

import pytest

from galaxy.datatypes.binary import Warc
from galaxy.datatypes.registry import example_datatype_registry_for_sample
from galaxy.datatypes.sniff import (
    FilePrefix,
    handle_compressed_file,
)
from galaxy.util.checkers import (
    check_bz2,
    check_gzip,
    check_html,
    check_image,
    check_xz,
    check_zip,
)
from galaxy.util.warc import is_warc_chunk


def test_check_html():
    html_text = '<p>\n<a href="url">Link</a>\n</p>\n'
    assert check_html(html_text, file_path=False)
    # Test a non-HTML binary string
    assert not check_html(b"No HTML here\nSecond line\n", file_path=False)
    with tempfile.NamedTemporaryFile(mode="w") as tmp:
        tmp.write(html_text)
        tmp.flush()
        assert check_html(tmp.name)
    # Test a non-UTF8 binary file
    with tempfile.NamedTemporaryFile(mode="wb") as tmpb:
        tmpb.write(b"\x1f\x8b")
        tmpb.flush()
        assert not check_html(tmpb.name)


def test_check_image():
    for filename, expected in (("1.tiff", True), ("454Score.png", True), ("1.bam", False)):
        path = os.path.join("test-data", filename)
        assert os.path.exists(path)
        assert check_image(path) is expected


HTML_PAYLOAD = b"<html><head><script>alert(1)</script></head></html>"


def _warc_record():
    return (
        b"WARC/1.1\r\n"
        b"WARC-Type: response\r\n"
        b"WARC-Record-ID: <urn:uuid:12345678-1234-1234-1234-123456789abc>\r\n"
        b"Content-Length: 128\r\n"
        b"\r\n" + HTML_PAYLOAD
    )


def test_is_warc_chunk():
    assert is_warc_chunk(_warc_record())
    assert is_warc_chunk(_warc_record().replace(b"\r\n", b"\n").replace(b"WARC/1.1", b"WARC/1.0"))
    assert not is_warc_chunk(None)
    assert not is_warc_chunk(b"")
    assert not is_warc_chunk(b"WARC/1.1")
    assert not is_warc_chunk(b"WARC/1.1\r\nWARC-Type: response\r\n\r\n" + HTML_PAYLOAD)
    assert not is_warc_chunk(b"  " + _warc_record())
    assert not is_warc_chunk(b"WARC/1.1\n<html><script>alert(1)</script>")
    spoofed = _warc_record().replace(b"WARC-Type:", b"X-Custom: WARC-Type:")
    assert not is_warc_chunk(spoofed)


def _write_compressed(path, payload: bytes):
    suffix = path.suffix
    if suffix == ".gz":
        path.write_bytes(gzip.compress(payload))
    elif suffix == ".bz2":
        path.write_bytes(bz2.compress(payload))
    elif suffix == ".xz":
        path.write_bytes(lzma.compress(payload))
    elif suffix == ".zip":
        with zipfile.ZipFile(path, "w") as zf:
            zf.writestr("record", payload)
    else:
        raise AssertionError(suffix)
    return str(path)


@pytest.mark.parametrize(
    "suffix,check",
    [(".gz", check_gzip), (".bz2", check_bz2), (".xz", check_xz), (".zip", check_zip)],
)
def test_compressed_warc_with_html_stays_valid(tmp_path, suffix, check):
    path = _write_compressed(tmp_path / f"record{suffix}", _warc_record())
    assert check(path, check_content=True) == (True, True)


@pytest.mark.parametrize(
    "suffix,check",
    [(".gz", check_gzip), (".bz2", check_bz2), (".xz", check_xz), (".zip", check_zip)],
)
def test_compressed_html_stays_invalid(tmp_path, suffix, check):
    path = _write_compressed(tmp_path / f"evil{suffix}", HTML_PAYLOAD)
    assert check(path, check_content=True) == (True, False)


def test_compressed_fake_warc_header_stays_invalid(tmp_path):
    fake = b"WARC/1.1\n<html><script>alert(1)</script>"
    path = tmp_path / "fake.gz"
    path.write_bytes(gzip.compress(fake))
    assert check_gzip(str(path), check_content=True) == (True, False)


def test_warc_sniff(tmp_path):
    assert Warc.is_binary == "maybe"
    assert Warc.get_display_behavior() == "download"
    assert Warc.is_datatype_change_allowed() is False
    assert Warc().get_mime() == "application/gzip"

    warc_gz = tmp_path / "record.gz"
    warc_gz.write_bytes(gzip.compress(_warc_record()))
    html_gz = tmp_path / "evil.gz"
    html_gz.write_bytes(gzip.compress(HTML_PAYLOAD))
    assert Warc().sniff(str(warc_gz)) is True  # type: ignore[attr-defined]
    assert Warc().sniff(str(html_gz)) is False  # type: ignore[attr-defined]


def test_warc_auto_detected_as_keep_compressed(tmp_path):
    datatypes_registry = example_datatype_registry_for_sample()
    path = tmp_path / "record.gz"
    path.write_bytes(gzip.compress(_warc_record()))
    response = handle_compressed_file(FilePrefix(str(path)), datatypes_registry, ext="auto")
    assert response.is_valid is True
    assert response.ext == "warc.gz"
    assert response.uncompressed_path == str(path)
