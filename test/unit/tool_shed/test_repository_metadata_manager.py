import copy

from tool_shed.context import ProvidesRepositoriesContext
from tool_shed.managers import repositories as repository_manager
from tool_shed.metadata import repository_metadata_manager
from tool_shed.webapp.model import Repository
from ._util import upload_directories_to_repository


def test_reset_simple(provides_repositories: ProvidesRepositoriesContext, new_repository: Repository):
    shed_app = provides_repositories.app
    upload_directories_to_repository(provides_repositories, new_repository, "column_maker")
    assert len(new_repository.downloadable_revisions) == 3
    assert "2:" in new_repository.revision()
    rmm = repository_metadata_manager.RepositoryMetadataManager(
        provides_repositories,
        repository=new_repository,
        resetting_all_metadata_on_repository=True,
        updating_installed_repository=False,
        persist=False,
    )
    repo_path = new_repository.repo_path(app=shed_app)
    rmm.reset_all_metadata_on_repository_in_tool_shed(repository_clone_url=repo_path)
    assert len(new_repository.downloadable_revisions) == 3


def test_reset_on_repo_with_uninstallable_revisions(
    provides_repositories: ProvidesRepositoriesContext, new_repository: Repository
):
    shed_app = provides_repositories.app
    upload_directories_to_repository(provides_repositories, new_repository, "column_maker_with_download_gaps")
    assert len(new_repository.downloadable_revisions) == 3
    assert "3:" in new_repository.revision()
    rmm = repository_metadata_manager.RepositoryMetadataManager(
        provides_repositories,
        repository=new_repository,
        resetting_all_metadata_on_repository=True,
        updating_installed_repository=False,
        persist=False,
    )
    repo_path = new_repository.repo_path(app=shed_app)
    rmm.reset_all_metadata_on_repository_in_tool_shed(repository_clone_url=repo_path)
    assert len(new_repository.downloadable_revisions) == 3


def test_reset_dm_with_uninstallable_revisions(
    provides_repositories: ProvidesRepositoriesContext, new_repository: Repository
):
    shed_app = provides_repositories.app
    upload_directories_to_repository(provides_repositories, new_repository, "data_manager_gaps")
    assert len(new_repository.downloadable_revisions) == 1
    assert "2:" in new_repository.revision()
    rmm = repository_metadata_manager.RepositoryMetadataManager(
        provides_repositories,
        repository=new_repository,
        resetting_all_metadata_on_repository=True,
        updating_installed_repository=False,
        persist=False,
    )
    repo_path = new_repository.repo_path(app=shed_app)
    rmm.reset_all_metadata_on_repository_in_tool_shed(repository_clone_url=repo_path)
    assert len(new_repository.downloadable_revisions) == 2


def test_reset_dry_run_does_not_persist(
    provides_repositories: ProvidesRepositoriesContext, new_repository: Repository
):
    """Verify dry_run=True doesn't modify DB."""
    shed_app = provides_repositories.app
    upload_directories_to_repository(provides_repositories, new_repository, "column_maker")
    original_count = len(new_repository.downloadable_revisions)
    assert original_count == 3

    # Delete existing metadata to test that dry_run won't recreate it
    for rm in list(new_repository.metadata_revisions):
        provides_repositories.sa_session.delete(rm)
    provides_repositories.sa_session.commit()
    provides_repositories.sa_session.expire_all()
    assert len(new_repository.downloadable_revisions) == 0

    rmm = repository_metadata_manager.RepositoryMetadataManager(
        provides_repositories,
        repository=new_repository,
        resetting_all_metadata_on_repository=True,
        updating_installed_repository=False,
        persist=False,
    )
    repo_path = new_repository.repo_path(app=shed_app)
    result = rmm.reset_all_metadata_on_repository_in_tool_shed(
        repository_clone_url=repo_path, dry_run=True, verbose=True
    )

    # DB should remain unchanged (no metadata recreated)
    provides_repositories.sa_session.expire_all()
    assert len(new_repository.downloadable_revisions) == 0
    # But we should have gotten detailed info back
    assert result.changeset_details is not None
    assert len(result.changeset_details) > 0


def test_reset_verbose_returns_changeset_details(
    provides_repositories: ProvidesRepositoriesContext, new_repository: Repository
):
    """Verify verbose=True returns per-changeset info."""
    shed_app = provides_repositories.app
    upload_directories_to_repository(provides_repositories, new_repository, "column_maker")

    rmm = repository_metadata_manager.RepositoryMetadataManager(
        provides_repositories,
        repository=new_repository,
        resetting_all_metadata_on_repository=True,
        updating_installed_repository=False,
        persist=False,
    )
    repo_path = new_repository.repo_path(app=shed_app)
    result = rmm.reset_all_metadata_on_repository_in_tool_shed(
        repository_clone_url=repo_path, verbose=True
    )

    assert result.changeset_details is not None
    assert len(result.changeset_details) >= 1
    for detail in result.changeset_details:
        assert detail.changeset_revision
        assert detail.action in ["created", "updated", "skipped", "unchanged", "pending"]


def test_reset_without_verbose_omits_details(
    provides_repositories: ProvidesRepositoriesContext, new_repository: Repository
):
    """Verify verbose=False (default) omits changeset_details."""
    shed_app = provides_repositories.app
    upload_directories_to_repository(provides_repositories, new_repository, "column_maker")

    rmm = repository_metadata_manager.RepositoryMetadataManager(
        provides_repositories,
        repository=new_repository,
        resetting_all_metadata_on_repository=True,
        updating_installed_repository=False,
        persist=False,
    )
    repo_path = new_repository.repo_path(app=shed_app)
    result = rmm.reset_all_metadata_on_repository_in_tool_shed(
        repository_clone_url=repo_path, verbose=False
    )

    assert result.changeset_details is None


def test_reset_dry_run_with_gaps(
    provides_repositories: ProvidesRepositoriesContext, new_repository: Repository
):
    """Test dry_run with repo that has uninstallable revisions."""
    shed_app = provides_repositories.app
    upload_directories_to_repository(provides_repositories, new_repository, "column_maker_with_download_gaps")
    original_count = len(new_repository.downloadable_revisions)
    assert original_count == 3

    rmm = repository_metadata_manager.RepositoryMetadataManager(
        provides_repositories,
        repository=new_repository,
        resetting_all_metadata_on_repository=True,
        updating_installed_repository=False,
        persist=False,
    )
    repo_path = new_repository.repo_path(app=shed_app)
    result = rmm.reset_all_metadata_on_repository_in_tool_shed(
        repository_clone_url=repo_path, dry_run=True, verbose=True
    )

    # Should still report what would happen
    assert result.changeset_details is not None
    assert len(result.changeset_details) > 0


def test_reset_metadata_fixes_tool_config_path(
    provides_repositories: ProvidesRepositoriesContext, new_repository: Repository
):
    """
    Verify reset_metadata repairs tool_config paths when repository location changes.

    Use case: Galaxy's file_path changed, so stored absolute paths in DB are now incorrect.
    Reset metadata should regenerate paths based on current repo location.
    """
    shed_app = provides_repositories.app
    upload_directories_to_repository(provides_repositories, new_repository, "column_maker")

    # 1. Verify initial state has tool metadata with valid tool_config path
    repo_path = new_repository.repo_path(app=shed_app)
    metadata_revision = new_repository.metadata_revisions[0]
    metadata = metadata_revision.metadata
    assert "tools" in metadata
    tools = metadata["tools"]
    assert len(tools) >= 1

    original_tool_config = tools[0]["tool_config"]
    # Verify it's an absolute path based on repo_path
    assert original_tool_config.startswith(repo_path), (
        f"Expected tool_config to start with repo_path.\n"
        f"  tool_config: {original_tool_config}\n"
        f"  repo_path: {repo_path}"
    )

    # 2. Corrupt the tool_config path (simulate repo location change)
    corrupted_path = "/old/wrong/path/column_maker.xml"
    # Must create a new dict to ensure MutableJSONType detects the change
    new_metadata = copy.deepcopy(metadata)
    new_metadata["tools"][0]["tool_config"] = corrupted_path
    metadata_revision.metadata = new_metadata
    provides_repositories.sa_session.add(metadata_revision)
    provides_repositories.sa_session.commit()
    provides_repositories.sa_session.expire_all()

    # Verify corruption persisted
    metadata_revision = new_repository.metadata_revisions[0]
    assert metadata_revision.metadata["tools"][0]["tool_config"] == corrupted_path

    # 3. Run reset_metadata with verbose=True to get before/after snapshots
    encoded_id = shed_app.security.encode_id(new_repository.id)
    result = repository_manager.reset_metadata_on_repository(
        provides_repositories, encoded_id, verbose=True, repository_clone_url=repo_path
    )

    # 4. Verify before/after snapshots show the fix
    assert result.repository_metadata_before is not None, "Expected before snapshot"
    assert result.repository_metadata_after is not None, "Expected after snapshot"

    # Find the revision with tools in both before and after
    before_dict = result.repository_metadata_before.root
    after_dict = result.repository_metadata_after.root

    # The before snapshot should show the corrupted path
    before_has_corruption = False
    for _rev_key, rev_data in before_dict.items():
        if rev_data.tools:
            for tool in rev_data.tools:
                if tool.tool_config == corrupted_path:
                    before_has_corruption = True
                    break
    assert before_has_corruption, (
        f"Expected before snapshot to contain corrupted path '{corrupted_path}'\n"
        f"Before keys: {list(before_dict.keys())}"
    )

    # The after snapshot should show the fixed path (based on repo_path)
    after_has_fix = False
    for _rev_key, rev_data in after_dict.items():
        if rev_data.tools:
            for tool in rev_data.tools:
                if tool.tool_config.startswith(repo_path):
                    after_has_fix = True
                    break
    assert after_has_fix, (
        f"Expected after snapshot to contain fixed path starting with '{repo_path}'\n"
        f"After keys: {list(after_dict.keys())}"
    )

    # 5. Verify tool_config is actually fixed in the database
    provides_repositories.sa_session.expire_all()
    metadata_revision = new_repository.metadata_revisions[0]
    fixed_tool_config = metadata_revision.metadata["tools"][0]["tool_config"]
    assert fixed_tool_config != corrupted_path, "tool_config should have been fixed"
    assert fixed_tool_config.startswith(repo_path), (
        f"Fixed tool_config should be based on current repo_path.\n"
        f"  fixed_tool_config: {fixed_tool_config}\n"
        f"  repo_path: {repo_path}"
    )


def test_reset_metadata_dry_run_shows_visual_diff(
    provides_repositories: ProvidesRepositoriesContext, new_repository: Repository
):
    """
    Verify dry_run=True shows accurate before/after diff without modifying database.

    The "after" snapshot should show what WOULD be generated (from regenerated metadata),
    enabling a visual diff even when dry_run=True prevents DB changes.
    """
    shed_app = provides_repositories.app
    upload_directories_to_repository(provides_repositories, new_repository, "column_maker")

    # 1. Get initial state
    repo_path = new_repository.repo_path(app=shed_app)
    metadata_revision = new_repository.metadata_revisions[0]
    metadata = metadata_revision.metadata
    assert "tools" in metadata
    original_tool_config = metadata["tools"][0]["tool_config"]
    assert original_tool_config.startswith(repo_path)

    # 2. Corrupt the tool_config path
    corrupted_path = "/old/wrong/path/column_maker.xml"
    new_metadata = copy.deepcopy(metadata)
    new_metadata["tools"][0]["tool_config"] = corrupted_path
    metadata_revision.metadata = new_metadata
    provides_repositories.sa_session.add(metadata_revision)
    provides_repositories.sa_session.commit()
    provides_repositories.sa_session.expire_all()

    # Verify corruption persisted
    metadata_revision = new_repository.metadata_revisions[0]
    assert metadata_revision.metadata["tools"][0]["tool_config"] == corrupted_path

    # 3. Run reset_metadata with dry_run=True
    encoded_id = shed_app.security.encode_id(new_repository.id)
    result = repository_manager.reset_metadata_on_repository(
        provides_repositories, encoded_id, dry_run=True, verbose=True, repository_clone_url=repo_path
    )

    # 4. Verify before snapshot captured the corrupted state
    assert result.repository_metadata_before is not None, "Expected before snapshot"
    before_dict = result.repository_metadata_before.root
    before_has_corruption = False
    for _rev_key, rev_data in before_dict.items():
        if rev_data.tools:
            for tool in rev_data.tools:
                if tool.tool_config == corrupted_path:
                    before_has_corruption = True
                    break
    assert before_has_corruption, "Before snapshot should show corrupted path"

    # 5. Verify "after" snapshot shows what WOULD be fixed (from regenerated metadata)
    # This is the key new functionality - dry_run now shows the diff!
    assert result.repository_metadata_after is not None, "Expected after snapshot"
    after_dict = result.repository_metadata_after.root
    after_has_fix = False
    for _rev_key, rev_data in after_dict.items():
        if rev_data.tools:
            for tool in rev_data.tools:
                if tool.tool_config.startswith(repo_path) and tool.tool_config != corrupted_path:
                    after_has_fix = True
                    break
    assert after_has_fix, (
        f"After snapshot should show what the fixed path WOULD be.\n"
        f"This enables visual diff even with dry_run=True.\n"
        f"After keys: {list(after_dict.keys())}"
    )

    # 6. Verify database was NOT modified (corruption should still be there)
    # This is the key assertion - dry_run should not change anything
    provides_repositories.sa_session.expire_all()
    metadata_revision = new_repository.metadata_revisions[0]
    db_tool_config = metadata_revision.metadata["tools"][0]["tool_config"]
    assert db_tool_config == corrupted_path, (
        f"dry_run should not modify database.\n"
        f"  Expected: {corrupted_path}\n"
        f"  Got: {db_tool_config}"
    )
