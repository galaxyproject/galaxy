"""Test low-level Markdown to HTML conversion.

It is an external library for the most part, but given sensitivity of escaping
HTML content - best to test in insolation and verify the security of our
dependencies.
"""

from galaxy.managers.markdown_util import to_html


def test_basics():
    as_html = to_html(
        """
# My header!

My cool document. **Bold** text.

## My sub header

Less important content.
"""
    )
    assert "<h1>My header!</h1>" in as_html
    assert "<strong>Bold</strong>" in as_html


def test_indent_code_blocks():
    as_html = to_html(
        """
A Code Block Follows:

    This is code right?
    Here is another line.
"""
    )
    assert "<pre><code>This is code right?\nHere is another line." in as_html


def test_tables():
    as_html = to_html(
        """
|animal|sound|
|------|-----|
|dog   |bark |
|cat   |meow |
"""
    )
    assert "<table>" in as_html, as_html


def test_tags_escaped():
    as_html = to_html(
        """
Bad block approaches <br>

<script>window.location.href = "bad_place";</script>
"""
    )
    assert "<script>" not in as_html, as_html


def test_embed_img_tags():
    as_html = to_html(
        """
![Red dot](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAUAAAAFCAYAAACNbyblAAAAHElEQVQI12P4//8/w38GIAXDIBKE0DHxgljNBAAO9TXL0Y4OHwAAAABJRU5ErkJggg==)
"""
    )
    assert "img" in as_html, as_html
    assert "iVBORw0KGgoAAAANSUhEUgAAAAUAAA" in as_html, as_html
