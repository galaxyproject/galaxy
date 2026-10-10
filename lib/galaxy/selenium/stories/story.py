"""Document model for collecting screenshots and narration into a story.

Usable from tests, standalone scripts and notebooks.
"""

import logging
import os
import zipfile
from abc import (
    ABC,
    abstractmethod,
)
from html import escape
from typing import (
    Literal,
    TypedDict,
)
from urllib.parse import quote

from galaxy.util.markdown_convert import (
    to_html,
    to_pdf_raw,
    weasyprint_available,
)

log = logging.getLogger(__name__)

ElementType = Literal["documentation", "screenshot"]


class ElementMetadata(TypedDict, total=False):
    caption: str


# (type, content, metadata) - content is a screenshot path or a markdown fragment.
StoryElement = tuple[ElementType, str, ElementMetadata]

HTML_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{title}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            line-height: 1.6;
        }}
        img {{
            max-width: 100%;
            height: auto;
            border: 1px solid #ddd;
            border-radius: 4px;
            margin: 10px 0;
        }}
        h1 {{
            color: #333;
            border-bottom: 2px solid #007bff;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #555;
            margin-top: 30px;
        }}
    </style>
</head>
<body>
{body}
</body>
</html>"""


def _escape_alt(text: str) -> str:
    """Backslash-escape what would end markdown image alt text early."""
    return text.replace("\\", "\\\\").replace("[", "\\[").replace("]", "\\]")


class StoryBase(ABC):
    """Interface shared by :class:`Story` and the null object :class:`NoopStory`."""

    @property
    @abstractmethod
    def enabled(self) -> bool:
        """Whether anything is actually being collected."""

    @property
    @abstractmethod
    def output_directory(self) -> str:
        """Directory story artifacts are written to."""

    @abstractmethod
    def screenshot_path(self, label: str, extension: str = ".png") -> str | None:
        """Reserve the next numbered screenshot path, or None when not collecting."""

    @abstractmethod
    def add_screenshot(self, screenshot_path: str, caption: str) -> None:
        """Record a screenshot already written to disk."""

    @abstractmethod
    def add_documentation(self, markdown_content: str) -> None:
        """Record a markdown fragment."""

    @abstractmethod
    def reset(self) -> None:
        """Discard everything collected so far, for a test retry."""

    @abstractmethod
    def finalize(self) -> None:
        """Write the story out."""


class Story(StoryBase):
    """Collects screenshots and narration, then writes them out as one document."""

    def __init__(self, title: str, description: str, output_directory: str) -> None:
        self.title = title
        self.description = description
        self._output_directory = output_directory
        self.elements: list[StoryElement] = []
        self._screenshot_counter = 0

    @property
    def enabled(self) -> bool:
        return True

    @property
    def output_directory(self) -> str:
        return self._output_directory

    def screenshot_path(self, label: str, extension: str = ".png") -> str:
        path = os.path.join(self.output_directory, f"{self._screenshot_counter:03d}_{label}{extension}")
        self._screenshot_counter += 1
        return path

    def add_screenshot(self, screenshot_path: str, caption: str) -> None:
        element_meta: ElementMetadata = {"caption": caption}
        self.elements.append(("screenshot", screenshot_path, element_meta))

    def add_documentation(self, markdown_content: str) -> None:
        self.elements.append(("documentation", markdown_content, {}))

    def reset(self) -> None:
        self.elements = []
        self._screenshot_counter = 0

    def finalize(self) -> None:
        """Write story.md, story.html, story.pdf and a sibling zip of the directory."""
        markdown_content = self._generate_markdown()
        with open(os.path.join(self.output_directory, "story.md"), "w", encoding="utf-8") as f:
            f.write(markdown_content)

        with open(os.path.join(self.output_directory, "story.html"), "w", encoding="utf-8") as f:
            # to_html sanitizes the body; the title bypasses it, so escape it here.
            f.write(HTML_TEMPLATE.format(title=escape(self.title), body=to_html(markdown_content)))

        self._generate_pdf(markdown_content, os.path.join(self.output_directory, "story.pdf"))

        zip_path = os.path.join(
            os.path.dirname(self.output_directory), f"{os.path.basename(self.output_directory)}.zip"
        )
        self._create_zip(zip_path)

    def _generate_markdown(self) -> str:
        lines = [f"# {self.title}\n"]
        if self.description:
            lines.append(self.description.strip())
            lines.append("\n")

        for element_type, content, metadata in self.elements:
            if element_type == "screenshot":
                caption = metadata.get("caption", "")
                # Reference by basename so the document stays valid inside the zip.
                lines.append(f"## {caption}\n")
                lines.append(f"![{_escape_alt(caption)}]({quote(os.path.basename(content))})\n")
            else:
                lines.append(content)
                lines.append("\n")

        return "\n".join(lines)

    def _generate_pdf(self, markdown_content: str, output_path: str) -> None:
        """Write the PDF, or skip it - weasyprint needs system libraries that are often absent."""
        if not weasyprint_available():
            log.info("weasyprint not available, skipping PDF generation for story %s", self.title)
            return
        try:
            # Render from the story directory so relative image references resolve.
            pdf_bytes = to_pdf_raw(markdown_content, directory=self.output_directory)
        except Exception:
            log.warning("Failed to generate PDF for story %s", self.title, exc_info=True)
            return
        with open(output_path, "wb") as f:
            f.write(pdf_bytes)

    def _create_zip(self, zip_path: str) -> None:
        """Archive documents and referenced screenshots, excluding discarded retries."""
        referenced = dict.fromkeys(
            os.path.basename(content) for element_type, content, _ in self.elements if element_type == "screenshot"
        )
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for name in ["story.md", "story.html", "story.pdf", *referenced]:
                path = os.path.join(self.output_directory, name)
                if os.path.exists(path):
                    zipf.write(path, name)


class NoopStory(StoryBase):
    """Null object used when story generation is off, so callers need no conditionals."""

    @property
    def enabled(self) -> bool:
        return False

    @property
    def output_directory(self) -> str:
        return ""

    def screenshot_path(self, label: str, extension: str = ".png") -> str | None:
        return None

    def add_screenshot(self, screenshot_path: str, caption: str) -> None:
        pass

    def add_documentation(self, markdown_content: str) -> None:
        pass

    def reset(self) -> None:
        pass

    def finalize(self) -> None:
        pass
