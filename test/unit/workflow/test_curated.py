"""Unit tests for the curated workflow catalog projection.

Everything here runs without a database and without touching the network:
``galaxy.workflow.curated`` is deliberately trans-free, and the only network
call it can make (``iwc_manifest.download_manifest``) is monkeypatched in every test
that reaches it.
"""

import fcntl
import json
import os
import subprocess
import sys
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from time import (
    monotonic,
    sleep,
)
from types import SimpleNamespace
from typing import (
    Any,
    cast,
)

import pytest

from galaxy.workflow import (
    curated,
    iwc_manifest,
)
from galaxy.workflow.trs_proxy import TrsProxy

# How long a test is willing to wait on a background thread before failing.
THREAD_TIMEOUT_SECONDS = 10.0

# Shaped like the real https://iwc.galaxyproject.org/workflow_manifest.json:
# a list of repositories, each carrying a list of workflow entries whose
# human-facing metadata lives under ``definition``.
SAMPLE_MANIFEST: list[dict[str, Any]] = [
    {
        "name": "velocyto",
        "workflows": [
            {
                # The literal string "main" -- the descriptor stem, not a name.
                "name": "main",
                "iwcID": "velocyto-velocyto-on10x-filtered-barcodes",
                "trsID": "#workflow/github.com/iwc-workflows/velocyto/main",
                "collections": ["Transcriptomics"],
                "categories": [],
                "doi": "10.5281/zenodo.1234567",
                "updated": "2024-05-02T10:00:00Z",
                "definition": {
                    "name": "Velocyto on 10x filtered barcodes",
                    "annotation": "RNA velocity analysis of 10x Genomics data",
                    "tags": ["name:velocyto", "transcriptomics", "single-cell"],
                    "steps": {"0": {}, "1": {}, "2": {}},
                    "release": "0.2",
                },
            }
        ],
    },
    {
        "name": "sra-tools",
        "workflows": [
            {
                "name": "main",
                "iwcID": "parallel-accession-download-main",
                "trsID": "#workflow/github.com/iwc-workflows/parallel-accession-download/main",
                "collections": ["Data import"],
                # Populated on only a small minority of real entries, and never
                # what the card should render.
                "categories": ["genomics"],
                "doi": None,
                "updated": "2025-01-15T08:30:00Z",
                "definition": {
                    "name": "Parallel Accession Download",
                    "annotation": "Fetch sequencing reads from the SRA",
                    "tags": ["name:sra", "data-import"],
                    "steps": {"0": {}, "1": {}},
                    "release": "0.1.7",
                },
            },
            {
                # Everything optional omitted -- must still project.
                "iwcID": "sparse-workflow",
                "trsID": "#workflow/github.com/iwc-workflows/sparse/main",
                "definition": {"name": "Sparse Workflow"},
            },
            {
                # No definition at all -- unrenderable, must be skipped.
                "iwcID": "no-definition",
                "trsID": "#workflow/github.com/iwc-workflows/no-definition/main",
            },
            {
                # No iwcID -- no stable client key, must be skipped.
                "trsID": "#workflow/github.com/iwc-workflows/no-iwc-id/main",
                "definition": {"name": "No IWC ID"},
            },
        ],
    },
]

VELOCYTO_TRS_BASE = (
    "https://dockstore.org/api/ga4gh/trs/v2/tools/%23workflow%2Fgithub.com%2Fiwc-workflows%2Fvelocyto%2Fmain"
)

SORT_ENTRIES: list[dict[str, Any]] = [
    {"id": "b", "name": "Beta", "description": "", "tags": [], "update_time": "2024-01-01T00:00:00Z"},
    {"id": "a", "name": "alpha", "description": "", "tags": [], "update_time": "2025-06-01T00:00:00Z"},
    {"id": "g", "name": "Gamma", "description": "", "tags": [], "update_time": None},
]


@pytest.fixture(autouse=True)
def clear_curated_caches():
    curated.clear_caches()
    yield
    curated.clear_caches()


@pytest.fixture
def projection_path(tmp_path) -> str:
    return str(tmp_path / "curated" / "iwc_workflows.json")


class FakeClock:
    """Stand-in for ``time.monotonic`` so cooldown tests are deterministic."""

    def __init__(self, now: float = 10_000.0) -> None:
        self.now = now

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def projected_by_id(entries: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {entry["id"]: entry for entry in entries}


def wait_for_refresh_to_finish(timeout: float = THREAD_TIMEOUT_SECONDS) -> None:
    deadline = monotonic() + timeout
    while monotonic() < deadline:
        if not curated._refresh_in_flight:
            return
        sleep(0.01)
    raise AssertionError("Timed out waiting for the background refresh to finish")


def test_project_manifest_takes_name_from_the_definition() -> None:
    entries = projected_by_id(curated.project_manifest(SAMPLE_MANIFEST))
    velocyto = entries["velocyto-velocyto-on10x-filtered-barcodes"]
    assert velocyto["name"] == "Velocyto on 10x filtered barcodes"
    assert velocyto["name"] != "main"
    assert entries["parallel-accession-download-main"]["name"] == "Parallel Accession Download"


def test_project_manifest_surfaces_collections_and_never_categories() -> None:
    entries = projected_by_id(curated.project_manifest(SAMPLE_MANIFEST))
    accession = entries["parallel-accession-download-main"]
    assert accession["collections"] == ["Data import"]
    assert "categories" not in accession
    assert "genomics" not in accession["collections"]
    assert entries["velocyto-velocyto-on10x-filtered-barcodes"]["collections"] == ["Transcriptomics"]


def test_project_manifest_maps_the_remaining_card_fields() -> None:
    entries = projected_by_id(curated.project_manifest(SAMPLE_MANIFEST))
    velocyto = entries["velocyto-velocyto-on10x-filtered-barcodes"]
    # The ``name:`` prefix survives projection so it matches what local rows
    # render, and so a clicked #tag (which expandNameTag rewrites back to
    # ``name:``) can still find the workflow.
    assert velocyto["tags"] == ["name:velocyto", "transcriptomics", "single-cell"]
    assert velocyto["number_of_steps"] == 3
    assert velocyto["description"] == "RNA velocity analysis of 10x Genomics data"
    # Normalized to what the response model accepts; "Z" becomes "+00:00".
    assert velocyto["update_time"] == "2024-05-02T10:00:00+00:00"
    assert velocyto["release"] == "0.2"
    assert velocyto["doi"] == "10.5281/zenodo.1234567"
    assert (
        velocyto["external_url"] == "https://iwc.galaxyproject.org/workflow/velocyto-velocyto-on10x-filtered-barcodes/"
    )
    assert velocyto["trs_url"] == VELOCYTO_TRS_BASE + "/versions/v0.2"
    assert velocyto["trs_fallback_url"] == VELOCYTO_TRS_BASE + "/versions/main"
    assert velocyto["owner"] is None
    assert velocyto["stored_workflow_id"] is None


def test_project_manifest_tolerates_missing_optional_fields() -> None:
    entries = projected_by_id(curated.project_manifest(SAMPLE_MANIFEST))
    sparse = entries["sparse-workflow"]
    assert sparse["name"] == "Sparse Workflow"
    assert sparse["description"] == ""
    assert sparse["tags"] == []
    assert sparse["collections"] == []
    assert sparse["number_of_steps"] == 0
    assert sparse["update_time"] is None
    assert sparse["release"] is None
    assert sparse["doi"] is None
    # With no release to pin, the branch is all there is, and nothing to fall back to.
    assert sparse["trs_url"] == (
        "https://dockstore.org/api/ga4gh/trs/v2/tools/%23workflow%2Fgithub.com%2Fiwc-workflows%2Fsparse%2Fmain"
        "/versions/main"
    )
    assert sparse["trs_fallback_url"] is None


def test_project_manifest_trs_url_parses_back_without_a_dockstore_server_configured(tmp_path: Path) -> None:
    """The import API parses the URL, not a server alias, so the catalog keeps
    importing on an instance whose trs_servers_config_file drops "dockstore"."""
    servers_file = tmp_path / "trs_servers.yml"
    servers_file.write_text("- id: workflowhub\n  api_url: https://workflowhub.eu\n")
    config = SimpleNamespace(trs_servers_config_file=str(servers_file), fetch_url_allowlist_ips=[])
    proxy = TrsProxy(cast(Any, config))
    assert [server["id"] for server in proxy.get_servers()] == ["workflowhub"]

    velocyto = projected_by_id(curated.project_manifest(SAMPLE_MANIFEST))["velocyto-velocyto-on10x-filtered-barcodes"]
    for url, version in ((velocyto["trs_url"], "v0.2"), (velocyto["trs_fallback_url"], "main")):
        parts = proxy._match_url(url)
        assert parts is not None
        assert parts["trs_base_url"] == "https://dockstore.org/api"
        assert parts["tool_id"] == "#workflow/github.com/iwc-workflows/velocyto/main"
        assert parts["version_id"] == version


def test_project_manifest_without_a_trs_id_has_nothing_to_import() -> None:
    entry = curated.project_manifest([{"workflows": [{"iwcID": "no-trs", "definition": {"name": "No TRS"}}]}])[0]
    assert entry["trs_url"] is None
    assert entry["trs_fallback_url"] is None


def test_project_manifest_skips_unrenderable_entries() -> None:
    entries = projected_by_id(curated.project_manifest(SAMPLE_MANIFEST))
    assert "no-definition" not in entries
    assert "No IWC ID" not in {entry["name"] for entry in entries.values()}
    assert len(entries) == 3


def test_project_manifest_of_an_empty_manifest_is_empty() -> None:
    assert curated.project_manifest([]) == []


def test_project_manifest_sanitizes_descriptions() -> None:
    """Catalog annotations are third-party content rendered through v-html.

    Locally-authored annotations are sanitized on write, which is what makes
    that binding safe elsewhere; the catalog has no write path, so the
    projection is the only place this can happen.
    """
    hostile = [
        {
            "workflows": [
                {
                    "iwcID": "hostile",
                    "trsID": "#workflow/github.com/iwc-workflows/hostile/main",
                    "definition": {
                        "name": "Hostile workflow",
                        "annotation": '<img src=x onerror="alert(1)"><script>alert(2)</script>',
                        "steps": {},
                    },
                }
            ]
        }
    ]

    description = curated.project_manifest(hostile)[0]["description"]

    assert "onerror" not in description
    assert "<script>" not in description


def test_project_manifest_drops_wrongly_typed_fields() -> None:
    """A type regression upstream must not reach the response model.

    Validation would otherwise happen on a request thread, turning a bad
    third-party value into a 500 for everyone browsing the tab.
    """
    mistyped = [
        {
            "workflows": [
                {
                    "iwcID": "mistyped",
                    "trsID": "#workflow/github.com/iwc-workflows/mistyped/main",
                    "doi": {"unexpected": "object"},
                    "collections": [{"nested": "object"}, "Genomics"],
                    "definition": {
                        "name": "Mistyped workflow",
                        "release": 0.1,
                        "tags": [1, "name:genomics"],
                        "steps": {},
                    },
                }
            ]
        }
    ]

    entry = curated.project_manifest(mistyped)[0]

    assert entry["release"] == "0.1"
    assert entry["doi"] is None
    assert entry["collections"] == ["Genomics"]
    assert entry["tags"] == ["1", "name:genomics"]


def test_write_and_load_projection_round_trip(projection_path: str) -> None:
    entries = curated.project_manifest(SAMPLE_MANIFEST)
    curated.write_projection(projection_path, entries)
    assert curated.load_projection(projection_path) == entries


def test_write_projection_leaves_no_tmp_file_behind(projection_path: str) -> None:
    curated.write_projection(projection_path, curated.project_manifest(SAMPLE_MANIFEST))
    written = sorted(os.listdir(os.path.dirname(projection_path)))
    assert written == ["iwc_workflows.json"]


def test_write_projection_tmp_names_differ_between_writes(projection_path: str, monkeypatch) -> None:
    """Containers sharing the projection directory commonly reuse pid and thread
    ident, so the scratch name must not be derivable from them alone."""
    tmp_names: list[str] = []
    original_replace = Path.replace

    def recording_replace(self: Path, target: Any) -> Path:
        tmp_names.append(self.name)
        return original_replace(self, target)

    monkeypatch.setattr(Path, "replace", recording_replace)
    entries = curated.project_manifest(SAMPLE_MANIFEST)
    curated.write_projection(projection_path, entries)
    curated.write_projection(projection_path, entries)

    assert len(tmp_names) == 2
    assert tmp_names[0] != tmp_names[1]
    assert all(name.startswith("iwc_workflows.json.") and name.endswith(".tmp") for name in tmp_names)


def test_load_projection_of_a_missing_file_is_none(projection_path: str) -> None:
    assert curated.load_projection(projection_path) is None


def test_load_projection_of_a_wrong_version_file_is_none(projection_path: str) -> None:
    os.makedirs(os.path.dirname(projection_path))
    with open(projection_path, "w") as out:
        json.dump({"version": curated.CURATED_PROJECTION_VERSION + 1, "workflows": []}, out)
    assert curated.load_projection(projection_path) is None


def test_load_projection_of_malformed_json_is_none(projection_path: str) -> None:
    """A truncated write must behave exactly like a missing file, not raise."""
    curated.write_projection(projection_path, curated.project_manifest(SAMPLE_MANIFEST))
    with open(projection_path) as fh:
        complete = fh.read()
    with open(projection_path, "w") as out:
        out.write(complete[: len(complete) // 2])
    assert curated.load_projection(projection_path) is None


@pytest.mark.parametrize(
    "payload",
    [
        [1, 2, 3],
        "not an object",
        {"version": curated.CURATED_PROJECTION_VERSION},
        {"version": curated.CURATED_PROJECTION_VERSION, "workflows": {"not": "a list"}},
    ],
)
def test_load_projection_of_an_unusable_payload_is_none(projection_path: str, payload: Any) -> None:
    os.makedirs(os.path.dirname(projection_path))
    with open(projection_path, "w") as out:
        json.dump(payload, out)
    assert curated.load_projection(projection_path) is None


def test_load_projection_serves_from_cache_until_the_file_is_replaced(projection_path: str) -> None:
    first = curated.project_manifest(SAMPLE_MANIFEST)
    curated.write_projection(projection_path, first)
    loaded = curated.load_projection(projection_path)
    assert loaded == first

    assert curated.load_projection(projection_path) is loaded, "an unchanged file must not be re-parsed"

    # Deliberately no mtime nudge: publication is an os.replace, so the
    # replacement has a new inode even when a coarse-resolution filesystem
    # reports the same timestamp for two writes in the same tick.
    curated.write_projection(projection_path, first[:1])

    reloaded = curated.load_projection(projection_path)
    assert reloaded is not loaded
    assert reloaded == first[:1]


def test_load_projection_sees_a_replacement_written_in_the_same_timestamp_tick(projection_path: str) -> None:
    first = curated.project_manifest(SAMPLE_MANIFEST)
    curated.write_projection(projection_path, first)
    assert curated.load_projection(projection_path) == first
    original = os.stat(projection_path)

    curated.write_projection(projection_path, first[:1])
    # Force the pathological case rather than hoping for it: same mtime, and on
    # a filesystem with coarse timestamps this is what a fast rewrite looks like.
    os.utime(projection_path, ns=(original.st_atime_ns, original.st_mtime_ns))

    assert curated.load_projection(projection_path) == first[:1]


def test_search_curated_without_a_search_returns_the_input() -> None:
    entries = curated.project_manifest(SAMPLE_MANIFEST)
    assert curated.search_curated(entries, None) == entries
    assert curated.search_curated(entries, "") == entries


def test_search_curated_bare_term_matches_name_description_and_tags() -> None:
    entries = curated.project_manifest(SAMPLE_MANIFEST)
    assert [entry["id"] for entry in curated.search_curated(entries, "VELOCYTO")] == [
        "velocyto-velocyto-on10x-filtered-barcodes"
    ]
    # Only in the annotation.
    assert [entry["id"] for entry in curated.search_curated(entries, "sequencing reads")] == [
        "parallel-accession-download-main"
    ]
    # Only in the tags.
    assert [entry["id"] for entry in curated.search_curated(entries, "single-cell")] == [
        "velocyto-velocyto-on10x-filtered-barcodes"
    ]


def test_search_curated_name_term_matches_names_only() -> None:
    entries = curated.project_manifest(SAMPLE_MANIFEST)
    assert [entry["id"] for entry in curated.search_curated(entries, "name:parallel")] == [
        "parallel-accession-download-main"
    ]
    # Not the annotation: the filter menu documents ``name:`` as matching names,
    # and local-owner mode filters on StoredWorkflow.name alone. A tab whose
    # ``name:`` results changed with the admin's config would be indefensible.
    assert "sequencing reads" in entries[1]["description"]
    assert curated.search_curated(entries, "name:sequencing") == []
    assert "velocity" in entries[0]["description"]
    assert curated.search_curated(entries, "name:velocity") == []
    # Nor the tags.
    assert curated.search_curated(entries, "name:single-cell") == []


def test_search_curated_tag_term_is_substring_unless_quoted() -> None:
    entries = curated.project_manifest(SAMPLE_MANIFEST)
    assert [entry["id"] for entry in curated.search_curated(entries, "tag:import")] == [
        "parallel-accession-download-main"
    ]
    assert [entry["id"] for entry in curated.search_curated(entries, "tag:'data-import'")] == [
        "parallel-accession-download-main"
    ]
    assert curated.search_curated(entries, "tag:'import'") == []


def test_search_curated_ands_multiple_terms() -> None:
    entries = curated.project_manifest(SAMPLE_MANIFEST)
    assert [entry["id"] for entry in curated.search_curated(entries, "name:velocyto tag:transcriptomics")] == [
        "velocyto-velocyto-on10x-filtered-barcodes"
    ]
    assert curated.search_curated(entries, "name:velocyto tag:data-import") == []


def test_search_curated_returns_empty_when_nothing_matches() -> None:
    entries = curated.project_manifest(SAMPLE_MANIFEST)
    assert curated.search_curated(entries, "no-such-workflow-anywhere") == []


def test_sort_curated_defaults_to_update_time_descending() -> None:
    assert [entry["id"] for entry in curated.sort_curated(SORT_ENTRIES, None, None)] == ["a", "b", "g"]


def test_sort_curated_puts_entries_without_an_update_time_last_in_both_directions() -> None:
    assert curated.sort_curated(SORT_ENTRIES, "update_time", True)[-1]["id"] == "g"
    assert curated.sort_curated(SORT_ENTRIES, "update_time", False)[-1]["id"] == "g"


def test_sort_curated_by_create_time_shares_the_update_time_ordering() -> None:
    by_create = curated.sort_curated(SORT_ENTRIES, "create_time", None)
    by_update = curated.sort_curated(SORT_ENTRIES, "update_time", None)
    assert [entry["id"] for entry in by_create] == [entry["id"] for entry in by_update]


def test_sort_curated_by_name_is_case_insensitive() -> None:
    assert [entry["id"] for entry in curated.sort_curated(SORT_ENTRIES, "name", False)] == ["a", "b", "g"]
    assert [entry["id"] for entry in curated.sort_curated(SORT_ENTRIES, "name", True)] == ["g", "b", "a"]


def test_sort_curated_does_not_mutate_the_input() -> None:
    original = list(SORT_ENTRIES)
    curated.sort_curated(SORT_ENTRIES, "name", False)
    assert SORT_ENTRIES == original


def test_request_background_refresh_is_single_flight(projection_path: str, monkeypatch) -> None:
    entered = threading.Event()
    release = threading.Event()
    calls: list[str] = []

    def blocking_refresh(path: str, timeout: float) -> int:
        calls.append(path)
        entered.set()
        assert release.wait(THREAD_TIMEOUT_SECONDS)
        return 0

    monkeypatch.setattr(curated, "refresh_projection", blocking_refresh)

    try:
        assert curated.request_background_refresh(projection_path) is True
        assert entered.wait(THREAD_TIMEOUT_SECONDS)
        # A second caller arriving while the first refresh is still running is
        # told a refresh is under way rather than starting another one.
        assert curated.request_background_refresh(projection_path) is True
        assert curated.request_background_refresh(projection_path) is True
        assert calls == [projection_path]
    finally:
        release.set()

    wait_for_refresh_to_finish()
    assert calls == [projection_path]


def test_request_background_refresh_never_downloads_on_the_calling_thread(projection_path: str, monkeypatch) -> None:
    entered = threading.Event()
    release = threading.Event()
    download_threads: list[threading.Thread] = []

    def blocking_download(timeout: float) -> list[dict[str, Any]]:
        download_threads.append(threading.current_thread())
        entered.set()
        assert release.wait(THREAD_TIMEOUT_SECONDS)
        return SAMPLE_MANIFEST

    monkeypatch.setattr(iwc_manifest, "download_manifest", blocking_download)

    calling_thread = threading.current_thread()
    try:
        assert curated.request_background_refresh(projection_path) is True
        # The caller has already returned while the download is still blocked,
        # which is only possible if it did not perform the download itself.
        assert entered.wait(THREAD_TIMEOUT_SECONDS)
        assert calling_thread not in download_threads
        assert [thread.name for thread in download_threads] == ["curated-workflows-refresh"]
    finally:
        release.set()

    wait_for_refresh_to_finish()
    # The projection the daemon thread wrote is readable, so the whole path
    # ran off the request thread.
    assert curated.load_projection(projection_path) == curated.project_manifest(SAMPLE_MANIFEST)


def test_request_background_refresh_holds_off_until_the_cooldown_expires(projection_path: str, monkeypatch) -> None:
    clock = FakeClock()
    monkeypatch.setattr(curated, "monotonic", clock)
    calls: list[str] = []

    def failing_refresh(path: str, timeout: float) -> int:
        calls.append(path)
        raise OSError("iwc.galaxyproject.org is unreachable")

    monkeypatch.setattr(curated, "refresh_projection", failing_refresh)

    assert curated.request_background_refresh(projection_path) is True
    wait_for_refresh_to_finish()
    assert calls == [projection_path]

    clock.advance(curated.REFRESH_COOLDOWN_SECONDS - 1)
    assert curated.request_background_refresh(projection_path) is False
    assert calls == [projection_path], "the cooldown must suppress the retry entirely"

    clock.advance(2)
    assert curated.request_background_refresh(projection_path) is True
    wait_for_refresh_to_finish()
    assert calls == [projection_path, projection_path]


def test_project_manifest_skips_malformed_containers() -> None:
    """A third-party shape error must cost one entry, not the whole catalog.

    The projection is all-or-nothing: if this raises, nothing is written and the
    tab has no catalog to serve at all.
    """
    malformed: Any = [
        "not-a-repository",
        {"workflows": "not-a-list"},
        {"workflows": ["not-a-workflow"]},
        {"workflows": [{"iwcID": "bad-definition", "definition": "not-an-object"}]},
        # ... and a good one alongside them, which must still come through.
        {
            "workflows": [
                {
                    "iwcID": "good",
                    "trsID": "#workflow/github.com/iwc-workflows/good/main",
                    "definition": {"name": "Good workflow", "steps": {}},
                }
            ]
        },
    ]

    entries = curated.project_manifest(malformed)

    assert [entry["id"] for entry in entries] == ["good"]


def test_project_manifest_of_a_non_list_manifest_is_empty() -> None:
    assert curated.project_manifest({"not": "a list"}) == []  # type: ignore[arg-type]


def test_project_manifest_drops_unparseable_timestamps() -> None:
    """An unparseable date would fail response-model validation on a request thread."""
    manifest: Any = [
        {
            "workflows": [
                {
                    "iwcID": "bad-date",
                    "updated": "last Tuesday",
                    "definition": {"name": "Bad date", "steps": {}},
                }
            ]
        }
    ]

    assert curated.project_manifest(manifest)[0]["update_time"] is None


def test_sort_curated_is_stable_across_manifest_reordering() -> None:
    """Ties must not be resolved by manifest order, which the hourly refresh rewrites."""
    tied = [
        {"id": "c", "name": "Gamma", "update_time": "2026-01-01T00:00:00"},
        {"id": "a", "name": "Alpha", "update_time": "2026-01-01T00:00:00"},
        {"id": "b", "name": "Beta", "update_time": "2026-01-01T00:00:00"},
    ]
    reordered = [tied[1], tied[2], tied[0]]

    for sort_by in ("update_time", "name"):
        for desc in (True, False):
            first = [entry["id"] for entry in curated.sort_curated(tied, sort_by, desc)]
            second = [entry["id"] for entry in curated.sort_curated(reordered, sort_by, desc)]
            assert first == second, f"{sort_by} desc={desc} depends on input order"


def test_is_projection_stale(projection_path: str) -> None:
    assert curated.is_projection_stale(projection_path, 3600) is True, "a missing file is stale"

    curated.write_projection(projection_path, curated.project_manifest(SAMPLE_MANIFEST))
    assert curated.is_projection_stale(projection_path, 3600) is False

    stat = os.stat(projection_path)
    os.utime(projection_path, (stat.st_atime - 7200, stat.st_mtime - 7200))
    assert curated.is_projection_stale(projection_path, 3600) is True
    assert curated.is_projection_stale(projection_path, 0) is False, "a zero interval disables the check"


def test_refresh_projection_skips_the_download_when_upstream_is_unchanged(projection_path: str, monkeypatch) -> None:
    curated.write_projection(projection_path, curated.project_manifest(SAMPLE_MANIFEST))
    stat = os.stat(projection_path)
    os.utime(projection_path, (stat.st_atime - 7200, stat.st_mtime - 7200))
    downloads: list[float] = []

    def recording_download(timeout: float) -> list[dict[str, Any]]:
        downloads.append(timeout)
        return []

    monkeypatch.setattr(iwc_manifest, "manifest_modified_since", lambda mtime, timeout=None: False)
    monkeypatch.setattr(iwc_manifest, "download_manifest", recording_download)

    assert curated.refresh_projection(projection_path) is None
    assert downloads == [], "an unchanged manifest must not be downloaded"
    # Re-stamped, so it stops looking stale and does not re-arm the check forever.
    assert curated.is_projection_stale(projection_path, 3600) is False


def test_refresh_projection_downloads_when_upstream_moved(projection_path: str, monkeypatch) -> None:
    curated.write_projection(projection_path, [])
    monkeypatch.setattr(iwc_manifest, "manifest_modified_since", lambda mtime, timeout=None: True)
    monkeypatch.setattr(iwc_manifest, "download_manifest", lambda timeout: SAMPLE_MANIFEST)

    assert curated.refresh_projection(projection_path) == len(curated.project_manifest(SAMPLE_MANIFEST))
    assert curated.load_projection(projection_path) == curated.project_manifest(SAMPLE_MANIFEST)


def test_refresh_projection_refuses_to_replace_a_good_catalog_with_an_empty_one(
    projection_path: str, monkeypatch
) -> None:
    """An upstream 200 carrying an empty body must not blank a healthy catalog."""
    healthy = curated.project_manifest(SAMPLE_MANIFEST)
    curated.write_projection(projection_path, healthy)

    monkeypatch.setattr(iwc_manifest, "manifest_modified_since", lambda mtime, timeout=None: True)
    monkeypatch.setattr(iwc_manifest, "download_manifest", lambda timeout: [])

    with pytest.raises(ValueError):
        curated.refresh_projection(projection_path)

    curated.clear_caches()
    assert curated.load_projection(projection_path) == healthy


def test_refresh_projection_allows_an_empty_catalog_when_there_is_nothing_to_lose(
    projection_path: str, monkeypatch
) -> None:
    monkeypatch.setattr(iwc_manifest, "manifest_modified_since", lambda mtime, timeout=None: True)
    monkeypatch.setattr(iwc_manifest, "download_manifest", lambda timeout: [])

    assert curated.refresh_projection(projection_path) == 0
    assert curated.load_projection(projection_path) == []


@contextmanager
def refresh_lock_held_elsewhere(projection_path: str) -> Iterator[None]:
    """Hold the refresh lock through a separate open file, as another process would.

    flock locks belong to the open file description, so this conflicts with
    refresh_projection's own open() even from the same process.
    """
    lock_path = Path(f"{projection_path}.lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with open(lock_path, "a") as holder:
        fcntl.flock(holder.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield


def test_refresh_projection_skips_without_fetching_while_another_process_refreshes(
    projection_path: str, monkeypatch
) -> None:
    fetches: list[str] = []

    def recording_head(mtime: float, timeout: float | None = None) -> bool:
        fetches.append("head")
        return True

    def recording_download(timeout: float) -> list[dict[str, Any]]:
        fetches.append("download")
        return SAMPLE_MANIFEST

    monkeypatch.setattr(iwc_manifest, "manifest_modified_since", recording_head)
    monkeypatch.setattr(iwc_manifest, "download_manifest", recording_download)

    with refresh_lock_held_elsewhere(projection_path):
        with pytest.raises(curated.RefreshInProgress):
            curated.refresh_projection(projection_path)
    assert fetches == []
    assert not os.path.exists(projection_path)

    # Released, the next refresh goes ahead.
    assert curated.refresh_projection(projection_path) == len(curated.project_manifest(SAMPLE_MANIFEST))
    assert fetches == ["download"]


def test_background_refresh_skipped_for_another_process_does_not_start_the_cooldown(
    projection_path: str, monkeypatch
) -> None:
    """Otherwise a cold-start request landing while another worker downloads would read "unavailable"."""
    downloads: list[float] = []

    def recording_download(timeout: float) -> list[dict[str, Any]]:
        downloads.append(timeout)
        return SAMPLE_MANIFEST

    monkeypatch.setattr(iwc_manifest, "download_manifest", recording_download)

    with refresh_lock_held_elsewhere(projection_path):
        assert curated.request_background_refresh(projection_path) is True
        wait_for_refresh_to_finish()
        assert curated.request_background_refresh(projection_path) is True
        wait_for_refresh_to_finish()
    assert downloads == []

    assert curated.request_background_refresh(projection_path) is True
    wait_for_refresh_to_finish()
    assert len(downloads) == 1


def test_name_tags_stay_searchable_by_their_prefixed_form() -> None:
    """The client rewrites a clicked #tag to ``tag:'name:...'`` before sending it.

    Stripping the prefix at projection time made that query unmatchable, so
    clicking a name tag on a card returned nothing.
    """
    entries = curated.project_manifest(SAMPLE_MANIFEST)

    assert [e["id"] for e in curated.search_curated(entries, "tag:'name:velocyto'")] == [
        "velocyto-velocyto-on10x-filtered-barcodes"
    ]


def test_search_curated_handles_many_quoted_terms() -> None:
    entries = curated.project_manifest(SAMPLE_MANIFEST)
    assert curated.search_curated(entries, " ".join("'zzz'" for _ in range(500))) == []


@pytest.mark.parametrize(
    "term",
    ["name:x", "tag:x", "tag:'x'", "'quoted'"],
)
def test_parse_curated_search_caps_every_kind_of_term(term: str) -> None:
    """filter_terms alone keeps every keyed and quoted term, so the anonymous
    endpoint caps them itself -- local-owner mode turns each into a SQL predicate."""
    parsed = curated.parse_curated_search(" ".join(term for _ in range(5000)))
    assert len(parsed.terms) == curated.MAX_CURATED_SEARCH_TERMS
    assert len(parsed.filter_terms) + len(parsed.text_terms) == curated.MAX_CURATED_SEARCH_TERMS


def test_parse_curated_search_keeps_terms_in_order_up_to_the_cap() -> None:
    search = " ".join(f"name:term{index}" for index in range(curated.MAX_CURATED_SEARCH_TERMS + 5))
    parsed = curated.parse_curated_search(search)
    assert [term.text for term in parsed.terms] == [f"term{index}" for index in range(curated.MAX_CURATED_SEARCH_TERMS)]


def test_import_does_not_load_galaxy_agents() -> None:
    """The workflow manager imports this module; galaxy.agents costs seconds to import.

    Runs in a fresh interpreter because other tests may already have imported
    galaxy.agents into this one.
    """
    lib_dir = str(Path(curated.__file__).resolve().parents[2])
    code = "import sys, galaxy.workflow.curated; print('galaxy.agents' in sys.modules)"
    env = {**os.environ, "PYTHONPATH": lib_dir}
    result = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True, check=True)
    assert result.stdout.strip() == "False"


def list_sample_catalog(projection_path: str, **overrides: Any) -> curated.CatalogPage:
    kwds: dict[str, Any] = dict(search=None, sort_by=None, sort_desc=None, offset=0, limit=24, max_age_seconds=0)
    kwds.update(overrides)
    return curated.list_catalog(projection_path, **kwds)


@pytest.fixture
def recorded_refreshes(monkeypatch) -> list[str]:
    calls: list[str] = []

    def record(path: str) -> bool:
        calls.append(path)
        return True

    monkeypatch.setattr(curated, "request_background_refresh", record)
    return calls


def test_list_catalog_orders_and_pages_the_projection(projection_path: str, recorded_refreshes: list[str]) -> None:
    curated.write_projection(projection_path, curated.project_manifest(SAMPLE_MANIFEST))

    everything = list_sample_catalog(projection_path)
    assert everything.source == "iwc"
    assert everything.total_matches == 3
    assert [entry["id"] for entry in everything.entries] == [
        "parallel-accession-download-main",
        "velocyto-velocyto-on10x-filtered-barcodes",
        "sparse-workflow",
    ]

    second_page = list_sample_catalog(projection_path, offset=1, limit=1)
    assert second_page.total_matches == 3
    assert [entry["id"] for entry in second_page.entries] == ["velocyto-velocyto-on10x-filtered-barcodes"]

    by_name = list_sample_catalog(projection_path, sort_by="name", sort_desc=False)
    assert [entry["name"] for entry in by_name.entries] == [
        "Parallel Accession Download",
        "Sparse Workflow",
        "Velocyto on 10x filtered barcodes",
    ]

    # The total counts matches, not the page, so the client can paginate.
    searched = list_sample_catalog(projection_path, search="name:velocyto", limit=0)
    assert searched.total_matches == 1
    assert searched.entries == []

    assert recorded_refreshes == [], "a fresh projection must not trigger a refresh"


def test_list_catalog_past_the_end_is_an_empty_page_with_the_real_total(
    projection_path: str, recorded_refreshes: list[str]
) -> None:
    curated.write_projection(projection_path, curated.project_manifest(SAMPLE_MANIFEST))

    page = list_sample_catalog(projection_path, offset=24)

    assert page == curated.CatalogPage("iwc", 3, [])


def test_list_catalog_serves_a_stale_projection_while_refreshing_behind_it(
    projection_path: str, recorded_refreshes: list[str]
) -> None:
    curated.write_projection(projection_path, curated.project_manifest(SAMPLE_MANIFEST))
    an_hour_ago = os.stat(projection_path).st_mtime - 3600
    os.utime(projection_path, (an_hour_ago, an_hour_ago))

    page = list_sample_catalog(projection_path, max_age_seconds=60)

    assert page.source == "iwc"
    assert page.total_matches == 3
    assert recorded_refreshes == [projection_path]


def test_list_catalog_without_a_projection_is_preparing_while_a_refresh_runs(
    projection_path: str, recorded_refreshes: list[str]
) -> None:
    page = list_sample_catalog(projection_path)

    assert page == curated.CatalogPage("preparing", 0, [])
    assert recorded_refreshes == [projection_path]


def test_list_catalog_without_a_projection_is_unavailable_during_the_cooldown(
    projection_path: str, monkeypatch
) -> None:
    monkeypatch.setattr(curated, "request_background_refresh", lambda path: False)

    assert list_sample_catalog(projection_path) == curated.CatalogPage("unavailable", 0, [])


def test_extract_tool_ids_walks_subworkflows_and_dedups() -> None:
    definition: dict[str, Any] = {
        "steps": {
            "0": {"type": "data_input", "tool_id": None},
            "1": {"tool_id": "toolshed.g2.bx.psu.edu/repos/iuc/fastp/fastp/0.23.4+galaxy0"},
            "2": {
                "type": "subworkflow",
                "subworkflow": {
                    "steps": {
                        "0": {"tool_id": "cat1"},
                        "1": {
                            "subworkflow": {
                                "steps": {"0": {"tool_id": "toolshed.g2.bx.psu.edu/repos/iuc/multiqc/multiqc/1.11"}}
                            }
                        },
                    }
                },
            },
            "3": {"tool_id": "cat1"},
        }
    }

    assert curated.extract_tool_ids(definition) == [
        "cat1",
        "toolshed.g2.bx.psu.edu/repos/iuc/fastp/fastp/0.23.4+galaxy0",
        "toolshed.g2.bx.psu.edu/repos/iuc/multiqc/multiqc/1.11",
    ]


@pytest.mark.parametrize(
    "steps",
    [
        None,
        "not-steps",
        {"0": "not-a-step", "1": {"tool_id": ""}, "2": {"tool_id": 42}, "3": {"subworkflow": "nope"}},
        {"0": {"subworkflow": {"steps": ["not-a-step"]}}},
    ],
)
def test_extract_tool_ids_skips_malformed_steps(steps: Any) -> None:
    assert curated.extract_tool_ids({"steps": steps}) == []


def test_extract_tool_ids_accepts_a_step_list_alongside_malformed_siblings() -> None:
    steps = [{"tool_id": "cat1"}, "junk", {"tool_id": None}, {"subworkflow": {"steps": {"0": {"tool_id": "sort1"}}}}]
    assert curated.extract_tool_ids({"steps": steps}) == ["cat1", "sort1"]


@pytest.mark.parametrize("prefix", ["#", "$"])
def test_extract_tool_ids_follows_references_into_the_subworkflows_map(prefix: str) -> None:
    definition: dict[str, Any] = {
        "subworkflows": {
            "trim": {
                "steps": {
                    "0": {"tool_id": "trimmer"},
                    "1": {"type": "subworkflow", "content_id": "#inner"},
                },
                # Scoped to the subworkflow that declares it, as the importer does.
                "subworkflows": {"inner": {"steps": {"0": {"tool_id": "sort1"}}}},
            },
        },
        "steps": {
            "0": {"tool_id": "cat1"},
            "1": {"type": "subworkflow", "content_id": f"{prefix}trim"},
            "2": {"type": "subworkflow", "content_id": f"{prefix}trim"},
        },
    }

    assert curated.extract_tool_ids(definition) == ["cat1", "sort1", "trimmer"]


@pytest.mark.parametrize(
    "step",
    [
        {"type": "subworkflow", "content_id": "https://example.org/workflow.ga", "content_source": "url"},
        # content_source wins over a map key the id happens to match, as in the importer.
        {"type": "subworkflow", "content_id": "#present", "content_source": "trs_url"},
        {"type": "subworkflow", "trs_tool_id": "#workflow/github.com/iwc/x", "trs_version_id": "v1"},
        {"type": "subworkflow", "content_id": "f2db41e1fa331b3e"},
        {"type": "subworkflow", "content_id": "#not-in-the-map"},
        {"type": "subworkflow", "content_id": "#malformed"},
        {"type": "subworkflow"},
    ],
)
def test_extract_tool_ids_is_unknown_when_a_subworkflow_cannot_be_resolved_offline(step: dict[str, Any]) -> None:
    """Listing only the tools we could see would let the card claim the workflow runs here."""
    definition = {
        "subworkflows": {"malformed": "not-a-definition", "present": {"steps": {"0": {"tool_id": "sort1"}}}},
        "steps": {"0": {"tool_id": "cat1"}, "1": step},
    }
    assert curated.extract_tool_ids(definition) is None


def test_extract_tool_ids_terminates_on_a_self_referencing_subworkflow() -> None:
    looping: dict[str, Any] = {"steps": {"0": {"tool_id": "sort1"}}}
    looping["steps"]["1"] = {"type": "subworkflow", "content_id": "#self"}
    looping["subworkflows"] = {"self": looping}

    assert curated.extract_tool_ids(looping) == ["sort1"]


def test_project_manifest_marks_unresolvable_subworkflows_unknown() -> None:
    manifest: Any = [
        {
            "workflows": [
                {
                    "iwcID": "external",
                    "definition": {
                        "name": "External subworkflow",
                        "steps": {"0": {"type": "subworkflow", "content_id": "https://example.org/sub.ga"}},
                    },
                }
            ]
        }
    ]

    entries = curated.project_manifest(manifest)

    assert entries[0]["tool_ids"] is None
    assert curated.find_missing_tools(entries, lambda tool_id: True) == {"external": None}


def test_hide_data_manager_tools_reports_them_missing_to_non_admins() -> None:
    dm_guid = "toolshed.g2.bx.psu.edu/repos/iuc/data_manager_fetch_genome/data_manager_fetch_genome/0.0.4"
    other_version = "toolshed.g2.bx.psu.edu/repos/iuc/data_manager_fetch_genome/data_manager_fetch_genome/0.0.3"
    installed = {dm_guid, "cat1"}

    def has_tool(tool_id: str) -> bool:
        return tool_id in installed or tool_id == other_version

    user_view = curated.hide_data_manager_tools(has_tool, [dm_guid], is_admin=False)
    assert user_view(dm_guid) is False
    assert user_view(other_version) is False, "another version of the same data manager is just as off limits"
    assert user_view("cat1") is True
    assert user_view("absent") is False

    admin_view = curated.hide_data_manager_tools(has_tool, [dm_guid], is_admin=True)
    assert admin_view(dm_guid) is True


def test_project_manifest_records_tool_ids() -> None:
    manifest: Any = [
        {
            "workflows": [
                {
                    "iwcID": "with-tools",
                    "definition": {
                        "name": "With tools",
                        "steps": {
                            "0": {"tool_id": "cat1"},
                            "1": {"subworkflow": {"steps": {"0": {"tool_id": "sort1"}}}},
                        },
                    },
                },
                {"iwcID": "no-steps", "definition": {"name": "No steps"}},
            ]
        }
    ]

    by_id = projected_by_id(curated.project_manifest(manifest))

    assert by_id["with-tools"]["tool_ids"] == ["cat1", "sort1"]
    assert by_id["no-steps"]["tool_ids"] == []


def test_refresh_projection_redownloads_an_old_version_file_even_when_upstream_is_unchanged(
    projection_path: str, monkeypatch
) -> None:
    """A v1 file on disk has no tool_ids, so it must read as missing and be refetched."""
    os.makedirs(os.path.dirname(projection_path))
    with open(projection_path, "w") as out:
        json.dump({"version": 1, "workflows": [{"id": "old", "name": "Old"}]}, out)
    monkeypatch.setattr(iwc_manifest, "manifest_modified_since", lambda mtime, timeout=None: False)
    monkeypatch.setattr(iwc_manifest, "download_manifest", lambda timeout: SAMPLE_MANIFEST)

    assert curated.load_projection(projection_path) is None
    assert curated.refresh_projection(projection_path) == len(curated.project_manifest(SAMPLE_MANIFEST))
    assert all("tool_ids" in entry for entry in curated.load_projection(projection_path) or [])


def test_find_missing_tools_reports_unavailable_tools_per_entry() -> None:
    entries: list[dict[str, Any]] = [
        {"id": "ready", "tool_ids": ["cat1", "sort1"]},
        {"id": "needs-one", "tool_ids": ["cat1", "absent_tool"]},
        {"id": "no-tools", "tool_ids": []},
        {"id": "unknown"},
        {"id": "garbled", "tool_ids": "cat1"},
    ]

    missing = curated.find_missing_tools(entries, lambda tool_id: tool_id != "absent_tool")

    assert missing == {
        "ready": [],
        "needs-one": ["absent_tool"],
        "no-tools": [],
        "unknown": None,
        "garbled": None,
    }


def test_find_missing_tools_looks_each_tool_up_once() -> None:
    lookups: list[str] = []

    def available(tool_id: str) -> bool:
        lookups.append(tool_id)
        return True

    entries = [{"id": str(index), "tool_ids": ["cat1", "sort1"]} for index in range(50)]
    curated.find_missing_tools(entries, available)

    assert sorted(lookups) == ["cat1", "sort1"]


RUNNABLE_ENTRIES: list[dict[str, Any]] = [
    {"id": "old-ready", "name": "Delta", "update_time": "2020-01-01T00:00:00"},
    {"id": "new-blocked", "name": "alpha", "update_time": "2026-01-01T00:00:00"},
    {"id": "tie-b", "name": "Charlie", "update_time": "2024-01-01T00:00:00"},
    {"id": "tie-a", "name": "bravo", "update_time": "2024-01-01T00:00:00"},
    {"id": "unknown", "name": "Echo", "update_time": "2027-01-01T00:00:00"},
]
RUNNABLE_MISSING: dict[str, list[str] | None] = {
    "old-ready": [],
    "new-blocked": ["absent_tool"],
    "tie-b": [],
    "tie-a": [],
    "unknown": None,
}


def test_sort_curated_puts_runnable_entries_first_by_default() -> None:
    ordered = curated.sort_curated(RUNNABLE_ENTRIES, None, None, RUNNABLE_MISSING)
    # Runnable group, newest first with the id tiebreaker; then the rest in the same order.
    assert [entry["id"] for entry in ordered] == ["tie-b", "tie-a", "old-ready", "unknown", "new-blocked"]


def test_sort_curated_runnable_first_is_independent_of_input_order() -> None:
    reordered = list(reversed(RUNNABLE_ENTRIES))
    assert [e["id"] for e in curated.sort_curated(reordered, None, None, RUNNABLE_MISSING)] == [
        e["id"] for e in curated.sort_curated(RUNNABLE_ENTRIES, None, None, RUNNABLE_MISSING)
    ]


@pytest.mark.parametrize("sort_by", ["name", "update_time"])
def test_sort_curated_explicit_sort_ignores_runnability(sort_by: str) -> None:
    for desc in (True, False):
        with_missing = curated.sort_curated(RUNNABLE_ENTRIES, sort_by, desc, RUNNABLE_MISSING)
        without = curated.sort_curated(RUNNABLE_ENTRIES, sort_by, desc)
        assert [e["id"] for e in with_missing] == [e["id"] for e in without]


def test_sort_curated_without_missing_tools_keeps_the_default_order() -> None:
    ordered = curated.sort_curated(RUNNABLE_ENTRIES, None, None)
    assert [entry["id"] for entry in ordered] == ["unknown", "new-blocked", "tie-b", "tie-a", "old-ready"]


TOOLED_ENTRIES: list[dict[str, Any]] = [
    {"id": "newest-missing", "name": "Newest", "update_time": "2026-03-01T00:00:00Z", "tool_ids": ["absent"]},
    {"id": "middle-runs", "name": "Middle", "update_time": "2026-02-01T00:00:00Z", "tool_ids": ["cat1"]},
    {"id": "oldest-unknown", "name": "Oldest", "update_time": "2026-01-01T00:00:00Z", "tool_ids": None},
    {"id": "dm-only", "name": "Data manager", "update_time": "2025-12-01T00:00:00Z", "tool_ids": ["dm_fetch"]},
]


def fake_toolbox(installed: set[str], data_managers: tuple[str, ...] = ()) -> Any:
    return SimpleNamespace(has_tool=lambda tool_id: tool_id in installed, data_manager_tools=list(data_managers))


def test_list_catalog_reports_missing_tools_and_puts_runnable_entries_first(
    projection_path: str, recorded_refreshes: list[str]
) -> None:
    curated.write_projection(projection_path, TOOLED_ENTRIES)
    toolbox = fake_toolbox({"cat1", "dm_fetch"}, data_managers=("dm_fetch",))

    as_user = list_sample_catalog(projection_path, toolbox=toolbox, is_admin=False)
    assert [(entry["id"], entry["missing_tools"]) for entry in as_user.entries] == [
        ("middle-runs", []),
        ("newest-missing", ["absent"]),
        ("oldest-unknown", None),
        ("dm-only", ["dm_fetch"]),
    ]

    as_admin = list_sample_catalog(projection_path, toolbox=toolbox, is_admin=True)
    assert [entry["id"] for entry in as_admin.entries][:2] == ["middle-runs", "dm-only"]

    # Paging happens after the runnable-first ordering, not before it.
    second = list_sample_catalog(projection_path, toolbox=toolbox, offset=1, limit=1)
    assert [entry["id"] for entry in second.entries] == ["newest-missing"]

    # An explicit sort is taken literally.
    by_update = list_sample_catalog(projection_path, toolbox=toolbox, sort_by="update_time")
    assert [entry["id"] for entry in by_update.entries][0] == "newest-missing"


def test_list_catalog_without_a_toolbox_leaves_runnability_unknown(
    projection_path: str, recorded_refreshes: list[str]
) -> None:
    curated.write_projection(projection_path, TOOLED_ENTRIES)

    page = list_sample_catalog(projection_path)

    assert [entry["id"] for entry in page.entries] == [entry["id"] for entry in TOOLED_ENTRIES]
    assert all(entry["missing_tools"] is None for entry in page.entries)
