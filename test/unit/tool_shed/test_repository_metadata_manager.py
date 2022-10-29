from tool_shed.metadata import repository_metadata_manager
from tool_shed.webapp.model import Repository
from ._util import (
    patch_url_for,
    TestToolShedApp,
    upload_directories_to_repository,
)


@patch_url_for
def test_reset_simple(shed_app: TestToolShedApp, new_repository: Repository):
    upload_directories_to_repository(shed_app, new_repository, "column_maker")
    assert len(new_repository.downloadable_revisions) == 3
    assert "2:" in new_repository.revision()
    rmm = repository_metadata_manager.RepositoryMetadataManager(
        app=shed_app,
        user=new_repository.user,
        repository=new_repository,
        resetting_all_metadata_on_repository=True,
        updating_installed_repository=False,
        persist=False,
    )
    repo_path = new_repository.repo_path(app=shed_app)
    rmm.reset_all_metadata_on_repository_in_tool_shed(repository_clone_url=repo_path)
    assert len(new_repository.downloadable_revisions) == 3


@patch_url_for
def test_reset_on_repo_with_uninstallable_revisions(shed_app: TestToolShedApp, new_repository: Repository):
    upload_directories_to_repository(shed_app, new_repository, "column_maker_with_download_gaps")
    assert len(new_repository.downloadable_revisions) == 3
    assert "3:" in new_repository.revision()
    rmm = repository_metadata_manager.RepositoryMetadataManager(
        app=shed_app,
        user=new_repository.user,
        repository=new_repository,
        resetting_all_metadata_on_repository=True,
        updating_installed_repository=False,
        persist=False,
    )
    repo_path = new_repository.repo_path(app=shed_app)
    rmm.reset_all_metadata_on_repository_in_tool_shed(repository_clone_url=repo_path)
    assert len(new_repository.downloadable_revisions) == 3
