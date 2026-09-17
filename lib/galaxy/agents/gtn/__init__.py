"""
GTN (Galaxy Training Network) Integration Module.

This module provides search and retrieval capabilities for GTN tutorials
through a lightweight SQLite database with FTS5 full-text search.
"""

from .search import (
    FAQResult,
    GTNSearchDB,
    SearchResult,
)

__all__ = ["GTNSearchDB", "SearchResult", "FAQResult"]
