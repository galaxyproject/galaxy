"""Whoosh-backed tool search index built from a ``ToolIndex``.

Single source of truth for tool search ranking between the lazy and eager
paths. The schema and field boosts mirror
:class:`galaxy.tools.search.ToolPanelViewSearch`, so a query that ranks a
tool first under the eager toolbox ranks it first here too.

The populator (or the lazy toolbox at boot) calls :meth:`ToolWhooshIndex.build`
once the JSON index is committed. ``ToolIndex.search`` then opens the
on-disk Whoosh index and queries it with ``BM25F`` scoring.
"""

import logging
import os
import re
import shutil
from dataclasses import dataclass
from typing import (
    TYPE_CHECKING,
)

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
from whoosh.scoring import BM25F
from whoosh.writing import AsyncWriter

from galaxy.tool_util.ontologies.ontology_data import curated_tool_tags
from galaxy.util import unicodify

if TYPE_CHECKING:
    from .index import (
        ToolIndex,
        ToolIndexEntry,
    )

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class ToolSearchTuning:
    """Whoosh schema/boost knobs for tool search.

    Mirrors the ``tool_*`` keys on ``GalaxyAppConfiguration`` so this module
    can build a search index without importing the full Galaxy config type
    or carrying a god-object reference. Wire one in at the call site —
    typically via :meth:`from_config`.
    """

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

    @classmethod
    def from_config(cls, config) -> "ToolSearchTuning":
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
        )


def build_schema(tuning: ToolSearchTuning) -> Schema:
    """Whoosh schema mirroring ``ToolPanelViewSearch`` field set + boosts."""
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


def _entry_to_doc(entry: "ToolIndexEntry") -> dict | None:
    """Turn a ``ToolIndexEntry`` into the document shape ``Schema`` expects."""
    # Data manager tools are admin-only; mirror ``ToolPanelViewSearch._create_doc``
    # by leaving them out of the public search corpus.
    if entry.tool_type == "data_manager":
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
    if "/repos/" in tool_id:
        short = tool_id.rsplit("/", 2)[-2]
        all_ids = [tool_id, tool_id.rsplit("/", 1)[0], short]
    if tags := curated_tool_tags(all_ids):
        doc["tool_tags"] = unicodify(",".join(tags))
    return doc


class ToolWhooshIndex:
    """Build + query a Whoosh index over ``ToolIndexEntry`` rows.

    Build at populate time (or at lazy-toolbox boot if no populator ran),
    query from :meth:`ToolIndex.search`. The on-disk format is plain Whoosh —
    no Galaxy-specific encoding, so an operator can reopen it offline.
    """

    def __init__(self, index_dir: str, tuning: ToolSearchTuning) -> None:
        self.index_dir = index_dir
        self.tuning = tuning
        self.schema = build_schema(tuning)

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

    def build(self, tool_index: "ToolIndex") -> int:
        """Rebuild the on-disk index from ``tool_index.entries``.

        Returns the number of documents written.
        """
        ix = self._open()
        existing_ids: set[str] = set()
        with ix.reader() as reader:
            for fields in reader.all_stored_fields():
                if fields:
                    existing_ids.add(fields["id"])

        written = 0
        new_ids: set[str] = set()
        with AsyncWriter(ix) as writer:
            for entry in tool_index.entries.values():
                if entry.hidden:
                    continue
                doc = _entry_to_doc(entry)
                if doc is None:
                    continue
                writer.update_document(**doc)
                new_ids.add(doc["id"])
                written += 1
            for stale_id in existing_ids - new_ids:
                writer.delete_by_term("id", stale_id)
        return written

    def search(self, query: str, limit: int = 50) -> list[str]:
        """Return tool ids ranked for ``query`` (most-relevant first).

        ``limit`` matches the cap on the existing hand-rolled scorer.
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
        parser = MultifieldParser(search_fields, schema=ix.schema, group=OrGroup)
        parsed = parser.parse(query)
        with ix.searcher(weighting=BM25F()) as searcher:
            hits = searcher.search(parsed, limit=limit)
            return [hit["id"] for hit in hits]
