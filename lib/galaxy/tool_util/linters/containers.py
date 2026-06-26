"""Linter rules covering container references on a tool source."""

import re
from collections.abc import Iterator
from typing import (
    TYPE_CHECKING,
)

from galaxy.tool_util.lint import Linter

if TYPE_CHECKING:
    from galaxy.tool_util.lint import LintContext
    from galaxy.tool_util.parser.interface import ToolSource


lint_tool_types = ["*"]


CONTAINER_PREFIXES: tuple[str, ...] = ("quay.io/biocontainers/", "docker://", "oras://")
DOCKER_IMAGE_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]*(/[a-zA-Z0-9._-]+)*(:[\w][\w.-]*)?$")


def _iter_container_identifiers(tool_source: "ToolSource") -> Iterator[str]:
    try:
        _, containers, _, _, _ = tool_source.parse_requirements()
    except Exception:
        return
    for container in containers or ():
        identifier = getattr(container, "identifier", None)
        if identifier:
            yield identifier


class ContainerImageShape(Linter):
    """Container identifiers should match a recognized shape.

    Recognized: a `quay.io/biocontainers/...`, `docker://...`, or `oras://...`
    prefix; or a Docker-Hub-style `<image>[:<tag>]` reference.
    """

    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext") -> None:
        for identifier in _iter_container_identifiers(tool_source):
            stripped = identifier.strip()
            if stripped.startswith(CONTAINER_PREFIXES):
                continue
            if DOCKER_IMAGE_RE.match(stripped):
                continue
            lint_ctx.warn(
                f"container '{identifier}' does not match a recognized shape "
                "(quay.io/biocontainers/..., docker://..., oras://..., or <image>[:<tag>])",
                linter=cls.name(),
            )
