"""General-purpose story builder for collecting screenshots and documentation.

This module provides the Story class for creating narrative documentation with
interleaved screenshots and markdown content. It's independent of any test
framework and can be used in tests, Jupyter notebooks, or standalone scripts.
"""

import os
import re
import zipfile
from abc import (
    ABC,
    abstractmethod,
)
from typing import (
    Any,
    Literal,
    Optional,
    TypedDict,
)

from galaxy.util.markdown import (
    to_html,
    to_pdf_raw,
    weasyprint_available,
)

# Type aliases for stronger typing
ElementType = Literal["documentation", "screenshot"]
SectionMode = Literal["replace", "append", "standalone"]

# Type for story elements: (type, content, metadata)
StoryElement = tuple[ElementType, str, "ElementMetadata"]


class SectionMetadata(TypedDict):
    """Metadata for a story section."""

    title: str
    anchor: str
    level: int
    skip: bool
    start_index: Optional[int]


class SectionMetadataInput(TypedDict):
    """Input metadata when creating a section (before enrichment)."""

    title: str
    anchor: str


class ElementMetadata(TypedDict, total=False):
    """Metadata for story elements."""

    caption: str
    section_start: str


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

    @abstractmethod
    def _begin_section(self, meta: SectionMetadataInput) -> None:
        """Start tracking a new section."""

    @abstractmethod
    def _end_section(self) -> None:
        """Finish tracking current section."""


class Story(StoryProtocol):
    """General-purpose story builder for collecting screenshots and documentation.

    This class is independent of any test framework and can be used in various
    contexts (tests, Jupyter notebooks for tutorials, user documentation, etc.).
    """

    def __init__(
        self,
        title: str,
        description: str,
        output_directory: str,
        only_sections: Optional[set[str]] = None,
        skip_sections: Optional[set[str]] = None,
        merge_target: Optional[str] = None,
        section_mode: SectionMode = "standalone",
    ):
        """Initialize a new story.

        Args:
            title: Story title (used as H1 heading)
            description: Story description (first paragraph after title)
            output_directory: Directory where story artifacts will be saved
            only_sections: Optional set of section anchors to include (exclude all others)
            skip_sections: Optional set of section anchors to skip
            merge_target: Path to existing markdown to merge sections into
            section_mode: How to handle sections: 'replace', 'append', or 'standalone'
        """
        self.title = title
        self.description = description
        self._output_directory = output_directory
        self.elements: list[StoryElement] = []
        self._screenshot_counter = 0

        # Section tracking
        self.section_stack: list[SectionMetadata] = []
        self.section_elements: dict[str, list[StoryElement]] = {}
        self.only_sections: Optional[set[str]] = only_sections
        self.skip_sections: Optional[set[str]] = skip_sections
        self.merge_target: Optional[str] = merge_target
        self.section_mode: SectionMode = section_mode
        self._filtering_active: bool = False

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
        if self._filtering_active:
            return  # Skip if in filtered-out section
        element_meta: ElementMetadata = {"caption": caption}
        self.elements.append(("screenshot", screenshot_path, element_meta))

    def add_documentation(self, markdown_content: str):
        """Add markdown documentation to the story.

        Args:
            markdown_content: Markdown-formatted content to append
        """
        if self._filtering_active:
            return  # Skip if in filtered-out section
        self.elements.append(("documentation", markdown_content, {}))

    def _begin_section(self, meta: SectionMetadataInput) -> None:
        """Start tracking a new section with filtering support."""
        anchor = meta["anchor"]

        # Determine if this section should be included
        should_skip = False
        if self.only_sections and anchor not in self.only_sections:
            should_skip = True
        if self.skip_sections and anchor in self.skip_sections:
            should_skip = True

        # Calculate level: 2 (H2) + current depth
        level = 2 + len(self.section_stack)

        # Create enriched metadata
        enriched: SectionMetadata = {
            "title": meta["title"],
            "anchor": anchor,
            "level": level,
            "skip": should_skip,
            "start_index": None if should_skip else len(self.elements),
        }

        if should_skip:
            self._filtering_active = True
        else:
            # Add section header
            heading = f"{'#' * level} {enriched['title']}"
            anchor_html = f'<a id="{anchor}"></a>'
            element_meta: ElementMetadata = {"section_start": anchor}
            self.elements.append(("documentation", f"{anchor_html}\n{heading}\n", element_meta))

        self.section_stack.append(enriched)

    def _end_section(self) -> None:
        """Finish tracking current section with filtering support."""
        if not self.section_stack:
            return

        meta = self.section_stack.pop()

        if meta["skip"]:
            # Update filtering state based on remaining stack
            self._filtering_active = len(self.section_stack) > 0 and any(s["skip"] for s in self.section_stack)
            return

        # Store section elements
        anchor = meta["anchor"]
        start = meta["start_index"]

        if start is None:
            return

        end = len(self.elements)
        self.section_elements[anchor] = self.elements[start:end].copy()

        # Update filtering state based on remaining stack
        self._filtering_active = len(self.section_stack) > 0 and any(s["skip"] for s in self.section_stack)

    def reset(self):
        """Reset story state for test retry.

        Clears all collected screenshots and documentation, resets counters.
        Used when a test is retried after failure to avoid accumulating content
        from failed attempts.
        """
        self.elements = []
        self._screenshot_counter = 0
        self.section_stack = []
        self.section_elements = {}
        self._filtering_active = False

    def finalize(self):
        """Generate final story artifacts (markdown, HTML, PDF, zip).

        Creates:
        - story.md: Markdown source with embedded screenshots
        - story.html: Self-contained HTML with embedded images
        - story.pdf: PDF version (if weasyprint available)
        - {output_directory}.zip: Zip archive of all artifacts

        If merge_target is set, merges sections into existing markdown before generation.
        """
        # Merge sections into existing document if requested
        if self.merge_target and os.path.exists(self.merge_target):
            self._merge_sections(self.merge_target)

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

    def _extract_sections_from_markdown(self, markdown_path: str) -> dict[str, list[str]]:
        """Parse existing markdown and extract sections by anchor.

        Returns a dict mapping anchor -> list of lines for that section.
        Also includes a special '__preamble__' key for content before first section.
        """
        with open(markdown_path) as f:
            content = f.read()

        sections: dict[str, list[str]] = {}
        current_anchor: Optional[str] = None
        current_lines: list[str] = []
        preamble_lines: list[str] = []

        for line in content.split("\n"):
            # Look for anchor tags: <a id="anchor_name"></a>
            if '<a id="' in line:
                # Save previous section if any
                if current_anchor:
                    sections[current_anchor] = current_lines
                elif current_lines and not any(sections.values()):
                    # This is preamble content (before first section)
                    preamble_lines = current_lines

                # Extract anchor from line
                match = re.search(r'<a id="([^"]+)">', line)
                current_anchor = match.group(1) if match else None
                current_lines = [line]
            elif current_anchor:
                current_lines.append(line)
            else:
                # Before any section
                preamble_lines.append(line)

        # Save last section
        if current_anchor and current_lines:
            sections[current_anchor] = current_lines

        # Save preamble if we have it
        if preamble_lines:
            sections["__preamble__"] = preamble_lines

        return sections

    def _elements_to_markdown(self, elements: list[StoryElement]) -> str:
        """Convert elements list to markdown string."""
        parts: list[str] = []
        for element_type, content, metadata in elements:
            if element_type == "documentation":
                parts.append(content)
            elif element_type == "screenshot":
                caption = metadata.get("caption", "")
                parts.append(f"## {caption}\n\n![{caption}]({os.path.basename(content)})\n")
        return "\n".join(parts)

    def _merge_sections(self, target_path: str) -> None:
        """Merge generated sections into existing document.

        Updates self.elements with merged content based on section_mode:
        - 'replace': Replace matching sections in existing doc
        - 'append': Append new sections to end
        - 'standalone': No merging (default behavior)
        """
        if self.section_mode == "standalone":
            return  # No merging needed

        # Extract sections from existing document
        existing_sections = self._extract_sections_from_markdown(target_path)

        if self.section_mode == "replace":
            # Replace matching sections, preserve order from existing doc
            merged_elements: list[StoryElement] = []

            # Start with preamble if it exists
            if "__preamble__" in existing_sections:
                preamble_text = "\n".join(existing_sections["__preamble__"])
                if preamble_text.strip():
                    merged_elements.append(("documentation", preamble_text, {}))

            # Track which new sections we've used
            used_anchors: set[str] = set()

            # Iterate through existing sections in order
            for anchor in existing_sections:
                if anchor == "__preamble__":
                    continue

                if anchor in self.section_elements:
                    # Use new version of this section
                    merged_elements.extend(self.section_elements[anchor])
                    used_anchors.add(anchor)
                else:
                    # Keep existing section
                    section_text = "\n".join(existing_sections[anchor])
                    merged_elements.append(("documentation", section_text, {}))

            # Add any new sections that weren't in the original
            for anchor, elements in self.section_elements.items():
                if anchor not in used_anchors:
                    merged_elements.extend(elements)

            self.elements = merged_elements

        elif self.section_mode == "append":
            # Keep all existing sections, append new ones that don't exist
            merged_elements = []

            # Start with preamble
            if "__preamble__" in existing_sections:
                preamble_text = "\n".join(existing_sections["__preamble__"])
                if preamble_text.strip():
                    merged_elements.append(("documentation", preamble_text, {}))

            # Add all existing sections
            for anchor in existing_sections:
                if anchor == "__preamble__":
                    continue
                section_text = "\n".join(existing_sections[anchor])
                merged_elements.append(("documentation", section_text, {}))

            # Append new sections that don't exist
            for anchor, elements in self.section_elements.items():
                if anchor not in existing_sections:
                    merged_elements.extend(elements)

            self.elements = merged_elements

    def _create_zip(self, zip_path: str) -> None:
        """Create zip archive of story directory."""
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            # Walk the output directory
            for root, _dirs, files in os.walk(self.output_directory):
                for file in files:
                    file_path = os.path.join(root, file)
                    # Add to zip with relative path
                    arcname = os.path.relpath(file_path, self.output_directory)
                    zipf.write(file_path, arcname)


class SectionProxy:
    """Context manager that tracks story sections.

    Evaluates to False when the section should be skipped (filtered out),
    allowing code to conditionally execute expensive operations:

        with driver.section("Example", "example") as section:
            if section:
                # This only runs if section is not filtered
                expensive_operation()
    """

    def __init__(self, driver_or_context: Any, title: str, anchor: str):
        self._driver = driver_or_context
        self._meta: SectionMetadataInput = {
            "title": title,
            "anchor": anchor,
        }
        self.should_skip: bool = False

    def __enter__(self) -> "SectionProxy":
        # Access story via driver/context
        story = getattr(self._driver, "story", None)
        if story and story.enabled:
            story._begin_section(self._meta)
            # Check if this section is being filtered out
            if story.section_stack:
                self.should_skip = story.section_stack[-1]["skip"]
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> Literal[False]:
        story = getattr(self._driver, "story", None)
        if story and story.enabled:
            story._end_section()
        return False  # Don't suppress exceptions

    def __bool__(self) -> bool:
        """Return False if section should be skipped, True otherwise."""
        return not self.should_skip


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

    def _begin_section(self, meta: SectionMetadataInput) -> None:
        """No-op: section not tracked."""
        pass

    def _end_section(self) -> None:
        """No-op: section not tracked."""
        pass
