from pathlib import Path

import pytest

from tool_shed.context import ProvidesRepositoriesContext
from tool_shed.managers.repositories import readmes
from tool_shed.test.base.populators import TEST_DATA_REPO_FILES
from tool_shed.util.metadata_util import get_latest_downloadable_changeset_revision
from tool_shed.util.readme_util import render_readme
from tool_shed.webapp.model import Repository
from ._util import upload


def test_rst_readme_is_not_evaluated_as_template():
    html = render_readme("README.rst", "Sum: ${7*6} <% import os %>\n")
    assert "42" not in html
    assert "${7*6}" in html


def test_rst_readme_raw_html_is_sanitized():
    rst = "Title\n\n.. raw:: html\n\n   <script>alert(1)</script><img src=x onerror=alert(2)>\n"
    html = render_readme("README.rst", rst)
    assert "<script" not in html
    assert "onerror" not in html


def test_rst_readme_keeps_formatting():
    html = render_readme("README.rst", "Some **bold** text and a `link <https://galaxyproject.org>`__.\n")
    assert "<strong>bold</strong>" in html
    assert 'href="https://galaxyproject.org"' in html


def test_plain_readme_is_escaped():
    html = render_readme("README.txt", "<script>alert(1)</script>")
    assert "<script" not in html
    assert "&lt;script&gt;" in html


def test_rst_readme_substitutes_legacy_placeholders(monkeypatch):
    def url_for(path, qualified=False):
        return "https://shed.example.org/" if qualified else "/shed_static"

    monkeypatch.setattr("tool_shed.util.readme_util.web.url_for", url_for)
    rst = "See `home <${host_url}view>`__.\n\n.. image:: ${static_path}/logo.png\n"
    html = render_readme("README.rst", rst)
    assert 'href="https://shed.example.org/view"' in html
    assert 'src="/shed_static/logo.png"' in html
    assert "${" not in html


def test_rst_readme_keeps_tables_code_and_images():
    rst = (
        "+---+---+\n| a | b |\n+---+---+\n\n"
        "::\n\n    samtools view in.bam\n\n"
        ".. image:: https://example.org/logo.png\n"
    )
    html = render_readme("README.rst", rst)
    assert "<table" in html
    assert "<pre" in html
    assert 'src="https://example.org/logo.png"' in html


COLUMN_MAKER_REVISIONS = TEST_DATA_REPO_FILES / "repos" / "column_maker"


def _upload_revision(
    provides_repositories: ProvidesRepositoriesContext,
    repository: Repository,
    tmp_path: Path,
    column_maker_version: str,
    label: str,
):
    revision_dir = tmp_path / column_maker_version
    revision_dir.mkdir()
    tool_xml = COLUMN_MAKER_REVISIONS / column_maker_version / "column_maker.xml"
    (revision_dir / "column_maker.xml").write_text(tool_xml.read_text())
    readme = f"{label} **bold** text.\n\n.. raw:: html\n\n   <script>alert(1)</script>\n"
    (revision_dir / "README.rst").write_text(readme)
    upload(provides_repositories, repository, revision_dir, arcname="readme_repo")


@pytest.mark.parametrize("label, other_label", [("Old", "New"), ("New", "Old")])
def test_readmes_renders_rst_readme_of_each_downloadable_revision(
    provides_repositories: ProvidesRepositoriesContext,
    new_repository: Repository,
    tmp_path: Path,
    label: str,
    other_label: str,
):
    app = provides_repositories.app
    _upload_revision(provides_repositories, new_repository, tmp_path, "1", "Old")
    _upload_revision(provides_repositories, new_repository, tmp_path, "2", "New")
    latest = get_latest_downloadable_changeset_revision(app, new_repository)
    (old,) = [m.changeset_revision for m in new_repository.downloadable_revisions if m.changeset_revision != latest]
    changeset_revision = old if label == "Old" else latest
    assert changeset_revision

    html = readmes(app, new_repository, changeset_revision)["README.rst"]

    assert f"{label} <strong>bold</strong> text." in html
    assert other_label not in html
    assert "<script" not in html
