"""Whoosh-backed search index built from ``ToolIndex`` entries."""

import json
import logging
import os
import re
import shutil
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
from whoosh.scoring import BM25F

from galaxy.config import GalaxyAppConfiguration
from galaxy.tool_util.ontologies.ontology_data import curated_tool_tags
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


def _entry_to_doc(entry: ToolIndexEntry, *, include_help: bool = False) -> dict | None:
    """Turn a ``ToolIndexEntry`` into the document shape ``Schema`` expects.

    ``include_help`` projects the entry's captured help text into a ``help``
    field, mirroring the eager toolbox's ``index_tool_help`` behaviour. It's
    off by default so callers that build a help-less schema never emit a field
    the schema lacks.
    """
    if entry.tool_type == DataManagerTool.tool_type:
        return None
    name_clean = _clean(entry.name)
    doc: dict = {
        "id": unicodify(entry.id),
        "id_exact": unicodify(entry.id),
        "name": name_clean,
        "name_exact": name_clean,
        "description": unicodify(entry.description or ""),
        "section": unicodify(entry.panel_section_name or ""),
        "edam_operations": [_clean(op) for op in entry.edam_operations or []],
        "edam_topics": [_clean(topic) for topic in entry.edam_topics or []],
        "repository": unicodify(entry.repository_name or ""),
        "owner": unicodify(entry.repository_owner or ""),
    }
    # GUID has shape ``shed/repos/owner/repo/tool/version``. The eager path
    # carves out ``owner/repo/tool`` as the search stub; fall back to the
    # plain id for local tools.
    if "/" in entry.id:
        slash_indexes = [m.start() for m in re.finditer("/", entry.id)]
        if len(slash_indexes) >= 5:
            doc["stub"] = _clean(entry.id[slash_indexes[1] + 1 : slash_indexes[4]])
        else:
            doc["stub"] = unicodify(entry.id)
    else:
        doc["stub"] = unicodify(entry.id)
    if entry.labels:
        doc["labels"] = unicodify(" ".join(entry.labels))
    tool_id = (entry.id or "").lower()
    all_ids = [tool_id]
    if is_shed_guid(tool_id):
        all_ids = [tool_id, remove_version_from_guid(tool_id) or tool_id, short_tool_id(tool_id)]
    if tags := curated_tool_tags(all_ids):
        doc["tool_tags"] = unicodify(",".join(tags))
    if include_help and entry.help_text:
        doc["help"] = unicodify(entry.help_text)
    return doc


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

    def build(self, tool_index: ToolIndex) -> int:
        """Rebuild from entries, returning zero when the corpus is unchanged."""
        docs = []
        for entry in tool_index.entries.values():
            if entry.hidden:
                continue
            doc = _entry_to_doc(entry, include_help=self.index_help)
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
        """Like :meth:`search`, but pair each tool id with its BM25 score.

        Callers merging hits across several store indexes need the scores
        to interleave results instead of concatenating whole result lists.
        """
        if not query or not query.strip():
            return []
        if not (os.path.isdir(self.index_dir) and index.exists_in(self.index_dir)):
            return []
        ix = index.open_dir(self.index_dir)
        search_fields = [
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
        # ``help`` is only present when the corpus was built with help indexing
        # on; querying a field the on-disk schema lacks raises in the parser.
        if "help" in ix.schema.names():
            search_fields.append("help")
        parser = MultifieldParser(search_fields, schema=ix.schema, group=OrGroup)
        parsed = parser.parse(query)
        with ix.searcher(weighting=BM25F()) as searcher:
            hits = searcher.search(parsed, limit=limit)
            return [(hit["id"], hit.score) for hit in hits]
