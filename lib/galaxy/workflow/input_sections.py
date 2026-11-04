"""Group workflow inputs into collapsible sections of the workflow run form.

A workflow carries an ordered list of section definitions (``input_sections``)
and each input step may name one of them (``section``). Sections only affect
how the run form presents inputs, never how a workflow is invoked.
"""

from collections.abc import Iterable
from typing import Any

from pydantic import (
    TypeAdapter,
    ValidationError,
)

from galaxy.exceptions import RequestParameterInvalidException
from galaxy.schema.schema import WorkflowInputSection

INPUT_STEP_TYPES = ("data_input", "data_collection_input", "parameter_input")

_sections_adapter = TypeAdapter(list[WorkflowInputSection])


def step_input_section(step_dict: dict[str, Any]) -> str | None:
    """Return the section name an input step dictionary is assigned to, if any."""
    if step_dict.get("type") not in INPUT_STEP_TYPES:
        return None
    section = step_dict.get("section")
    if section is None:
        return None
    if not isinstance(section, str):
        raise RequestParameterInvalidException(f"Workflow input step section must be a string, got {section!r}.")
    return section.strip() or None


def normalize_input_sections(
    raw_sections: Any, referenced_sections: Iterable[str | None]
) -> list[dict[str, Any]] | None:
    """Validate section definitions and add one for each referenced section without a definition.

    Undefined sections are appended in the order they are first referenced, labelled by their name.
    """
    try:
        sections = _sections_adapter.validate_python(raw_sections or [])
    except ValidationError as e:
        raise RequestParameterInvalidException(f"Invalid workflow input_sections: {e}")
    names = [section.name for section in sections]
    duplicates = sorted({name for name in names if names.count(name) > 1})
    if duplicates:
        raise RequestParameterInvalidException(f"Duplicate workflow input section names: {', '.join(duplicates)}.")
    known = set(names)
    for name in referenced_sections:
        if name and name not in known:
            sections.append(WorkflowInputSection(name=name))
            known.add(name)
    return [section.model_dump(exclude_none=True) for section in sections] or None
