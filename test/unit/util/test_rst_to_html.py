from concurrent.futures import ThreadPoolExecutor

from galaxy.util.rst_to_html import rst_to_html


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
