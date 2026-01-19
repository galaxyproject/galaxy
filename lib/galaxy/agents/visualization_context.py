"""
Helper functions for providing visualization plugin context to AI agents.
"""

from typing import (
    Any,
    TYPE_CHECKING,
)

if TYPE_CHECKING:
    from galaxy.managers.context import ProvidesUserContext

# Shared keywords for identifying visualization-related queries
VISUALIZATION_KEYWORDS = [
    "visualiz",
    "chart",
    "plot",
    "graph",
    "view",
    "display",
    "genome browser",
    "igv",
    "phylo",
    "tree",
    "heatmap",
    "scatter",
    "histogram",
]


def is_visualization_query(query: str, visualizations: list[dict[str, Any]] | None = None) -> bool:
    """
    Check if a query is about visualization.

    Args:
        query: User query string
        visualizations: Optional list of available visualization plugins

    Returns:
        True if query appears to be visualization-related
    """
    query_lower = query.lower()

    # Check for general visualization keywords
    if any(keyword in query_lower for keyword in VISUALIZATION_KEYWORDS):
        return True

    # Check if query mentions any known visualization plugin by name or title
    if visualizations:
        for viz in visualizations:
            plugin_name = viz.get("name", "").lower()
            plugin_title = viz.get("title", "").lower()
            if plugin_name and plugin_name in query_lower:
                return True
            if plugin_title and plugin_title in query_lower:
                return True

    return False


def get_visualization_summaries(trans: "ProvidesUserContext") -> list[dict[str, Any]]:
    """
    Get condensed visualization plugin info for AI agent context.

    Returns a list of dictionaries containing:
    - name: Plugin identifier
    - title: Display name
    - description: Plugin description
    - keywords: Tags/keywords for the plugin
    - url: URL path to create visualization

    Args:
        trans: Galaxy transaction context

    Returns:
        List of visualization plugin summaries, sorted by title
    """
    summaries = []

    if not hasattr(trans, "app") or not hasattr(trans.app, "visualizations_registry"):
        return summaries

    registry = trans.app.visualizations_registry
    if not hasattr(registry, "plugins"):
        return summaries

    for name, plugin in registry.plugins.items():
        if plugin.config.get("hidden"):
            continue
        summaries.append({
            "name": name,
            "title": plugin.config.get("name") or name,
            "description": plugin.config.get("description") or "",
            "keywords": plugin.config.get("tags") or [],
            "url": f"/visualizations/create/{name}",
        })

    return sorted(summaries, key=lambda x: x["title"])


def format_visualization_context(summaries: list[dict[str, Any]]) -> str:
    """
    Format visualization summaries for inclusion in LLM prompts.

    Args:
        summaries: List of visualization plugin summaries

    Returns:
        Formatted string for prompt injection
    """
    if not summaries:
        return ""

    lines = ["## Available Visualizations", ""]

    for viz in summaries:
        title = viz.get("title", viz.get("name", "Unknown"))
        name = viz.get("name", "")
        description = viz.get("description", "")
        keywords = viz.get("keywords", [])

        line = f"- **{title}** (`{name}`)"
        if description:
            line += f": {description}"
        if keywords:
            line += f" [Keywords: {', '.join(keywords)}]"

        lines.append(line)

    lines.append("")
    return "\n".join(lines)
