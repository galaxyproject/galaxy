"""Extract ToolShed tool references from Galaxy workflows.

Handles both native (.ga) and format2 (.gxwf.yml) workflow formats.
Recurses into subworkflows.
"""

import json
import logging
from typing import (
    Dict,
    List,
    Optional,
    Set,
    Tuple,
)

log = logging.getLogger(__name__)


def extract_toolshed_tools(workflow_dict: Dict) -> List[Tuple[str, Optional[str]]]:
    """Extract all ToolShed tool references from a workflow dict.

    Returns list of (tool_id, tool_version) tuples.
    Only includes tools with '/repos/' in their tool_id (ToolShed tools).
    Deduplicates by (tool_id, tool_version).
    """
    seen: Set[Tuple[str, Optional[str]]] = set()
    _extract_from_dict(workflow_dict, seen)
    return sorted(seen)


def extract_all_tools(workflow_dict: Dict) -> List[Tuple[str, Optional[str]]]:
    """Extract all tool references from a workflow dict, including stock tools.

    Returns list of (tool_id, tool_version) tuples.
    Includes both ToolShed tools (with '/repos/') and stock tools (simple IDs).
    Deduplicates by (tool_id, tool_version).
    """
    seen: Set[Tuple[str, Optional[str]]] = set()
    _extract_all_from_dict(workflow_dict, seen)
    return sorted(seen)


def _extract_from_dict(workflow_dict: Dict, seen: Set[Tuple[str, Optional[str]]]):
    """Recursively extract tool references from a workflow dict."""
    # Detect format: native has "steps" as dict with int keys, format2 has "steps" as list
    steps = workflow_dict.get("steps")
    if steps is None:
        return

    if isinstance(steps, dict):
        _extract_from_native(steps, seen)
    elif isinstance(steps, list):
        _extract_from_format2(steps, seen)


def _extract_from_native(steps: Dict, seen: Set[Tuple[str, Optional[str]]]):
    """Extract from native .ga format (steps is dict with string-int keys)."""
    for step_data in steps.values():
        if not isinstance(step_data, dict):
            continue

        tool_id = step_data.get("tool_id")
        tool_version = step_data.get("tool_version")

        if tool_id and "/repos/" in tool_id:
            seen.add((tool_id, tool_version))

        # Recurse into subworkflows
        subworkflow = step_data.get("subworkflow")
        if isinstance(subworkflow, dict):
            _extract_from_dict(subworkflow, seen)


def _extract_from_format2(steps: List, seen: Set[Tuple[str, Optional[str]]]):
    """Extract from format2 .gxwf.yml format (steps is a list)."""
    for step_data in steps:
        if not isinstance(step_data, dict):
            continue

        tool_id = step_data.get("tool_id")
        tool_version = step_data.get("tool_version")

        if tool_id and "/repos/" in tool_id:
            seen.add((tool_id, tool_version))

        # format2 subworkflows use 'run' key
        run = step_data.get("run")
        if isinstance(run, dict):
            _extract_from_dict(run, seen)


def _extract_all_from_dict(workflow_dict: Dict, seen: Set[Tuple[str, Optional[str]]]):
    """Recursively extract all tool references from a workflow dict."""
    steps = workflow_dict.get("steps")
    if steps is None:
        return

    if isinstance(steps, dict):
        _extract_all_from_native(steps, seen)
    elif isinstance(steps, list):
        _extract_all_from_format2(steps, seen)


def _extract_all_from_native(steps: Dict, seen: Set[Tuple[str, Optional[str]]]):
    """Extract all tools from native .ga format, including stock tools."""
    for step_data in steps.values():
        if not isinstance(step_data, dict):
            continue

        tool_id = step_data.get("tool_id")
        tool_version = step_data.get("tool_version")

        if tool_id:
            seen.add((tool_id, tool_version))

        subworkflow = step_data.get("subworkflow")
        if isinstance(subworkflow, dict):
            _extract_all_from_dict(subworkflow, seen)


def _extract_all_from_format2(steps: List, seen: Set[Tuple[str, Optional[str]]]):
    """Extract all tools from format2 .gxwf.yml format, including stock tools."""
    for step_data in steps:
        if not isinstance(step_data, dict):
            continue

        tool_id = step_data.get("tool_id")
        tool_version = step_data.get("tool_version")

        if tool_id:
            seen.add((tool_id, tool_version))

        run = step_data.get("run")
        if isinstance(run, dict):
            _extract_all_from_dict(run, seen)


def load_workflow(path: str) -> Dict:
    """Load a workflow from a .ga or .gxwf.yml file."""
    with open(path) as f:
        if path.endswith((".yml", ".yaml")):
            try:
                from galaxy.util.yaml_util import ordered_load

                return ordered_load(f)
            except ImportError:
                import yaml

                return yaml.safe_load(f)
        else:
            return json.load(f)
