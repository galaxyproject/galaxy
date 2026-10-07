from typing import cast

import pytest

from galaxy.exceptions import (
    InconsistentApplicationState,
    ObjectNotFound,
    RequestParameterInvalidException,
)
from tool_shed.context import ProvidesRepositoriesContext
from tool_shed.managers import repositories as repositories_manager
from tool_shed.managers.repositories import (
    guid_to_repository,
    repository_file_contents,
    repository_files,
)
from tool_shed.structured_app import ToolShedApp
from tool_shed.webapp.model import Repository
from ._util import upload_directories_to_repository


def test_guid_to_repository_rejects_malformed_guid():
    # A guid without enough slashes used to raise a bare ValueError from the
    # tuple unpacking, surfacing as a 500 in the TRS API (see issue #23139).
    # The malformed-id check runs before app is dereferenced, so a cast None
    # is enough to exercise this path.
    app = cast(ToolShedApp, None)
    with pytest.raises(RequestParameterInvalidException):
        guid_to_repository(app, "localhost/repos/owner")


def test_guid_to_repository_parses_owner_and_name(monkeypatch):
    # A well-formed guid is "shed/repos/owner/name/rest...". The manager should
    # extract owner and name and look the repository up by name and owner,
    # ignoring the shed host and everything after the name.
    captured = {}
    sentinel_repository = object()
    sentinel_context = object()

    def fake_lookup(context, name, owner):
        captured["context"] = context
        captured["name"] = name
        captured["owner"] = owner
        return sentinel_repository

    monkeypatch.setattr(repositories_manager, "_get_repository_by_name_and_owner", fake_lookup)

    class _Model:
        context = sentinel_context

    class _App:
        model = _Model()

    app = cast(ToolShedApp, _App())
    result = guid_to_repository(app, "localhost:9009/repos/owner/name/1234abcd/tool_id")

    assert result is sentinel_repository
    assert captured["owner"] == "owner"
    assert captured["name"] == "name"
    assert captured["context"] is sentinel_context


def _uploaded_unchanged(provides_repositories: ProvidesRepositoriesContext, repository: Repository) -> dict[str, str]:
    # column_maker_unchanged: revision 0 has no metadata row (its metadata moves to revision 1,
    # which only adds README.txt), revision 2 removes README.txt and bumps the tool.
    upload_directories_to_repository(provides_repositories, repository, "column_maker_unchanged")
    hg_repo = repository.hg_repo
    return {name: str(hg_repo[rev]) for name, rev in (("first", 0), ("readme", 1), ("last", 2))}


def test_repository_files_lists_unchanged_files(provides_repositories, new_repository):
    revisions = _uploaded_unchanged(provides_repositories, new_repository)
    app = provides_repositories.app
    listing = repository_files(app, new_repository, revisions["readme"]).build()
    assert listing.changeset_revision == revisions["readme"]
    assert sorted(entry.path for entry in listing.files) == [
        "column_maker_unchanged/README.txt",
        "column_maker_unchanged/column_maker.xml",
    ]
    contents = repository_file_contents(
        app, new_repository, revisions["readme"], "column_maker_unchanged/column_maker.xml"
    ).build()
    assert contents.content and "<tool" in contents.content
    last = repository_files(app, new_repository, revisions["last"]).build()
    assert [entry.path for entry in last.files] == ["column_maker_unchanged/column_maker.xml"]


def test_repository_files_rejects_revision_without_metadata(provides_repositories, new_repository):
    revisions = _uploaded_unchanged(provides_repositories, new_repository)
    with pytest.raises(ObjectNotFound):
        repository_files(provides_repositories.app, new_repository, revisions["first"])


def test_repository_file_contents_rejects_missing_path(provides_repositories, new_repository):
    revisions = _uploaded_unchanged(provides_repositories, new_repository)
    app = provides_repositories.app
    for path in ("column_maker_unchanged/README.txt", "column_maker_unchanged", ".hg/hgrc"):
        with pytest.raises(ObjectNotFound):
            repository_file_contents(app, new_repository, revisions["last"], path)


def test_repository_files_rejects_malicious_revision(provides_repositories, new_repository):
    revisions = _uploaded_unchanged(provides_repositories, new_repository)
    sa_session = provides_repositories.sa_session
    for metadata_revision in new_repository.metadata_revisions:
        if metadata_revision.changeset_revision == revisions["last"]:
            metadata_revision.malicious = True
            sa_session.add(metadata_revision)
    sa_session.commit()
    app = provides_repositories.app
    with pytest.raises(ObjectNotFound):
        repository_files(app, new_repository, revisions["last"])
    repository_files(app, new_repository, revisions["readme"])


@pytest.mark.parametrize("attribute", ["deleted", "deprecated"])
def test_repository_files_rejects_unavailable_repository(provides_repositories, new_repository, attribute):
    revisions = _uploaded_unchanged(provides_repositories, new_repository)
    setattr(new_repository, attribute, True)
    with pytest.raises(ObjectNotFound):
        repository_files(provides_repositories.app, new_repository, revisions["last"])


def test_repository_files_reports_revision_missing_from_hg(provides_repositories, new_repository, monkeypatch):
    # The metadata row says the revision is downloadable, so hg not finding it is a fault, not a 404.
    revisions = _uploaded_unchanged(provides_repositories, new_repository)
    monkeypatch.setattr(repositories_manager, "changectx_for_revision", lambda hg_repo, revision: None)
    with pytest.raises(InconsistentApplicationState):
        repository_files(provides_repositories.app, new_repository, revisions["last"])


def test_repository_file_validators_do_not_build(provides_repositories, new_repository, monkeypatch):
    revisions = _uploaded_unchanged(provides_repositories, new_repository)

    def fail(*args, **kwargs):
        raise AssertionError("built while only validating")

    monkeypatch.setattr(repositories_manager, "list_manifest", fail)
    monkeypatch.setattr(repositories_manager, "read_file", fail)
    app = provides_repositories.app
    listing = repository_files(app, new_repository, revisions["last"])
    contents = repository_file_contents(
        app, new_repository, revisions["last"], "column_maker_unchanged/column_maker.xml"
    )
    assert listing.validator != contents.validator
