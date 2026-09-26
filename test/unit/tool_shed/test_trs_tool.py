import pytest

from galaxy.exceptions import ObjectNotFound
from tool_shed.context import ProvidesRepositoriesContext
from tool_shed.managers.tools import tool_source_for
from tool_shed.managers.trs import get_tool
from tool_shed.webapp.model import Repository
from tool_shed_client.schema.trs import Tool
from ._util import upload_directories_to_repository


def test_get_tool(provides_repositories: ProvidesRepositoriesContext, new_repository: Repository):
    upload_directories_to_repository(provides_repositories, new_repository, "column_maker")
    owner = new_repository.user.username
    name = new_repository.name
    encoded_id = f"{owner}~{name}~Add_a_column1"
    tool: Tool = get_tool(provides_repositories, encoded_id)
    assert tool
    assert tool.organization == owner
    assert tool.id == encoded_id
    assert tool.aliases
    assert tool.aliases[0] == f"localhost/repos/{owner}/{name}/Add_a_column1"

    tool_versions = tool.versions
    assert len(tool_versions) == 3


@pytest.mark.parametrize(
    "tool_id",
    ["__SAMPLE_SHEET_TO_TABULAR__", "__FILTER_FROM_FILE__", "__FLATTEN__", "Filter1", "sort1", "Show beginning1"],
)
def test_get_stock_tool(provides_repositories: ProvidesRepositoriesContext, tool_id: str):
    tool = get_tool(provides_repositories, tool_id)
    assert tool.id == tool_id
    assert tool.organization == "galaxyproject"
    assert tool.name
    assert tool.versions
    for version in tool.versions:
        source, repository_metadata = tool_source_for(provides_repositories, tool_id, version.id)
        assert source.parse_id() == tool_id
        assert source.parse_version() == version.id
        assert repository_metadata is None
        assert version.author == ["galaxyproject"]
        assert version.descriptor_type is not None
        assert [descriptor.value for descriptor in version.descriptor_type] == ["GALAXY"]


def test_get_unknown_stock_tool(provides_repositories: ProvidesRepositoriesContext):
    with pytest.raises(ObjectNotFound):
        get_tool(provides_repositories, "unknown_stock_tool")


def test_stock_tool_versions_oldest_first(provides_repositories: ProvidesRepositoriesContext):
    tool = get_tool(provides_repositories, "multiple_versions_sorted")
    assert [version.id for version in tool.versions] == ["1.9", "1.10"]
    for version in tool.versions:
        source, repository_metadata = tool_source_for(provides_repositories, tool.id, version.id)
        assert source.parse_id() == tool.id
        assert source.parse_version() == version.id
        assert repository_metadata is None
