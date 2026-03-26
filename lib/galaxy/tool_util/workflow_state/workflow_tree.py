"""Directory tree scanner and report builder for workflow operations.

Discovers .ga and .gxwf.yml workflows under a root directory,
following patterns from loader_directory.py (os.walk with dir exclusion,
extension filtering, content validation).
"""

import json
import os
from dataclasses import (
    dataclass,
    field,
)
from typing import (
    Dict,
    List,
    Literal,
    Optional,
)

from galaxy.tool_util.loader_directory import EXCLUDE_WALK_DIRS

NATIVE_EXTENSIONS = (".ga",)
FORMAT2_EXTENSIONS = (".gxwf.yml", ".gxwf.yaml")
YAML_EXTENSIONS = (".yml", ".yaml")
JSON_EXTENSIONS = (".json",)

WorkflowFormat = Literal["native", "format2"]


# TODO: Make category a computed field please.
@dataclass
class WorkflowInfo:
    path: str
    relative_path: str
    category: str  # first parent dir relative to root, or "" for root-level
    format: WorkflowFormat


@dataclass
class ReportSection:
    title: str
    rows: List[List[str]] = field(default_factory=list)
    columns: List[str] = field(default_factory=list)


@dataclass
class WorkflowReport:
    title: str
    summary: str
    sections: List[ReportSection] = field(default_factory=list)
    details: List[str] = field(default_factory=list)


def _is_workflow_content(path: str, fmt: WorkflowFormat) -> bool:
    """Validate file content looks like a workflow by parsing and checking key fields."""
    try:
        if fmt == "native":
            with open(path) as f:
                data = json.load(f)
            return isinstance(data, dict) and data.get("a_galaxy_workflow") == "true"
        else:
            from gxformat2.yaml import ordered_load

            with open(path) as f:
                data = ordered_load(f)
            return isinstance(data, dict) and data.get("class") == "GalaxyWorkflow"
    except Exception:
        return False


def discover_workflows(root: str, include_format2: bool = True) -> List[WorkflowInfo]:
    """Discover workflow files under root directory.

    Recognizes workflows by extension and content:
    - .ga, .json → native if a_galaxy_workflow == "true"
    - .gxwf.yml, .gxwf.yaml → format2 if class == "GalaxyWorkflow"
    - .yml, .yaml → format2 if class == "GalaxyWorkflow" (checked before .gxwf)
    """
    root = os.path.abspath(root)
    workflows: List[WorkflowInfo] = []

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_WALK_DIRS]

        for filename in filenames:
            fmt: Optional[WorkflowFormat] = None

            if filename.endswith(NATIVE_EXTENSIONS):
                fmt = "native"
            elif filename.endswith(JSON_EXTENSIONS):
                fmt = "native"
            elif include_format2 and filename.endswith(FORMAT2_EXTENSIONS):
                fmt = "format2"
            elif include_format2 and filename.endswith(YAML_EXTENSIONS):
                fmt = "format2"
            else:
                continue

            filepath = os.path.join(dirpath, filename)
            if not _is_workflow_content(filepath, fmt):
                continue

            relative = os.path.relpath(filepath, root)
            parts = relative.split(os.sep)
            category = parts[0] if len(parts) > 1 else ""

            workflows.append(
                WorkflowInfo(
                    path=filepath,
                    relative_path=relative,
                    category=category,
                    format=fmt,
                )
            )

    workflows.sort(key=lambda w: w.relative_path)
    return workflows


def load_workflow_safe(info: WorkflowInfo) -> Optional[dict]:
    """Load a workflow dict, returning None on parse failure."""
    try:
        with open(info.path) as f:
            if info.format == "format2":
                # TODO: Use the YAML load from gxformat2 please.
                try:
                    from galaxy.util.yaml_util import ordered_load

                    return ordered_load(f)
                except ImportError:
                    import yaml

                    return yaml.safe_load(f)
            else:
                return json.load(f)
    except Exception:
        return None


def render_markdown(report: WorkflowReport) -> str:
    """Render a WorkflowReport to Markdown."""
    lines = [f"# {report.title}", "", report.summary, ""]

    for section in report.sections:
        lines.append(f"## {section.title}")
        lines.append("")
        if section.columns and section.rows:
            lines.append("| " + " | ".join(section.columns) + " |")
            lines.append("| " + " | ".join("---" for _ in section.columns) + " |")
            for row in section.rows:
                lines.append("| " + " | ".join(row) + " |")
            lines.append("")
        elif not section.rows:
            lines.append("No entries.")
            lines.append("")

    if report.details:
        lines.append("## Details")
        lines.append("")
        for detail in report.details:
            lines.append(detail)
        lines.append("")

    return "\n".join(lines)


def group_by_category(workflows: List[WorkflowInfo]) -> Dict[str, List[WorkflowInfo]]:
    """Group workflows by category (first parent directory)."""
    groups: Dict[str, List[WorkflowInfo]] = {}
    for wf in workflows:
        cat = wf.category or "(root)"
        groups.setdefault(cat, []).append(wf)
    return groups
