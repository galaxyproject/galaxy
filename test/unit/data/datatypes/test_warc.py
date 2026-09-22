import gzip

from galaxy.datatypes.binary import Warc
from galaxy.datatypes.registry import example_datatype_registry_for_sample
from galaxy.datatypes.sniff import (
    FilePrefix,
    handle_compressed_file,
)

HTML_PAYLOAD = b"<html><head><script>alert(1)</script></head></html>"


def _warc_record():
    return (
        b"WARC/1.1\r\n"
        b"WARC-Type: response\r\n"
        b"WARC-Record-ID: <urn:uuid:12345678-1234-1234-1234-123456789abc>\r\n"
        b"Content-Length: 128\r\n"
        b"\r\n" + HTML_PAYLOAD
    )


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
