"""End-to-end-ish tests for the four ``gxwf`` Tool Shed subcommands."""

import json
import os

import responses

from galaxy.tool_util.workflow_state.scripts import gxwf

FIXTURE_ROOT = os.path.join(os.path.dirname(__file__), "fixtures", "toolshed_search")


def _load(rel):
    with open(os.path.join(FIXTURE_ROOT, rel)) as f:
        return json.load(f)


def _run(argv, monkeypatch, capsys):
    parser = gxwf.build_parser()
    args = parser.parse_args(argv)
    code = args.func(args) or 0
    captured = capsys.readouterr()
    return code, captured.out, captured.err


@responses.activate
def test_tool_search_human_output(capsys, monkeypatch):
    payload = _load("toolshed-search/with-optional-fields.json")
    responses.add(responses.GET, "https://toolshed.example/api/tools", json=payload, status=200)
    responses.add(
        responses.GET,
        "https://toolshed.example/api/tools",
        json=_load("toolshed-search/empty.json"),
        status=200,
    )
    code, out, _err = _run(
        ["tool-search", "fastqc", "--toolshed-url", "https://toolshed.example", "--page-size", "1"],
        monkeypatch,
        capsys,
    )
    assert code == 0
    assert "owner/repo" in out
    assert "devteam/fastqc" in out


@responses.activate
def test_tool_search_json_envelope(capsys, monkeypatch):
    responses.add(
        responses.GET,
        "https://toolshed.example/api/tools",
        json=_load("toolshed-search/with-optional-fields.json"),
        status=200,
    )
    responses.add(
        responses.GET,
        "https://toolshed.example/api/tools",
        json=_load("toolshed-search/empty.json"),
        status=200,
    )
    code, out, _err = _run(
        [
            "tool-search",
            "fastqc",
            "--toolshed-url",
            "https://toolshed.example",
            "--page-size",
            "1",
            "--json",
        ],
        monkeypatch,
        capsys,
    )
    assert code == 0
    envelope = json.loads(out)
    assert envelope["query"] == "fastqc"
    assert envelope["hits"][0]["trsToolId"] == "devteam~fastqc~fastqc"


@responses.activate
def test_tool_search_match_name_drops_off_topic_hits(capsys, monkeypatch):
    """--match-name keeps only hits whose tool name shares a token with the query."""
    payload = _load("toolshed-search/with-optional-fields.json")
    # Mutate the fixture: rename the tool so the query "fastqc" no longer matches.
    payload["hits"][0]["tool"]["name"] = "Other Tool"
    responses.add(
        responses.GET,
        "https://toolshed.example/api/tools",
        json=payload,
        status=200,
    )
    # Iterator continues to page 2 because page 1 was full; serve an empty page.
    responses.add(
        responses.GET,
        "https://toolshed.example/api/tools",
        json=_load("toolshed-search/empty.json"),
        status=200,
    )
    code, _out, err = _run(
        [
            "tool-search",
            "fastqc",
            "--toolshed-url",
            "https://toolshed.example",
            "--page-size",
            "1",
            "--match-name",
        ],
        monkeypatch,
        capsys,
    )
    assert code == 2
    assert "No hits" in err


@responses.activate
def test_tool_search_fetch_error_exits_3(capsys, monkeypatch):
    responses.add(responses.GET, "https://toolshed.example/api/tools", body="boom", status=500)
    code, _out, err = _run(
        ["tool-search", "fastqc", "--toolshed-url", "https://toolshed.example"],
        monkeypatch,
        capsys,
    )
    assert code == 3
    assert "Tool Shed search failed" in err


@responses.activate
def test_tool_search_no_hits_exits_2(capsys, monkeypatch):
    responses.add(
        responses.GET,
        "https://toolshed.example/api/tools",
        json=_load("toolshed-search/empty.json"),
        status=200,
    )
    code, _out, err = _run(
        ["tool-search", "nothing", "--toolshed-url", "https://toolshed.example"],
        monkeypatch,
        capsys,
    )
    assert code == 2
    assert "No hits" in err


@responses.activate
def test_repo_search_owner_filter(capsys, monkeypatch):
    payload = _load("toolshed-repo-search/fastqc-owner-devteam.json")
    responses.add(
        responses.GET,
        "https://toolshed.example/api/repositories",
        json=payload,
        status=200,
    )
    responses.add(
        responses.GET,
        "https://toolshed.example/api/repositories",
        json=_load("toolshed-repo-search/empty.json"),
        status=200,
    )
    code, out, _err = _run(
        [
            "repo-search",
            "fastqc",
            "--owner",
            "devteam",
            "--toolshed-url",
            "https://toolshed.example",
            "--page-size",
            str(max(len(payload["hits"]), 1)),
            "--json",
        ],
        monkeypatch,
        capsys,
    )
    assert code == 0
    envelope = json.loads(out)
    assert envelope["filters"]["owner"] == "devteam"


@responses.activate
def test_tool_versions_latest(capsys, monkeypatch):
    responses.add(
        responses.GET,
        "https://toolshed.example/api/ga4gh/trs/v2/tools/devteam~fastqc~fastqc/versions",
        json=[
            {"id": "0.72+galaxy0", "name": None, "url": "u", "descriptor_type": ["GALAXY"], "author": []},
            {"id": "0.74+galaxy0", "name": None, "url": "u", "descriptor_type": ["GALAXY"], "author": []},
        ],
        status=200,
    )
    code, out, _err = _run(
        [
            "tool-versions",
            "devteam/fastqc/fastqc",
            "--latest",
            "--toolshed-url",
            "https://toolshed.example",
        ],
        monkeypatch,
        capsys,
    )
    assert code == 0
    assert out.strip() == "0.74+galaxy0"


@responses.activate
def test_tool_versions_json_empty_exits_2(capsys, monkeypatch):
    responses.add(
        responses.GET,
        "https://toolshed.example/api/ga4gh/trs/v2/tools/devteam~fastqc~fastqc/versions",
        json=[],
        status=200,
    )
    code, out, _err = _run(
        [
            "tool-versions",
            "devteam/fastqc/fastqc",
            "--latest",
            "--json",
            "--toolshed-url",
            "https://toolshed.example",
        ],
        monkeypatch,
        capsys,
    )
    assert code == 2
    envelope = json.loads(out)
    assert envelope == {"trsToolId": "devteam~fastqc~fastqc", "versions": []}


@responses.activate
def test_tool_revisions_latest_json_envelope(capsys, monkeypatch):
    repo = _load("toolshed-revisions/fastqc-repo.json")
    metadata = _load("toolshed-revisions/fastqc-metadata.json")
    ordered = _load("toolshed-revisions/fastqc-ordered.json")
    responses.add(responses.GET, "https://toolshed.example/api/repositories", json=repo, status=200)
    responses.add(
        responses.GET,
        f"https://toolshed.example/api/repositories/{repo[0]['id']}/metadata",
        json=metadata,
        status=200,
    )
    responses.add(
        responses.GET,
        "https://toolshed.example/api/repositories/get_ordered_installable_revisions",
        json=ordered,
        status=200,
    )
    code, out, _err = _run(
        [
            "tool-revisions",
            "devteam/fastqc/fastqc",
            "--latest",
            "--json",
            "--toolshed-url",
            "https://toolshed.example",
        ],
        monkeypatch,
        capsys,
    )
    assert code == 0
    envelope = json.loads(out)
    # TS-parity: envelope keys ordered trsToolId, [version], revisions.
    assert list(envelope.keys()) == ["trsToolId", "revisions"]
    assert envelope["trsToolId"] == "devteam~fastqc~fastqc"
    assert len(envelope["revisions"]) == 1
    assert {"changesetRevision", "toolVersion"} <= envelope["revisions"][0].keys()


@responses.activate
def test_tool_revisions_table(capsys, monkeypatch):
    repo = _load("toolshed-revisions/fastqc-repo.json")
    metadata = _load("toolshed-revisions/fastqc-metadata.json")
    ordered = _load("toolshed-revisions/fastqc-ordered.json")
    responses.add(responses.GET, "https://toolshed.example/api/repositories", json=repo, status=200)
    responses.add(
        responses.GET,
        f"https://toolshed.example/api/repositories/{repo[0]['id']}/metadata",
        json=metadata,
        status=200,
    )
    responses.add(
        responses.GET,
        "https://toolshed.example/api/repositories/get_ordered_installable_revisions",
        json=ordered,
        status=200,
    )
    code, out, _err = _run(
        [
            "tool-revisions",
            "devteam/fastqc/fastqc",
            "--toolshed-url",
            "https://toolshed.example",
        ],
        monkeypatch,
        capsys,
    )
    assert code == 0
    lines = [line for line in out.strip().splitlines() if line]
    assert lines, "expected at least one revision line"
    # tab-separated <changeset>\t<version>
    assert all("\t" in line for line in lines)
