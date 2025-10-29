"""General-purpose story builder for collecting screenshots and documentation.

This module provides the Story class for creating narrative documentation with
interleaved screenshots and markdown content. It's independent of any test
framework and can be used in tests, Jupyter notebooks, or standalone scripts.
"""

import os
import zipfile
from abc import (
    ABC,
    abstractmethod,
)

from galaxy.util.markdown import (
    to_html,
    to_pdf_raw,
    weasyprint_available,
)

# Type for story elements: (type, content, metadata)
StoryElement = tuple[str, str, dict[str, str]]


class StoryProtocol(ABC):
    """Protocol for story implementations (real or noop)."""

    @property
    @abstractmethod
    def enabled(self) -> bool:
        """Whether story generation is enabled."""

    @property
    @abstractmethod
    def output_directory(self) -> str:
        """Output directory for story artifacts."""

    @property
    @abstractmethod
    def screenshot_counter(self) -> int:
        """Current screenshot counter."""

    @screenshot_counter.setter
    @abstractmethod
    def screenshot_counter(self, value: int):
        """Set screenshot counter."""

    @abstractmethod
    def add_screenshot(self, screenshot_path: str, caption: str):
        """Add a screenshot to the story."""

    @abstractmethod
    def add_documentation(self, markdown_content: str):
        """Add markdown documentation to the story."""

    @abstractmethod
    def reset(self):
        """Reset story state."""

    @abstractmethod
    def finalize(self):
        """Generate final story artifacts."""


class Story(StoryProtocol):
    """General-purpose story builder for collecting screenshots and documentation.

    This class is independent of any test framework and can be used in various
    contexts (tests, Jupyter notebooks for tutorials, user documentation, etc.).
    """

    def __init__(self, title: str, description: str, output_directory: str):
        """Initialize a new story.

        Args:
            title: Story title (used as H1 heading)
            description: Story description (first paragraph after title)
            output_directory: Directory where story artifacts will be saved
        """
        self.title = title
        self.description = description
        self._output_directory = output_directory
        self.elements: list[StoryElement] = []  # List of (type, content, metadata) tuples
        self._screenshot_counter = 0

    @property
    def enabled(self) -> bool:
        """Story generation is enabled for Story instances."""
        return True

    @property
    def output_directory(self) -> str:
        """Output directory for story artifacts."""
        return self._output_directory

    @property
    def screenshot_counter(self) -> int:
        """Current screenshot counter."""
        return self._screenshot_counter

    @screenshot_counter.setter
    def screenshot_counter(self, value: int):
        """Set screenshot counter."""
        self._screenshot_counter = value

    def add_screenshot(self, screenshot_path: str, caption: str):
        """Add a screenshot to the story.

        Args:
            screenshot_path: Absolute path to screenshot file
            caption: Caption for the screenshot (used as heading and alt text)
        """
        self.elements.append(("screenshot", screenshot_path, {"caption": caption}))

    def add_documentation(self, markdown_content: str):
        """Add markdown documentation to the story.

        Args:
            markdown_content: Markdown-formatted content to append
        """
        self.elements.append(("documentation", markdown_content, {}))

    def reset(self):
        """Reset story state for test retry.

        Clears all collected screenshots and documentation, resets counters.
        Used when a test is retried after failure to avoid accumulating content
        from failed attempts.
        """
        self.elements = []
        self._screenshot_counter = 0

    def finalize(self):
        """Generate final story artifacts (markdown, HTML, PDF, zip).

        Creates:
        - story.md: Markdown source with embedded screenshots
        - story.html: Self-contained HTML with embedded images
        - story.pdf: PDF version (if weasyprint available)
        - {output_directory}.zip: Zip archive of all artifacts
        """
        # 1. Generate markdown file
        markdown_content = self._generate_markdown()
        markdown_path = os.path.join(self.output_directory, "story.md")
        with open(markdown_path, "w") as f:
            f.write(markdown_content)

        # 2. Generate HTML file
        html_content = self._generate_html(markdown_content)
        html_path = os.path.join(self.output_directory, "story.html")
        with open(html_path, "w") as f:
            f.write(html_content)

        # 3. Generate PDF file
        pdf_path = os.path.join(self.output_directory, "story.pdf")
        self._generate_pdf(markdown_content, pdf_path)

        # 4. Create zip archive
        zip_path = os.path.join(
            os.path.dirname(self.output_directory), f"{os.path.basename(self.output_directory)}.zip"
        )
        self._create_zip(zip_path)

    def _generate_markdown(self) -> str:
        """Generate markdown content for the story."""
        lines = []

        # Title
        lines.append(f"# {self.title}\n")

        # Description as first paragraph
        if self.description:
            lines.append(self.description.strip())
            lines.append("\n")

        # Interleave screenshots and documentation
        for element_type, content, metadata in self.elements:
            if element_type == "screenshot":
                screenshot_path = content
                caption = metadata.get("caption", "")
                # Use relative path for markdown
                rel_path = os.path.basename(screenshot_path)
                lines.append(f"## {caption}\n")
                lines.append(f"![{caption}]({rel_path})\n")
            elif element_type == "documentation":
                lines.append(content)
                lines.append("\n")

        return "\n".join(lines)

    def _generate_html(self, markdown_content: str) -> str:
        """Generate HTML from markdown."""
        html_body = to_html(markdown_content)

        # Wrap in basic HTML structure with styling
        html_template = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{self.title}</title>
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
{html_body}
</body>
</html>"""

        return html_template

    def _generate_pdf(self, markdown_content: str, output_path: str):
        """Generate PDF from markdown using weasyprint.

        Degrades gracefully if weasyprint is not available.
        """
        try:
            if not weasyprint_available():
                print("Warning: weasyprint not available, skipping PDF generation")
                return

            pdf_bytes = to_pdf_raw(markdown_content, directory=self.output_directory)
            with open(output_path, "wb") as f:
                f.write(pdf_bytes)
        except Exception as e:
            print(f"Warning: Failed to generate PDF: {e}")
            # Non-fatal - we still have markdown and HTML

    def _create_zip(self, zip_path: str):
        """Create zip archive of story directory."""
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            # Walk the output directory
            for root, _dirs, files in os.walk(self.output_directory):
                for file in files:
                    file_path = os.path.join(root, file)
                    # Add to zip with relative path
                    arcname = os.path.relpath(file_path, self.output_directory)
                    zipf.write(file_path, arcname)


class NoopStory(StoryProtocol):
    """No-op story implementation for when story generation is disabled.

    Implements the StoryProtocol interface but does nothing. Used as a null
    object to avoid conditional checks throughout the codebase.
    """

    def __init__(self):
        """Initialize noop story."""
        self._screenshot_counter = 0

    @property
    def enabled(self) -> bool:
        """Story generation is disabled for NoopStory instances."""
        return False

    @property
    def output_directory(self) -> str:
        """Return empty string for noop story."""
        return ""

    @property
    def screenshot_counter(self) -> int:
        """Return counter (unused but required by protocol)."""
        return self._screenshot_counter

    @screenshot_counter.setter
    def screenshot_counter(self, value: int):
        """Set counter (no-op but required by protocol)."""
        self._screenshot_counter = value

    def add_screenshot(self, screenshot_path: str, caption: str):
        """No-op: screenshot not added to story."""
        pass

    def add_documentation(self, markdown_content: str):
        """No-op: documentation not added to story."""
        pass

    def reset(self):
        """No-op: nothing to reset."""
        pass

    def finalize(self):
        """No-op: no artifacts to generate."""
        pass
