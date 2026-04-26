"""Tests for the Tool Shed search client and high-level service.

Fixtures are synced from packages/search/test/fixtures/ in the
galaxy-tool-util TS monorepo (`make push-toolshed-search-fixtures`); both test
suites consume the same JSON shapes.
"""

import json
import os

import pytest
import responses
from pydantic import ValidationError

from galaxy.tool_util.workflow_state._toolshed_search_client import (
    build_repo_query,
    get_latest_trs_tool_version,
    get_tool_revisions,
    get_trs_tool_versions,
    iterate_repo_search_pages,
    iterate_tool_search_pages,
    search_repositories,
    search_tools,
    ToolFetchError,
)
from galaxy.tool_util.workflow_state._toolshed_search_models import (
    SearchResults,
    ToolSearchHit,
)
from galaxy.tool_util.workflow_state.tool_search import (
    normalize_hit,
    to_trs_tool_id,
    tool_id_from_trs,
    ToolSource,
)

FIXTURE_ROOT = os.path.join(os.path.dirname(__file__), "fixtures", "toolshed_search")
TS_FIXTURES = os.path.join(FIXTURE_ROOT, "toolshed-search")
REPO_FIXTURES = os.path.join(FIXTURE_ROOT, "toolshed-repo-search")
REV_FIXTURES = os.path.join(FIXTURE_ROOT, "toolshed-revisions")

TOOLSHED = "https://toolshed.example"


def _load(path):
    with open(path) as f:
        return json.load(f)


# -- model normalization --


def test_search_results_coerces_stringified_pagination():
    payload = _load(os.path.join(TS_FIXTURES, "with-optional-fields.json"))
    results = SearchResults[ToolSearchHit].model_validate(payload)
    assert results.total_results == 1
    assert results.page == 1
    assert results.page_size == 10
    assert results.hits[0].tool.version == "0.74+galaxy0"
    assert results.hits[0].tool.changeset_revision == "abc123def456"


def test_search_results_empty_fixture():
    payload = _load(os.path.join(TS_FIXTURES, "empty.json"))
    results = SearchResults[ToolSearchHit].model_validate(payload)
    assert results.total_results == 0
    assert results.hits == []


def test_search_results_rejects_non_numeric_pagination():
    with pytest.raises(ValidationError):
        SearchResults[ToolSearchHit].model_validate(
            {
                "total_results": "not-a-number",
                "page": 1,
                "page_size": 10,
                "hostname": "x",
                "hits": [],
            }
        )


# -- build_repo_query --


def test_build_repo_query_passes_query_through():
    assert build_repo_query("fastqc") == "fastqc"


def test_build_repo_query_appends_owner_and_simple_category():
    assert build_repo_query("fastqc", owner="devteam", category="sequence") == "fastqc owner:devteam category:sequence"


def test_build_repo_query_quotes_categories_with_whitespace():
    assert build_repo_query("", category="sequence analysis") == 'category:"sequence analysis"'


# -- to_trs_tool_id --


def test_to_trs_tool_id_passthrough():
    assert to_trs_tool_id("devteam~fastqc~fastqc") == "devteam~fastqc~fastqc"


def test_to_trs_tool_id_pretty_form():
    assert to_trs_tool_id("devteam/fastqc/fastqc") == "devteam~fastqc~fastqc"


def test_to_trs_tool_id_rejects_garbage():
    with pytest.raises(ValueError):
        to_trs_tool_id("not-a-tool-id")


def test_tool_id_from_trs():
    assert (
        tool_id_from_trs("https://toolshed.g2.bx.psu.edu", "devteam~fastqc~fastqc")
        == "toolshed.g2.bx.psu.edu/repos/devteam/fastqc/fastqc"
    )


# -- normalize_hit --


def test_normalize_hit_builds_full_tool_id_with_version():
    payload = _load(os.path.join(TS_FIXTURES, "with-optional-fields.json"))
    hit = SearchResults[ToolSearchHit].model_validate(payload).hits[0]
    source = ToolSource(type="toolshed", url="https://toolshed.example")
    n = normalize_hit(hit, source)
    assert n.trs_tool_id == "devteam~fastqc~fastqc"
    assert n.full_tool_id == "toolshed.example/repos/devteam/fastqc/fastqc/0.74+galaxy0"
    assert n.version == "0.74+galaxy0"


# -- HTTP client (search_tools) --


@responses.activate
def test_search_tools_returns_normalized_payload():
    payload = _load(os.path.join(TS_FIXTURES, "with-optional-fields.json"))
    responses.add(responses.GET, f"{TOOLSHED}/api/tools", json=payload, status=200)
    result = search_tools(TOOLSHED, "fastqc", page=1, page_size=10)
    assert result.total_results == 1
    assert result.hits[0].tool.id == "fastqc"


@responses.activate
def test_search_tools_treats_404_as_empty_page():
    responses.add(responses.GET, f"{TOOLSHED}/api/tools", json={"err": "ObjectNotFound"}, status=404)
    result = search_tools(TOOLSHED, "missing", page=99, page_size=10)
    assert result.total_results == 0
    assert result.hits == []


@responses.activate
def test_search_tools_raises_tool_fetch_error_on_500():
    responses.add(responses.GET, f"{TOOLSHED}/api/tools", body="boom", status=500)
    with pytest.raises(ToolFetchError) as excinfo:
        search_tools(TOOLSHED, "fastqc")
    assert excinfo.value.status == 500


@responses.activate
def test_search_tools_raises_on_malformed_json():
    responses.add(responses.GET, f"{TOOLSHED}/api/tools", body="not-json", status=200)
    with pytest.raises(ToolFetchError):
        search_tools(TOOLSHED, "fastqc")


@responses.activate
def test_iterate_tool_search_pages_stops_at_partial_page():
    full = _load(os.path.join(TS_FIXTURES, "fastqc-page1.json"))
    # First page: full size; second page: empty.
    responses.add(responses.GET, f"{TOOLSHED}/api/tools", json=full, status=200)
    responses.add(
        responses.GET,
        f"{TOOLSHED}/api/tools",
        json=_load(os.path.join(TS_FIXTURES, "empty.json")),
        status=200,
    )
    pages = list(iterate_tool_search_pages(TOOLSHED, "fastqc", page_size=len(full["hits"])))
    assert len(pages) == 2
    assert pages[1].hits == []


@responses.activate
def test_iterate_tool_search_pages_stops_at_short_partial_page():
    """Stops on a single page whose len < page_size, without a follow-up empty fetch."""
    full = _load(os.path.join(TS_FIXTURES, "fastqc-page1.json"))
    short = dict(full)
    short["hits"] = full["hits"][: max(1, len(full["hits"]) - 1)]
    # Register only one response — if the iterator wrongly requests page 2,
    # responses will fail the test with a ConnectionError.
    responses.add(responses.GET, f"{TOOLSHED}/api/tools", json=short, status=200)
    pages = list(iterate_tool_search_pages(TOOLSHED, "fastqc", page_size=len(full["hits"])))
    assert len(pages) == 1
    assert len(pages[0].hits) == len(short["hits"])


# -- HTTP client (search_repositories) --


@responses.activate
def test_search_repositories_with_owner_filter():
    payload = _load(os.path.join(REPO_FIXTURES, "fastqc-owner-devteam.json"))
    responses.add(responses.GET, f"{TOOLSHED}/api/repositories", json=payload, status=200)
    result = search_repositories(TOOLSHED, "fastqc", owner="devteam")
    assert all(h.repository.repo_owner_username == "devteam" for h in result.hits)


@responses.activate
def test_iterate_repo_search_pages_stops_on_empty():
    responses.add(
        responses.GET,
        f"{TOOLSHED}/api/repositories",
        json=_load(os.path.join(REPO_FIXTURES, "empty.json")),
        status=200,
    )
    pages = list(iterate_repo_search_pages(TOOLSHED, "nothing", page_size=10))
    assert len(pages) == 1
    assert pages[0].hits == []


# -- get_tool_revisions --


@responses.activate
def test_get_tool_revisions_orders_oldest_to_newest():
    repo = _load(os.path.join(REV_FIXTURES, "fastqc-repo.json"))
    metadata = _load(os.path.join(REV_FIXTURES, "fastqc-metadata.json"))
    ordered = _load(os.path.join(REV_FIXTURES, "fastqc-ordered.json"))
    repo_id = repo[0]["id"]
    responses.add(responses.GET, f"{TOOLSHED}/api/repositories", json=repo, status=200)
    responses.add(
        responses.GET,
        f"{TOOLSHED}/api/repositories/{repo_id}/metadata",
        json=metadata,
        status=200,
    )
    responses.add(
        responses.GET,
        f"{TOOLSHED}/api/repositories/get_ordered_installable_revisions",
        json=ordered,
        status=200,
    )
    matches = get_tool_revisions(TOOLSHED, owner="devteam", repo="fastqc", tool_id="fastqc")
    assert matches, "expected at least one revision"
    assert matches == sorted(matches, key=lambda m: m.order)


@responses.activate
def test_get_tool_revisions_filters_by_tool_version():
    repo = _load(os.path.join(REV_FIXTURES, "fastqc-repo.json"))
    metadata = _load(os.path.join(REV_FIXTURES, "fastqc-metadata.json"))
    ordered = _load(os.path.join(REV_FIXTURES, "fastqc-ordered.json"))
    repo_id = repo[0]["id"]
    responses.add(responses.GET, f"{TOOLSHED}/api/repositories", json=repo, status=200)
    responses.add(
        responses.GET,
        f"{TOOLSHED}/api/repositories/{repo_id}/metadata",
        json=metadata,
        status=200,
    )
    responses.add(
        responses.GET,
        f"{TOOLSHED}/api/repositories/get_ordered_installable_revisions",
        json=ordered,
        status=200,
    )
    all_matches = get_tool_revisions(TOOLSHED, owner="devteam", repo="fastqc", tool_id="fastqc")
    target_version = all_matches[-1].tool_version
    responses.add(responses.GET, f"{TOOLSHED}/api/repositories", json=repo, status=200)
    responses.add(
        responses.GET,
        f"{TOOLSHED}/api/repositories/{repo_id}/metadata",
        json=metadata,
        status=200,
    )
    responses.add(
        responses.GET,
        f"{TOOLSHED}/api/repositories/get_ordered_installable_revisions",
        json=ordered,
        status=200,
    )
    filtered = get_tool_revisions(
        TOOLSHED,
        owner="devteam",
        repo="fastqc",
        tool_id="fastqc",
        version=target_version,
    )
    assert filtered, "expected at least one match for the target version"
    assert all(m.tool_version == target_version for m in filtered)
    assert len(filtered) <= len(all_matches)


@responses.activate
def test_get_tool_revisions_empty_repo_returns_empty_list():
    responses.add(responses.GET, f"{TOOLSHED}/api/repositories", json=[], status=200)
    matches = get_tool_revisions(TOOLSHED, owner="ghost", repo="nope", tool_id="nope")
    assert matches == []


# -- TRS versions --


@responses.activate
def test_get_trs_tool_versions_and_latest():
    payload = [
        {
            "id": "0.72+galaxy0",
            "name": None,
            "url": "https://toolshed.example/.../versions/0.72+galaxy0",
            "descriptor_type": ["GALAXY"],
            "author": [],
        },
        {
            "id": "0.74+galaxy0",
            "name": None,
            "url": "https://toolshed.example/.../versions/0.74+galaxy0",
            "descriptor_type": ["GALAXY"],
            "author": [],
        },
    ]
    responses.add(
        responses.GET,
        f"{TOOLSHED}/api/ga4gh/trs/v2/tools/devteam~fastqc~fastqc/versions",
        json=payload,
        status=200,
    )
    versions = get_trs_tool_versions(TOOLSHED, "devteam~fastqc~fastqc")
    assert [v.id for v in versions] == ["0.72+galaxy0", "0.74+galaxy0"]


@responses.activate
def test_get_latest_trs_tool_version_none_for_empty():
    responses.add(
        responses.GET,
        f"{TOOLSHED}/api/ga4gh/trs/v2/tools/devteam~fastqc~fastqc/versions",
        json=[],
        status=200,
    )
    assert get_latest_trs_tool_version(TOOLSHED, "devteam~fastqc~fastqc") is None
