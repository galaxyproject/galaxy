"""Whoosh-backed search index built from ``ToolIndex`` entries."""

import json
import logging
import os
import re
import shutil
from collections.abc import Collection
from dataclasses import dataclass

from whoosh import (
    analysis,
    index,
    writing,
)
from whoosh.fields import (
    ID,
    KEYWORD,
    NGRAMWORDS,
    Schema,
    TEXT,
)
from whoosh.qparser import (
    MultifieldParser,
    OrGroup,
)
from whoosh.scoring import (
    BM25F,
    Frequency,
    MultiWeighting,
)

from galaxy.config import GalaxyAppConfiguration
from galaxy.tool_util.ontologies.ontology_data import curated_tool_tags
from galaxy.tool_util_models.tool_source import HelpContent
from galaxy.tools import DataManagerTool
from galaxy.tools.source_store.index import (
    ToolIndex,
    ToolIndexEntry,
)
from galaxy.util import unicodify
from galaxy.util.hash_util import md5_hash_str
from galaxy.util.tool_version import (
    is_shed_guid,
    remove_version_from_guid,
    short_tool_id,
)

log = logging.getLogger(__name__)

# Matching sidecar signatures let ``build`` skip an unchanged corpus.
_CORPUS_SIGNATURE_FILE = "corpus.md5"

# Tool help can contain embedded tables and tutorials large enough to dominate
# both the persisted metadata index and Whoosh. Eager and cached search must
# apply the same bound so their corpora and ranking remain equivalent.
MAX_TOOL_SEARCH_HELP_CHARS = 20_000


@dataclass(frozen=True)
class ToolSearchTuning:
    """Configuration-derived Whoosh schema and boost settings."""

    id_boost: float
    name_boost: float
    name_exact_multiplier: float
    stub_boost: float
    section_boost: float
    description_boost: float
    label_boost: float
    ngram_minsize: int
    ngram_maxsize: int
    enable_ngram_search: bool
    ngram_factor: float
    # Defaults preserve existing explicit tuning literals.
    help_boost: float = 1.0
    index_tool_help: bool = True
    help_bm25f_k1: float = 1.2

    @classmethod
    def from_config(cls, config: GalaxyAppConfiguration) -> "ToolSearchTuning":
        return cls(
            id_boost=float(config.tool_id_boost),
            name_boost=float(config.tool_name_boost),
            name_exact_multiplier=float(config.tool_name_exact_multiplier),
            stub_boost=float(config.tool_stub_boost),
            section_boost=float(config.tool_section_boost),
            description_boost=float(config.tool_description_boost),
            label_boost=float(config.tool_label_boost),
            ngram_minsize=int(config.tool_ngram_minsize),
            ngram_maxsize=int(config.tool_ngram_maxsize),
            enable_ngram_search=bool(config.tool_enable_ngram_search),
            ngram_factor=float(config.tool_ngram_factor),
            help_boost=float(config.tool_help_boost),
            index_tool_help=bool(config.index_tool_help),
            help_bm25f_k1=float(config.tool_help_bm25f_k1),
        )


def build_search_schema(tuning: ToolSearchTuning, *, help_boost: float | None = None) -> Schema:
    """Build the shared eager/store schema, optionally including help."""
    schema_conf: dict = {
        "id": ID(stored=True, unique=True),
        "id_exact": NGRAMWORDS(
            minsize=tuning.ngram_minsize,
            maxsize=tuning.ngram_maxsize,
            field_boost=(tuning.id_boost * tuning.name_exact_multiplier),
        ),
        "name_exact": TEXT(
            field_boost=(tuning.name_boost * tuning.name_exact_multiplier),
            analyzer=analysis.IDTokenizer() | analysis.LowercaseFilter(),
        ),
        "stub": KEYWORD(field_boost=tuning.stub_boost),
        "section": TEXT(field_boost=tuning.section_boost),
        "edam_operations": TEXT(field_boost=tuning.section_boost),
        "edam_topics": TEXT(field_boost=tuning.section_boost),
        "repository": TEXT(field_boost=tuning.section_boost),
        "owner": TEXT(field_boost=tuning.section_boost),
        "description": TEXT(
            field_boost=tuning.description_boost,
            analyzer=analysis.StemmingAnalyzer(),
        ),
        "labels": KEYWORD(field_boost=tuning.label_boost),
        "tool_tags": TEXT(
            field_boost=tuning.label_boost,
            analyzer=analysis.KeywordAnalyzer(lowercase=True, commas=True),
        ),
    }
    if help_boost is not None:
        schema_conf["help"] = TEXT(field_boost=help_boost, analyzer=analysis.StemmingAnalyzer())
    if tuning.enable_ngram_search:
        schema_conf["name"] = NGRAMWORDS(
            minsize=tuning.ngram_minsize,
            maxsize=tuning.ngram_maxsize,
            field_boost=tuning.name_boost * tuning.ngram_factor,
        )
    else:
        schema_conf["name"] = TEXT(field_boost=tuning.name_boost)
    return Schema(**schema_conf)


_REX = analysis.RegexTokenizer()


def _clean(s: str | None) -> str:
    """Tokenise hyphenated text — hyphens are Whoosh wildcards."""
    if not s:
        return ""
    text = unicodify(s)
    if "-" in text:
        return " ".join(token.text for token in _REX(text))
    return text


def build_search_document(
    *,
    tool_id: str,
    name: str,
    description: str | None = None,
    section: str | None = None,
    edam_operations: Collection[str] | None = None,
    edam_topics: Collection[str] | None = None,
    repository: str | None = None,
    owner: str | None = None,
    labels: Collection[str] | None = None,
    tool_tags: Collection[str] | None = None,
    guid: str | None = None,
    help_text: str | HelpContent | None = None,
    tool_type: str = "default",
) -> dict | None:
    """Build the common eager/cached Whoosh document for one tool."""
    if tool_type == DataManagerTool.tool_type:
        return None
    name_clean = _clean(name)
    doc: dict = {
        "id": unicodify(tool_id),
        "id_exact": unicodify(tool_id),
        "name": name_clean,
        "name_exact": name_clean,
        "description": unicodify(description or ""),
        "section": unicodify(section or ""),
        "edam_operations": [_clean(op) for op in edam_operations or []],
        "edam_topics": [_clean(topic) for topic in edam_topics or []],
        "repository": unicodify(repository or ""),
        "owner": unicodify(owner or ""),
    }
    # A Tool Shed GUID has shape ``shed/repos/owner/repo/tool/version``.
    # Carve out ``owner/repo/tool`` as the search stub.
    stub_source = guid or tool_id
    if guid:
        slash_indexes = [m.start() for m in re.finditer("/", stub_source)]
        if len(slash_indexes) >= 5:
            doc["stub"] = _clean(stub_source[slash_indexes[1] + 1 : slash_indexes[4]])
        else:
            doc["stub"] = unicodify(tool_id)
    else:
        doc["stub"] = unicodify(tool_id)
    if labels:
        doc["labels"] = unicodify(" ".join(labels))
    if tool_tags is None:
        normalized_id = tool_id.lower()
        all_ids = [normalized_id]
        if is_shed_guid(normalized_id):
            all_ids = [
                normalized_id,
                remove_version_from_guid(normalized_id) or normalized_id,
                short_tool_id(normalized_id),
            ]
        tool_tags = curated_tool_tags(all_ids)
    if tool_tags:
        doc["tool_tags"] = unicodify(",".join(tool_tags))
    if help_text is not None:
        help_content = help_text.content if isinstance(help_text, HelpContent) else help_text
        doc["help"] = unicodify(help_content or "")[:MAX_TOOL_SEARCH_HELP_CHARS]
    return doc


def entry_to_search_document(entry: ToolIndexEntry, *, include_help: bool = False) -> dict | None:
    """Project one cached metadata entry into the common document shape."""
    entry_id = entry.id
    return build_search_document(
        tool_id=entry_id,
        guid=entry_id if is_shed_guid(entry_id) else None,
        name=entry.name,
        description=entry.description,
        section=entry.panel_section_name,
        edam_operations=entry.edam_operations,
        edam_topics=entry.edam_topics,
        repository=entry.repository_name,
        owner=entry.repository_owner,
        labels=entry.labels,
        help_text=entry.help_text if include_help else None,
        tool_type=entry.tool_type,
    )


def search_whoosh_index(
    ix: index.FileIndex,
    query: str,
    tuning: ToolSearchTuning,
    limit: int | None = None,
) -> list[tuple[str, float]]:
    """Search an eager or cached index with one parser and scoring policy."""
    if not query or not query.strip():
        return []
    search_fields = [
        "id",
        "id_exact",
        "name",
        "name_exact",
        "stub",
        "description",
        "section",
        "edam_operations",
        "edam_topics",
        "repository",
        "owner",
        "labels",
        "tool_tags",
    ]
    if "help" in ix.schema.names():
        search_fields.append("help")
    parser = MultifieldParser(search_fields, schema=ix.schema, group=OrGroup)
    parsed = parser.parse(query)
    weighting = MultiWeighting(
        Frequency(),
        help=BM25F(K1=tuning.help_bm25f_k1),
    )
    with ix.searcher(weighting=weighting) as searcher:
        hits = searcher.search(parsed, limit=None, sortedby="", terms=True)
        scored = [(hit["id"], hit.score) for hit in hits]
    # Whoosh does not define a stable tie order. Sharing an explicit secondary
    # key makes eager and cached result ordering deterministic.
    scored.sort(key=lambda hit: (-hit[1], hit[0]))
    return scored if limit is None else scored[:limit]


class ToolWhooshIndex:
    """Build and query a Whoosh index over ``ToolIndexEntry`` rows."""

    def __init__(self, index_dir: str, tuning: ToolSearchTuning) -> None:
        self.index_dir = index_dir
        self.tuning = tuning
        # Changing help indexing changes the schema and corpus signature.
        self.index_help = tuning.index_tool_help
        self.schema = build_search_schema(
            tuning,
            help_boost=tuning.help_boost if tuning.index_tool_help else None,
        )

    def _open(self) -> index.FileIndex:
        os.makedirs(self.index_dir, exist_ok=True)
        if index.exists_in(self.index_dir):
            ix = index.open_dir(self.index_dir)
            if ix.schema == self.schema:
                return ix
            # Schema drift — rebuild from scratch so old field layouts don't
            # poison ranking.
            log.info("ToolWhooshIndex schema changed; rebuilding %s", self.index_dir)
            ix.close()
            shutil.rmtree(self.index_dir)
            os.makedirs(self.index_dir, exist_ok=True)
        return index.create_in(self.index_dir, schema=self.schema)

    def _corpus_signature(self, docs: list[dict]) -> str:
        """Fingerprint document content, schema, and tuning."""
        return md5_hash_str(
            repr(self.tuning)
            + json.dumps(sorted(self.schema.names()))
            + json.dumps(sorted(docs, key=lambda d: d["id"]), sort_keys=True)
        )

    def build(self, tool_index: ToolIndex, tool_ids: Collection[str] | None = None) -> int:
        """Rebuild one panel-view corpus, or all entries when unscoped."""
        docs = []
        entries = (
            tool_index.entries.values()
            if tool_ids is None
            else (tool_index.entries[tool_id] for tool_id in sorted(tool_ids) if tool_id in tool_index.entries)
        )
        for entry in entries:
            if entry.hidden:
                continue
            doc = entry_to_search_document(entry, include_help=self.index_help)
            if doc is None:
                continue
            docs.append(doc)

        # Avoid re-tokenising an unchanged corpus.
        signature = self._corpus_signature(docs)
        signature_path = os.path.join(self.index_dir, _CORPUS_SIGNATURE_FILE)
        if os.path.isdir(self.index_dir) and index.exists_in(self.index_dir):
            try:
                with open(signature_path) as f:
                    if f.read().strip() == signature:
                        log.info("Whoosh index at %s is up to date; skipping rebuild", self.index_dir)
                        return 0
            except OSError:
                pass

        # Replace the complete corpus atomically.
        ix = self._open()
        writer = ix.writer(limitmb=256)
        for doc in docs:
            writer.add_document(**doc)
        writer.commit(mergetype=writing.CLEAR)
        with open(signature_path, "w") as f:
            f.write(signature)
        return len(docs)

    def search(self, query: str, limit: int | None = None) -> list[str]:
        """Return tool ids ranked for ``query`` (most-relevant first).

        ``limit=None`` returns every match — the eager
        ``ToolPanelViewSearch`` searches unlimited, and capped results
        truncate uniform-score hits arbitrarily (a tag query fanning out to
        23 tools would silently lose the last 3 in doc-insertion order).
        """
        return [tool_id for tool_id, _score in self.search_scored(query, limit=limit)]

    def search_scored(self, query: str, limit: int | None = None) -> list[tuple[str, float]]:
        """Like :meth:`search`, but pair each tool id with its score."""
        if not query or not query.strip():
            return []
        if not (os.path.isdir(self.index_dir) and index.exists_in(self.index_dir)):
            return []
        ix = index.open_dir(self.index_dir)
        return search_whoosh_index(ix, query, self.tuning, limit=limit)
