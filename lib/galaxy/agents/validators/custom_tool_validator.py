"""Structural semantic validator for ``UserToolSource`` instances.

Pydantic catches schema-level issues but not semantic ones -- a tool
definition can be schema-valid yet reference undeclared inputs in its
``shell_command`` template, have malformed citations, or list a container
that doesn't match expected registry shapes. This module catches those
deterministically before any LLM critic touches the tool. Pure code:
no LLM calls, no network, no registry resolution. Container shape is
checked as a string only; verifying the image actually exists is left
as future work (intentionally opt-in/cached so the cheap structural
check stays cheap).
"""

import re
from collections.abc import Iterable
from typing import (
    Optional,
)

from galaxy.tool_util_models import UserToolSource
from galaxy.tool_util_models.tool_source import Citation

# Tool ID: lowercase letters, digits, underscores; must start with a letter.
_TOOL_ID_RE = re.compile(r"^[a-z][a-z0-9_]*$")

# DOI: '10.<registrant>/<suffix>' per Crossref's published shape.
_DOI_RE = re.compile(r"^10\.\d{4,9}/.+$")

# BibTeX entries open with '@<type>{' -- e.g. '@article{', '@inproceedings{'.
_BIBTEX_RE = re.compile(r"^@[a-zA-Z]+\s*\{", re.MULTILINE)

# References inside shell_command. Templates use ecmascript-style $(...) blocks
# (see YamlTemplateConfigFile in tool_source.py). We pull every $(<expr>) and
# extract the leading 'inputs.<name>' identifier from each. Anything fancier
# (map/join over a multiple input, conditionals) is intentionally not parsed --
# we only flag obvious typos, not hairy expressions.
_TEMPLATE_BLOCK_RE = re.compile(r"\$\((.*?)\)", re.DOTALL)
_INPUTS_REF_RE = re.compile(r"\binputs\.([A-Za-z_][A-Za-z0-9_]*)")

# Docker Hub-style image references. Allow optional registry path segments and
# an optional tag. Examples that should pass: 'busybox', 'ubuntu:latest',
# 'biocontainers/blast:2.13.0', 'library/python:3.11-slim'.
_DOCKER_IMAGE_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]*(/[a-zA-Z0-9._-]+)*(:[\w][\w.-]*)?$")

_CONTAINER_PREFIXES = ("quay.io/biocontainers/", "docker://", "oras://")


def _input_names(tool: UserToolSource) -> set[str]:
    """Collect declared input names. Skips any input the model couldn't expose
    a name on -- pydantic validation already requires it on real instances."""
    names: set[str] = set()
    for param in tool.inputs or []:
        # YamlGalaxyToolParameter is a RootModel; the concrete param hangs off .root.
        root = getattr(param, "root", param)
        name = getattr(root, "name", None)
        if name:
            names.add(name)
    return names


def _output_names(tool: UserToolSource) -> Iterable[str]:
    for output in tool.outputs or []:
        name = getattr(output, "name", None)
        if name:
            yield name


def _command_input_refs(shell_command: str) -> set[str]:
    """Extract every 'inputs.<name>' identifier referenced from shell_command.

    Limitation: only catches identifiers that appear literally as
    ``inputs.<name>`` inside a ``$(...)`` block. Computed/aliased references
    (``const x = inputs; x.foo``) slip through. That's fine -- the goal is
    catching obvious typos cheaply, not modelling ecmascript scope.
    """
    refs: set[str] = set()
    for block in _TEMPLATE_BLOCK_RE.findall(shell_command or ""):
        for match in _INPUTS_REF_RE.findall(block):
            refs.add(match)
    return refs


def _validate_container(container: Optional[str]) -> Optional[str]:
    if not container or not container.strip():
        return "container is required and must be non-empty"
    value = container.strip()
    if value.startswith(_CONTAINER_PREFIXES):
        return None
    if _DOCKER_IMAGE_RE.match(value):
        return None
    return (
        f"container '{container}' does not match a recognized shape "
        "(quay.io/biocontainers/..., docker://..., oras://..., or <image>[:<tag>])"
    )


def _validate_citation(citation: Citation, index: int) -> Optional[str]:
    content = (citation.content or "").strip()
    if not content:
        return f"citation #{index + 1} has empty content"
    citation_type = (citation.type or "").strip().lower()
    if citation_type == "doi":
        if not _DOI_RE.match(content):
            return (
                f"citation #{index + 1} declared as DOI but '{content}' does not match DOI shape (^10\\.\\d{{4,9}}/.+$)"
            )
        return None
    if citation_type == "bibtex":
        if not _BIBTEX_RE.search(content):
            return f"citation #{index + 1} declared as bibtex but content does not start with '@<type>{{'"
        return None
    # Type wasn't explicitly doi/bibtex -- accept if the content shape is one of
    # the two known forms. Lets a slightly mis-typed entry through instead of
    # fighting models that emit type='reference' or similar.
    if _DOI_RE.match(content) or _BIBTEX_RE.search(content):
        return None
    return f"citation #{index + 1} (type={citation.type!r}) is neither a recognizable DOI nor a BibTeX entry"


def validate_user_tool_source(tool: UserToolSource) -> Optional[list[str]]:
    """Return a list of human-readable error strings, or ``None`` if valid.

    See module docstring for scope. The list is order-stable so callers can
    surface it directly without reshuffling.
    """
    errors: list[str] = []

    # Required fields populated.
    if not tool.name or not tool.name.strip():
        errors.append("name is required and must be non-empty")
    if not tool.version or not tool.version.strip():
        errors.append("version is required and must be non-empty")
    if not tool.description or not tool.description.strip():
        errors.append("description is required and must be non-empty")

    # Tool ID format.
    if not tool.id:
        errors.append("id is required")
    elif not _TOOL_ID_RE.match(tool.id):
        errors.append(
            f"id '{tool.id}' must match ^[a-z][a-z0-9_]*$ "
            "(lowercase, start with a letter, only letters/digits/underscores)"
        )

    # Container shape.
    container_error = _validate_container(tool.container)
    if container_error:
        errors.append(container_error)

    # Citations: at least one, each well-shaped.
    if not tool.citations:
        errors.append("at least one citation is required")
    else:
        for idx, citation in enumerate(tool.citations):
            citation_error = _validate_citation(citation, idx)
            if citation_error:
                errors.append(citation_error)

    # Command-template references must point at declared inputs.
    declared_inputs = _input_names(tool)
    referenced = _command_input_refs(tool.shell_command or "")
    undeclared = sorted(referenced - declared_inputs)
    for name in undeclared:
        errors.append(f"shell_command references inputs.{name} but no input named '{name}' is declared")

    # Outputs: a declared output should appear in the command (named on the
    # command line) OR have from_work_dir set. We accept anything else as a
    # false-negative tradeoff -- catching genuinely abandoned outputs matters
    # less than not yelling at clever templates.
    command = tool.shell_command or ""
    for name in _output_names(tool):
        if name in command:
            continue
        produced = False
        for output in tool.outputs or []:
            if getattr(output, "name", None) != name:
                continue
            from_work_dir = getattr(output, "from_work_dir", None)
            if from_work_dir:
                produced = True
                break
        if not produced:
            errors.append(
                f"output '{name}' is declared but not referenced in shell_command "
                "and has no from_work_dir set -- it will never be produced"
            )

    return errors or None
