import gzip

import pytest

from galaxy.datatypes.binary import Warc
from galaxy.datatypes.registry import example_datatype_registry_for_sample
from galaxy.datatypes.sniff import (
    FilePrefix,
    handle_compressed_file,
)

HTML_PAYLOAD = b"<html><head><script>alert(1)</script></head></html>"
WARC_RECORD = (
    b"WARC/1.1\r\n"
    b"WARC-Type: response\r\n"
    b"WARC-Record-ID: <urn:uuid:12345678-1234-1234-1234-123456789abc>\r\n"
    b"Content-Length: 128\r\n"
    b"\r\n" + HTML_PAYLOAD
)
FAKE_WARC = b"WARC/1.1\n<html><script>alert(1)</script>"


def _gz(tmp_path, payload: bytes) -> str:
    path = tmp_path / "upload.gz"
    path.write_bytes(gzip.compress(payload))
    return str(path)


def test_warc_serving_posture():
    assert Warc.is_binary == "maybe"
    assert Warc.get_display_behavior() == "download"
    assert Warc.is_datatype_change_allowed() is False
    assert Warc().get_mime() == "application/gzip"


@pytest.mark.parametrize(
    "payload,expected",
    [
        (WARC_RECORD, True),
        (WARC_RECORD.replace(b"\r\n", b"\n").replace(b"WARC/1.1", b"WARC/1.0"), True),
        (HTML_PAYLOAD, False),
        (b"WARC/1.1", False),
        (b"WARC/1.1\r\nWARC-Type: response\r\n\r\n" + HTML_PAYLOAD, False),
        (b"  " + WARC_RECORD, False),
        (FAKE_WARC, False),
        (WARC_RECORD.replace(b"WARC-Type:", b"X-Custom: WARC-Type:"), False),
    ],
)
def test_warc_sniff(tmp_path, payload, expected):
    assert Warc().sniff(_gz(tmp_path, payload)) is expected  # type: ignore[attr-defined]


def test_warc_auto_detected_as_keep_compressed(tmp_path):
    path = _gz(tmp_path, WARC_RECORD)
    response = handle_compressed_file(FilePrefix(path), example_datatype_registry_for_sample(), ext="auto")
    assert response.is_valid is True
    assert response.ext == "warc.gz"
    assert response.uncompressed_path == path


@pytest.mark.parametrize("payload", [HTML_PAYLOAD, FAKE_WARC])
@pytest.mark.parametrize("ext", ["auto", "warc.gz"])
def test_compressed_html_rejected(tmp_path, payload, ext):
    path = _gz(tmp_path, payload)
    response = handle_compressed_file(FilePrefix(path), example_datatype_registry_for_sample(), ext=ext)
    assert response.is_valid is False
