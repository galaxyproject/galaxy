"""Utilities shared by server-side + client-side Pyodide execution flows.

This module intentionally avoids importing Galaxy ORM models so it can be used
in lightweight contexts (including unit tests) without requiring the full
Galaxy runtime dependencies.
"""

from __future__ import annotations

import ast
from typing import Any, Iterable, Optional, Set

_REQUIREMENTS_MARKER = "# requirements:"

# Keep this deliberately small and focused on packages that are commonly usable in Pyodide.
# (Some large native packages are not generally available or are very slow to install.)
_MODULE_TO_PACKAGE: dict[str, str] = {
    "sklearn": "scikit-learn",
    "pil": "pillow",
    "yaml": "pyyaml",
    "bs4": "beautifulsoup4",
}

# Common stdlib modules that should never trigger package installation.
_STDLIB_MODULES: Set[str] = {
    "abc",
    "argparse",
    "asyncio",
    "base64",
    "bisect",
    "calendar",
    "collections",
    "concurrent",
    "contextlib",
    "copy",
    "csv",
    "dataclasses",
    "datetime",
    "decimal",
    "difflib",
    "enum",
    "functools",
    "gc",
    "getpass",
    "glob",
    "gzip",
    "hashlib",
    "heapq",
    "html",
    "http",
    "importlib",
    "inspect",
    "io",
    "itertools",
    "json",
    "logging",
    "math",
    "mimetypes",
    "numbers",
    "operator",
    "os",
    "pathlib",
    "pickle",
    "platform",
    "pprint",
    "random",
    "re",
    "shlex",
    "shutil",
    "signal",
    "socket",
    "sqlite3",
    "statistics",
    "string",
    "struct",
    "subprocess",
    "sys",
    "tempfile",
    "textwrap",
    "threading",
    "time",
    "traceback",
    "types",
    "typing",
    "unicodedata",
    "urllib",
    "uuid",
    "warnings",
    "weakref",
    "xml",
    "zipfile",
}


def infer_requirements_from_python(code: str) -> list[str]:
    """Infer Pyodide packages needed to execute the given Python code.

    - Supports explicit annotations via `# requirements: a, b, c`
    - Extracts imported top-level modules and maps them to installable package names
    - Ignores common stdlib modules
    """

    if not code:
        return []

    explicit: set[str] = set()
    for line in code.splitlines():
        normalized = line.strip()
        if normalized.lower().startswith(_REQUIREMENTS_MARKER):
            _, _, payload = normalized.partition(":")
            for item in payload.split(","):
                cleaned = item.strip()
                if cleaned:
                    explicit.add(cleaned)
            break

    imported: set[str] = set()
    try:
        tree = ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    name = (alias.name or "").split(".", 1)[0].strip()
                    if name:
                        imported.add(name)
            elif isinstance(node, ast.ImportFrom):
                if node.level and node.level > 0:
                    continue
                module = (node.module or "").split(".", 1)[0].strip()
                if module:
                    imported.add(module)
    except SyntaxError:
        imported = set()
    except Exception:  # pragma: no cover - defensive guard
        imported = set()

    inferred: set[str] = set(explicit)
    for module in imported:
        module_key = module.lower()
        if module_key in _STDLIB_MODULES:
            continue
        package = _MODULE_TO_PACKAGE.get(module_key, module_key)
        if package and package not in _STDLIB_MODULES:
            inferred.add(package)

    return sorted(inferred)


def dataset_descriptors_from_files(files: Any) -> list[dict[str, Any]]:
    """Convert Pyodide download entries into minimal dataset descriptors."""

    if not isinstance(files, list):
        return []
    descriptors: list[dict[str, Any]] = []
    for entry in files:
        if not isinstance(entry, dict):
            continue
        dataset_id = entry.get("id")
        if not dataset_id:
            continue
        descriptors.append(
            {
                "id": dataset_id,
                "name": entry.get("name") or dataset_id,
                "size": entry.get("size"),
                "aliases": entry.get("aliases") or [dataset_id],
            }
        )
    return descriptors


def merge_execution_metadata(
    metadata: dict[str, Any],
    *,
    task_id: Optional[str],
    success: bool,
    stdout: str,
    stderr: str,
    artifacts: Optional[list[dict[str, Any]]] = None,
) -> None:
    """Merge client-side execution output into the assistant message metadata.

    Keeps `executed_task.datasets` structurally consistent (dataset descriptor list),
    preferring `pyodide_context.datasets` when available.
    """

    metadata["pyodide_status"] = "completed" if success else "error"
    metadata["stdout"] = stdout or ""
    metadata["stderr"] = stderr or ""
    metadata["execution"] = {
        "success": success,
        "stdout": stdout or "",
        "stderr": stderr or "",
        "artifacts": artifacts or [],
        "task_id": task_id,
    }

    executed_task: dict[str, Any] = {}
    if isinstance(metadata.get("executed_task"), dict):
        executed_task.update(metadata.get("executed_task") or {})

    pyodide_task = metadata.get("pyodide_task")
    pyodide_context = metadata.get("pyodide_context") if isinstance(metadata.get("pyodide_context"), dict) else {}

    if isinstance(pyodide_task, dict):
        executed_task.setdefault("code", pyodide_task.get("original_code") or pyodide_task.get("code"))
        executed_task.setdefault("requirements", pyodide_task.get("packages"))

        datasets = executed_task.get("datasets")
        if not isinstance(datasets, list) or not datasets:
            context_datasets = pyodide_context.get("datasets")
            if isinstance(context_datasets, list) and context_datasets:
                executed_task["datasets"] = context_datasets
            else:
                executed_task["datasets"] = dataset_descriptors_from_files(pyodide_task.get("files"))

        alias_map = executed_task.get("alias_map")
        if not isinstance(alias_map, dict) or not alias_map:
            context_alias_map = pyodide_context.get("alias_map")
            if isinstance(context_alias_map, dict) and context_alias_map:
                executed_task["alias_map"] = context_alias_map
            else:
                candidate_alias_map = pyodide_task.get("alias_map")
                if isinstance(candidate_alias_map, dict):
                    executed_task["alias_map"] = candidate_alias_map

    if executed_task:
        executed_task["task_id"] = task_id
        metadata["executed_task"] = executed_task

    metadata.pop("pyodide_task", None)

    if artifacts:
        metadata["artifacts"] = artifacts
        # Provide best-effort plot/file lists for the UI even when the LLM does
        # not explicitly populate them.
        existing_plots = metadata.get("plots") if isinstance(metadata.get("plots"), list) else []
        existing_files = metadata.get("files") if isinstance(metadata.get("files"), list) else []
        if not existing_plots or not existing_files:
            inferred_plots: list[str] = list(existing_plots) if isinstance(existing_plots, list) else []
            inferred_files: list[str] = list(existing_files) if isinstance(existing_files, list) else []
            for artifact in artifacts:
                if not isinstance(artifact, dict):
                    continue
                name = artifact.get("name") or artifact.get("path") or artifact.get("dataset_id") or ""
                if not isinstance(name, str) or not name:
                    continue
                path = name if name.startswith("generated_file/") else f"generated_file/{name}"
                mime = artifact.get("mime_type") or ""
                if isinstance(mime, str) and mime.startswith("image/"):
                    if path not in inferred_plots:
                        inferred_plots.append(path)
                else:
                    if path not in inferred_files:
                        inferred_files.append(path)
            if not existing_plots and inferred_plots:
                metadata["plots"] = inferred_plots
            if not existing_files and inferred_files:
                metadata["files"] = inferred_files
