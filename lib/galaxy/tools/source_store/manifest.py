"""Versioned sidecar manifests for file-backed tool source stores."""

import hashlib
import json
import os
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import (
    datetime,
    timezone,
)
from pathlib import Path

from pydantic import BaseModel
from sqlalchemy.engine import make_url

from galaxy.version import VERSION

from .index import (
    INDEX_SCHEMA_HASH,
    INDEX_SCHEMA_REVISION,
    ToolIndex,
)

MANIFEST_VERSION = 1
TOOL_SOURCE_STORE_COHORT = "v1"
DATABASE_FORMAT_VERSION = "1.0"
TOOL_SOURCE_FORMAT_VERSION = "1.0"
TOOL_INDEX_FORMAT_VERSION = f"{INDEX_SCHEMA_REVISION}.0"

TOOL_SOURCE_STORE_CAPABILITIES = (
    "tool-index.entries-by-version",
    "tool-index.help-text",
    "tool-index.panel-items",
    "tool-index.panel-views",
)


@dataclass(frozen=True)
class ResolvedToolSourceStore:
    database_path: Path
    manifest_path: Path
    manifest: "ToolSourceStoreManifest"


class ProducerManifest(BaseModel):
    galaxy_version: str
    git_revision: str | None = None


class FormatManifest(BaseModel):
    database: str
    tool_source: str
    tool_index: str


class ToolSnapshotManifest(BaseModel):
    digest: str
    default_tool_count: int
    versioned_entry_count: int
    freshness_token: str | None = None


class ToolSourceStoreManifest(BaseModel):
    manifest_version: int
    cohort: str
    store: str
    producer: ProducerManifest
    formats: FormatManifest
    tool_index_schema_hash: str
    capabilities: list[str]
    built_at: datetime
    tool_snapshot: ToolSnapshotManifest


def read_manifest(path: Path) -> ToolSourceStoreManifest:
    """Load and validate a tool source store sidecar."""
    with path.open(encoding="utf-8") as handle:
        return ToolSourceStoreManifest.model_validate(json.load(handle))


def manifest_compatibility_errors(manifest: ToolSourceStoreManifest, store_name: str) -> list[str]:
    """Explain why this Galaxy process cannot consume ``manifest``."""
    errors: list[str] = []
    if manifest.manifest_version != MANIFEST_VERSION:
        errors.append(f"manifest version {manifest.manifest_version} != {MANIFEST_VERSION}")
    if manifest.cohort != TOOL_SOURCE_STORE_COHORT:
        errors.append(f"cohort {manifest.cohort!r} != {TOOL_SOURCE_STORE_COHORT!r}")
    if manifest.store != store_name:
        errors.append(f"store {manifest.store!r} != {store_name!r}")
    expected_formats = FormatManifest(
        database=DATABASE_FORMAT_VERSION,
        tool_source=TOOL_SOURCE_FORMAT_VERSION,
        tool_index=TOOL_INDEX_FORMAT_VERSION,
    )
    if manifest.formats != expected_formats:
        errors.append(f"formats {manifest.formats.model_dump()} != {expected_formats.model_dump()}")
    if manifest.tool_index_schema_hash != INDEX_SCHEMA_HASH:
        errors.append(f"index schema {manifest.tool_index_schema_hash!r} != {INDEX_SCHEMA_HASH!r}")
    missing_capabilities = set(TOOL_SOURCE_STORE_CAPABILITIES) - set(manifest.capabilities)
    if missing_capabilities:
        errors.append(f"missing capabilities {sorted(missing_capabilities)!r}")
    return errors


def resolve_compatible_store(
    cohort_directory: Path, store_name: str
) -> tuple[ResolvedToolSourceStore | None, list[str]]:
    """Select the newest compatible database from a publisher cohort tree.

    Sidecars are discovered one directory below ``cohort_directory`` using
    the standalone populator's ``<database>.manifest.json`` convention.
    Invalid and incompatible candidates are reported to the caller and never
    opened as stores.
    """
    diagnostics: list[str] = []
    compatible: list[ResolvedToolSourceStore] = []
    if not cohort_directory.is_dir():
        return None, [f"cohort directory {cohort_directory} does not exist"]
    for manifest_path in sorted(cohort_directory.glob("*/*.manifest.json")):
        database_path = Path(str(manifest_path).removesuffix(".manifest.json"))
        if not database_path.is_file():
            diagnostics.append(f"{manifest_path}: database {database_path} does not exist")
            continue
        try:
            manifest = read_manifest(manifest_path)
        except Exception as e:
            diagnostics.append(f"{manifest_path}: invalid manifest ({e})")
            continue
        errors = manifest_compatibility_errors(manifest, store_name)
        if errors:
            diagnostics.append(f"{manifest_path}: {'; '.join(errors)}")
            continue
        compatible.append(
            ResolvedToolSourceStore(
                database_path=database_path,
                manifest_path=manifest_path,
                manifest=manifest,
            )
        )
    if not compatible:
        if not diagnostics:
            diagnostics.append(f"no manifests found under {cohort_directory}")
        return None, diagnostics
    compatible.sort(key=lambda candidate: (candidate.manifest.built_at.isoformat(), str(candidate.manifest_path)))
    return compatible[-1], diagnostics


def _source_checkout_revision() -> str | None:
    """Return the source checkout revision when running from a Git tree."""
    source_root = Path(__file__).resolve().parents[4]
    if not (source_root / ".git").exists():
        return None
    try:
        completed = subprocess.run(
            ["git", "-C", str(source_root), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    revision = completed.stdout.strip()
    return revision or None


def _snapshot_rows(index: ToolIndex) -> list[tuple[str, str, str, str, str, str]]:
    rows: list[tuple[str, str, str, str, str, str]] = []
    if index.entries_by_version:
        entries = (
            entry
            for tool_id in sorted(index.entries_by_version)
            for _version, entry in sorted(index.entries_by_version[tool_id].items())
        )
    else:
        entries = (index.entries[tool_id] for tool_id in sorted(index.entries))
    for entry in entries:
        rows.append(
            (
                entry.id,
                entry.version or "",
                entry.source_hash,
                entry.source_class,
                entry.source_path or "",
                entry.file_hash or "",
            )
        )
    return sorted(rows)


def tool_snapshot(index: ToolIndex) -> ToolSnapshotManifest:
    rows = _snapshot_rows(index)
    encoded = json.dumps(rows, ensure_ascii=True, separators=(",", ":")).encode("utf-8")
    return ToolSnapshotManifest(
        digest=hashlib.sha256(encoded).hexdigest(),
        default_tool_count=len(index.entries),
        versioned_entry_count=len(rows),
        freshness_token=index.freshness_token,
    )


def build_manifest(store_name: str, index: ToolIndex, *, built_at: datetime | None = None) -> ToolSourceStoreManifest:
    return ToolSourceStoreManifest(
        manifest_version=MANIFEST_VERSION,
        cohort=TOOL_SOURCE_STORE_COHORT,
        store=store_name,
        producer=ProducerManifest(galaxy_version=VERSION, git_revision=_source_checkout_revision()),
        formats=FormatManifest(
            database=DATABASE_FORMAT_VERSION,
            tool_source=TOOL_SOURCE_FORMAT_VERSION,
            tool_index=TOOL_INDEX_FORMAT_VERSION,
        ),
        tool_index_schema_hash=INDEX_SCHEMA_HASH,
        capabilities=sorted(TOOL_SOURCE_STORE_CAPABILITIES),
        built_at=built_at or datetime.now(timezone.utc),
        tool_snapshot=tool_snapshot(index),
    )


def sqlite_database_path(url: str) -> Path | None:
    """Return the filesystem path represented by a file-backed SQLite URL."""
    parsed = make_url(url)
    if parsed.drivername.split("+")[0] != "sqlite":
        return None
    database = parsed.database
    if not database or database in {":memory:", "file::memory:"}:
        return None
    if database.startswith("file:"):
        database = database.removeprefix("file:")
    if not database or database == ":memory:":
        return None
    return Path(database).absolute()


def manifest_path_for_url(url: str) -> Path | None:
    database_path = sqlite_database_path(url)
    if database_path is None:
        return None
    return Path(f"{database_path}.manifest.json")


def write_manifest(url: str, manifest: ToolSourceStoreManifest) -> Path | None:
    """Atomically write a manifest beside a file-backed SQLite database."""
    manifest_path = manifest_path_for_url(url)
    if manifest_path is None:
        return None
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=manifest_path.parent,
            prefix=f".{manifest_path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary_path = handle.name
            json.dump(manifest.model_dump(mode="json"), handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, manifest_path)
    except Exception:
        if temporary_path is not None:
            try:
                os.unlink(temporary_path)
            except FileNotFoundError:
                pass
        raise
    return manifest_path
