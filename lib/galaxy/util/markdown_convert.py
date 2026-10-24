"""Convert markdown to HTML and PDF.

Separate from ``galaxy.util.markdown`` because the formatting helpers there are
imported by ``galaxy.datatypes`` on the metadata path, and these conversions pull
in Markdown and weasyprint. Both are optional: ``galaxy-util`` does not require
either, and Galaxy itself treats weasyprint as a conditional dependency.
"""

import tempfile
from contextlib import ExitStack

from galaxy.util.resources import resource_string
from galaxy.util.sanitize_html import sanitize_html

try:
    import markdown
except ImportError:
    markdown = None  # type: ignore[assignment,unused-ignore]

# weasyprint raises OSError, not ImportError, when its system libraries are absent.
try:
    import weasyprint
except Exception:
    weasyprint = None


def weasyprint_available() -> bool:
    return weasyprint is not None


def to_html(basic_markdown: str) -> str:
    if markdown is None:
        raise ImportError("markdown is required for HTML conversion - install galaxy-util[markdown-convert]")
    # Allow data: urls so we can embed images.
    html = sanitize_html(markdown.markdown(basic_markdown, extensions=["tables"]), allow_data_urls=True)
    return html


def to_pdf_raw(basic_markdown: str, css_paths: list[str] | None = None, directory: str | None = None) -> bytes:
    """Convert RAW markdown with specified CSS paths into bytes of a PDF.

    ``directory`` is where the intermediate HTML is written; weasyprint resolves
    relative image references against it. Pass the directory holding the images,
    or leave it unset for a temporary one.
    """
    if not weasyprint_available():
        # Not an extra - see weasyprint in lib/galaxy/dependencies/conditional-requirements.txt.
        raise ImportError("weasyprint is required for PDF conversion")
    css_paths = css_paths or []
    as_html = to_html(basic_markdown)
    with ExitStack() as stack:
        if directory is None:
            directory = stack.enter_context(tempfile.TemporaryDirectory("gxmarkdown"))
        # Deleted on exit, so a caller-owned directory is left as it was.
        index = stack.enter_context(
            tempfile.NamedTemporaryFile(
                mode="w", suffix=".html", dir=directory, encoding="utf-8", errors="xmlcharrefreplace"
            )
        )
        index.write(as_html)
        index.flush()
        html = weasyprint.HTML(filename=index.name)
        stylesheets = [weasyprint.CSS(string=resource_string(__name__, "markdown_export_base.css"))]
        for css_path in css_paths:
            with open(css_path) as f:
                css_content = f.read()
            css = weasyprint.CSS(string=css_content)
            stylesheets.append(css)
        # weasyprint ships no stubs, so pin the contract here rather than return Any.
        pdf: bytes = html.write_pdf(stylesheets=stylesheets)
        return pdf
