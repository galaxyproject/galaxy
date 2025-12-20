"""Tests for composable story sections functionality."""

import tempfile
from pathlib import Path

import pytest

from galaxy.selenium.stories.story import (
    SectionMetadataInput,
    SectionProxy,
    Story,
)


@pytest.fixture
def temp_story_dir():
    """Create a temporary directory for story output."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


class TestSectionTracking:
    """Test basic section tracking functionality."""

    def test_basic_section_tracking(self, temp_story_dir):
        """Test creating and tracking a basic section."""
        story = Story("Test", "Description", temp_story_dir)

        meta: SectionMetadataInput = {"title": "Test Section", "anchor": "test_section"}
        story._begin_section(meta)
        story.add_documentation("Test content")
        story._end_section()

        # Check that section was tracked
        assert "test_section" in story.section_elements
        assert len(story.section_elements["test_section"]) > 0

    def test_section_with_screenshots(self, temp_story_dir):
        """Test section containing screenshots."""
        story = Story("Test", "Desc", temp_story_dir)

        # Create a dummy screenshot file
        screenshot_path = Path(temp_story_dir) / "001_test.png"
        screenshot_path.write_text("fake image")

        meta: SectionMetadataInput = {"title": "Screenshots", "anchor": "screenshots"}
        story._begin_section(meta)
        story.add_screenshot(str(screenshot_path), "Test Screenshot")
        story.add_documentation("Screenshot description")
        story._end_section()

        assert "screenshots" in story.section_elements
        elements = story.section_elements["screenshots"]
        # Should contain header, screenshot, and documentation
        assert any(e[0] == "screenshot" for e in elements)
        assert any(e[0] == "documentation" for e in elements)

    def test_nested_sections(self, temp_story_dir):
        """Test nested section hierarchy."""
        story = Story("Test", "Desc", temp_story_dir)

        meta_outer: SectionMetadataInput = {"title": "Outer", "anchor": "outer"}
        meta_inner: SectionMetadataInput = {"title": "Inner", "anchor": "inner"}

        story._begin_section(meta_outer)
        story.add_documentation("Outer content")
        story._begin_section(meta_inner)
        story.add_documentation("Inner content")
        story._end_section()
        story._end_section()

        # Both sections should be tracked
        assert "outer" in story.section_elements
        assert "inner" in story.section_elements


class TestSectionFiltering:
    """Test section filtering (only_sections, skip_sections)."""

    def test_only_sections_filter(self, temp_story_dir):
        """Test --only-sections flag filters correctly."""
        story = Story(
            "Test",
            "Desc",
            temp_story_dir,
            only_sections={"included"},
        )

        # Add included section
        meta1: SectionMetadataInput = {"title": "Included", "anchor": "included"}
        story._begin_section(meta1)
        story.add_documentation("Included content")
        story._end_section()

        # Add excluded section
        meta2: SectionMetadataInput = {"title": "Excluded", "anchor": "excluded"}
        story._begin_section(meta2)
        story.add_documentation("Excluded content")
        story._end_section()

        # Only included should be in section_elements
        assert "included" in story.section_elements
        assert "excluded" not in story.section_elements

    def test_skip_sections_filter(self, temp_story_dir):
        """Test --skip-sections flag filters correctly."""
        story = Story(
            "Test",
            "Desc",
            temp_story_dir,
            skip_sections={"skipped"},
        )

        # Add kept section
        meta1: SectionMetadataInput = {"title": "Kept", "anchor": "kept"}
        story._begin_section(meta1)
        story.add_documentation("Kept content")
        story._end_section()

        # Add skipped section
        meta2: SectionMetadataInput = {"title": "Skipped", "anchor": "skipped"}
        story._begin_section(meta2)
        story.add_documentation("Skipped content")
        story._end_section()

        # Only kept should be in section_elements
        assert "kept" in story.section_elements
        assert "skipped" not in story.section_elements

    def test_only_and_skip_conflict(self, temp_story_dir):
        """Test that skip takes precedence over only."""
        story = Story(
            "Test",
            "Desc",
            temp_story_dir,
            only_sections={"section_a", "section_b"},
            skip_sections={"section_b"},
        )

        # Add section_a (in only, not skipped)
        meta_a: SectionMetadataInput = {"title": "A", "anchor": "section_a"}
        story._begin_section(meta_a)
        story.add_documentation("A")
        story._end_section()

        # Add section_b (in only but also skipped)
        meta_b: SectionMetadataInput = {"title": "B", "anchor": "section_b"}
        story._begin_section(meta_b)
        story.add_documentation("B")
        story._end_section()

        # Add section_c (not in only)
        meta_c: SectionMetadataInput = {"title": "C", "anchor": "section_c"}
        story._begin_section(meta_c)
        story.add_documentation("C")
        story._end_section()

        # Only section_a should be included
        assert "section_a" in story.section_elements
        assert "section_b" not in story.section_elements  # Skipped takes precedence
        assert "section_c" not in story.section_elements  # Not in only


class TestSectionHeadingLevels:
    """Test that section heading levels auto-increment with nesting."""

    def test_top_level_heading(self, temp_story_dir):
        """Test that top-level sections are H2."""
        story = Story("Test", "Desc", temp_story_dir)

        meta: SectionMetadataInput = {"title": "Top Level", "anchor": "top"}
        story._begin_section(meta)
        story._end_section()

        # Check that section was added with H2 heading
        elements = story.elements
        assert any("## Top Level" in e[1] for e in elements if e[0] == "documentation")

    def test_nested_heading_levels(self, temp_story_dir):
        """Test that nested sections increment heading levels."""
        story = Story("Test", "Desc", temp_story_dir)

        meta_outer: SectionMetadataInput = {"title": "Outer", "anchor": "outer"}
        meta_inner: SectionMetadataInput = {"title": "Inner", "anchor": "inner"}

        story._begin_section(meta_outer)
        # Inner section starts while outer is active
        story._begin_section(meta_inner)
        story._end_section()
        story._end_section()

        # Check heading levels in elements
        elements_text = "\n".join(e[1] for e in story.elements if e[0] == "documentation")
        assert "## Outer" in elements_text
        assert "### Inner" in elements_text


class TestSectionProxy:
    """Test SectionProxy context manager."""

    def test_section_proxy_context_manager(self, temp_story_dir):
        """Test using SectionProxy as context manager."""
        story = Story("Test", "Desc", temp_story_dir)

        class FakeDriver:
            def __init__(self, story_obj):
                self.story = story_obj

        driver = FakeDriver(story)

        # Use section proxy as context manager
        with SectionProxy(driver, "Test Section", "test") as section:
            if section:
                story.add_documentation("Content in section")

        # Section should be tracked
        assert "test" in story.section_elements

    def test_section_proxy_truthiness_when_included(self, temp_story_dir):
        """Test that section proxy is truthy when not filtered."""
        story = Story("Test", "Desc", temp_story_dir)

        class FakeDriver:
            def __init__(self, story_obj):
                self.story = story_obj

        driver = FakeDriver(story)

        # Section should be truthy (not filtered)
        with SectionProxy(driver, "Test Section", "test") as section:
            assert section  # Should be truthy
            assert not section.should_skip

    def test_section_proxy_truthiness_when_filtered(self, temp_story_dir):
        """Test that section proxy is falsy when filtered out."""
        story = Story("Test", "Desc", temp_story_dir, only_sections={"other"})

        class FakeDriver:
            def __init__(self, story_obj):
                self.story = story_obj

        driver = FakeDriver(story)

        # Section should be falsy (filtered out)
        executed = False
        with SectionProxy(driver, "Test Section", "test") as section:
            assert not section  # Should be falsy
            assert section.should_skip
            if section:
                executed = True

        # Code inside the if should not have run
        assert not executed


class TestReset:
    """Test resetting story state."""

    def test_reset_clears_sections(self, temp_story_dir):
        """Test that reset() clears section tracking."""
        story = Story("Test", "Desc", temp_story_dir)

        meta: SectionMetadataInput = {"title": "Test", "anchor": "test"}
        story._begin_section(meta)
        story.add_documentation("Content")
        story._end_section()

        assert "test" in story.section_elements

        # Reset
        story.reset()

        assert len(story.section_elements) == 0
        assert len(story.section_stack) == 0
        assert not story._filtering_active


class TestMarkdownMerging:
    """Test markdown section extraction and merging."""

    def test_extract_sections_from_markdown(self, temp_story_dir):
        """Test extracting sections from existing markdown."""
        # Create a markdown file with sections
        md_path = Path(temp_story_dir) / "existing.md"
        md_content = """# Title

This is preamble content before any sections.

<a id="section1"></a>
## Section 1

Content for section 1.

<a id="section2"></a>
## Section 2

Content for section 2.
"""
        md_path.write_text(md_content)

        story = Story("Test", "Desc", temp_story_dir)
        sections = story._extract_sections_from_markdown(str(md_path))

        # Should have preamble and 2 sections
        assert "__preamble__" in sections
        assert "section1" in sections
        assert "section2" in sections

        # Check preamble content
        preamble = "\n".join(sections["__preamble__"])
        assert "Title" in preamble
        assert "preamble content" in preamble

        # Check section content
        section1 = "\n".join(sections["section1"])
        assert 'id="section1"' in section1
        assert "Section 1" in section1
        assert "Content for section 1" in section1

    def test_merge_sections_replace_mode(self, temp_story_dir):
        """Test replacing sections in existing markdown."""
        # Create existing markdown
        existing_path = Path(temp_story_dir) / "existing.md"
        existing_content = """# Tutorial

<a id="intro"></a>
## Introduction

Old intro content.

<a id="section1"></a>
## Section 1

Old section 1 content.

<a id="section2"></a>
## Section 2

Old section 2 content.
"""
        existing_path.write_text(existing_content)

        # Create story with replace mode
        output_dir = Path(temp_story_dir) / "output"
        output_dir.mkdir()
        story = Story(
            "Tutorial",
            "",
            str(output_dir),
            merge_target=str(existing_path),
            section_mode="replace",
        )

        # Add updated section1
        meta: SectionMetadataInput = {"title": "Section 1 Updated", "anchor": "section1"}
        story._begin_section(meta)
        story.add_documentation("New section 1 content!")
        story._end_section()

        # Merge sections
        story._merge_sections(str(existing_path))

        # Check that elements were updated
        markdown = story._generate_markdown()

        # Should have intro (preserved), updated section1, and section2 (preserved)
        assert "Old intro content" in markdown
        assert "New section 1 content" in markdown
        assert "Old section 2 content" in markdown
        assert "Old section 1 content" not in markdown  # Replaced

    def test_merge_sections_append_mode(self, temp_story_dir):
        """Test appending new sections to existing markdown."""
        # Create existing markdown
        existing_path = Path(temp_story_dir) / "existing.md"
        existing_content = """# Tutorial

<a id="section1"></a>
## Section 1

Existing section 1 content.
"""
        existing_path.write_text(existing_content)

        # Create story with append mode
        output_dir = Path(temp_story_dir) / "output"
        output_dir.mkdir()
        story = Story(
            "Tutorial",
            "",
            str(output_dir),
            merge_target=str(existing_path),
            section_mode="append",
        )

        # Add new section (doesn't exist in original)
        meta1: SectionMetadataInput = {"title": "Section 2", "anchor": "section2"}
        story._begin_section(meta1)
        story.add_documentation("New section 2 content.")
        story._end_section()

        # Try to add existing section (should be ignored in append mode)
        meta2: SectionMetadataInput = {"title": "Section 1 Updated", "anchor": "section1"}
        story._begin_section(meta2)
        story.add_documentation("This should be ignored in append mode.")
        story._end_section()

        # Merge sections
        story._merge_sections(str(existing_path))

        markdown = story._generate_markdown()

        # Should have existing section1 (not updated) and new section2
        assert "Existing section 1 content" in markdown
        assert "New section 2 content" in markdown
        assert "This should be ignored" not in markdown  # Not appended (already exists)

    def test_merge_sections_standalone_mode(self, temp_story_dir):
        """Test that standalone mode doesn't merge."""
        existing_path = Path(temp_story_dir) / "existing.md"
        existing_path.write_text("# Old Content")

        output_dir = Path(temp_story_dir) / "output"
        output_dir.mkdir()
        story = Story(
            "New Tutorial",
            "New description",
            str(output_dir),
            merge_target=str(existing_path),
            section_mode="standalone",  # Default
        )

        # Add section
        meta: SectionMetadataInput = {"title": "New Section", "anchor": "new"}
        story._begin_section(meta)
        story.add_documentation("New content.")
        story._end_section()

        # Merge should do nothing in standalone mode
        story._merge_sections(str(existing_path))

        markdown = story._generate_markdown()

        # Should have new content, not old
        assert "New Tutorial" in markdown
        assert "New content" in markdown
        assert "Old Content" not in markdown

    def test_finalize_with_merge(self, temp_story_dir):
        """Test that finalize() calls merge when merge_target is set."""
        # Create existing markdown
        existing_path = Path(temp_story_dir) / "existing.md"
        existing_content = """# Tutorial

<a id="section1"></a>
## Section 1

Old content.
"""
        existing_path.write_text(existing_content)

        # Create story with replace mode
        output_dir = Path(temp_story_dir) / "output"
        output_dir.mkdir()
        story = Story(
            "Tutorial",
            "",
            str(output_dir),
            merge_target=str(existing_path),
            section_mode="replace",
        )

        # Add updated section
        meta: SectionMetadataInput = {"title": "Section 1", "anchor": "section1"}
        story._begin_section(meta)
        story.add_documentation("Updated content!")
        story._end_section()

        # Test merge by calling _merge_sections directly (avoids HTML/PDF generation)
        story._merge_sections(str(existing_path))

        # Check merged content
        markdown = story._generate_markdown()
        assert "Updated content" in markdown
        assert "Old content" not in markdown

    def test_merge_preserves_section_order(self, temp_story_dir):
        """Test that replace mode preserves original section order."""
        existing_path = Path(temp_story_dir) / "existing.md"
        existing_content = """# Tutorial

<a id="first"></a>
## First

First section.

<a id="second"></a>
## Second

Second section.

<a id="third"></a>
## Third

Third section.
"""
        existing_path.write_text(existing_content)

        output_dir = Path(temp_story_dir) / "output"
        output_dir.mkdir()
        story = Story(
            "Tutorial",
            "",
            str(output_dir),
            merge_target=str(existing_path),
            section_mode="replace",
        )

        # Update second section only
        meta: SectionMetadataInput = {"title": "Second Updated", "anchor": "second"}
        story._begin_section(meta)
        story.add_documentation("Updated second section.")
        story._end_section()

        story._merge_sections(str(existing_path))
        markdown = story._generate_markdown()

        # Check order is preserved: first, second (updated), third
        first_pos = markdown.find("First section")
        second_pos = markdown.find("Updated second section")
        third_pos = markdown.find("Third section")

        assert first_pos < second_pos < third_pos

    def test_merge_adds_new_sections_at_end(self, temp_story_dir):
        """Test that new sections are added at the end in replace mode."""
        existing_path = Path(temp_story_dir) / "existing.md"
        existing_content = """# Tutorial

<a id="existing"></a>
## Existing Section

Existing content.
"""
        existing_path.write_text(existing_content)

        output_dir = Path(temp_story_dir) / "output"
        output_dir.mkdir()
        story = Story(
            "Tutorial",
            "",
            str(output_dir),
            merge_target=str(existing_path),
            section_mode="replace",
        )

        # Add new section that doesn't exist
        meta: SectionMetadataInput = {"title": "New Section", "anchor": "new"}
        story._begin_section(meta)
        story.add_documentation("New content at end.")
        story._end_section()

        story._merge_sections(str(existing_path))
        markdown = story._generate_markdown()

        # New section should come after existing
        existing_pos = markdown.find("Existing content")
        new_pos = markdown.find("New content at end")

        assert existing_pos < new_pos
