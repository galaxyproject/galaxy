from galaxy.schema.workflows import (
    ToolShedRepositoryReference,
    UnavailableWorkflowTool,
)
from galaxy.workflow.missing_tools import (
    missing_repositories,
    parse_shed_tool_id,
)

SHED_TOOL_ID = "toolshed.g2.bx.psu.edu/repos/iuc/compose_text_param/compose_text_param/0.1.0"


def test_parse_shed_tool_id():
    repository = parse_shed_tool_id(SHED_TOOL_ID)
    assert repository is not None
    assert repository.tool_shed == "toolshed.g2.bx.psu.edu"
    assert repository.owner == "iuc"
    assert repository.name == "compose_text_param"
    assert repository.changeset_revision is None


def test_parse_shed_tool_id_ignores_local_tools():
    assert parse_shed_tool_id("cat1") is None


def test_parse_shed_tool_id_ignores_unparsable_ids():
    # a shed style id that does not have the expected number of components
    assert parse_shed_tool_id("toolshed.g2.bx.psu.edu/repos/iuc/compose_text_param") is None


def _unavailable(tool_id, repository=None):
    return UnavailableWorkflowTool(tool_id=tool_id, repository=repository)


def test_missing_repositories_dedupes_and_keeps_order():
    first = ToolShedRepositoryReference(tool_shed="shed", owner="iuc", name="a")
    again = ToolShedRepositoryReference(tool_shed="shed", owner="iuc", name="a")
    second = ToolShedRepositoryReference(tool_shed="shed", owner="iuc", name="b")
    repositories = missing_repositories(
        [_unavailable("a", first), _unavailable("a2", again), _unavailable("b", second)]
    )
    assert [repository.name for repository in repositories] == ["a", "b"]


def test_missing_repositories_skips_tools_without_a_repository():
    assert missing_repositories([_unavailable("cat1")]) == []


def test_parse_shed_tool_id_keeps_the_tool_and_version_wanted():
    """The version in the id decides which revision has to be installed, so it must survive."""
    repository = parse_shed_tool_id(SHED_TOOL_ID)
    assert repository is not None
    assert repository.tool_id == "compose_text_param"
    assert repository.tool_version == "0.1.0"
