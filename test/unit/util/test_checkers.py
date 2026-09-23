import bz2
import gzip
import lzma
import os.path
import tempfile
import zipfile

import pytest

from galaxy.util.checkers import (
    check_bz2,
    check_gzip,
    check_html,
    check_image,
    check_xz,
    check_zip,
)


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
def test_compressed_html_stays_invalid(tmp_path, suffix, check):
    path = _write_compressed(tmp_path / f"evil{suffix}", HTML_PAYLOAD)
    assert check(path, check_content=True) == (True, False)
