"""Filling in output labels of YAML tools, admin and user-defined alike.

A label is text with references matching ``USER_TOOL_LABEL_REFERENCE_RE``. ``$(inputs.<name>)``
reads the tool state, through conditionals and sections, and for a dataset or collection
ends with ``name``, ``element_identifier`` or ``format``. ``$(runtime.on_string)`` is the
text XML tool labels get as ``on_string``. Nothing is evaluated as Cheetah or JavaScript.

A label is filled in when the job is created, so it offers nothing an input only gets once
the job that makes it has finished, such as its file name. A reference that can't be filled
in is kept as written, so a label never fails a job.
"""

import re
from collections.abc import (
    Container,
    Mapping,
    Sequence,
)
from typing import (
    Any,
)

from galaxy import model
from galaxy.tool_util_models.tool_outputs import (
    MAX_USER_TOOL_LABEL_LENGTH,
    USER_TOOL_LABEL_REFERENCE_RE,
)


def render_yaml_tool_label(
    label: str, input_names: Container[str], state: Mapping[str, Any], on_string: str | None
) -> str:
    def fill(match: re.Match[str]) -> str:
        if match["input"] is None:
            text = on_string
        elif match["input"] in input_names:
            text = _resolve([match["input"], *match["keys"].split(".")[1:]], state)
        else:
            text = None
        return match[0] if text is None else text

    return USER_TOOL_LABEL_REFERENCE_RE.sub(fill, label[:MAX_USER_TOOL_LABEL_LENGTH])[:MAX_USER_TOOL_LABEL_LENGTH]


def _resolve(keys: Sequence[str], state: Mapping[str, Any]) -> str | None:
    """Return the text ``state[keys[0]][keys[1]]...`` fills in, or None if it can't be filled in."""
    value: Any = state
    for position, key in enumerate(keys):
        if value is None:
            # An optional input left empty.
            return ""
        if isinstance(
            value, (model.DatasetInstance, model.DatasetCollectionElement, model.HistoryDatasetCollectionAssociation)
        ):
            return _dataset_attribute(value, key) if position == len(keys) - 1 else None
        if not isinstance(value, Mapping) or key.startswith("__") or key not in value:
            return None
        value = value[key]
    if value is None:
        return ""
    # Anything else, like a dataset without an attribute or a workflow editor runtime value, is not text.
    return str(value) if isinstance(value, (str, int, float)) else None


def _dataset_attribute(value: Any, key: str) -> str | None:
    if isinstance(value, model.DatasetCollectionElement):
        # The element a job mapped over a nested collection runs on.
        return value.element_identifier if key in ("name", "element_identifier") else None
    if isinstance(value, model.HistoryDatasetCollectionAssociation):
        return value.name if key in ("name", "element_identifier") else None
    if key == "element_identifier":
        # Expanding a mapped-over collection records each element's identifier on its dataset.
        identifier: str | None = getattr(value, "element_identifier", None) or value.name
        return identifier
    return {"name": value.name, "format": value.extension}.get(key)
