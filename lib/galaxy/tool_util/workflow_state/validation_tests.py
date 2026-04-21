"""Validate workflow-test files (``*-tests.yml``) against ``Tests`` models.

Thin adapter over ``galaxy.tool_util_models.Tests.model_validate`` with
``ValidationError`` flattened into structured diagnostics compatible with
the ``Diagnostic`` shape emitted by ``gxwf validate``.
"""

from typing import (
    Any,
    List,
    Literal,
    Optional,
)

from pydantic import (
    BaseModel,
    ValidationError,
)

from galaxy.tool_util_models import Tests

Severity = Literal["error", "warning", "info"]


class TestDiagnostic(BaseModel):
    path: str
    message: str
    severity: Severity = "error"
    category: Optional[str] = None


class TestsValidationResult(BaseModel):
    valid: bool
    diagnostics: List[TestDiagnostic] = []


def load_tests_file(path: str) -> Any:
    """Parse a workflow-tests YAML file; return parsed structure (not validated)."""
    try:
        from galaxy.util.yaml_util import ordered_load

        with open(path) as f:
            return ordered_load(f)
    except ImportError:
        import yaml

        with open(path) as f:
            return yaml.safe_load(f)


def validate_tests_file(parsed: Any) -> TestsValidationResult:
    """Validate a parsed workflow-tests document against ``Tests``."""
    try:
        Tests.model_validate(parsed)
    except ValidationError as e:
        return TestsValidationResult(
            valid=False,
            diagnostics=[_error_to_diagnostic(err) for err in e.errors()],
        )
    return TestsValidationResult(valid=True)


def _error_to_diagnostic(err: dict) -> TestDiagnostic:
    loc = err.get("loc", ())
    path = "/".join(str(p) for p in loc)
    return TestDiagnostic(
        path=path,
        message=err.get("msg", ""),
        severity="error",
        category=err.get("type"),
    )
