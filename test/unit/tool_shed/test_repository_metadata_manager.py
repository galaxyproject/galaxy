from tool_shed.context import ProvidesRepositoriesContext
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
