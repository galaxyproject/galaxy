from tool_shed.context import ProvidesRepositoriesContext
from tool_shed.util.repository_content_util import upload_tar
from tool_shed.webapp.model import (
    Repository,
    User,
)
from ._util import (
    attach_category,
    create_category,
    repository_fixture,
    TEST_DATA_FILES,
    TestToolShedApp,
)


def test_create_repository(shed_app: TestToolShedApp, new_user: User):
    name = "testname"
    manager = shed_app.hgweb_config_manager
    entry = None
    entry_name = f"repos/{new_user.username}/{name}"
    try:
        entry = manager.get_entry(entry_name)
    except Exception:
        pass
    assert not entry
    repository_fixture(shed_app, new_user, name)
    entry = manager.get_entry(entry_name)
    assert entry


def test_upload_tar(provides_repositories: ProvidesRepositoriesContext, new_repository: Repository):
    tar_resource = TEST_DATA_FILES.joinpath("column_maker/column_maker.tar")
    old_tip = new_repository.tip()
    upload_ok, _, _, alert, dirs_removed, files_removed = upload_tar(
        provides_repositories,
        new_repository.user.username,
        new_repository,
        tar_resource,
        commit_message="Commit Message",
    )
    assert upload_ok
    assert alert == ""
    assert dirs_removed == 0
    assert files_removed == 0
    new_tip = new_repository.tip()
    assert old_tip != new_tip
    changesets = new_repository.get_changesets_for_setting_metadata(provides_repositories.app)
    assert len(changesets) == 1
    for change in changesets:
        ctx = new_repository.hg_repo[change]
        assert str(ctx) == new_tip


def test_upload_fails_if_contains_symlink(
    provides_repositories: ProvidesRepositoriesContext, new_repository: Repository
):
    tar_resource = TEST_DATA_FILES.joinpath("safetar_with_symlink.tar")
    upload_ok, message, _, _, _, _ = upload_tar(
        provides_repositories,
        new_repository.user.username,
        new_repository,
        tar_resource,
        commit_message="Commit Message",
    )
    assert not upload_ok
    assert "Invalid paths" in message


def test_upload_dry_run_ok(provides_repositories: ProvidesRepositoriesContext, new_repository: Repository):
    tar_resource = TEST_DATA_FILES.joinpath("column_maker/column_maker.tar")
    old_tip = new_repository.tip()
    upload_ok, _, _, alert, dirs_removed, files_removed = upload_tar(
        provides_repositories,
        new_repository.user.username,
        new_repository,
        tar_resource,
        commit_message="Commit Message",
        dry_run=True,
    )
    assert upload_ok
    assert alert == ""
    assert dirs_removed == 0
    assert files_removed == 0
    new_tip = new_repository.tip()
    assert old_tip == new_tip


def test_category_count(provides_repositories: ProvidesRepositoriesContext, new_repository: Repository):
    category = create_category(provides_repositories, {"name": "test_category_count_1"})
    attach_category(provides_repositories, new_repository, category)

    category = new_repository.categories[0].category
    assert category.active_repository_count() == 1

    tar_resource = TEST_DATA_FILES.joinpath("column_maker/column_maker.tar")
    upload_ok, *_ = upload_tar(
        provides_repositories,
        new_repository.user.username,
        new_repository,
        tar_resource,
        commit_message="Commit Message",
    )
    assert upload_ok

    category = new_repository.categories[0].category
    assert category.active_repository_count() == 1


def test_upload_dry_run_failed(provides_repositories: ProvidesRepositoriesContext, new_repository: Repository):
    tar_resource = TEST_DATA_FILES.joinpath("safetar_with_symlink.tar")
    upload_ok, message, _, _, _, _ = upload_tar(
        provides_repositories,
        new_repository.user.username,
        new_repository,
        tar_resource,
        commit_message="Commit Message",
        dry_run=True,
    )
    assert not upload_ok
    assert "Invalid paths" in message
