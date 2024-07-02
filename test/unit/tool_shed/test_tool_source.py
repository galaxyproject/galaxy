from tool_shed.context import ProvidesRepositoriesContext
from tool_shed.managers.tools import (
    tool_input_models_cached_for,
    tool_input_models_for,
    tool_source_for,
)
from tool_shed.webapp.model import Repository
from ._util import upload_directories_to_repository


def test_get_tool(provides_repositories: ProvidesRepositoriesContext, new_repository: Repository):
    upload_directories_to_repository(provides_repositories, new_repository, "column_maker")
    owner = new_repository.user.username
    name = new_repository.name
    encoded_id = f"{owner}~{name}~Add_a_column1"

    repo_path = new_repository.repo_path(app=provides_repositories.app)
    tool_source = tool_source_for(provides_repositories, encoded_id, "1.2.0", repository_clone_url=repo_path)
    assert tool_source.parse_id() == "Add_a_column1"
    bundle = tool_input_models_for(provides_repositories, encoded_id, "1.2.0", repository_clone_url=repo_path)
    assert len(bundle.input_models) == 3

    cached_bundle = tool_input_models_cached_for(
        provides_repositories, encoded_id, "1.2.0", repository_clone_url=repo_path
    )
    assert len(cached_bundle.input_models) == 3

    cached_bundle = tool_input_models_cached_for(
        provides_repositories, encoded_id, "1.2.0", repository_clone_url=repo_path
    )
    assert len(cached_bundle.input_models) == 3


def test_stock_bundle(provides_repositories: ProvidesRepositoriesContext):
    cached_bundle = tool_input_models_cached_for(
        provides_repositories, "__ZIP_COLLECTION__", "1.0.0", repository_clone_url=None
    )
    assert len(cached_bundle.input_models) == 2
