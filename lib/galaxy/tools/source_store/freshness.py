"""Freshness probes for tool source stores.

A probe reads a cheap token describing the state of the tool tree a store
indexes. The populator stamps the probe's value into the persisted
``ToolIndex`` (``freshness_token``); a booting process re-probes and
compares. A match certifies the store still covers the current tree, so
boot skips the per-path coverage scan (and the populate it would trigger).
A mismatch is always safe — it only falls back to scanning/populating.

The built-in probe is ``tool_confs``: md5 over the tool and data-manager
conf file contents, plus the (recursive) directory mtimes of any
``tool_dir`` entries they declare. This captures tool
additions/removals/renames — the same class of drift the coverage scan
detects — without touching individual tool files. In-place edits to a
tool's XML are invisible to both, by design: content changes are the
incremental populate's job (raw-file md5), not the coverage check's.
Wired to the default (writable) store automatically.

Read-only stores need no probe for boot freshness — they are trusted as
published (see ``SqlAlchemyToolSourceStore.index_is_fresh``); a probe on
such a store only feeds the watcher's change detection.
"""

import hashlib
import logging
import os
from collections.abc import (
    Callable,
    Iterator,
)
from typing import TYPE_CHECKING

from .discover import conf_tool_directories

if TYPE_CHECKING:
    from galaxy.config import GalaxyAppConfiguration

log = logging.getLogger(__name__)

# A probe returns the current token; it raises FreshnessProbeError (or any
# OSError-ish failure) when the token cannot be read — callers treat that
# as "not fresh", never as fresh.
FreshnessProbe = Callable[[], str]


class FreshnessProbeError(Exception):
    """Raised when a freshness probe cannot read its token."""


def _dir_mtime_chunks(directory: str, recursive: bool) -> Iterator[bytes]:
    """Yield ``directory``'s (and, if recursive, its subdirectories') mtimes.

    A file created, deleted, or renamed in a directory bumps that
    directory's mtime, so hashing directory mtimes — never file ones —
    detects membership changes at stat-per-directory cost instead of
    stat-per-file.
    """
    try:
        yield str(os.stat(directory).st_mtime_ns).encode()
    except OSError:
        yield b"<missing>"
        return
    if not recursive:
        return
    for dirpath, dirnames, _files in os.walk(directory):
        dirnames.sort()
        for dirname in dirnames:
            subdir = os.path.join(dirpath, dirname)
            yield subdir.encode()
            try:
                yield str(os.stat(subdir).st_mtime_ns).encode()
            except OSError:
                yield b"<missing>"


def tool_confs_token(config: "GalaxyAppConfiguration") -> str:
    """Current ``tool_confs`` probe value for ``config``'s tool tree."""
    digest = hashlib.md5()
    conf_files = list(config.all_tool_config_files())
    for data_manager_conf in (config.data_manager_config_file, config.shed_data_manager_config_file):
        if data_manager_conf:
            conf_files.append(data_manager_conf)
    for path in sorted(set(conf_files)):
        digest.update(path.encode())
        try:
            with open(path, "rb") as f:
                digest.update(f.read())
        except OSError:
            digest.update(b"<missing>")
    for directory, recursive in conf_tool_directories(config):
        digest.update(directory.encode())
        for chunk in _dir_mtime_chunks(directory, recursive):
            digest.update(chunk)
    return f"confs:{digest.hexdigest()}"


def tool_confs_probe(config: "GalaxyAppConfiguration") -> FreshnessProbe:
    return lambda: tool_confs_token(config)
