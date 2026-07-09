# Unifying ObjectStore and FilesSource on a Shared Transport

**Status:** Proposal / design sketch
**Scope:** `lib/galaxy/objectstore/`, `lib/galaxy/files/`

## 1. Motivation

Galaxy has two storage abstractions that have grown independently:

- **ObjectStore** (`lib/galaxy/objectstore/`) — the canonical, Galaxy-owned home for
  dataset bytes. Keyed by `Dataset`/`Job` objects, quota-bearing, cache-backed, and
  contractually obliged to hand callers a **real, local, seekable POSIX path**
  (`get_filename`) plus **byte-range reads** (`get_data`).
- **FilesSource** (`lib/galaxy/files/`) — user-facing reach-out to foreign storage to
  import/export **whole files**. Keyed by URI, browse-oriented, with rich per-user
  auth (vault, OIDC, roles/groups, templating).

The two abstractions **re-implement the same backend adapters twice**. S3 exists as
both `objectstore/s3_boto3.py` (boto3) and `files/sources/s3fs.py` (fsspec); the same
duplication holds for Azure, Google Cloud Storage, and iRODS. Each cloud is maintained,
tested, and credential-configured in two places.

This document proposes collapsing that duplication by extracting a **shared whole-file
transport** that both abstractions sit on top of — **without merging the two domain
contracts**, which encode genuinely different intents.

## 2. Key insight: the seam already exists inside the object store

`CachingConcreteObjectStore` already splits internally into an **addressing** half and a
**transport** half. Every public call funnels through the same shape
(`BaseObjectStore.exists` → `_invoke` → `_exists`, `__init__.py:504`):

```
exists(obj, base_dir=, dir_only=, extra_dir=, alt_name=, obj_dir=)   # public, obj-addressed
  → self._exists(obj, **kwargs)
     → rel_path = self._construct_path(obj, **kwargs)                 # ADDRESSING
     → self._exists_remotely(rel_path)                               # TRANSPORT
```

`_construct_path` (`_caching_base.py:53`) reduces `(obj, store_by, directory_hash_id,
extra_dir, obj_dir, alt_name)` to a plain relative key such as `000/001/dataset_1.dat`.
Everything below that line is keyed only on `rel_path`, and those methods are a
**whole-file, key-addressed transport** — which is almost exactly the `FilesSource`
contract:

| Caching seam method (`_caching_base.py`)                  | FilesSource equivalent               |
| --------------------------------------------------------- | ------------------------------------ |
| `_download(rel_path)` → cache (`:421`)                    | `realize_to(rel_path, cache_path)`   |
| `_push_file_to_path(rel_path, src)` (`:435`)              | `write_from(rel_path, src)`          |
| `_push_string_to_path(rel_path, s)` (`:432`)              | `write_from` from a temp file        |
| `_exists_remotely(rel_path)` (`:396`)                     | **needs** `exists(path)`             |
| `_get_remote_size(rel_path)` (`:393`)                     | **needs** `size(path)`               |
| `_delete_existing_remote` / `_delete_remote_all` (`:425`) | **needs** `remove(path, recursive=)` |
| `_download_directory_into_cache` (`:308`)                 | recursive `list` + `realize_to`      |
| `_get_object_url` (presigned, `s3_boto3.py:383`)          | optional `get_public_url(path)`      |

The S3 implementations of these (`s3_boto3.py:299-365`) are a FilesSource with the method
names filed off — and `S3FsFilesSource` already exists and performs the same operations
against the same service.

## 3. Design

### 3.1 Composition, not inheritance

**An ObjectStore _owns_ a FilesSource; it is not one.** This is the coherence guarantee.
The object store keeps everything that is genuinely its own and never leaks it into the
transport:

- addressing (`_construct_path`, `store_by` id/uuid, `directory_hash_id`, old-style
  backward-compat)
- quota / `get_store_usage_percent`, `object_store_id` routing (distributed /
  hierarchical), `device`
- `private`, `badges`, `enable_direct_download` policy, `get_concrete_store_*`

A file source never grows a quota; an object store never grows per-user OIDC templating.

### 3.2 Contract additions to `FilesSource`

All default-derivable, so the ~30 existing sources do not break. Added to
`SingleFileSource`:

```python
# --- raw transport ---
def exists(self, path, ...) -> bool: ...          # default: via list(parent) / native fs.exists
def size(self, path, ...) -> int: ...             # default: from list entry / native
def remove(self, path, recursive=False, ...):     # writable sources only
    raise NotImplementedError
def get_public_url(self, path, ...) -> Optional[str]:  # presign opt-in
    return None

# --- resolve: the "source owns the path" method ---
def get_local_path(self, path, ...) -> str:
    """Return a local fs path for `path` that the caller may READ IN PLACE.
    The SOURCE owns the lifecycle — unlike realize_to, the caller must not
    move/delete it. Equivalent to ObjectStore.get_filename's contract."""
```

`fsspec`/`PyFilesystem2` provide `exists`/`size`/`rm` natively, so the two base helper
classes (`_fsspec.py`, `_pyfilesystem2.py`) implement these once for most sources.

### 3.3 `get_local_path` vs `realize_to` — keep them distinct

- `realize_to(source_path, native_path)` — the **caller** allocates `native_path` and
  receives a **disposable copy** it owns. Existing contract (`files/sources/__init__.py:111`).
  Posix honours it literally with `shutil.copyfile` (`posix.py:120`).
- `get_local_path(path) -> str` — the **source** returns a path it owns; for posix this is
  the real file (**zero copy**), for a remote source it is the cache path. Callers must not
  move or delete it.

This distinction is load-bearing: posix's `delete_on_realize` move (`posix.py:121`) is fine
for `realize_to` and **catastrophic** for `get_local_path` (it would move canonical data out
from under Galaxy).

### 3.4 `CachingFilesSource` — the object store's cache, relocated

For a remote source, `get_local_path` needs a cache. So the cache half of
`CachingConcreteObjectStore` — `_get_cache_path` / `_in_cache` / `_pull_into_cache` /
`_atomic_download` / `cache_target` / `InProcessCacheMonitor` / `check_cache`
(`_caching_base.py:107-419`, `caching.py`) — moves into a mixin that **wraps a raw
FilesSource**:

```python
class CachingFilesSource(BaseFilesSource):
    def __init__(self, inner: BaseFilesSource, staging_path, cache_size, ...):
        self._inner = inner          # the raw transport (s3, azure, …)
        # staging_path, cache_target, InProcessCacheMonitor — reused verbatim

    def get_local_path(self, path, ...) -> str:      # == _get_filename body, :272-306
        cache_path = self._get_cache_path(path)
        if self._in_cache(path) and os.path.getsize(cache_path) > 0:
            return cache_path
        if self._inner.exists(path):
            with self._atomic_download(cache_path) as tmp:
                self._inner.realize_to(path, tmp)    # ← transport, was _download
            return cache_path
        raise ObjectNotFound(path)

    def write_from(self, path, native_path, ...):    # == _push_to_storage
        self._inner.write_from(path, native_path)
    def exists(self, p): return self._in_cache(p) or self._inner.exists(p)
    def size(self, p):   return self._get_size_in_cache(p) if self._in_cache(p) else self._inner.size(p)
```

This is the same composition the object store has today (cache base + backend methods),
re-expressed as _wrapping a FilesSource_ instead of _mixing in `_download`_. The LRU
monitor, the atomic `.tmp` rename, and `cache_targets()` are reused unchanged.

### 3.5 Reimplementation sketch: `DiskObjectStore`

```python
class DiskObjectStore(ConcreteObjectStore):
    def __init__(self, config, config_dict):
        ...
        self._io = PosixFilesSource(root=self.file_path)   # one local source

    def _get_filename(self, obj, **kw):
        return self._io.get_local_path(self._rel_path(obj, **kw))   # returns REAL file, no copy
    def _exists(self, obj, **kw):  return self._io.exists(self._rel_path(obj, **kw))
    def _size(self, obj, **kw):    return self._io.size(self._rel_path(obj, **kw))
    def _delete(self, obj, **kw):  return self._io.remove(self._rel_path(obj, **kw), recursive=...)
    def _update_from_file(self, obj, file_name, **kw):
        self._io.write_from(self._rel_path(obj, **kw), file_name)
    def _get_store_usage_percent(self): return statvfs(self.file_path)...   # STAYS here
```

Posix's `get_local_path` is the zero-copy one-liner `return self._to_native_path(path)`.
Compare to today's `DiskObjectStore._get_filename` (`__init__.py:1155`): same outcome,
minus the special-casing. The disk store stops being a special case — it is simply the
source whose cache is the identity function.

### 3.6 Reimplementation sketch: `S3ObjectStore`

```python
class S3ObjectStore(ConcreteObjectStore):     # no longer needs CachingConcreteObjectStore
    def __init__(self, config, config_dict):
        raw = S3RawFilesSource(bucket=…, creds=…)      # realize_to/write_from/exists/size/remove/sign
        self._io = CachingFilesSource(raw, staging_path=…, cache_size=…)
    # _get_filename/_exists/_size/_delete/_update_from_file: identical to Disk above
    def _get_object_url(self, obj, **kw): return self._io.get_public_url(self._rel_path(obj, **kw))
    def _get_store_usage_percent(self): return 0.0
```

`S3RawFilesSource` is `s3_boto3.py:299-365` renamed to the FilesSource contract — or,
better, the **already-existing `S3FsFilesSource`**, now consumed by both the file-source
registry and the object store. One S3 adapter instead of two; likewise Azure, GCS, iRODS.

## 4. Risk ledger

1. **The cache migration is the bulk of the work and the real risk** — relocating
   LRU/monitor/`cache_targets()` into the files layer, and `cache_targets()` (admin cache
   management) now reaching _through_ the object store into its source. This is the
   reliability-sensitive part, not the disk store.
2. **`get_local_path` (owned) vs `realize_to` (disposable) must never be conflated** — see
   §3.3. `delete_on_realize` semantics are safe for one and lethal for the other.
3. **Perms & symlinks ride on `FilesSourceOptions`** — `update_from_file`'s
   `preserve_symlinks` (`__init__.py:1184`) and `umask_fix_perms` / `fix_permissions` must
   pass through opts, or stay thin in the object-store wrapper.
4. **Preserve `_exists`'s side effects** — today `_exists` auto-creates job dirs and does an
   opportunistic sync-push (`_caching_base.py:147-169`). The transport `exists` must be
   **pure**; that bookkeeping stays in the object-store wrapper.
5. **The file source's per-user auth path is unused in this mode** — the object store
   instantiates its source from admin config with no `user_context`. Fine for posix/s3 raw
   sources, but worth stating so nobody expects vault/roles to apply on the dataset I/O path.
   (Bring-Your-Own-Storage object stores are where the two credential worlds _do_ converge —
   a bonus prize.)
6. **`job_work` / `temp` are always-local** (`__init__.py:451`) — always a posix source
   rooted at `jobs_directory`, regardless of the dataset backend. This _clarifies_ the model
   rather than complicating it.
7. **`get_data` byte ranges** — served by reading the resolved local path and seeking
   (`_caching_base.py:128`, `__init__.py:1147`). No remote range support is needed.

## 5. Staged rollout

### Stage 1 — delegate the transport, keep the cache (low risk, immediate payoff)

Keep `CachingConcreteObjectStore` as-is, but make its backend methods
(`_download` / `_push_file_to_path` / `_push_string_to_path` / `_exists_remotely` /
`_get_remote_size` / `_delete_*`) delegate to a raw whole-file transport. Nothing above the
cache changes. Prove it with a local/in-memory transport standing in for the "remote", then
point it at the existing fsspec S3 source. This dedups the cloud adapters with **zero
visible contract change** to the rest of Galaxy.

### Stage 2 — introduce `get_local_path` + `CachingFilesSource` (the unification)

Add `get_local_path` and the `CachingFilesSource` mixin, collapse `DiskObjectStore` and
`S3ObjectStore` onto it, and delete the disk special-case. This is where the cache
physically moves into the files layer.

## 6. Testing strategy (TDD)

- **Stage 1** starts with a failing round-trip test: a `CachingConcreteObjectStore`-derived
  store whose transport is a **local FilesSource** rooted at a temp "remote" dir, with a
  separate cache dir. Assert `create` → `update_from_file` → `get_filename` returns a cache
  path with the expected content, that the bytes also landed in the "remote" dir, and that
  `exists` / `size` / `delete` propagate through to the remote. No cloud credentials needed.
- Reuse the existing object-store unit harness in `test/unit/objectstore/`.
- Contract additions to `FilesSource` (`exists` / `size` / `remove`) get their own
  per-source tests via the existing file-source test fixtures.

## 7. Open questions

- Where does `cache_targets()` live once the cache is in the files layer — does the object
  store forward to the source, or does an admin cache-management API address sources directly?
- How do distributed/hierarchical stores (`object_store_id` routing) compose with sources —
  unchanged (they wrap concrete stores), but worth confirming.

## 8. Implementation progress

**Stage 1 landed (proof-of-concept):**

- `objectstore/_transport.py` — the `ObjectStoreTransport` protocol (the narrow whole-file
  seam), a `LocalTransport`, and a `FilesSourceTransport` that satisfies it by wrapping any
  FilesSource. The adapter is typed against `BaseFilesSource` under `TYPE_CHECKING`, so the
  object store keeps **no runtime dependency** on `galaxy.files`.
- `objectstore/delegating.py` — `DelegatingObjectStore(CachingConcreteObjectStore)`, routing
  the backend hooks to an injected transport with the cache layer untouched.
- **Contract additions to `FilesSource`** — `exists` / `size` / `remove` on `BaseFilesSource`
  (default `NotImplementedError`, so the ~30 existing sources are unaffected), implemented
  natively in `PosixFilesSource` and as base-class defaults on `FsspecFilesSource`
  (`fs.exists` / `fs.size` / `fs.rm`), which every fsspec source (s3fs, azure, gcs, ...)
  inherits for free.
- **Tests** (`test/unit/objectstore/test_delegating_objectstore.py`) — the full
  create → write → exists → size → get_filename → byte-range → delete lifecycle runs through
  (a) a local transport, (b) a real `PosixFilesSource`, and (c) an fsspec `MemoryFilesSource`,
  verifying the backend directly in each case. This resolves the open question above: Stage 1
  uses the narrow `ObjectStoreTransport` protocol and the FilesSource satisfies it via the
  `FilesSourceTransport` adapter.

**Stage 2 landed (proof-of-concept) — the collapse:**

- **`get_local_path` on the `FilesSource` contract** — the "source owns the returned path"
  resolve method (`BaseFilesSource`, default `NotImplementedError`). `PosixFilesSource`
  implements it as a **zero-copy** return of the real backing file; it is kept distinct from
  `realize_to` (which copies to a caller-chosen destination).
- `objectstore/_caching_source.py` — `CachingFilesSource`, which wraps a raw source with a
  staging cache (atomic downloads, `CacheTarget`) and implements `get_local_path` as
  pull-into-cache. This is the object store's cache **relocated to wrap a source**. It lives
  in the object store package for now (reuses `objectstore.caching`) and keeps no runtime
  dependency on `galaxy.files`.
- `objectstore/source_store.py` — `SourceObjectStore(ConcreteObjectStore)` owns a source
  (via the `ObjectStoreFilesSource` protocol) and resolves `get_filename` through
  `get_local_path`. It has **no cache of its own**; addressing / quota / `store_by` stay here.
- **Tests** (`test/unit/objectstore/test_source_objectstore.py`) — the _same_
  `SourceObjectStore` class does the full lifecycle in both roles: backed by
  `PosixFilesSource` (`get_filename` returns the real backing file — asserted zero copy) and
  backed by `CachingFilesSource(MemoryFilesSource)` (`get_filename` returns a cache path). The
  disk special-case is gone.

**Shared cache extracted (`CacheArea`):**

- `objectstore/caching.py` gains **`CacheArea`** — the single cache implementation (path
  resolution, in-cache check, atomic writes, size accounting, `CacheTarget` fits-policy).
- `CachingConcreteObjectStore` (`_caching_base.py`) now delegates its cache primitives
  (`_get_cache_path` / `_in_cache` / `_get_size_in_cache` / `cache_target` /
  `_atomic_download` / `_ensure_staging_path_writable`) to a lazily-built `CacheArea`; the
  monitor lifecycle is unchanged. Behavior-preserving — the existing cloud config-parse and
  the Stage 1 cache-pull tests are the guardrail (one abspath regression was caught and fixed).
- `CachingFilesSource` now uses the _same_ `CacheArea` instead of a reimplemented lean cache,
  so there is one cache implementation across the object store and files layers.

**Deferred / productionization (not yet done):**

- **Cut the real `DiskObjectStore` / `S3ObjectStore` over to `SourceObjectStore`** and delete
  the duplicated cloud adapters. This is the final step: it touches Galaxy's production data
  path, so it must be gated by the full integration/e2e suite (and `moto` for S3), not unit
  tests alone. The recommended path is to register `SourceObjectStore` as a new store type and
  migrate via config, rather than rewrite the battle-tested classes in place.

**`DiskObjectStore` parity reached (verified against the disk contract):**

- `SourceObjectStore` now handles the full disk surface: dataset lifecycle, `store_by=uuid`,
  `alt_name` (with `safe_relpath` validation), real `get_store_usage_percent` (via an optional
  `usage_percent` source capability — `PosixFilesSource` reports `statvfs`, remote sources
  return `None`), and **`base_dir` (`job_work` / `temp`)** handled on the local filesystem
  (these are always-local scratch dirs for every backend, so they bypass the source).
- `test/unit/objectstore/test_source_objectstore.py` asserts parity: dataset round-trip,
  zero-copy `get_filename`, `store_by=uuid`, `alt_name`, usage %, and job-work directory
  create/exists/get_filename/delete.

**Config-selectable (`type: source`):**

- `type_to_object_store_class` recognizes `type: source`; `SourceObjectStore` builds its
  backing FilesSource from a `files_source` plugin block (via the file-source plugin loader).
  A `cache` block wraps a remote source in `CachingFilesSource`; a local (posix) source needs
  none. This is the **safe adoption path** — no rewrite of `DiskObjectStore`/`S3ObjectStore`;
  admins opt in per store. `test_source_objectstore.py` builds both roles through
  `build_object_store_from_config` and runs the full round-trip.

```yaml
# disk role -- one posix source, no cache
type: source
files_source:
  type: posix
  root: /data/galaxy/files
  writable: true

# cloud role -- a remote source behind a local cache
type: source
files_source:
  type: s3fs
  bucket: my-galaxy-bucket
  # ... s3fs credentials/params
cache:
  path: /srv/galaxy/cache
  size: 100
```

**Still deferred:**

- `dir_only` create for the _dataset_ source (composite / extra-files dirs) and the
  `object_store_check_old_style` backward-compat path; `get_object_url` (presigned) for the
  cloud role; XML configuration (`SourceObjectStore` is YAML-only for now).
- **Relocate the cache primitives to a neutral module** (e.g. `galaxy.util` or a shared
  package) so `CacheArea` / `CachingFilesSource` can move fully into `galaxy.files` without
  `galaxy.files` importing `galaxy.objectstore`. Also fold the object store's background
  eviction monitor into `CacheArea` (today it stays on the object store).
- An s3fs-behind-`moto` integration test (gated like the other real-cloud tests) to exercise
  the _actual_ duplicated S3 adapter end to end. `moto` is not currently a test dependency.
- `_push_string_to_path` / `_create` stage through a temp file (`write_from` is whole-file
  only); acceptable, but a `write_from_string` fast-path could be added.
