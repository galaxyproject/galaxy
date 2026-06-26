"""Direct tests for the semantic validators on ``UserToolSource``.

The corpus of cases lives in ``user_tool_source_validation_cases.yml`` so it
can be replayed by external validators (the TS port in
``galaxy-tool-util-ts``, MCP clients, IDE plugins). Each case overrides
``VALID_TOOL`` with its ``doc`` and either validates cleanly (``valid: true``)
or raises a ``ValidationError`` whose distilled output matches the listed
``expected_errors`` by stable error ``code``.

Container *shape* is enforced by the lint framework, not pydantic — see
``test_container_shape_lint.py``.
"""

from copy import deepcopy
from pathlib import Path
from typing import (
    Any,
)

import pytest
import yaml
from pydantic import ValidationError

from galaxy.tool_util_models import (
    format_validation_errors,
    UserToolSource,
)
from galaxy.util.resources import resource_string

VALID_TOOL: dict[str, Any] = {
    "class": "GalaxyUserTool",
    "id": "my-cool-tool",
    "name": "My Cool Tool",
    "version": "0.1.0",
    "description": "A cool tool.",
    "container": "quay.io/biocontainers/python:3.13",
    "shell_command": "head -n '$(inputs.n_lines)' '$(inputs.data_input.path)' > out.txt",
    "inputs": [
        {"type": "integer", "name": "n_lines"},
        {"type": "data", "name": "data_input"},
    ],
    "outputs": [
        {"type": "data", "name": "out", "from_work_dir": "out.txt"},
    ],
    "citations": [
        {"type": "doi", "content": "10.1234/abc.def"},
    ],
}


def _load_cases() -> list[dict[str, Any]]:
    try:
        yaml_str = resource_string(__name__, "user_tool_source_validation_cases.yml")
    except AttributeError:
        # Fallback for invocations that bypass importlib.resources; resolve
        # relative to this file rather than cwd.
        yaml_str = (Path(__file__).parent / "user_tool_source_validation_cases.yml").read_text()
    return yaml.safe_load(yaml_str)["cases"]


CASES = _load_cases()


def _doc_for(case: dict[str, Any]) -> dict[str, Any]:
    base = deepcopy(VALID_TOOL)
    base.update(case.get("doc") or {})
    return base


def _flatten_loc(loc: Any) -> str:
    if isinstance(loc, (list, tuple)):
        return ".".join(str(p) for p in loc if p != "__root__")
    return str(loc)


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["name"])
def test_user_tool_source_corpus(case: dict[str, Any]) -> None:
    doc = _doc_for(case)
    if case.get("valid"):
        UserToolSource.model_validate(doc)
        return

    with pytest.raises(ValidationError) as info:
        UserToolSource.model_validate(doc)

    if "expected_format" in case:
        assert format_validation_errors(info.value) == case["expected_format"]

    raised = [{"loc": _flatten_loc(err["loc"]), "code": err["type"], "msg": err["msg"]} for err in info.value.errors()]
    for expected in case.get("expected_errors") or []:
        match = next(
            (
                e
                for e in raised
                if e["code"] == expected["code"]
                and ("loc" not in expected or e["loc"] == expected["loc"])
                and ("msg_contains" not in expected or expected["msg_contains"] in e["msg"])
            ),
            None,
        )
        assert match is not None, f"no error matched {expected!r}; raised={raised!r}"
