from concurrent.futures import ThreadPoolExecutor

import pytest

from galaxy.util.rst_to_html import rst_to_html

FILE_MARKER = "rst-file-insertion-marker"


def test_rst_to_html_basic():
    html = rst_to_html("**bold**")
    assert "<strong>bold</strong>" in html


def test_rst_to_html_concurrent_conversions():
    documents = [f"Section {i}\n=========={'=' * len(str(i))}\n\nParagraph *{i}* with ``code``.\n" for i in range(50)]
    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(rst_to_html, documents))
    for i, html in enumerate(results):
        assert f"Section {i}" in html
        assert f"<em>{i}</em>" in html


@pytest.fixture
def marker_file(tmp_path):
    path = tmp_path / "marker.txt"
    path.write_text(FILE_MARKER)
    return path


@pytest.mark.parametrize(
    "directive",
    [
        ".. include:: {path}\n",
        ".. raw:: html\n   :file: {path}\n",
        ".. csv-table:: Table\n   :file: {path}\n",
    ],
)
def test_rst_to_html_file_insertion_disabled(marker_file, directive):
    assert FILE_MARKER not in rst_to_html(directive.format(path=marker_file))


def test_rst_to_html_inline_csv_table():
    html = rst_to_html('.. csv-table:: Table\n   :header: "a", "b"\n\n   "1", "2"\n')
    assert "<table" in html
    assert "<td>2</td>" in html
