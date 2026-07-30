from galaxy.schema.workflows import (
    ToolShedRepositoryReference,
    UnavailableWorkflowTool,
)
from galaxy.workflow import missing_tools
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


class FakeShed:
    """Stands in for the tool shed API that revision_for_tool_version queries."""

    def __init__(self, metadata):
        self.metadata = metadata
        self.tool_shed_registry = self

    def url_auth(self, _url):
        return None

    def response_for(self, pathspec):
        if pathspec[-1] == "repositories":
            return [{"id": "repo1"}]
        return self.metadata


def _patch_shed(monkeypatch, shed, fail=False):
    def fake_get(app, tool_shed_url, pathspec, params):
        if fail:
            raise OSError("shed unreachable")
        return shed.response_for(pathspec)

    monkeypatch.setattr(missing_tools, "_shed_get", fake_get)


METADATA = {
    "20:fbf99087e067": {
        "numeric_revision": 20,
        "changeset_revision": "fbf99087e067",
        "tools": [{"id": "tp_easyjoin_tool", "version": "9.3+galaxy1"}],
    },
    "21:86755160afbf": {
        "numeric_revision": 21,
        "changeset_revision": "86755160afbf",
        "tools": [{"id": "tp_easyjoin_tool", "version": "9.3+galaxy1"}],
    },
    "25:ab83aa685821": {
        "numeric_revision": 25,
        "changeset_revision": "ab83aa685821",
        "tools": [{"id": "tp_easyjoin_tool", "version": "9.5+galaxy3"}],
    },
}


def test_revision_for_tool_version_picks_the_revision_with_that_version(monkeypatch):
    """Installing the newest revision installs the newest tool, which a pinned workflow did not ask for."""
    shed = FakeShed(METADATA)
    _patch_shed(monkeypatch, shed)
    revision = missing_tools.revision_for_tool_version(
        shed, "https://shed", "text_processing", "bgruening", "tp_easyjoin_tool", "9.3+galaxy1"
    )
    # 9.3+galaxy1 is in two revisions, the newer of the two is the one to install
    assert revision == "86755160afbf"


def test_revision_for_tool_version_finds_a_newer_version_too(monkeypatch):
    shed = FakeShed(METADATA)
    _patch_shed(monkeypatch, shed)
    revision = missing_tools.revision_for_tool_version(
        shed, "https://shed", "text_processing", "bgruening", "tp_easyjoin_tool", "9.5+galaxy3"
    )
    assert revision == "ab83aa685821"


def test_revision_for_tool_version_gives_up_on_an_unknown_version(monkeypatch):
    """The caller falls back to the newest revision rather than installing nothing."""
    shed = FakeShed(METADATA)
    _patch_shed(monkeypatch, shed)
    revision = missing_tools.revision_for_tool_version(
        shed, "https://shed", "text_processing", "bgruening", "tp_easyjoin_tool", "0.0+nope"
    )
    assert revision is None


def test_revision_for_tool_version_survives_an_unreachable_shed(monkeypatch):
    shed = FakeShed(METADATA)
    _patch_shed(monkeypatch, shed, fail=True)
    revision = missing_tools.revision_for_tool_version(
        shed, "https://shed", "text_processing", "bgruening", "tp_easyjoin_tool", "9.3+galaxy1"
    )
    assert revision is None
