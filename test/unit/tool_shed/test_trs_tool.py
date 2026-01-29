from tool_shed.context import ProvidesRepositoriesContext
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
