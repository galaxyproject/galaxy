"""Common markdown formatting helpers for per-datatype rendering and conversion."""

import os
import shutil
import tempfile
from typing import (
    List,
    Optional,
)

from galaxy.util.resources import resource_string
from galaxy.util.sanitize_html import sanitize_html

# Optional markdown import
try:
    import markdown
except ImportError:
    markdown = None  # type: ignore[assignment,unused-ignore]

# Optional weasyprint import
try:
    import weasyprint
except ImportError:
    weasyprint = None  # type: ignore[assignment,unused-ignore]


def literal_via_fence(content):
    return "\n{}\n".format("\n".join(f"    {line}" for line in content.splitlines()))


def indicate_data_truncated():
    return "\n**Warning:** The above data has been truncated to be embedded in this document.\n\n"


def pre_formatted_contents(markdown):
    return f"<pre>{markdown}</pre>"


def markdown_available() -> bool:
    """Check if markdown library is available."""
    return markdown is not None


def weasyprint_available() -> bool:
    """Check if weasyprint library is available."""
    return weasyprint is not None


def to_html(basic_markdown: str) -> str:
    """Convert markdown to HTML.

    Args:
        basic_markdown: Markdown content to convert

    Returns:
        HTML string

    Raises:
        ImportError: If markdown library is not available
    """
    if not markdown_available():
        raise ImportError(
            "markdown library is required for HTML conversion. Install with: pip install 'galaxy-util[markdown-convert]'"
        )

    # Allow data: urls so we can embed images.
    html = sanitize_html(markdown.markdown(basic_markdown, extensions=["tables"]), allow_data_urls=True)
    return html


def to_pdf_raw(basic_markdown: str, css_paths: Optional[List[str]] = None, directory=None) -> bytes:
    """Convert markdown to PDF bytes.

    Args:
        basic_markdown: Markdown content to convert
        css_paths: Optional list of CSS file paths to apply to the PDF

    Returns:
        PDF as bytes

    Raises:
        ImportError: If markdown or weasyprint libraries are not available
    """
    if not markdown_available():
        raise ImportError(
            "markdown library is required for PDF conversion. Install with: pip install 'galaxy-util[markdown-convert]'"
        )

    if not weasyprint_available():
        raise ImportError(
            "weasyprint library is required for PDF conversion. Install with: pip install 'galaxy-util[markdown-convert]'"
        )

    css_paths = css_paths or []
    as_html = to_html(basic_markdown)
    directory_is_temp = False
    if directory is None:
        directory = tempfile.mkdtemp("gxmarkdown")
        directory_is_temp = True
    index = os.path.join(directory, "index.html")
    try:
        output_file = open(index, "w", encoding="utf-8", errors="xmlcharrefreplace")
        output_file.write(as_html)
        output_file.close()
        html = weasyprint.HTML(filename=index)
        stylesheets = [weasyprint.CSS(string=resource_string(__name__, "markdown_export_base.css"))]
        for css_path in css_paths:
            with open(css_path) as f:
                css_content = f.read()
            css = weasyprint.CSS(string=css_content)
            stylesheets.append(css)
        return html.write_pdf(stylesheets=stylesheets)
    finally:
        if directory_is_temp:
            shutil.rmtree(directory)
