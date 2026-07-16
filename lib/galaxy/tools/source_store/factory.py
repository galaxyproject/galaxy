"""Builders resolving Galaxy configuration into tool source stores."""

import logging
from typing import TYPE_CHECKING

from galaxy.tool_util.toolbox.parser import get_toolbox_parser
from .composite import CompositeToolSourceStore
from .freshness import (
    FreshnessProbe,
    tool_confs_probe,
)
from .interface import (
    ConfigurationError,
    ToolSourceStore,
)
from .sqlalchemy import SqlAlchemyToolSourceStore

if TYPE_CHECKING:
    from galaxy.config import GalaxyAppConfiguration

log = logging.getLogger(__name__)


def _build_default_store(
    config: "GalaxyAppConfiguration",
) -> ToolSourceStore:
    """Build the default store from the top-level SQLAlchemy URI config.

    The default store always carries the ``tool_confs`` freshness probe: it
    is populated and probed on the same host, so hashing the local conf
    files is both cheap and meaningful.
    """
    url = config.tool_source_database_connection
    if not url:
        raise ConfigurationError("tool_source_database_connection is required")
    return SqlAlchemyToolSourceStore(url=url, read_only=False, freshness_probe=tool_confs_probe(config))


def _build_freshness_probe(
    name: str,
    spec: dict,
    config: "GalaxyAppConfiguration",
) -> FreshnessProbe | None:
    freshness = spec.get("freshness")
    if freshness in (None, "none"):
        return None
    if freshness == "tool_confs":
        return tool_confs_probe(config)
    raise ConfigurationError(
        f"tool_source_stores[{name!r}] freshness must be 'tool_confs' or 'none' (got {freshness!r})"
    )


def build_named_store(
    name: str,
    spec: dict,
    config: "GalaxyAppConfiguration",
) -> ToolSourceStore:
    """Build a single named store from a ``tool_source_stores`` entry.

    ``spec`` is the dict from galaxy.yml - a SQLAlchemy ``url`` plus
    optional ``read_only`` and ``freshness`` keys.
    Named stores get no probe unless one is declared: a store populated on
    a different host (the CVMFS publishing model) would never match a
    locally-computed conf hash, so ``tool_confs`` cannot be the default
    here the way it is for the default store.
    """
    if not isinstance(spec, dict):
        raise ConfigurationError(f"tool_source_stores[{name!r}] must be a mapping")
    if "backend" in spec or "path" in spec:
        raise ConfigurationError(
            f"tool_source_stores[{name!r}] must use 'url'; 'backend' and 'path' are no longer supported"
        )
    url = spec.get("url")
    if not url:
        raise ConfigurationError(f"tool_source_stores[{name!r}] requires a 'url'")
    read_only = bool(spec.get("read_only", False))
    probe = _build_freshness_probe(name, spec, config)
    return SqlAlchemyToolSourceStore(url=url, read_only=read_only, freshness_probe=probe)


def _collect_per_conf_store_names(config: "GalaxyAppConfiguration") -> set[str]:
    """Walk configured tool_confs and collect referenced store names."""
    names: set[str] = set()
    for path in config.all_tool_config_files():
        try:
            parser = get_toolbox_parser(path)
        except Exception as e:
            log.error(f"skipping tool conf {path}: {e}")
            continue
        store = parser.parse_store_name()
        if store:
            names.add(store)
    return names


def build_tool_source_store(
    config: "GalaxyAppConfiguration",
) -> ToolSourceStore:
    """Build the active tool source store, composing per-conf overrides.

    Returns the default store directly when no tool_conf opts into a named
    override (zero overhead for the common case). Otherwise wraps the
    default plus each referenced named store in a
    :class:`CompositeToolSourceStore`, with the default consulted last and
    receiving all writes. A ``store="..."`` reference without a matching
    ``tool_source_stores`` catalog entry is a configuration error.

    Args:
        config: The Galaxy application configuration.
    """
    default_store = _build_default_store(config)

    referenced = _collect_per_conf_store_names(config)
    if not referenced:
        return default_store

    catalog = config.tool_source_stores or {}
    members: list[tuple[str, ToolSourceStore]] = []
    for name in referenced:
        if name not in catalog:
            raise ConfigurationError(
                f"tool_conf references store {name!r} but no such entry exists in tool_source_stores"
            )
        members.append((name, build_named_store(name, catalog[name], config)))

    # Default is consulted last so per-conf overrides shadow it on hash collisions.
    members.append(("__default__", default_store))

    return CompositeToolSourceStore(members=members, default="__default__")
