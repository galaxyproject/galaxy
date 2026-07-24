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
