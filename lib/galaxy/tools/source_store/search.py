"""Whoosh-backed search index built from ``ToolIndex`` entries."""

import json
import logging
import os
import re
import shutil
import threading
from collections.abc import (
    Collection,
    Iterator,
)
from contextlib import contextmanager
from dataclasses import dataclass

from whoosh import (
    analysis,
    index,
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
from whoosh.reading import IndexReader
from whoosh.scoring import (
    BM25F,
    Frequency,
    MultiWeighting,
)
from whoosh.searching import Searcher

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

# Stored per-document fingerprint; a build rewrites only the documents whose
# fingerprint differs from the corpus it is given.
_DOC_HASH_FIELD = "doc_hash"

# Galaxy processes share ``tool_search_index_dir``. The elected config watcher
# writes it, but another process can still hold the write lock: a previous
# watcher, or at boot a web worker that elected itself before its peers
# registered and stays watcher until its next heartbeat. A rebuild that cannot
# get the lock in time gives up rather than block the control task, and the
# caller leaves the index stale.
INDEX_WRITE_LOCK_TIMEOUT = 60.0

# Whoosh's estimate of its in-memory posting pool before spilling to disk. The
# real pool is several times larger, and pymalloc keeps the arenas it filled,
# so this bounds the memory a full build leaves the building process with.
# Building a 9000-tool corpus takes as long at 32 as at 256.
INDEX_WRITER_LIMITMB = 32

# Tool help can contain embedded tables and tutorials large enough to dominate
# both the persisted metadata index and Whoosh. Eager and cached search must
# apply the same bound so their corpora and ranking remain equivalent.
MAX_TOOL_SEARCH_HELP_CHARS = 20_000
SearchDocument = dict[str, str | list[str]]


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
) -> SearchDocument | None:
    """Build the common eager/cached Whoosh document for one tool."""
    if tool_type == DataManagerTool.tool_type:
        return None
    name_clean = _clean(name)
    doc: SearchDocument = {
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


def entry_to_search_document(entry: ToolIndexEntry, *, include_help: bool = False) -> SearchDocument | None:
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


def search_weighting(tuning: ToolSearchTuning) -> MultiWeighting:
    return MultiWeighting(
        Frequency(),
        help=BM25F(K1=tuning.help_bm25f_k1),
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
    with ix.searcher(weighting=search_weighting(tuning)) as searcher:
        return search_whoosh_searcher(searcher, query, limit=limit)


def search_whoosh_searcher(searcher: Searcher, query: str, limit: int | None = None) -> list[tuple[str, float]]:
    """Search with a searcher opened with :func:`search_weighting`."""
    if not query or not query.strip():
        return []
    schema = searcher.schema
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
    if "help" in schema.names():
        search_fields.append("help")
    parser = MultifieldParser(search_fields, schema=schema, group=OrGroup)
    parsed = parser.parse(query)
    hits = searcher.search(parsed, limit=None, sortedby="", terms=True)
    scored = [(hit["id"], hit.score) for hit in hits]
    # Whoosh does not define a stable tie order. Sharing an explicit secondary
    # key makes eager and cached result ordering deterministic.
    scored.sort(key=lambda hit: (-hit[1], hit[0]))
    return scored if limit is None else scored[:limit]


# Whoosh writes ``_MAIN_<generation>.toc`` on each commit of an index opened
# with the default name, and names a segment's files ``<segment id>.<ext>``.
_TOC_FILENAME = re.compile(r"_MAIN_([0-9]+)\.toc")


def _latest_generation(filenames: list[str]) -> int:
    return max((int(match.group(1)) for name in filenames if (match := _TOC_FILENAME.fullmatch(name))), default=-1)


def _reads_latest_commit(searcher: Searcher, filenames: list[str]) -> bool:
    """Whether ``searcher`` reads the latest commit of the index holding ``filenames``.

    Rebuilding an index for a new schema restarts its generations at 0, so the
    rebuilt index can reach the generation of the one it replaced. Its segments
    have new ids, though, and the replaced segments' files are gone.
    """
    reader = searcher.reader()
    if reader.generation() != _latest_generation(filenames):
        return False
    stems = {name.split(".", 1)[0] for name in filenames}
    segments = (leaf.segment() for leaf, _docbase in reader.leaf_readers())
    return all(segment.segment_id() in stems for segment in segments if segment is not None)


def _stored_doc_hashes(reader: IndexReader) -> dict[str, str | None]:
    return {fields["id"]: fields.get(_DOC_HASH_FIELD) for fields in reader.all_stored_fields() if fields}


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
        self._schema_without_doc_hash = self.schema.copy()
        self.schema.add(_DOC_HASH_FIELD, ID(stored=True))
        # Opening an index and its segment readers costs as much as a search,
        # so searchers are kept until the index has a newer commit. A searcher
        # serves one thread at a time.
        self._idle_searchers: list[Searcher] = []
        self._idle_searchers_lock = threading.Lock()

    def _open(self) -> index.FileIndex:
        os.makedirs(self.index_dir, exist_ok=True)
        if index.exists_in(self.index_dir):
            ix = index.open_dir(self.index_dir)
            # An index written before documents carried their hash gains the
            # field in place (see ``build``), so the upgrade rewrites documents
            # in an ordinary commit rather than deleting a directory other
            # processes may be searching.
            if ix.schema == self.schema or ix.schema == self._schema_without_doc_hash:
                return ix
            # Schema drift — rebuild from scratch so old field layouts don't
            # poison ranking.
            log.info("ToolWhooshIndex schema changed; rebuilding %s", self.index_dir)
            ix.close()
            shutil.rmtree(self.index_dir)
            os.makedirs(self.index_dir, exist_ok=True)
        return index.create_in(self.index_dir, schema=self.schema)

    def build(self, tool_index: ToolIndex, tool_ids: Collection[str] | None = None) -> int:
        """Bring one panel-view corpus, or all entries when unscoped, up to date.

        Returns the number of documents written. Raises ``LockError`` when
        another writer holds the index for longer than
        ``INDEX_WRITE_LOCK_TIMEOUT``; nothing is written then.
        """
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
        doc_hashes = {str(doc["id"]): md5_hash_str(json.dumps(doc, sort_keys=True)) for doc in docs}

        # Tokenising is the expensive part of a build, and a shed install
        # changes a handful of documents in a corpus of thousands, so compare
        # against the hashes stored with the indexed documents and rewrite only
        # the differences. A previous config watcher may have written this
        # directory too, so the committed documents are the one record of what
        # it holds.
        ix = self._open()
        with ix.reader() as reader:
            if _stored_doc_hashes(reader) == doc_hashes:
                log.info("Whoosh index at %s is up to date; skipping rebuild", self.index_dir)
                return 0
        written = 0
        with ix.writer(limitmb=INDEX_WRITER_LIMITMB, timeout=INDEX_WRITE_LOCK_TIMEOUT) as writer:
            if _DOC_HASH_FIELD not in writer.schema:
                writer.add_field(_DOC_HASH_FIELD, ID(stored=True))
            # Another process may have committed between the check above and
            # taking the lock.
            with writer.reader() as reader:
                indexed = _stored_doc_hashes(reader)
            for tool_id in indexed.keys() - doc_hashes.keys():
                writer.delete_by_term("id", tool_id)
            for doc in docs:
                doc_hash = doc_hashes[str(doc["id"])]
                if indexed.get(str(doc["id"])) != doc_hash:
                    writer.update_document(**doc, **{_DOC_HASH_FIELD: doc_hash})
                    written += 1
        return written

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
        with self._searcher() as searcher:
            if searcher is None:
                return []
            return search_whoosh_searcher(searcher, query, limit=limit)

    @contextmanager
    def _searcher(self) -> Iterator[Searcher | None]:
        try:
            filenames = os.listdir(self.index_dir)
        except FileNotFoundError:
            filenames = []
        with self._idle_searchers_lock:
            searcher = self._idle_searchers.pop() if self._idle_searchers else None
        if searcher is not None and not _reads_latest_commit(searcher, filenames):
            searcher.close()
            searcher = None
        if searcher is None:
            if _latest_generation(filenames) < 0:
                yield None
                return
            searcher = index.open_dir(self.index_dir).searcher(weighting=search_weighting(self.tuning))
        try:
            yield searcher
        except BaseException:
            searcher.close()
            raise
        with self._idle_searchers_lock:
            self._idle_searchers.append(searcher)
