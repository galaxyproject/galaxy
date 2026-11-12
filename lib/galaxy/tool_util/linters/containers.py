"""Linter rules covering container references on a tool source."""

from collections.abc import Iterator
from typing import (
    TYPE_CHECKING,
)

from galaxy.tool_util.deps.image_references import (
    ImageReferenceError,
    parse_image_reference,
)
from galaxy.tool_util.lint import Linter

if TYPE_CHECKING:
    from galaxy.tool_util.lint import LintContext
    from galaxy.tool_util.parser.interface import ToolSource


lint_tool_types = ["*"]


# Singularity/Apptainer pull these from an OCI artifact registry; their shape is not checked.
UNCHECKED_PREFIXES: tuple[str, ...] = ("oras://",)


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

    Recognized: an `oras://...` reference, or a Docker image reference
    `[docker://][<registry>/]<repository>[:<tag>][@<digest>]`.
    """

    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext") -> None:
        for identifier in _iter_container_identifiers(tool_source):
            if identifier.startswith(UNCHECKED_PREFIXES):
                continue
            try:
                parse_image_reference(identifier)
            except ImageReferenceError as e:
                lint_ctx.warn(
                    f"container '{identifier}' does not match a recognized shape "
                    f"(oras://... or [<registry>/]<repository>[:<tag>][@<digest>]): {e}",
                    linter=cls.name(),
                )
