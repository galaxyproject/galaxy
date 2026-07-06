"""Builders resolving Galaxy configuration into tool source stores."""

import logging
from typing import TYPE_CHECKING

from galaxy.tool_util.toolbox.parser import get_toolbox_parser
from .composite import CompositeToolSourceStore
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
    """Build the default store from top-level ``tool_source_*`` config."""
    backend = config.tool_source_store

    if backend in ("sqlalchemy", "sqlite"):
        path = config.tool_source_disk_path
        if path:
            return SqlAlchemyToolSourceStore(path=path, read_only=False)
        raise ConfigurationError(f"{backend!r} backend requires tool_source_disk_path")

    raise ConfigurationError(f"Unknown tool source store backend: {backend}")


def build_named_store(
    name: str,
    spec: dict,
) -> ToolSourceStore:
    """Build a single named store from a ``tool_source_stores`` entry.

    ``spec`` is the dict from galaxy.yml — a ``backend`` plus its options
    plus an optional ``read_only`` flag.
    """
    if not isinstance(spec, dict):
        raise ConfigurationError(f"tool_source_stores[{name!r}] must be a mapping")
    backend = spec.get("backend")
    read_only = bool(spec.get("read_only", False))

    if backend in ("sqlalchemy", "sqlite"):
        url = spec.get("url")
        path = spec.get("path")
        if not url and not path:
            raise ConfigurationError(f"tool_source_stores[{name!r}] requires a 'url' or 'path'")
        return SqlAlchemyToolSourceStore(url=url, path=path, read_only=read_only)

    raise ConfigurationError(f"tool_source_stores[{name!r}] has unknown backend {backend!r}")


def _collect_per_conf_store_names(config: "GalaxyAppConfiguration") -> set[str]:
    """Walk configured tool_confs and collect referenced store names."""
    if not config.tool_configs:
        return set()
    names: set[str] = set()
    for path in config.tool_configs:
        try:
            parser = get_toolbox_parser(path)
        except Exception as e:
            log.debug(f"skipping tool conf {path}: {e}")
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
        members.append((name, build_named_store(name, catalog[name])))

    # Default is consulted last so per-conf overrides shadow it on hash collisions.
    members.append(("__default__", default_store))

    return CompositeToolSourceStore(members=members, default="__default__")
