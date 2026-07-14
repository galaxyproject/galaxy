"""
GTN Search Library - Interface to the GTN SQLite database.

Provides search over Galaxy Training Network tutorials and FAQs
using SQLite FTS5 full-text search with BM25 ranking.
"""

import http.client
import logging
import os
import re
import shutil
import sqlite3
import tarfile
import urllib.request
from dataclasses import dataclass
from datetime import (
    datetime,
    timedelta,
    timezone,
)
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import (
    Any,
)

from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings

GTN_DATABASE_URL = "https://depot.galaxyproject.org/chatgxy/gtn_search.db"
GTN_VECTOR_DATABASE_URL = "https://zenodo.org/records/20707620/files/chroma_db.tar.gz"
GTN_FAQ_BASE_URL = "https://training.galaxyproject.org/training-material/faqs"
# Connect + per-read timeout for the initial GTN database download. The file
# is ~25MB; this bounds individual socket reads so a stalled depot can't hang
# an agent init forever. Total wall-clock can still exceed this if the
# remote keeps sending small chunks, which is the trade for stdlib-only.
GTN_DOWNLOAD_TIMEOUT_SECONDS = 60
# HEAD is a small request; an unreachable depot during a freshness check
# shouldn't hold the periodic queue for the full download budget.
GTN_FRESHNESS_TIMEOUT_SECONDS = 10

_ONE_SECOND = timedelta(seconds=1)

log = logging.getLogger(__name__)


def _parse_last_modified(header: str | None) -> datetime | None:
    """Parse an HTTP Last-Modified header into an aware UTC datetime, or None."""
    if not header:
        return None
    try:
        parsed = parsedate_to_datetime(header)
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _escape_like(value: str) -> str:
    """Escape SQLite LIKE metacharacters so tool names match literally."""
    return value.replace("\\", "\\\\").replace("%", r"\%").replace("_", r"\_")


def _or_form(fts_query: str) -> str | None:
    """OR-joined fallback for a multi-token FTS5 query, or None.

    Returns None for quoted phrases (preserve as-is) and single-token
    queries (no fallback needed). Callers should retry an AND-form
    search with this if the AND form returns no rows.
    """
    if not fts_query or '"' in fts_query or " " not in fts_query:
        return None
    return " OR ".join(fts_query.split())


def sanitize_fts5_query(query: str, preserve_phrases: bool = True) -> str:
    """Strip FTS5 operators from user input to prevent syntax errors.

    >>> sanitize_fts5_query("climate data, help me analyze (temperature)")
    'climate data help me analyze temperature'
    >>> sanitize_fts5_query('find "exact phrase" in data', preserve_phrases=True)
    'find "exact phrase" in data'
    >>> sanitize_fts5_query('find "exact phrase" in data', preserve_phrases=False)
    'find exact phrase in data'
    >>> sanitize_fts5_query("color deconvolution site:example.org/path")
    'color deconvolution site example org path'
    """
    if not query or not query.strip():
        return ""

    # Split hyphens (RNA-seq -> RNA seq) so the porter stemmer can index each
    # word individually rather than treating the hyphenated form as one token.
    sanitized = query.replace("-", " ")

    # Models sometimes paste URL- or operator-flavored tokens (site:, dotted
    # hostnames, slashes, column-filter colons). Left in, ".", ":" and "/" reach
    # FTS5 as syntax and the whole search errors out as no-results -- so strip
    # them along with the other FTS5 operators.
    for char in ",.:/()+?!;[]^=~@<>{}|&":
        sanitized = sanitized.replace(char, " ")

    # Phrase preservation only works with a balanced pair of quotes. An odd
    # count means the user left one open, and passing that to FTS5 raises
    # "unterminated string" which the search layer swallows as no-results.
    if not preserve_phrases or sanitized.count('"') % 2 == 1:
        sanitized = sanitized.replace('"', " ")

    # Keep "*" only at the end of a word so users can write prefix matches
    # like "tumor*", but strip stray ones that would be FTS5 syntax errors.
    sanitized = re.sub(r"\*(?!\s|$)", " ", sanitized)

    return re.sub(r"\s+", " ", sanitized).strip()


@dataclass
class SearchResult:
    """Represents a search result from the GTN database."""

    id: int
    topic: str
    tutorial: str
    title: str
    url: str
    snippet: str
    score: float
    difficulty: str
    hands_on: bool
    time_estimation: str
    description: str = ""
    result_type: str = "tutorial"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization.

        Returns only the fields the LLM needs to pick tutorials and
        construct get_tutorial_content calls, keeping token usage low.
        Includes ``score`` so the agent can gauge match quality.
        """
        snippet = self.snippet.replace("<mark>", "").replace("</mark>", "")
        return {
            "title": self.title,
            "topic": self.topic,
            "tutorial": self.tutorial,
            "url": self.url,
            "difficulty": self.difficulty,
            "time_estimation": self.time_estimation,
            "snippet": snippet,
            "score": round(self.score, 2),
        }


@dataclass
class GTNVectorSearchResults:
    """Represents a search result from vector store db."""

    id: str
    title: str
    topic: str
    tutorial: str
    url: str
    score: float
    source: str
    difficulty: str
    time_estimation: str
    description: str
    snippet: str
    content: str

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization.

        Returns only the fields the LLM needs to pick tutorials and
        construct get_tutorial_content calls, keeping token usage low.
        Includes ``score`` so the agent can gauge match quality.
        """
        return {
            "id": self.id,
            "title": self.title,
            "topic": self.topic,
            "tutorial": self.tutorial,
            "url": self.url,
            "difficulty": self.difficulty,
            "time_estimation": self.time_estimation,
            "description": self.description,
            "snippet": self.snippet,
            "content": self.content,
            "score": round(self.score, 2),
            "source": self.source,
        }


@dataclass
class WorkflowVectorSearchResults:
    """Represents a search result from vector store db."""

    source: str
    categories: str
    content_type: str
    workflow_id: str
    collections: str
    doi: str
    updated: str
    path: str
    url: str
    workflow_name: str
    topic: str
    data_source: str
    score: float
    snippet: str
    content: str

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization.

        Returns the workflow metadata fields provided by the IWC vector store.
        Includes ``score`` so the agent can gauge match quality.
        """
        return {
            "source": self.source,
            "categories": self.categories,
            "content_type": self.content_type,
            "workflow_id": self.workflow_id,
            "collections": self.collections,
            "doi": self.doi,
            "updated": self.updated,
            "path": self.path,
            "url": self.url,
            "workflow_name": self.workflow_name,
            "topic": self.topic,
            "data_source": self.data_source,
            "snippet": self.snippet,
            "content": self.content,
            "score": round(self.score, 2),
        }
    
@dataclass
class FAQVectorSearchResults:
    """Represents a search result from vector store db."""
    area: str
    content: str
    snippet: str
    score: float
    source: str
    content_type: str
    tutorial: str
    area: str
    question: str
    tier: str
    topic: str

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization.

        Returns the FAQ metadata fields provided by the FAQ vector store.
        Includes ``score`` so the agent can gauge match quality.
        """
        return {
            "area": self.area,
            "question": self.question,
            "snippet": self.snippet,
            "score": round(self.score, 2),
            "result_type": "faq",
            "content": self.content,
            "tier": self.tier,
            "topic": self.topic,
            "source": self.source,
            "content_type": self.content_type,
            "tutorial": self.tutorial,
        }


@dataclass
class FAQResult:
    """Represents a FAQ search result."""

    id: int
    category: str
    filename: str
    title: str
    area: str
    content: str
    snippet: str
    score: float

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        snippet = self.snippet.replace("<mark>", "").replace("</mark>", "")
        return {
            "title": self.title,
            "category": self.category,
            "filename": self.filename,
            "area": self.area,
            "url": f"{GTN_FAQ_BASE_URL}/{self.category}/{self.filename}.html",
            "snippet": snippet,
            "score": round(self.score, 2),
            "result_type": "faq",
        }


class GTNSearchDB:
    """Interface to the GTN search database."""

    def __init__(self, db_path: str | None = None, vector_db_path:str | None = None, \
                 download_url: str | None = None, vector_db_url: str | None = None):
        if db_path is None and vector_db_path is None:
            current_dir = Path(__file__).parent
            self.db_path = current_dir / "data" / "gtn_search.db"
            self.vector_db_path = current_dir / "data" / "gtn_chroma_db_composite"
        else:
            self.db_path = Path(db_path)
            self.vector_db_path = Path(vector_db_path)

        self.download_url = download_url or GTN_DATABASE_URL
        self.vector_db_url = vector_db_url or GTN_VECTOR_DATABASE_URL

        if not self.db_path.exists():
            self._download_database()

        if not self.vector_db_path.exists():
            self._download_vector_database()

        try:
            metadata = self._validate_database_file(self.db_path)
            log.info(
                f"GTN database loaded from {self.db_path} "
                f"(version={metadata['version']}, built={metadata['build_date']}, "
                f"tutorials={metadata['tutorial_count']})"
            )
        except sqlite3.Error as e:
            raise RuntimeError(f"Failed to initialize GTN database: {e}") from e

    @staticmethod
    def _read_meta(cursor: sqlite3.Cursor, key: str) -> str | None:
        try:
            cursor.execute("SELECT value FROM metadata WHERE key = ?", (key,))
        except sqlite3.Error:
            return None
        row = cursor.fetchone()
        return row[0] if row else None

    def _download_database(self):
        """Download the GTN database from the configured URL."""
        metadata = self._download_database_to_path(self.db_path, self.download_url)
        log.info(
            f"GTN database downloaded to {self.db_path} "
            f"(version={metadata['version']}, tutorials={metadata['tutorial_count']}, faqs={metadata['faq_count']})"
        )
    
    def _download_vector_database(self):
        """Download the GTN vector database from the configured URL."""
        if not self.vector_db_url:
            log.warning("No URL configured for GTN vector database; skipping download.")
            return

        try:
            self.vector_db_path = GTNSearchDB._download_vector_database_to_path(self.vector_db_path, self.vector_db_url)
            log.info(f"GTN vector database downloaded to {self.vector_db_path}")
        except Exception as e:
            log.warning(f"Failed to download GTN vector database: {e}")

    def refresh(self) -> None:
        """Force-redownload the database from ``download_url``, replacing it atomically."""
        self._download_database()

    @classmethod
    def refresh_database(cls, db_path: str | Path, download_url: str | None = None) -> dict[str, Any]:
        """Download, validate, and atomically replace a GTN database without opening the old copy."""
        return cls._download_database_to_path(Path(db_path), download_url or GTN_DATABASE_URL)

    @classmethod
    def _download_vector_database_to_path(cls, vector_db_path: Path, vector_db_url: str) -> None:
        vector_db_path.mkdir(parents=True, exist_ok=True)
        tmp_path = vector_db_path.with_suffix(".tmp")
        tmp_path.unlink(missing_ok=True)
        try:
            log.info(f"Downloading vector database from {vector_db_url} ...")
            with urllib.request.urlopen(vector_db_url, timeout=GTN_DOWNLOAD_TIMEOUT_SECONDS) as response:
                with tarfile.open(fileobj=response, mode="r:gz") as tar:
                    tar.extractall(path=tmp_path)
            items = list(tmp_path.iterdir())
            if len(items) == 1 and items[0].is_dir():
                source_dir = items[0]
            else:
                source_dir = tmp_path
            for item in source_dir.iterdir():
                target = vector_db_path / item.name
                if item.is_dir():
                    shutil.copytree(item, target, dirs_exist_ok=True)
                else:
                    shutil.copy2(item, target)
            if tmp_path.exists():
                shutil.rmtree(tmp_path)
        except (OSError, tarfile.TarError) as e:
            tmp_path.unlink(missing_ok=True)
            raise FileNotFoundError(f"GTN vector database download failed for {vector_db_path}: {e}") from e

    def refresh_database_if_stale(cls, db_path: str | Path, download_url: str | None = None) -> dict[str, Any] | None:
        """HEAD the URL and re-download only if its Last-Modified is newer than the local file's mtime.

        Returns the new metadata dict when a refresh happened, ``None`` when the
        local copy was current. If the local file is missing, or the HEAD fails,
        falls through to a full download -- safer than skipping silently when we
        can't tell whether the local copy is current.
        """
        target = Path(db_path)
        url = download_url or GTN_DATABASE_URL

        if target.exists():
            remote_mtime = cls._remote_last_modified(url)
            if remote_mtime is not None:
                local_mtime = datetime.fromtimestamp(target.stat().st_mtime, tz=timezone.utc)
                # depot's Last-Modified has second resolution; the 1-second slack
                # absorbs rounding so a successful refresh isn't immediately re-triggered.
                if remote_mtime <= local_mtime + _ONE_SECOND:
                    return None

        return cls._download_database_to_path(target, url)

    @staticmethod
    def _remote_last_modified(url: str) -> datetime | None:
        """HEAD ``url`` and return its parsed Last-Modified, or None on failure."""
        try:
            req = urllib.request.Request(url, method="HEAD")
            with urllib.request.urlopen(req, timeout=GTN_FRESHNESS_TIMEOUT_SECONDS) as resp:
                header = resp.headers.get("Last-Modified")
        except (OSError, ValueError, http.client.HTTPException) as e:
            # http.client.HTTPException covers malformed responses
            # (RemoteDisconnected, BadStatusLine) that urllib doesn't wrap
            # into URLError -- without it the periodic queue would record a
            # failed run instead of falling through to a full download.
            log.debug(f"GTN freshness HEAD failed for {url}: {e}")
            return None
        return _parse_last_modified(header)

    @classmethod
    def _download_database_to_path(cls, db_path: Path, download_url: str) -> dict[str, Any]:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = db_path.with_suffix(f"{db_path.suffix}.tmp")
        tmp_path.unlink(missing_ok=True)
        try:
            log.info(f"Downloading GTN database from {download_url} ...")
            with urllib.request.urlopen(download_url, timeout=GTN_DOWNLOAD_TIMEOUT_SECONDS) as response:
                last_modified_header = response.headers.get("Last-Modified")
                with open(tmp_path, "wb") as out:
                    shutil.copyfileobj(response, out)
            metadata = cls._validate_database_file(tmp_path)
            # Stamp the file with depot's Last-Modified so the next stale check
            # compares against the upstream mtime rather than "right now", which
            # would also drift with any local clock skew.
            remote_dt = _parse_last_modified(last_modified_header)
            if remote_dt is not None:
                remote_ts = remote_dt.timestamp()
                os.utime(tmp_path, (remote_ts, remote_ts))
            tmp_path.replace(db_path)
            return metadata
        except (OSError, sqlite3.Error) as e:
            tmp_path.unlink(missing_ok=True)
            raise FileNotFoundError(f"GTN database download failed for {db_path}: {e}") from e

    @classmethod
    def _validate_database_file(cls, db_path: Path) -> dict[str, Any]:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, isolation_level=None)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM tutorials")
            tutorial_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM faqs")
            faq_count = cursor.fetchone()[0]
            return {
                "tutorial_count": tutorial_count,
                "faq_count": faq_count,
                "version": cls._read_meta(cursor, "version") or "unknown",
                "build_date": cls._read_meta(cursor, "build_date") or "unknown",
            }
        finally:
            conn.close()

    def _get_connection(self) -> sqlite3.Connection:
        """Open a read-only, autocommit connection to the GTN database."""
        conn = sqlite3.connect(
            f"file:{self.db_path}?mode=ro",
            uri=True,
            isolation_level=None,
            check_same_thread=False,
        )
        conn.row_factory = sqlite3.Row
        return conn

    def search(
        self,
        query: str,
        limit: int = 5,
        topic: str | None = None,
        difficulty: str | None = None,
        hands_on_only: bool = False,
    ) -> list[SearchResult]:
        """Search tutorials using FTS5 full-text search with optional filters."""
        if not query:
            return []

        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                fts_query = sanitize_fts5_query(query, preserve_phrases=True)
                # tutorials_fts columns: title, description, content, topic
                # Weight title/description/topic above raw content so broad
                # queries surface the tutorial that's actually about the topic
                # rather than the one that mentions it most.
                sql = """
                    SELECT
                        t.id,
                        t.topic,
                        t.tutorial,
                        t.title,
                        t.url,
                        t.description,
                        t.difficulty,
                        t.hands_on,
                        t.time_estimation,
                        snippet(tutorials_fts, 2, '<mark>', '</mark>', '...', 30) as snippet,
                        bm25(tutorials_fts, 10.0, 3.0, 1.0, 2.0) as score
                    FROM tutorials_fts
                    JOIN tutorials t ON t.id = tutorials_fts.rowid
                    WHERE tutorials_fts MATCH ?
                """

                params: list[Any] = [fts_query]

                conditions = []
                if topic:
                    conditions.append("t.topic = ?")
                    params.append(topic)

                if difficulty:
                    conditions.append("t.difficulty = ?")
                    params.append(difficulty.lower())

                if hands_on_only:
                    conditions.append("t.hands_on = 1")

                if conditions:
                    sql += " AND " + " AND ".join(conditions)

                sql += " ORDER BY score LIMIT ?"
                params.append(limit)

                rows = list(cursor.execute(sql, params))
                or_query = _or_form(fts_query) if not rows else None
                if or_query:
                    params[0] = or_query
                    rows = list(cursor.execute(sql, params))

                search_results = []
                for row in rows:
                    search_results.append(
                        SearchResult(
                            id=row["id"],
                            topic=row["topic"],
                            tutorial=row["tutorial"],
                            title=row["title"],
                            url=row["url"],
                            snippet=row["snippet"],
                            score=abs(row["score"]),  # BM25 scores are negative
                            difficulty=row["difficulty"],
                            hands_on=bool(row["hands_on"]),
                            time_estimation=row["time_estimation"] or "",
                            description=row["description"] or "",
                        )
                    )

                return search_results

        except sqlite3.Error as e:
            log.warning(f"Search failed for query '{query}': {e}")
            return []

    def search_faqs(
        self,
        query: str,
        limit: int = 5,
        category: str | None = None,
        area: str | None = None,
    ) -> list[FAQResult]:
        """Search FAQs using FTS5 full-text search with optional filters."""
        if not query:
            return []

        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                fts_query = sanitize_fts5_query(query, preserve_phrases=True)
                # faqs_fts columns: title, content, category, area
                sql = """
                    SELECT
                        f.id,
                        f.category,
                        f.filename,
                        f.title,
                        f.area,
                        f.content,
                        snippet(faqs_fts, 1, '<mark>', '</mark>', '...', 30) as snippet,
                        bm25(faqs_fts, 10.0, 1.0, 2.0, 2.0) as score
                    FROM faqs_fts
                    JOIN faqs f ON f.id = faqs_fts.rowid
                    WHERE faqs_fts MATCH ?
                """

                params: list[Any] = [fts_query]

                conditions = []
                if category:
                    conditions.append("f.category = ?")
                    params.append(category)

                if area:
                    conditions.append("f.area = ?")
                    params.append(area)

                if conditions:
                    sql += " AND " + " AND ".join(conditions)

                sql += " ORDER BY score LIMIT ?"
                params.append(limit)

                rows = list(cursor.execute(sql, params))
                or_query = _or_form(fts_query) if not rows else None
                if or_query:
                    params[0] = or_query
                    rows = list(cursor.execute(sql, params))

                faq_results = []
                for row in rows:
                    faq_results.append(
                        FAQResult(
                            id=row["id"],
                            category=row["category"],
                            filename=row["filename"],
                            title=row["title"],
                            area=row["area"] or "",
                            content=row["content"],
                            snippet=row["snippet"],
                            score=abs(row["score"]),
                        )
                    )

                return faq_results

        except sqlite3.Error as e:
            log.warning(f"FAQ search failed for query '{query}': {e}")
            return []
        
    def search_gtn_vector_db(
        self,
        query: str,
        embeddings: OpenAIEmbeddings,
        persist_dir: Path,
        collection_name: str = "gtn_tutorials",
        limit: int = 5,
        doc_type: str | None = None,
    ) -> list[GTNVectorSearchResults]:
        try:
            # Check if the persist directory exists
            if not Path(persist_dir).exists():
                log.warning(f"ChromaDB persist directory does not exist: {persist_dir}")
                return []

            vectorstore = Chroma(
                persist_directory=persist_dir,
                collection_name=collection_name,
                embedding_function=embeddings
            )

            # Use similarity_search_with_score to get relevance scores
            results_with_scores = vectorstore.similarity_search_with_score(query, k=limit)

            vector_results = []

            for i, (doc, score) in enumerate(results_with_scores, start=1):
                source_id = doc.metadata.get("source")
                parent_docs = vectorstore.get(where={"source": source_id})
                # use longer context by taking multiple documents with the same source, if available
                parent_context_docs = ""
                for d in parent_docs["documents"][:10]:
                    parent_context_docs += d + " "

                result = GTNVectorSearchResults(
                    id=doc.metadata.get("title"),
                    title=doc.metadata.get("title"),
                    description=f" {doc.metadata.get('topic')} {doc.metadata.get('title')} ",
                    topic=doc.metadata.get("topic"),
                    tutorial=doc.metadata.get("tutorial"),
                    url=doc.metadata.get("url"),
                    score=score,
                    source=doc.metadata.get("source"),
                    difficulty=doc.metadata.get("difficulty"),
                    time_estimation=doc.metadata.get("time_estimation"),
                    snippet=str(doc.page_content),
                    content=parent_context_docs,
                )
                vector_results.append(result)

            return vector_results
        except Exception as e:
            log.warning(f"Vector DB GTN search failed for query '{query}': {e}")
            return []

    def search_workflow_vector_db(
        self,
        query: str,
        embeddings: OpenAIEmbeddings,
        persist_dir: Path,
        collection_name: str = "iwc_workflows",
        limit: int = 5,
    ) -> list[WorkflowVectorSearchResults]:
        try:
            # Check if the persist directory exists
            if not Path(persist_dir).exists():
                log.warning(f"ChromaDB persist directory does not exist: {persist_dir}")
                return []

            vectorstore = Chroma(
                persist_directory=persist_dir,
                collection_name=collection_name,
                embedding_function=embeddings
            )

            # Use similarity_search_with_score to get relevance scores
            results_with_scores = vectorstore.similarity_search_with_score(query, k=limit)

            vector_results = []

            for i, (doc, score) in enumerate(results_with_scores, start=1):
                source_id = doc.metadata.get("source")
                parent_docs = vectorstore.get(where={"source": source_id})
                # use longer context by taking multiple documents with the same source, if available
                parent_context_docs = ""
                for d in parent_docs["documents"][:10]:
                    parent_context_docs += d + " "

                result = WorkflowVectorSearchResults(
                    source=doc.metadata.get("source", ""),
                    categories=doc.metadata.get("categories", ""),
                    content_type=doc.metadata.get("content_type", ""),
                    workflow_id=doc.metadata.get("workflow_id", ""),
                    collections=doc.metadata.get("collections", ""),
                    doi=doc.metadata.get("doi", ""),
                    updated=doc.metadata.get("updated", ""),
                    path=doc.metadata.get("path", ""),
                    url=doc.metadata.get("url", ""),
                    workflow_name=doc.metadata.get("workflow_name", ""),
                    topic=doc.metadata.get("topic", ""),
                    data_source=doc.metadata.get("data_source", ""),
                    score=score,
                    snippet=str(doc.page_content),
                    content=parent_context_docs,
                )
                vector_results.append(result)

            return vector_results
        except Exception as e:
            log.warning(f"Vector DB workflow search failed for query '{query}': {e}")
            return []
        
    def search_faq_vector_db(
        self,
        query: str,
        embeddings: OpenAIEmbeddings,
        persist_dir: Path,
        collection_name: str = "galaxy_faqs",
        limit: int = 5,
    ) -> list[FAQVectorSearchResults]:
        try:
            # Check if the persist directory exists
            if not Path(persist_dir).exists():
                log.warning(f"ChromaDB persist directory does not exist: {persist_dir}")
                return []

            vectorstore = Chroma(
                persist_directory=persist_dir,
                collection_name=collection_name,
                embedding_function=embeddings
            )

            # Use similarity_search_with_score to get relevance scores
            results_with_scores = vectorstore.similarity_search_with_score(query, k=limit)

            vector_results = []

            for i, (doc, score) in enumerate(results_with_scores, start=1):
                source_id = doc.metadata.get("source")
                parent_docs = vectorstore.get(where={"source": source_id})
                # use longer context by taking multiple documents with the same source, if available
                parent_context_docs = ""
                for d in parent_docs["documents"][:3]:
                    parent_context_docs += d + " "

                result = FAQVectorSearchResults(
                    source=doc.metadata.get("source", ""),
                    content_type=doc.metadata.get("content_type", ""),
                    tutorial=doc.metadata.get("tutorial", ""),
                    area=doc.metadata.get("area", ""),
                    question=doc.metadata.get("question", ""),
                    tier=doc.metadata.get("tier", ""),
                    topic=doc.metadata.get("topic", ""),
                    score=score,
                    snippet=str(doc.page_content),
                    content=parent_context_docs,
                )
                vector_results.append(result)

            return vector_results
        except Exception as e:
            log.warning(f"Vector DB FAQ search failed for query '{query}': {e}")
            return []

    def get_tutorial_content(self, topic: str, tutorial: str, max_length: int | None = None) -> str | None:
        """Retrieve tutorial content, optionally truncated to max_length."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                result = cursor.execute(
                    "SELECT content FROM tutorials WHERE topic = ? AND tutorial = ?",
                    (topic, tutorial),
                )

                row = result.fetchone()
                if row:
                    content = row["content"]
                    if max_length and len(content) > max_length:
                        content = content[:max_length] + "..."
                    return content

                return None

        except sqlite3.Error as e:
            log.warning(f"Failed to get tutorial content for {topic}/{tutorial}: {e}")
            return None

    def get_topics(self) -> list[str]:
        """List all available topics."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                results = cursor.execute("SELECT DISTINCT topic FROM tutorials ORDER BY topic")

                return [row["topic"] for row in results]

        except sqlite3.Error as e:
            log.warning(f"Failed to get topics: {e}")
            return []

    def search_by_tools(self, tool_names: list[str], limit: int = 5) -> list[SearchResult]:
        """Search for tutorials that use specific tools."""
        if not tool_names:
            return []

        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                tool_conditions = []
                params: list[Any] = []
                for tool in tool_names:
                    tool_conditions.append(r"tools_json LIKE ? ESCAPE '\'")
                    params.append(f"%{_escape_like(tool)}%")

                sql = f"""
                    SELECT
                        id, topic, tutorial, title, url, description,
                        difficulty, hands_on, time_estimation
                    FROM tutorials
                    WHERE {" OR ".join(tool_conditions)}
                    LIMIT ?
                """
                params.append(limit)

                results = cursor.execute(sql, params)

                search_results = []
                for row in results:
                    search_results.append(
                        SearchResult(
                            id=row["id"],
                            topic=row["topic"],
                            tutorial=row["tutorial"],
                            title=row["title"],
                            url=row["url"],
                            snippet=f"Tutorial uses tools: {', '.join(tool_names)}",
                            score=1.0,  # No relevance score for tool search
                            difficulty=row["difficulty"],
                            hands_on=bool(row["hands_on"]),
                            time_estimation=row["time_estimation"] or "",
                            description=row["description"] or "",
                        )
                    )

                return search_results

        except sqlite3.Error as e:
            log.warning(f"Failed to search by tools: {e}")
            return []
