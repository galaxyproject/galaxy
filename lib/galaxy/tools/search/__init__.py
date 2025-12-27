"""
Module for building and searching the index of installed tools.

The previous implementation relied on Whoosh; this module now uses Tantivy
via the `tantivy` Python bindings.  Each toolbox panel view has its own
index directory so the rest of Galaxy's search infrastructure (tools service,
reindex hooks, etc.) can continue to call `ToolPanelViewSearch` without
changes.
"""

import json
import logging
import os
import re
import shutil
import sys
from dataclasses import dataclass
from typing import (
    Iterable,
    Optional,
    TYPE_CHECKING,
    Union,
)

import tantivy

from galaxy.config import GalaxyAppConfiguration
from galaxy.util import (
    ExecutionTimer,
    unicodify,
)

if TYPE_CHECKING:
    from galaxy.tools import (
        Tool,
        ToolBox,
    )
    from galaxy.tools.cache import ToolCache

log = logging.getLogger(__name__)


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


@dataclass(frozen=True)
class SchemaFieldSpec:
    name: str
    tokenizer: str
    stored: bool = False
    fast: bool = False
    index_option: str = "position"

    def metadata(self) -> dict:
        return {
            "name": self.name,
            "type": "text",
            "options": {
                "indexing": {
                    "record": self.index_option,
                    "fieldnorms": True,
                    "tokenizer": self.tokenizer,
                },
                "stored": self.stored,
                "fast": self.fast,
            },
        }


class ToolPanelViewSearch:
    """Support searching tools in a toolbox via a Tantivy index."""

    def __init__(
        self,
        panel_view_id: str,
        index_dir: str,
        config: GalaxyAppConfiguration,
        index_help: bool = True,
    ) -> None:
        self.panel_view_id = panel_view_id
        self.index_help = index_help
        self.config = config
        self.index_dir = index_dir
        self._schema_fields = self._build_field_schemas()
        self.schema_metadata = {field.name: field.metadata() for field in self._schema_fields}
        self.schema = self._build_schema()
        self.index = self._index_setup()
        self.field_boosts = self._build_field_boosts()
        self.search_fields = self._build_search_fields()
        self._search_limit = self._resolve_search_limit()

    def _resolve_search_limit(self) -> int:
        limit = getattr(self.config, "tool_search_limit", None)
        if isinstance(limit, int) and limit > 0:
            return limit
        return sys.maxsize

    def _build_field_schemas(self) -> list[SchemaFieldSpec]:
        fields = [
            SchemaFieldSpec(name="id", tokenizer="raw", stored=True, index_option="basic"),
            SchemaFieldSpec(name="id_exact", tokenizer="raw", index_option="basic"),
            SchemaFieldSpec(name="name_exact", tokenizer="raw"),
            SchemaFieldSpec(name="name", tokenizer="galaxy_stemming"),
        ]
        if self.config.tool_enable_ngram_search:
            fields.append(SchemaFieldSpec(name="name_ngram", tokenizer="galaxy_ngram"))
        extra_text_fields = [
            "description",
            "section",
            "edam_operations",
            "edam_topics",
            "repository",
            "owner",
            "help",
            "labels",
            "stub",
        ]
        fields.extend(SchemaFieldSpec(name=name, tokenizer="galaxy_stemming") for name in extra_text_fields)
        return fields

    def _build_schema(self) -> tantivy.Schema:
        builder = tantivy.SchemaBuilder()
        for schema_field in self._schema_fields:
            builder.add_text_field(
                schema_field.name,
                stored=schema_field.stored,
                fast=schema_field.fast,
                tokenizer_name=schema_field.tokenizer,
                index_option=schema_field.index_option,
            )
        return builder.build()

    def _build_field_boosts(self) -> dict[str, float]:
        boosts = {
            "id_exact": float(self.config.tool_id_boost * self.config.tool_name_exact_multiplier),
            "name_exact": float(self.config.tool_name_boost * self.config.tool_name_exact_multiplier),
            "name": float(self.config.tool_name_boost),
            "description": float(self.config.tool_description_boost),
            "section": float(self.config.tool_section_boost),
            "edam_operations": float(self.config.tool_section_boost),
            "edam_topics": float(self.config.tool_section_boost),
            "repository": float(self.config.tool_section_boost),
            "owner": float(self.config.tool_section_boost),
            "help": float(self.config.tool_help_boost),
            "labels": float(self.config.tool_label_boost),
            "stub": float(self.config.tool_stub_boost),
        }
        if self.config.tool_enable_ngram_search:
            boosts["name_ngram"] = float(self.config.tool_name_boost * self.config.tool_ngram_factor)
        return boosts

    def _build_search_fields(self) -> list[str]:
        fields = [
            "id",
            "id_exact",
            "name",
            "name_exact",
        ]
        if self.config.tool_enable_ngram_search:
            fields.append("name_ngram")
        fields.extend(
            [
                "description",
                "section",
                "edam_operations",
                "edam_topics",
                "repository",
                "owner",
                "help",
                "labels",
                "stub",
            ]
        )
        return fields

    def _index_setup(self) -> tantivy.Index:
        os.makedirs(self.index_dir, exist_ok=True)
        existing_schema = self._read_existing_schema_metadata()
        if existing_schema is not None and existing_schema != self.schema_metadata:
            shutil.rmtree(self.index_dir)
            os.makedirs(self.index_dir, exist_ok=True)
        index = tantivy.Index(self.schema, self.index_dir)
        self._register_analyzers(index)
        return index

    def _read_existing_schema_metadata(self) -> Optional[dict[str, dict]]:
        meta_path = os.path.join(self.index_dir, "meta.json")
        if not os.path.exists(meta_path):
            return None
        try:
            with open(meta_path, encoding="utf-8") as meta_file:
                metadata = json.load(meta_file)
        except Exception:
            return None
        schema = metadata.get("schema", [])
        return {entry["name"]: entry for entry in schema}

    def _register_analyzers(self, index: tantivy.Index) -> None:
        if getattr(self, "_tokenizers_registered", False):
            return
        stemming_analyzer = (
            tantivy.TextAnalyzerBuilder(tantivy.Tokenizer.simple())
            .filter(tantivy.Filter.lowercase())
            .filter(tantivy.Filter.ascii_fold())
            .filter(tantivy.Filter.stemmer("English"))
            .build()
        )
        index.register_tokenizer("galaxy_stemming", stemming_analyzer)
        if self.config.tool_enable_ngram_search:
            ngram_analyzer = (
                tantivy.TextAnalyzerBuilder(
                    tantivy.Tokenizer.ngram(
                        self.config.tool_ngram_minsize,
                        self.config.tool_ngram_maxsize,
                    )
                )
                .filter(tantivy.Filter.lowercase())
                .filter(tantivy.Filter.ascii_fold())
                .build()
            )
            index.register_tokenizer("galaxy_ngram", ngram_analyzer)
        self._tokenizers_registered = True

    def build_index(self, tool_cache: "ToolCache", toolbox: "ToolBox", index_help: bool = True) -> None:
        log.debug(f"Starting to build toolbox index of panel {self.panel_view_id}.")
        execution_timer = ExecutionTimer()
        writer = self.index.writer()
        writer.delete_all_documents()
        for tool in self._iter_tools_to_index(toolbox, tool_cache):
            doc = self._create_document(tool, index_help=index_help)
            if not doc:
                continue
            document = tantivy.Document()
            for field_name, value in doc.items():
                if isinstance(value, list):
                    for item in value:
                        if item is None:
                            continue
                        document.add_text(field_name, str(item))
                else:
                    if value is None:
                        continue
                    document.add_text(field_name, str(value))
            writer.add_document(document)
        writer.commit()
        self.index.reload()
        log.debug("Toolbox index of panel %s finished %s", self.panel_view_id, execution_timer)

    def _iter_tools_to_index(self, toolbox: "ToolBox", tool_cache: "ToolCache") -> Iterable["Tool"]:
        seen: set[str] = set()
        for _tool_id, tool in toolbox.tools():
            if not tool or not tool.is_latest_version:
                continue
            if not toolbox.panel_has_tool(tool, self.panel_view_id):
                continue
            tool_to_index = self._resolve_visible_tool(tool, tool_cache)
            if not tool_to_index:
                continue
            if tool_to_index.id in seen:
                continue
            seen.add(tool_to_index.id)
            yield tool_to_index

    def _resolve_visible_tool(self, tool: "Tool", tool_cache: "ToolCache") -> Optional["Tool"]:
        if not tool.hidden:
            return tool
        if not tool.lineage:
            return None
        tool_versions = reversed(tool.lineage.get_versions())
        for tool_version in tool_versions:
            candidate = tool_cache.get_tool_by_id(tool_version.id)
            if candidate and not candidate.hidden:
                return candidate
        return None

    def _create_document(self, tool: "Tool", index_help: bool = True) -> dict[str, Union[str, list[str]]]:
        def clean(value: str) -> str:
            if "-" in value:
                return value.replace("-", " ")
            return value

        if tool.tool_type == "manage_data":
            return {}
        document: dict[str, Union[str, list[str]]] = {
            "id": unicodify(tool.id),
            "id_exact": unicodify(tool.id),
            "name": clean(tool.name),
            "description": unicodify(tool.description),
            "section": tool.get_panel_section()[1] or "",
            "edam_operations": [clean(item) for item in tool.edam_operations or []],
            "edam_topics": [clean(item) for item in tool.edam_topics or []],
            "repository": unicodify(tool.repository_name),
            "owner": unicodify(tool.repository_owner),
            "help": unicodify(""),
        }
        if tool.guid:
            slash_indexes = [match.start() for match in re.finditer("/", tool.guid)]
            if len(slash_indexes) >= 5:
                stub = tool.guid[(slash_indexes[1] + 1) : slash_indexes[4]]
            else:
                stub = tool.guid
            document["stub"] = clean(stub)
        else:
            document["stub"] = unicodify(tool.id)
        if tool.labels:
            document["labels"] = unicodify(" ".join(tool.labels))
        if index_help:
            raw_help = tool.raw_help
            if raw_help:
                try:
                    document["help"] = unicodify(raw_help)
                except Exception:
                    pass
        document["name_exact"] = document["name"]
        return document

    def _parse_query(self, query: str) -> Optional[tantivy.Query]:
        if not query:
            return None
        try:
            return self.index.parse_query(
                query,
                default_field_names=self.search_fields,
                field_boosts=self.field_boosts,
            )
        except ValueError:
            query_result, errors = self.index.parse_query_lenient(
                query,
                default_field_names=self.search_fields,
                field_boosts=self.field_boosts,
            )
            if errors:
                log.debug("Search query lenient parsing returned errors %s", errors)
            return query_result
        except Exception:
            log.exception("Failed to parse search query %s", query)
            return None

    def search(self, q: str, config: GalaxyAppConfiguration) -> list[str]:
        parsed_query = self._parse_query(q)
        if parsed_query is None:
            return []
        self.index.reload()
        searcher = self.index.searcher()
        limit = self._search_limit or sys.maxsize
        results = searcher.search(parsed_query, limit=limit)
        tool_ids: list[str] = []
        for _, doc_address in results.hits:
            doc = searcher.doc(doc_address)
            doc_id = doc.get_first("id")
            if doc_id:
                tool_ids.append(doc_id)
        return tool_ids
