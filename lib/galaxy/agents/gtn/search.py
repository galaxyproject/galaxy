"""
GTN Search Library - Interface to the GTN SQLite database.

This module provides search capabilities for Galaxy Training Network content
using SQLite FTS5 full-text search with BM25 ranking.
"""

import logging
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import (
    Any,
    Dict,
    List,
    Optional,
)

log = logging.getLogger(__name__)


def sanitize_fts5_query(query: str, preserve_phrases: bool = True) -> str:
    """
    Sanitize a query string for use with SQLite FTS5 full-text search.

    FTS5 has special operators that can cause syntax errors if present in user input:
    - Commas (,) are used for column specifications
    - Parentheses () are used for grouping
    - Colons (:) are used for column prefixes
    - Plus (+) and minus (-) are used for AND/NOT operators
    - Asterisk (*) is used for prefix matching
    - Double quotes (") are used for phrase matching

    Args:
        query: Raw user query string
        preserve_phrases: If True, keeps double quotes for phrase matching
                         If False, removes all quotes to prevent unmatched quote errors

    Returns:
        Sanitized query string safe for FTS5 MATCH operations

    Example:
        >>> sanitize_fts5_query("climate data, help me analyze (temperature)")
        'climate data help me analyze temperature'
        >>> sanitize_fts5_query('find "exact phrase" in data', preserve_phrases=True)
        'find "exact phrase" in data'
        >>> sanitize_fts5_query('find "exact phrase" in data', preserve_phrases=False)
        'find exact phrase in data'
    """
    if not query or not query.strip():
        return ""

    # Start with the input query
    sanitized = query

    # Replace hyphens with spaces for better matching (RNA-seq -> RNA seq)
    sanitized = sanitized.replace("-", " ")

    # Remove FTS5 special characters that commonly cause syntax errors
    sanitized = sanitized.replace(",", " ")  # Remove commas (column separators)
    sanitized = sanitized.replace("(", " ")  # Remove opening parentheses
    sanitized = sanitized.replace(")", " ")  # Remove closing parentheses
    sanitized = sanitized.replace(":", " ")  # Remove colons (column prefixes)
    sanitized = sanitized.replace("+", " ")  # Remove plus signs (AND operator)
    sanitized = sanitized.replace("?", " ")  # Remove question marks
    sanitized = sanitized.replace("!", " ")  # Remove exclamation marks
    sanitized = sanitized.replace(";", " ")  # Remove semicolons
    sanitized = sanitized.replace("[", " ")  # Remove square brackets
    sanitized = sanitized.replace("]", " ")  # Remove square brackets

    # Handle quotes based on preserve_phrases setting
    if not preserve_phrases:
        sanitized = sanitized.replace('"', " ")  # Remove all quotes
    # else: keep quotes as-is for phrase matching

    # Handle asterisks - remove them unless they're clearly meant for prefix matching
    # Simple heuristic: keep * only if it's at the end of a word
    sanitized = re.sub(r"\*(?!\s|$)", " ", sanitized)  # Remove * not at word boundaries

    # Clean up whitespace: collapse multiple spaces and trim
    sanitized = re.sub(r"\s+", " ", sanitized).strip()

    return sanitized


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
    result_type: str = "tutorial"  # "tutorial" or "faq"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "topic": self.topic,
            "tutorial": self.tutorial,
            "title": self.title,
            "url": self.url,
            "snippet": self.snippet,
            "score": self.score,
            "difficulty": self.difficulty,
            "hands_on": self.hands_on,
            "time_estimation": self.time_estimation,
            "description": self.description,
            "result_type": self.result_type,
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

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "category": self.category,
            "filename": self.filename,
            "title": self.title,
            "area": self.area,
            "snippet": self.snippet,
            "score": self.score,
            "result_type": "faq",
        }


class GTNSearchDB:
    """Interface to the GTN search database."""

    def __init__(self, db_path: str = None):
        """
        Initialize connection to GTN search database.

        Args:
            db_path: Path to the database file. If None, uses default location.
        """
        if db_path is None:
            # Default to the bundled database
            current_dir = Path(__file__).parent
            db_path = current_dir / "data" / "gtn_search.db"

        self.db_path = Path(db_path)

        if not self.db_path.exists():
            raise FileNotFoundError(f"GTN database not found at {self.db_path}")

        # Test connection
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM tutorials")
                count = cursor.fetchone()[0]
                log.info(f"GTN database loaded with {count} tutorials")
        except sqlite3.Error as e:
            raise RuntimeError(f"Failed to initialize GTN database: {e}") from e

    def _get_connection(self) -> sqlite3.Connection:
        """Get a database connection."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def search(
        self,
        query: str,
        limit: int = 5,
        topic: Optional[str] = None,
        difficulty: Optional[str] = None,
        hands_on_only: bool = False,
    ) -> List[SearchResult]:
        """
        Search tutorials using FTS5.

        Args:
            query: Search terms (supports phrases with quotes)
            limit: Maximum results to return
            topic: Filter by topic (e.g., "transcriptomics")
            difficulty: Filter by difficulty level
            hands_on_only: Only return hands-on tutorials

        Returns:
            List of SearchResult objects with tutorial info and relevance scores
        """
        if not query:
            return []

        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                # Sanitize query for FTS5 to prevent syntax errors
                fts_query = sanitize_fts5_query(query, preserve_phrases=True)

                # Build the base query
                # Note: FTS5 tables are separate, so we join on rowid
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
                        bm25(tutorials_fts) as score
                    FROM tutorials_fts
                    JOIN tutorials t ON t.id = tutorials_fts.rowid
                    WHERE tutorials_fts MATCH ?
                """

                params = [fts_query]

                # Add filters
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

                # Add ordering and limit
                sql += " ORDER BY score LIMIT ?"
                params.append(limit)

                # Execute query
                results = cursor.execute(sql, params)

                # Convert to SearchResult objects
                search_results = []
                for row in results:
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
        category: Optional[str] = None,
        area: Optional[str] = None,
    ) -> List[FAQResult]:
        """
        Search FAQs using FTS5.

        Args:
            query: Search terms
            limit: Maximum results to return
            category: Filter by category (galaxy or gtn)
            area: Filter by area (e.g., "analysis", "account")

        Returns:
            List of FAQResult objects
        """
        if not query:
            return []

        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                # Sanitize query for FTS5 to prevent syntax errors
                fts_query = sanitize_fts5_query(query, preserve_phrases=True)

                # Build the query
                sql = """
                    SELECT 
                        f.id,
                        f.category,
                        f.filename,
                        f.title,
                        f.area,
                        f.content,
                        snippet(faqs_fts, 1, '<mark>', '</mark>', '...', 30) as snippet,
                        bm25(faqs_fts) as score
                    FROM faqs_fts
                    JOIN faqs f ON f.id = faqs_fts.rowid
                    WHERE faqs_fts MATCH ?
                """

                params = [fts_query]

                # Add filters
                conditions = []
                if category:
                    conditions.append("f.category = ?")
                    params.append(category)

                if area:
                    conditions.append("f.area = ?")
                    params.append(area)

                if conditions:
                    sql += " AND " + " AND ".join(conditions)

                # Add ordering and limit
                sql += " ORDER BY score LIMIT ?"
                params.append(limit)

                # Execute query
                results = cursor.execute(sql, params)

                # Convert to FAQResult objects
                faq_results = []
                for row in results:
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

    def get_tutorial_content(self, topic: str, tutorial: str, max_length: Optional[int] = None) -> Optional[str]:
        """
        Retrieve full or truncated tutorial content.

        Args:
            topic: Topic of the tutorial
            tutorial: Tutorial name
            max_length: Maximum content length to return

        Returns:
            Tutorial content or None if not found
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                result = cursor.execute(
                    "SELECT content FROM tutorials WHERE topic = ? AND tutorial = ?", (topic, tutorial)
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

    def get_topics(self) -> List[str]:
        """
        List all available topics.

        Returns:
            List of topic names
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                results = cursor.execute("SELECT DISTINCT topic FROM tutorials ORDER BY topic")

                return [row["topic"] for row in results]

        except sqlite3.Error as e:
            log.warning(f"Failed to get topics: {e}")
            return []

    def get_metadata(self) -> Dict[str, Any]:
        """
        Get database version and build information.

        Returns:
            Dictionary with metadata
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                results = cursor.execute("SELECT key, value FROM metadata")

                metadata = {}
                for row in results:
                    metadata[row["key"]] = row["value"]

                return metadata

        except sqlite3.Error as e:
            log.warning(f"Failed to get metadata: {e}")
            return {}

    def suggest_queries(self, partial: str) -> List[str]:
        """
        Suggest queries based on partial input.

        Args:
            partial: Partial query string

        Returns:
            List of suggested queries
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                # Get example queries that match the partial
                results = cursor.execute(
                    "SELECT query FROM example_queries WHERE query LIKE ? LIMIT 5", (f"%{partial}%",)
                )

                suggestions = [row["query"] for row in results]

                # Also suggest popular topics
                if len(suggestions) < 5:
                    topic_results = cursor.execute(
                        """
                        SELECT topic, COUNT(*) as count 
                        FROM tutorials 
                        WHERE topic LIKE ? 
                        GROUP BY topic 
                        ORDER BY count DESC 
                        LIMIT ?
                        """,
                        (f"%{partial}%", 5 - len(suggestions)),
                    )

                    for row in topic_results:
                        suggestions.append(f"topic:{row['topic']}")

                return suggestions

        except sqlite3.Error as e:
            log.warning(f"Failed to get query suggestions: {e}")
            return []

    def get_tutorial_by_id(self, tutorial_id: int) -> Optional[Dict[str, Any]]:
        """
        Get complete tutorial information by ID.

        Args:
            tutorial_id: Tutorial database ID

        Returns:
            Dictionary with tutorial information or None
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                result = cursor.execute(
                    """
                    SELECT 
                        id, topic, tutorial, title, description, url,
                        difficulty, hands_on, time_estimation, content,
                        questions, objectives, key_points,
                        tools_json, requirements_json, tags_json
                    FROM tutorials
                    WHERE id = ?
                    """,
                    (tutorial_id,),
                )

                row = result.fetchone()
                if row:
                    return dict(row)

                return None

        except sqlite3.Error as e:
            log.warning(f"Failed to get tutorial by ID {tutorial_id}: {e}")
            return None

    def search_by_tools(self, tool_names: List[str], limit: int = 5) -> List[SearchResult]:
        """
        Search for tutorials that use specific tools.

        Args:
            tool_names: List of tool names to search for
            limit: Maximum results to return

        Returns:
            List of SearchResult objects
        """
        if not tool_names:
            return []

        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                # Build query to search in tools_json field
                tool_conditions = []
                params = []
                for tool in tool_names:
                    tool_conditions.append("tools_json LIKE ?")
                    params.append(f"%{tool}%")

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
