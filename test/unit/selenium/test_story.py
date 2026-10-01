"""Tests for the story document model."""

import os
import zipfile

import pytest

from galaxy.selenium.stories import (
    NoopStory,
    Story,
)


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

    def test_caption_defaults_are_not_invented(self, story_dir):
        story = Story("T", "", story_dir)
        story.add_screenshot(os.path.join(story_dir, "a.png"), "")
        story.finalize()

        markdown = open(os.path.join(story_dir, "story.md")).read()
        assert "![](a.png)" in markdown


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
        # to_pdf_raw's intermediate HTML must not survive into the archive.
        assert "index.html" not in names
        assert not any(n.startswith("/") for n in names)

    def test_pdf_leaves_no_intermediate_html_in_the_zip(self, story_dir, monkeypatch):
        """Drive the real to_pdf_raw with a stub weasyprint, so the cleanup actually runs."""
        import types

        from galaxy.util import markdown_convert

        class FakeHtml:
            def __init__(self, filename):
                self.filename = filename
                # The intermediate really exists at this point - that is the thing
                # whose cleanup is under test.
                assert os.path.basename(filename) == "index.html"
                assert os.path.exists(filename)

            def write_pdf(self, stylesheets=None):
                return b"%PDF-fake"

        monkeypatch.setattr(
            markdown_convert, "weasyprint", types.SimpleNamespace(HTML=FakeHtml, CSS=lambda string=None: string)
        )
        _write_png(os.path.join(story_dir, "000_a.png"))
        story = Story("T", "", story_dir)
        story.add_screenshot(os.path.join(story_dir, "000_a.png"), "a")
        story.finalize()

        assert open(os.path.join(story_dir, "story.pdf"), "rb").read() == b"%PDF-fake"
        assert not os.path.exists(os.path.join(story_dir, "index.html"))
        with zipfile.ZipFile(f"{story_dir}.zip") as zf:
            assert "index.html" not in zf.namelist()
            assert "story.pdf" in zf.namelist()

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

    def test_enabled_distinguishes_the_null_object(self):
        assert Story("T", "", "/tmp").enabled
        assert not NoopStory().enabled


class TestNoopStory:
    def test_collecting_and_finalizing_write_nothing(self, story_dir, monkeypatch):
        monkeypatch.chdir(story_dir)
        story = NoopStory()
        story.add_documentation("ignored")
        story.add_screenshot("a.png", "ignored")
        story.reset()
        story.finalize()

        assert os.listdir(story_dir) == []

    def test_counter_round_trips(self):
        story = NoopStory()
        story.screenshot_counter += 1
        assert story.screenshot_counter == 1
