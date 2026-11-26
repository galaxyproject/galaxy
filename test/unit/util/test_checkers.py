import bz2
import gzip
import io
import lzma
import os.path
import tarfile
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
    is_zip,
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


def _zip_bytes(members=(("record", b"content\n"),)) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        for name, data in members:
            zf.writestr(name, data)
    return buffer.getvalue()


def _tar_ending_in_zip() -> bytes:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w") as tf:
        for name, data in (("first.txt", b"first\n"), ("inner.zip", _zip_bytes())):
            info = tarfile.TarInfo(name)
            info.size = len(data)
            tf.addfile(info, io.BytesIO(data))
    return buffer.getvalue()


@pytest.mark.parametrize(
    "content,expected",
    [
        (_zip_bytes(), True),
        (_zip_bytes(members=()), True),
        (b"#!/usr/bin/env python3\n" + _zip_bytes(), False),
        (_tar_ending_in_zip(), False),
        (b"PK\x03\x04 not an archive", False),
    ],
    ids=["zip", "empty_zip", "zip_with_prepended_data", "tar_ending_in_zip", "zip_magic_only"],
)
def test_is_zip_requires_archive_at_start_of_file(tmp_path, content, expected):
    path = tmp_path / "candidate"
    path.write_bytes(content)
    assert is_zip(str(path)) is expected
