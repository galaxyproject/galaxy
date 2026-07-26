import pytest

from galaxy.tool_shed.util.hg_util import (
    get_changectx_for_changeset,
    INITIAL_CHANGELOG_HASH,
)
from tool_shed.context import ProvidesRepositoriesContext
from tool_shed.util.metadata_util import (
    get_metadata_revisions,
    get_next_downloadable_changeset_revision,
)
from tool_shed.util.repository_util import get_repo_info_dict
from tool_shed.webapp.model import Repository
from ._util import upload_directories_to_repository


def changelog(repository: Repository) -> list[str]:
    repo = repository.hg_repo
    return [str(repo[changeset]) for changeset in repo.changelog]


@pytest.mark.parametrize("fixture", ["column_maker", "column_maker_with_download_gaps"])
def test_get_changectx_for_changeset(
    provides_repositories: ProvidesRepositoriesContext, new_repository: Repository, fixture: str
):
    upload_directories_to_repository(provides_repositories, new_repository, fixture)
    repo = new_repository.hg_repo
    revisions = changelog(new_repository)
    assert len(revisions) > 1

    for expected_rev, changeset_revision in enumerate(revisions):
        ctx = get_changectx_for_changeset(repo, changeset_revision)
        assert ctx is not None
        assert ctx.rev() == expected_rev

    assert get_changectx_for_changeset(repo, INITIAL_CHANGELOG_HASH) is None
    assert get_changectx_for_changeset(repo, "deadbeefdead") is None
    assert get_changectx_for_changeset(repo, "zzzzzzzzzzzz") is None
    assert get_changectx_for_changeset(repo, "") is None
    # A prefix of a real hash is not a changeset revision.
    assert get_changectx_for_changeset(repo, revisions[0][:4]) is None


def test_next_downloadable_changeset_revision_follows_changelog_order(
    provides_repositories: ProvidesRepositoriesContext, new_repository: Repository
):
    # This repository has a revision without installable metadata between two that have it, which
    # leaves RepositoryMetadata.numeric_revision out of step with the real changelog position.
    upload_directories_to_repository(provides_repositories, new_repository, "column_maker_with_download_gaps")
    app = provides_repositories.app
    revisions = changelog(new_repository)
    downloadable = [changeset_revision for _rev, changeset_revision in get_metadata_revisions(app, new_repository)]

    for position, changeset_revision in enumerate(revisions):
        expected = next((cs for cs in revisions[position + 1 :] if cs in downloadable), None)
        assert get_next_downloadable_changeset_revision(app, new_repository, changeset_revision) == expected

    assert get_next_downloadable_changeset_revision(app, new_repository, "deadbeefdead") is None


@pytest.mark.parametrize("fixture", ["column_maker", "column_maker_with_download_gaps"])
def test_repo_info_dict_ctx_rev_is_the_mercurial_revision(
    provides_repositories: ProvidesRepositoriesContext, new_repository: Repository, fixture: str
):
    upload_directories_to_repository(provides_repositories, new_repository, fixture)
    app = provides_repositories.app
    encoded_id = app.security.encode_id(new_repository.id)
    revisions = changelog(new_repository)

    for _rev, changeset_revision in get_metadata_revisions(app, new_repository):
        repo_info_dict = get_repo_info_dict(provides_repositories, encoded_id, changeset_revision)[0]
        ctx_rev = repo_info_dict[new_repository.name][3]
        assert ctx_rev == str(revisions.index(changeset_revision))
