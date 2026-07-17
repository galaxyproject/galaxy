import json
from datetime import (
    datetime,
    timezone,
)

import pytest

import galaxy.tools.source_store.manifest as manifest_module
from galaxy.tools.source_store.index import (
    INDEX_SCHEMA_HASH,
    ToolIndex,
    ToolIndexEntry,
)
from galaxy.tools.source_store.manifest import (
    build_manifest,
    manifest_compatibility_errors,
    manifest_path_for_url,
    resolve_compatible_store,
    sqlite_database_path,
    tool_snapshot,
    write_manifest,
)


def _index(source_hash: str = "source-a") -> ToolIndex:
    index = ToolIndex(freshness_token="snapshot:1")
    index.add_entry(
        ToolIndexEntry(
            id="tool_a",
            version="1.0",
            source_hash=source_hash,
            source_class="XmlToolSource",
            source_path="/cvmfs/example/tools/a.xml",
            file_hash="file-a",
        )
    )
    return index


def test_manifest_contract_and_snapshot_counts(monkeypatch):
    monkeypatch.setattr(manifest_module, "_source_checkout_revision", lambda: "abc123")
    built_at = datetime(2026, 7, 16, 12, 0, tzinfo=timezone.utc)

    manifest = build_manifest("cvmfs_main", _index(), built_at=built_at)

    assert manifest.manifest_version == 1
    assert manifest.cohort == "v1"
    assert manifest.store == "cvmfs_main"
    assert manifest.producer.git_revision == "abc123"
    assert manifest.tool_index_schema_hash == INDEX_SCHEMA_HASH
    assert manifest.capabilities == sorted(manifest.capabilities)
    assert manifest.built_at == built_at
    assert manifest.tool_snapshot.default_tool_count == 1
    assert manifest.tool_snapshot.versioned_entry_count == 1
    assert manifest.tool_snapshot.freshness_token == "snapshot:1"


def test_snapshot_digest_is_stable_and_content_sensitive():
    first = _index()
    second = _index()
    second.entries["tool_a"].indexed_at = datetime.now(timezone.utc)
    second.entries_by_version["tool_a"]["1.0"].indexed_at = datetime.now(timezone.utc)

    assert tool_snapshot(first).digest == tool_snapshot(second).digest
    assert tool_snapshot(first).digest != tool_snapshot(_index(source_hash="source-b")).digest


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("sqlite:////tmp/sources.sqlite", "/tmp/sources.sqlite"),
        ("sqlite:///file:/tmp/sources.sqlite?mode=rw&uri=true", "/tmp/sources.sqlite"),
        ("sqlite:///:memory:", None),
        ("postgresql://example.invalid/tools", None),
    ],
)
def test_sqlite_database_path(url, expected):
    path = sqlite_database_path(url)
    assert (str(path) if path is not None else None) == expected


def test_write_manifest_uses_database_name_sidecar(tmp_path, monkeypatch):
    monkeypatch.setattr(manifest_module, "_source_checkout_revision", lambda: None)
    database_path = tmp_path / "sources.sqlite"
    database_path.touch()
    url = f"sqlite:///{database_path}"

    path = write_manifest(url, build_manifest("cvmfs_main", _index()))

    assert path == manifest_path_for_url(url)
    assert path == tmp_path / "sources.sqlite.manifest.json"
    payload = json.loads(path.read_text())
    assert payload["cohort"] == "v1"
    assert payload["producer"]["git_revision"] is None
    assert payload["tool_snapshot"]["digest"] == tool_snapshot(_index()).digest


def test_atomic_replace_failure_preserves_prior_manifest(tmp_path, monkeypatch):
    database_path = tmp_path / "sources.sqlite"
    database_path.touch()
    manifest_path = tmp_path / "sources.sqlite.manifest.json"
    manifest_path.write_text('{"old": true}\n')

    def fail_replace(source, destination):
        raise OSError("replace failed")

    monkeypatch.setattr(manifest_module.os, "replace", fail_replace)
    with pytest.raises(OSError, match="replace failed"):
        write_manifest(f"sqlite:///{database_path}", build_manifest("cvmfs_main", _index()))

    assert manifest_path.read_text() == '{"old": true}\n'
    assert list(tmp_path.glob("*.tmp")) == []


def test_manifest_compatibility_requires_current_cohort_schema_and_store():
    compatible = build_manifest("cvmfs_main", _index())
    assert manifest_compatibility_errors(compatible, "cvmfs_main") == []

    incompatible = compatible.model_copy(
        update={
            "cohort": "v2",
            "store": "cvmfs_test",
            "tool_index_schema_hash": "outdated",
        }
    )
    errors = manifest_compatibility_errors(incompatible, "cvmfs_main")
    assert any("cohort" in error for error in errors)
    assert any("store" in error for error in errors)
    assert any("index schema" in error for error in errors)


def test_resolve_compatible_store_selects_newest_compatible_candidate(tmp_path):
    older_time = datetime(2026, 7, 15, tzinfo=timezone.utc)
    newer_time = datetime(2026, 7, 16, tzinfo=timezone.utc)
    for cohort, built_at in (("old", older_time), ("new", newer_time)):
        database_path = tmp_path / cohort / "sources.sqlite"
        database_path.parent.mkdir()
        database_path.touch()
        write_manifest(f"sqlite:///{database_path}", build_manifest("cvmfs_main", _index(), built_at=built_at))

    rejected_database = tmp_path / "wrong" / "sources.sqlite"
    rejected_database.parent.mkdir()
    rejected_database.touch()
    rejected = build_manifest("cvmfs_main", _index()).model_copy(update={"cohort": "v2"})
    write_manifest(f"sqlite:///{rejected_database}", rejected)

    resolved, diagnostics = resolve_compatible_store(tmp_path, "cvmfs_main")

    assert resolved is not None
    assert resolved.database_path == tmp_path / "new" / "sources.sqlite"
    assert any("cohort" in diagnostic for diagnostic in diagnostics)


def test_resolve_compatible_store_returns_diagnostics_instead_of_an_incompatible_database(tmp_path):
    database_path = tmp_path / "v2" / "sources.sqlite"
    database_path.parent.mkdir()
    database_path.touch()
    incompatible = build_manifest("cvmfs_main", _index()).model_copy(update={"cohort": "v2"})
    write_manifest(f"sqlite:///{database_path}", incompatible)

    resolved, diagnostics = resolve_compatible_store(tmp_path, "cvmfs_main")

    assert resolved is None
    assert diagnostics
