import os.path
import tempfile

from galaxy.util.checkers import (
    check_html,
    check_image,
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
        path = f"test-data/{filename}"
        assert os.path.exists(path)
        assert check_image(path) is expected
