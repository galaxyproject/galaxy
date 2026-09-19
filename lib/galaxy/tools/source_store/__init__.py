"""
Tool Source Store - standalone storage for Galaxy tool sources.

Tool sources and their derived ``ToolIndex`` live in a standalone SQLAlchemy
database chosen by connection URL (``tool_source_database_connection``;
defaults to a ``sqlite:///`` file, but any SQLAlchemy URL such as
``postgresql://`` works just as well). There is a single store
implementation, ``SqlAlchemyToolSourceStore``; a tool_conf may point at a
named store declared in ``tool_source_stores``, and those are layered over
the default in a ``CompositeToolSourceStore``.
"""

from .factory import (
    build_named_store,
    build_tool_source_store,
)
from .index import (
    ToolIndex,
    ToolIndexEntry,
)
from .interface import (
    ConfigurationError,
    ReadOnlyStoreError,
    StoredToolSource,
    ToolSourceStore,
)

__all__ = [
    "StoredToolSource",
    "ToolSourceStore",
    "ToolIndex",
    "ToolIndexEntry",
    "build_tool_source_store",
    "build_named_store",
    "ConfigurationError",
    "ReadOnlyStoreError",
]
