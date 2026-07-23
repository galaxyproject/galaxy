"""
Module for building and searching the index of installed tools.

Before changing index-building or searching related parts it is highly
recommended to read the docs at https://whoosh.readthedocs.io.

Schema - this is how we define the index, both for building and searching. A
    field is created for each data element that we want to add e.g. tool name,
    tool ID, description. The type of field and its attributes define how
    entries for that field will be indexed and ultimately how they can be
    searched. Score weighting (boost) is added here on a per-field bases, to
    allow matches to important fields like "name" to receive a higher score.

Tokenizers - these take an attribute (e.g. name) and parse it into "tokens" to
    be stored in the index. Can be done in many ways for different search
    functionality. For example, the IDTokenizer creates one token for an entire
    entry, resulting in an index field that requires a full-field match. The
    default tokenizer will break an entry into words, so that single word
    matches are possible.

Filters - various filters are available for processing content as the index is
    built. A StopFilter removes common articles 'a', 'for', 'and' etc. A
    StemmingFilter removes suffixes from words to create a 'base work' e.g.
    stemming -> stem; opened -> open; philosophy -> philosoph.

"""

import logging
import os
import shutil
from typing import (
    Protocol,
    runtime_checkable,
    TYPE_CHECKING,
)

from whoosh import index
from whoosh.fields import Schema
from whoosh.writing import AsyncWriter

from galaxy.config import GalaxyAppConfiguration
from galaxy.tools.source_store.search import (
    build_search_document,
    build_search_schema,
    search_whoosh_index,
    ToolSearchTuning,
    ToolWhooshIndex,
)
from galaxy.util import ExecutionTimer

if TYPE_CHECKING:
    from galaxy.tool_util.toolbox.views.interface import ToolPanelViewModel
    from galaxy.tools import (
        Tool,
        ToolBox,
    )
    from galaxy.tools.cache import ToolCache
    from galaxy.tools.source_store.index import ToolIndex
    from galaxy.util.path import StrPath

log = logging.getLogger(__name__)

CanConvertToFloat = str | int | float
CanConvertToInt = str | int | float


def get_or_create_index(index_dir: "StrPath", schema: Schema) -> index.FileIndex:
    """Get or create a reference to the index."""
    os.makedirs(index_dir, exist_ok=True)
    if index.exists_in(index_dir):
        idx = index.open_dir(index_dir)
        if idx.schema == schema:
            return idx
    log.warning(f"Index at '{index_dir}' uses outdated schema, creating a new index")

    # Delete the old index and return a new index reference
    shutil.rmtree(index_dir)
    os.makedirs(index_dir)
    return index.create_in(index_dir, schema=schema)


class ToolBoxSearch:
    """Support searching across all fixed panel views in a toolbox.

    Search is delegated off to ToolPanelViewSearch for each panel object.
    """

    def __init__(self, toolbox: "ToolBox", index_dir: str, index_help: bool = True) -> None:
        panel_searches: dict[str, ToolPanelViewSearch] = {}
        for panel_view in toolbox.panel_views():
            panel_view_id = panel_view.id
            panel_index_dir = os.path.join(index_dir, panel_view_id)
            panel_searches[panel_view_id] = ToolPanelViewSearch(
                panel_view_id,
                panel_index_dir,
                index_help=index_help,
                config=toolbox.app.config,
            )
        self.panel_searches = panel_searches
        # We keep track of how many times the tool index has been rebuilt.
        # We start at -1, so that after the first index the count is at 0,
        # which is the same as the toolbox reload count. This way we can skip
        # reindexing if the index count is equal to the toolbox reload count.
        self.index_count = -1

    def build_index(self, tool_cache: "ToolCache", toolbox: "ToolBox", index_help: bool = True) -> None:
        self.index_count += 1
        for panel_search in self.panel_searches.values():
            panel_search.build_index(tool_cache, toolbox, index_help=index_help)

    def search(self, q: str, panel_view: str, config: GalaxyAppConfiguration) -> list[str]:
        if panel_view not in self.panel_searches:
            raise KeyError(f"Unknown panel_view specified {panel_view}")
        panel_search = self.panel_searches[panel_view]
        return panel_search.search(q, config)


@runtime_checkable
class SupportsCachedSearch(Protocol):
    """The toolbox surface :class:`CachedToolboxSearch` consumes."""

    @property
    def tool_index(self) -> "ToolIndex | None": ...

    def panel_views(self) -> "list[ToolPanelViewModel]": ...

    def panel_view_tool_ids(self, panel_view_id: str) -> set[str]: ...


class CachedToolboxSearch(ToolBoxSearch):
    """Build one metadata-only Whoosh corpus per rendered panel view."""

    def __init__(self, config: GalaxyAppConfiguration, toolbox: SupportsCachedSearch | None = None) -> None:
        self.config = config
        self._toolbox: SupportsCachedSearch | None = None
        self.cached_panel_searches: dict[str, ToolWhooshIndex] = {}
        self._panel_view_ids: set[str] = set()
        self.index_count = -1
        if toolbox is not None:
            self._sync_panel_searches(toolbox)

    def build_index(self, tool_cache: "ToolCache", toolbox: "ToolBox", index_help: bool = True) -> None:
        cached_toolbox = self._require_search_toolbox(toolbox)
        self._sync_panel_searches(cached_toolbox)
        tool_index = cached_toolbox.tool_index
        if tool_index is not None:
            for panel_view_id, searcher in self.cached_panel_searches.items():
                searcher.build(tool_index, cached_toolbox.panel_view_tool_ids(panel_view_id))
        self.index_count += 1

    def search(self, q: str, panel_view: str, config: GalaxyAppConfiguration) -> list[str]:
        if panel_view not in self._panel_view_ids:
            raise KeyError(f"Unknown panel_view specified {panel_view}")
        if not config.tool_search_index_dir:
            return []
        return self.cached_panel_searches[panel_view].search(q, limit=None)

    def _sync_panel_searches(self, toolbox: SupportsCachedSearch) -> None:
        self._toolbox = toolbox
        panel_view_ids = {panel_view.id for panel_view in toolbox.panel_views()}
        self._panel_view_ids = panel_view_ids
        if not self.config.tool_search_index_dir:
            self.cached_panel_searches = {}
            return
        tuning = ToolSearchTuning.from_config(self.config)
        self.cached_panel_searches = {
            panel_view_id: ToolWhooshIndex(
                index_dir=os.path.join(self.config.tool_search_index_dir, panel_view_id),
                tuning=tuning,
            )
            for panel_view_id in panel_view_ids
        }

    @staticmethod
    def _require_search_toolbox(toolbox: "ToolBox") -> SupportsCachedSearch:
        if not isinstance(toolbox, SupportsCachedSearch):
            raise TypeError("CachedToolboxSearch requires a toolbox with a tool index, e.g. CachedToolBox")
        return toolbox


class ToolPanelViewSearch:
    """
    Support searching tools in a toolbox. This implementation uses
    the Whoosh search library.
    """

    def __init__(
        self,
        panel_view_id: str,
        index_dir: str,
        config: GalaxyAppConfiguration,
        index_help: bool = True,
    ) -> None:
        """Build the schema and validate against the index."""
        tuning = ToolSearchTuning.from_config(config)
        self.schema = build_search_schema(
            tuning,
            help_boost=tuning.help_boost if index_help else None,
        )
        self.tuning = tuning
        self.index_dir = index_dir
        self.panel_view_id = panel_view_id
        self.index = self._index_setup()

    def _index_setup(self) -> index.FileIndex:
        """Get or create a reference to the index."""
        return get_or_create_index(self.index_dir, self.schema)

    def build_index(self, tool_cache: "ToolCache", toolbox: "ToolBox", index_help: bool = True) -> None:
        """Prepare search index for tools loaded in toolbox.

        Use `tool_cache` to determine which tools need indexing and which
        should be removed.
        """
        log.debug(f"Starting to build toolbox index of panel {self.panel_view_id}.")
        execution_timer = ExecutionTimer()

        with self.index.reader() as reader:
            # Index ocasionally contains empty stored fields
            self.indexed_tool_ids = {f["id"] for f in reader.all_stored_fields() if f}

        tool_ids_to_remove = self._get_tools_to_remove(tool_cache)
        tools_to_index = self._get_tool_list(
            toolbox,
            tool_cache,
        )

        with AsyncWriter(self.index) as writer:
            for tool_id in tool_ids_to_remove:
                writer.delete_by_term("id", tool_id)
            for tool in tools_to_index:
                add_doc_kwds = self._create_doc(
                    tool=tool,
                    index_help=index_help,
                )
                # Add tool document to index (or overwrite if existing)
                writer.update_document(**add_doc_kwds)

        log.debug("Toolbox index of panel %s finished %s", self.panel_view_id, execution_timer)

    def _get_tools_to_remove(self, tool_cache: "ToolCache") -> list[str]:
        """Return list of tool IDs to be removed from index."""
        tool_ids_to_remove = (self.indexed_tool_ids - set(tool_cache._tool_paths_by_id.keys())).union(
            tool_cache._removed_tool_ids
        )

        for indexed_tool_id in self.indexed_tool_ids:
            indexed_tool = tool_cache.get_tool_by_id(indexed_tool_id)
            if indexed_tool:
                if indexed_tool.is_latest_version:
                    continue
                latest_version = indexed_tool.latest_version
                if latest_version and latest_version.hidden:
                    continue
            tool_ids_to_remove.add(indexed_tool_id)

        return list(tool_ids_to_remove)

    def _get_tool_list(self, toolbox: "ToolBox", tool_cache: "ToolCache") -> list["Tool"]:
        """Return list of tools to add and remove from index."""
        tools_to_index: list[Tool] = []

        for tool_id in tool_cache._new_tool_ids - self.indexed_tool_ids:
            tool_like = toolbox.get_tool(tool_id)
            tool = toolbox.materialize_tool(tool_like, reason="detail") if tool_like else None
            if tool and tool.is_latest_version and toolbox.panel_has_tool(tool, self.panel_view_id):
                if tool.hidden:
                    # Check if there is an older tool we can return
                    if tool.lineage:
                        tool_versions = reversed(tool.lineage.get_versions())
                        for tool_version in tool_versions:
                            tool = tool_cache.get_tool_by_id(tool_version.id)
                            if tool and not tool.hidden:
                                break
                        else:
                            continue
                    else:
                        continue
                tools_to_index.append(tool)

        return tools_to_index

    def _create_doc(
        self,
        tool: "Tool",
        index_help: bool = True,
    ) -> dict[str, str | list[str]]:
        if tool.id is None:
            return {}
        document = build_search_document(
            tool_id=tool.id,
            guid=tool.guid,
            name=tool.name,
            description=tool.description,
            section=tool.get_panel_section()[1],
            edam_operations=tool.edam_operations,
            edam_topics=tool.edam_topics,
            repository=tool.repository_name,
            owner=tool.repository_owner,
            labels=tool.labels,
            tool_tags=tool.tool_tags,
            help_text=tool.raw_help if index_help else None,
            tool_type=tool.tool_type,
        )
        return document or {}

    def search(
        self,
        q: str,
        config: GalaxyAppConfiguration,
    ) -> list[str]:
        """Perform search on the in-memory index."""
        tuning = ToolSearchTuning.from_config(config)
        return [tool_id for tool_id, _score in search_whoosh_index(self.index, q, tuning, limit=None)]
