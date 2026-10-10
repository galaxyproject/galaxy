"""Tests for the story document model."""

import datetime
import os
import zipfile
from dataclasses import dataclass
from pathlib import Path

import pytest

from galaxy.selenium.stories import (
    link_latest,
    NoopStory,
    run_directory,
    runs,
    Story,
    story_for_run,
    write_story,
)
from galaxy.util import markdown_convert


@dataclass
class FakeWeasyprint:
    """Stands in for weasyprint, whose system libraries are often missing."""

    HTML: type

    def CSS(self, string=None):
        return string


class FrozenDatetime(datetime.datetime):
    @classmethod
    def now(cls, tz=None):
        return cls(2026, 10, 1, 12, 0)


@pytest.fixture
def story_dir(tmp_path):
    directory = tmp_path / "story"
    directory.mkdir()
    return str(directory)


def _write_png(path: str) -> str:
    # Smallest valid PNG, so weasyprint has something real to embed.
    png = bytes.fromhex(
        "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4"
        "890000000a49444154789c6300010000050001"
        "0d0a2db40000000049454e44ae426082"
    )
    with open(path, "wb") as f:
        f.write(png)
    return path


class TestStoryMarkdown:
    def test_title_and_description_head_the_document(self, story_dir):
        story = Story("My Title", "My description.", story_dir)
        story.finalize()

        markdown = open(os.path.join(story_dir, "story.md")).read()
        assert markdown.startswith("# My Title\n")
        assert "My description." in markdown

    def test_documentation_appears_in_order(self, story_dir):
        story = Story("T", "", story_dir)
        story.add_documentation("first")
        story.add_documentation("second")
        story.finalize()

        markdown = open(os.path.join(story_dir, "story.md")).read()
        assert markdown.index("first") < markdown.index("second")

    def test_screenshot_is_referenced_by_basename(self, story_dir):
        shot = _write_png(os.path.join(story_dir, "000_upload.png"))
        story = Story("T", "", story_dir)
        story.add_screenshot(shot, "The upload button")
        story.finalize()

        markdown = open(os.path.join(story_dir, "story.md")).read()
        # Relative, so the markdown stays valid next to its images in the zip.
        assert "![The upload button](000_upload.png)" in markdown
        assert story_dir not in markdown


class TestStoryArtifacts:
    def test_finalize_writes_markdown_and_html(self, story_dir):
        story = Story("Escaping <b>Matters</b>", "", story_dir)
        story.add_documentation("Some **bold** text.")
        story.finalize()

        assert os.path.exists(os.path.join(story_dir, "story.md"))
        html = open(os.path.join(story_dir, "story.html")).read()
        assert "<strong>bold</strong>" in html
        assert html.startswith("<!DOCTYPE html>")
        # The title is interpolated into <title> without going through to_html.
        assert "<title>Escaping &lt;b&gt;Matters&lt;/b&gt;</title>" in html

    def test_relative_image_references_survive_sanitization(self, story_dir):
        """sanitize_html's URL policy must leave the story's own screenshots alone."""
        _write_png(os.path.join(story_dir, "000_a.png"))
        story = Story("T", "", story_dir)
        story.add_screenshot(os.path.join(story_dir, "000_a.png"), "a")
        story.finalize()

        html = open(os.path.join(story_dir, "story.html")).read()
        assert 'src="000_a.png"' in html

    def test_zip_is_written_beside_the_directory(self, story_dir):
        _write_png(os.path.join(story_dir, "000_a.png"))
        story = Story("T", "", story_dir)
        story.add_screenshot(os.path.join(story_dir, "000_a.png"), "a")
        story.finalize()

        zip_path = f"{story_dir}.zip"
        assert os.path.exists(zip_path)
        with zipfile.ZipFile(zip_path) as zf:
            names = zf.namelist()
        # Arcnames are relative, so unzipping does not recreate the absolute path.
        assert "story.md" in names
        assert "000_a.png" in names
        # Only the documents and referenced screenshots - story.pdf depends on weasyprint.
        assert set(names) - {"story.pdf"} == {"story.md", "story.html", "000_a.png"}
        assert not any(n.startswith("/") for n in names)

    def test_pdf_leaves_no_intermediate_html_in_the_zip(self, story_dir, monkeypatch):
        """Drive the real to_pdf_raw with a stub weasyprint, so the cleanup actually runs."""

        class FakeHtml:
            def __init__(self, filename):
                self.filename = filename
                assert os.path.dirname(filename) == story_dir
                assert os.path.exists(filename)

            def write_pdf(self, stylesheets=None):
                return b"%PDF-fake"

        monkeypatch.setattr(markdown_convert, "weasyprint", FakeWeasyprint(HTML=FakeHtml))
        _write_png(os.path.join(story_dir, "000_a.png"))
        story = Story("T", "", story_dir)
        story.add_screenshot(os.path.join(story_dir, "000_a.png"), "a")
        story.finalize()

        assert open(os.path.join(story_dir, "story.pdf"), "rb").read() == b"%PDF-fake"
        assert sorted(os.listdir(story_dir)) == ["000_a.png", "story.html", "story.md", "story.pdf"]
        with zipfile.ZipFile(f"{story_dir}.zip") as zf:
            assert sorted(zf.namelist()) == ["000_a.png", "story.html", "story.md", "story.pdf"]

    def test_retry_leftovers_are_not_archived(self, story_dir):
        """A discarded attempt's screenshots stay on disk but must not ship."""
        _write_png(os.path.join(story_dir, "000_first_try.png"))
        _write_png(os.path.join(story_dir, "001_crash_point.png"))
        story = Story("T", "", story_dir)
        story.add_screenshot(os.path.join(story_dir, "000_first_try.png"), "a")
        story.add_screenshot(os.path.join(story_dir, "001_crash_point.png"), "b")

        story.reset()
        _write_png(os.path.join(story_dir, "000_second_try.png"))
        story.add_screenshot(os.path.join(story_dir, "000_second_try.png"), "a")
        story.finalize()

        with zipfile.ZipFile(f"{story_dir}.zip") as zf:
            names = zf.namelist()
        assert "000_second_try.png" in names
        assert "001_crash_point.png" not in names

    def test_finalize_without_weasyprint_still_writes_the_rest(self, story_dir, monkeypatch):
        monkeypatch.setattr("galaxy.selenium.stories.story.weasyprint_available", lambda: False)
        story = Story("T", "", story_dir)
        story.finalize()

        assert os.path.exists(os.path.join(story_dir, "story.md"))
        assert os.path.exists(os.path.join(story_dir, "story.html"))
        assert not os.path.exists(os.path.join(story_dir, "story.pdf"))


class TestStoryState:
    def test_reset_discards_collected_content(self, story_dir):
        story = Story("T", "", story_dir)
        story.add_documentation("from the failed attempt")
        story.screenshot_counter = 7
        story.reset()
        story.add_documentation("from the retry")
        story.finalize()

        markdown = open(os.path.join(story_dir, "story.md")).read()
        assert "from the failed attempt" not in markdown
        assert "from the retry" in markdown
        assert story.screenshot_counter == 0


class TestNoopStory:
    def test_collecting_and_finalizing_write_nothing(self, story_dir, monkeypatch):
        monkeypatch.chdir(story_dir)
        story = NoopStory()
        story.add_documentation("ignored")
        story.add_screenshot("a.png", "ignored")
        story.reset()
        story.finalize()

        assert os.listdir(story_dir) == []


class TestStoryRuns:
    def test_disabled_stories_are_noops(self, tmp_path, monkeypatch):
        # A disabled story has no directory, so anything it wrote would land in cwd.
        monkeypatch.chdir(tmp_path)
        story = story_for_run(None, "test_example_", "T", "")
        write_story(story, failed=True)

        assert not story.enabled
        assert list(tmp_path.iterdir()) == []

    def test_run_gets_a_fresh_directory_under_the_base(self, tmp_path):
        story = story_for_run(str(tmp_path), "test_example_", "T", "")

        assert os.path.dirname(story.output_directory) == str(tmp_path)
        assert os.path.basename(story.output_directory).startswith("test_example_")
        assert os.path.isdir(story.output_directory)

    def test_run_directories_are_unique_at_the_same_time(self, tmp_path, monkeypatch):
        monkeypatch.setattr(runs.datetime, "datetime", FrozenDatetime)
        first = run_directory(str(tmp_path), "test_example_")
        second = run_directory(str(tmp_path), "test_example_")

        assert first != second
        assert sorted(os.listdir(tmp_path)) == sorted([os.path.basename(first), os.path.basename(second)])

    def test_write_links_latest(self, tmp_path):
        first = story_for_run(str(tmp_path), "test_example_", "T", "")
        write_story(first)
        second = story_for_run(str(tmp_path), "test_example_", "T", "")
        write_story(second)

        assert (tmp_path / "latest").resolve() == Path(second.output_directory).resolve()
        assert os.path.exists(f"{first.output_directory}.zip")

    def test_failed_write_marks_the_document(self, tmp_path):
        story = story_for_run(str(tmp_path), "test_example_", "T", "")
        story.add_documentation("Collected narration.")
        write_story(story, failed=True)

        markdown = open(os.path.join(story.output_directory, "story.md")).read()
        assert markdown.index("Collected narration.") < markdown.index("Test Failed")

    def test_write_failure_is_swallowed_and_not_linked(self, tmp_path):
        story = Story("T", "", str(tmp_path / "missing"))
        write_story(story)

        assert not os.path.lexists(tmp_path / "latest")

    def test_link_latest_replaces_an_existing_link(self, tmp_path):
        first = tmp_path / "first"
        second = tmp_path / "second"
        first.mkdir()
        second.mkdir()
        link_latest(str(first))
        link_latest(str(second))

        assert (tmp_path / "latest").resolve() == second.resolve()
