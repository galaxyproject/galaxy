"""Integration tests for repository API endpoints.

These tests access app components directly outside the API to set up specific
conditions (e.g., corrupted metadata) that can't be created through normal API usage.

Unlike pure API tests in test_shed_repositories.py, these tests verify the API
correctly handles edge cases that require backend manipulation to reproduce.
"""
import copy
from dataclasses import dataclass

from sqlalchemy import select

from galaxy_test.base import api_asserts
from tool_shed.test.base import test_db_util
from tool_shed.webapp import model
from ..base.api import (
    ShedApiTestCase,
    skip_if_api_v1,
)

CORRUPTED_PATH = "/old/wrong/path/column_maker.xml"


@dataclass
class CorruptedRepoFixture:
    """Tracks state for a repository with corrupted metadata."""

    repository: object  # API repository object
    db_repo: model.Repository
    metadata_revision_id: int
    corrupted_path: str


def corrupt_tool_config_path(repository, corrupted_path: str = CORRUPTED_PATH) -> CorruptedRepoFixture:
    """Corrupt tool_config path in repository metadata via direct DB access."""
    sa_session = test_db_util.sa_session()
    db_repo = test_db_util.get_repository_by_name_and_owner(repository.name, repository.owner)
    assert db_repo is not None
    assert len(db_repo.metadata_revisions) >= 1

    # Find a revision with tools
    metadata_revision = None
    for rev in db_repo.metadata_revisions:
        if rev.metadata and rev.metadata.get("tools"):
            metadata_revision = rev
            break
    assert metadata_revision is not None, "Expected repository to have tools"

    # Corrupt the metadata (must create new dict for MutableJSONType)
    new_metadata = copy.deepcopy(metadata_revision.metadata)
    new_metadata["tools"][0]["tool_config"] = corrupted_path
    metadata_revision.metadata = new_metadata
    sa_session.add(metadata_revision)
    sa_session.commit()

    # Verify corruption persisted
    sa_session.expire_all()
    metadata_revision = sa_session.get(model.RepositoryMetadata, metadata_revision.id)
    assert metadata_revision.metadata["tools"][0]["tool_config"] == corrupted_path

    return CorruptedRepoFixture(
        repository=repository,
        db_repo=db_repo,
        metadata_revision_id=metadata_revision.id,
        corrupted_path=corrupted_path,
    )


def metadata_contains_path(metadata_dict: dict, path: str) -> bool:
    """Check if any tool in metadata dict has the given tool_config path."""
    for rev_data in metadata_dict.values():
        for tool in rev_data.get("tools") or []:
            if tool.get("tool_config") == path:
                return True
    return False


def metadata_has_valid_paths(metadata_dict: dict, invalid_prefix: str = "/old/wrong") -> bool:
    """Check if metadata has at least one valid (non-corrupted) tool_config path."""
    for rev_data in metadata_dict.values():
        for tool in rev_data.get("tools") or []:
            tool_config = tool.get("tool_config", "")
            if tool_config and not tool_config.startswith(invalid_prefix):
                return True
    return False


class TestRepositoriesIntegration(ShedApiTestCase):
    @skip_if_api_v1
    def test_reset_metadata_dry_run_shows_corrupted_path_fix(self):
        """Verify dry_run=True shows before/after diff for corrupted tool_config paths.

        This simulates a scenario where repository metadata has stale absolute paths
        (e.g., after file_path config change). The dry_run preview should show:
        - repository_metadata_before: contains corrupted path
        - repository_metadata_after: contains fixed path
        - DB remains unchanged (dry_run doesn't persist)
        """
        repository = self.populator.setup_column_maker_repo(prefix="integcorrupt")
        fixture = corrupt_tool_config_path(repository)

        # Call reset_metadata API with dry_run=True, verbose=True
        response = self.api_interactor.post(
            f"repositories/{repository.id}/reset_metadata",
            params={"dry_run": True, "verbose": True},
        )
        api_asserts.assert_status_code_is_ok(response)
        result = response.json()

        assert result["dry_run"] is True
        assert result["status"] == "ok"
        assert result["repository_metadata_before"] is not None
        assert result["repository_metadata_after"] is not None

        before = result["repository_metadata_before"]
        after = result["repository_metadata_after"]

        assert metadata_contains_path(before, fixture.corrupted_path), (
            f"Expected before snapshot to contain corrupted path '{fixture.corrupted_path}'"
        )
        assert not metadata_contains_path(after, fixture.corrupted_path), (
            "After snapshot should not contain corrupted path"
        )
        assert metadata_has_valid_paths(after), (
            "Expected after snapshot to contain fixed path"
        )

        # Verify DB still has corrupted data (dry_run shouldn't persist)
        sa_session = test_db_util.sa_session()
        sa_session.expire_all()
        metadata_revision = sa_session.get(model.RepositoryMetadata, fixture.metadata_revision_id)
        assert metadata_revision.metadata["tools"][0]["tool_config"] == fixture.corrupted_path, (
            "dry_run should not have modified the database"
        )

    @skip_if_api_v1
    def test_reset_metadata_fixes_corrupted_path_when_not_dry_run(self):
        """Verify non-dry-run reset actually fixes corrupted tool_config paths."""
        repository = self.populator.setup_column_maker_repo(prefix="integfix")
        fixture = corrupt_tool_config_path(repository)

        # Call reset_metadata without dry_run
        response = self.api_interactor.post(
            f"repositories/{repository.id}/reset_metadata",
            params={"dry_run": False, "verbose": True},
        )
        api_asserts.assert_status_code_is_ok(response)
        result = response.json()
        assert result["dry_run"] is False
        assert result["status"] == "ok"

        # Verify DB now has fixed path
        sa_session = test_db_util.sa_session()
        sa_session.expire_all()
        stmt = (
            select(model.RepositoryMetadata)
            .where(model.RepositoryMetadata.repository_id == fixture.db_repo.id)
        )
        revisions = sa_session.scalars(stmt).all()
        assert len(revisions) >= 1

        # Build metadata dict from DB revisions for reuse of helper
        db_metadata = {str(rev.id): rev.metadata for rev in revisions if rev.metadata}
        assert metadata_has_valid_paths(db_metadata), (
            "Expected reset to fix the corrupted tool_config path"
        )
