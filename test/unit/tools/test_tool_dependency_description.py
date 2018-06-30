from galaxy.model import tool_shed_install
from galaxy.tools.deps import (
    dependencies,
    requirements
)


def test_serialization():
    repository = tool_shed_install.ToolShedRepository(
        owner="devteam",
        name="tophat",
        installed_changeset_revision="abcdefghijk",
    )
    dependency = tool_shed_install.ToolDependency(
        name="tophat",
        version="2.0",
        type="package",
        status=tool_shed_install.ToolDependency.installation_status.INSTALLED,
    )
    dependency.tool_shed_repository = repository
    tool_requirement = requirements.ToolRequirement(
        name="tophat",
        version="2.0",
        type="package",
    )
    descript = dependencies.DependenciesDescription(
        requirements=[tool_requirement],
        installed_tool_dependencies=[dependency],
    )
    result_descript = dependencies.DependenciesDescription.from_dict(
        descript.to_dict()
    )
    result_requirement = result_descript.requirements[0]
    assert result_requirement.name == "tophat"
    assert result_requirement.version == "2.0"
    assert result_requirement.type == "package"

    result_tool_shed_dependency = list(result_descript.installed_tool_dependencies)[0]
    result_tool_shed_dependency.name = "tophat"
    result_tool_shed_dependency.version = "2.0"
    result_tool_shed_dependency.type = "package"
    result_tool_shed_repository = result_tool_shed_dependency.tool_shed_repository
    result_tool_shed_repository.name = "tophat"
    result_tool_shed_repository.owner = "devteam"
    result_tool_shed_repository.installed_changeset_revision = "abcdefghijk"
