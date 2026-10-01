"""Tests for galaxy.util.markdown_convert."""

import os
import types

import pytest

from galaxy.util import markdown_convert as markdown_util


class FakeHtml:
    def __init__(self, filename):
        self.filename = filename

    def write_pdf(self, stylesheets=None):
        # Read back through the path weasyprint was handed, so the test fails if
        # the intermediate file is written somewhere else.
        with open(self.filename) as f:
            return f.read().encode("utf-8")


@pytest.fixture
def fake_weasyprint(monkeypatch):
    fake = types.SimpleNamespace(HTML=FakeHtml, CSS=lambda string=None: string)
    monkeypatch.setattr(markdown_util, "weasyprint", fake)
    return fake


def test_to_pdf_raw_renders_in_a_given_directory(fake_weasyprint, tmp_path):
    directory = str(tmp_path)
    rendered = markdown_util.to_pdf_raw("# Hello", directory=directory).decode("utf-8")

    assert "<h1>Hello</h1>" in rendered
    # The caller's directory survives; only the intermediate HTML is cleaned up.
    assert os.path.isdir(directory)
    assert os.listdir(directory) == []


def test_to_pdf_raw_cleans_up_its_temporary_directory(fake_weasyprint, monkeypatch):
    created = []
    real_mkdtemp = markdown_util.tempfile.mkdtemp

    def record(*args, **kwargs):
        path = real_mkdtemp(*args, **kwargs)
        created.append(path)
        return path

    monkeypatch.setattr(markdown_util.tempfile, "mkdtemp", record)
    markdown_util.to_pdf_raw("# Hello")

    assert created and not os.path.exists(created[0])


def test_to_pdf_raw_cleans_up_when_rendering_fails(fake_weasyprint, tmp_path):
    class Exploding(FakeHtml):
        def write_pdf(self, stylesheets=None):
            raise RuntimeError("boom")

    fake_weasyprint.HTML = Exploding
    with pytest.raises(RuntimeError):
        markdown_util.to_pdf_raw("# Hello", directory=str(tmp_path))

    assert os.listdir(str(tmp_path)) == []


def test_to_pdf_raw_without_weasyprint(monkeypatch, tmp_path):
    monkeypatch.setattr(markdown_util, "weasyprint", None)
    with pytest.raises(ImportError, match="weasyprint is required"):
        markdown_util.to_pdf_raw("# Hello", directory=str(tmp_path))


def test_to_html_without_markdown(monkeypatch):
    monkeypatch.setattr(markdown_util, "markdown", None)
    with pytest.raises(ImportError, match="markdown-convert"):
        markdown_util.to_html("# Hello")


def test_to_html_sanitizes_scripts():
    assert "<script>" not in markdown_util.to_html("<script>alert(1)</script>")
