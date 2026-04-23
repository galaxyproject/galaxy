"""Pydantic models for structured CLI report output.

Shared base types for validation and cleaning reports, plus
tool-specific result models. JSON serialization is handled by
Pydantic's model_dump(by_alias=True); text and Markdown formatters
consume these models directly via field names.
"""

import os
from typing import (
    Any,
    Dict,
    List,
    Literal,
    Optional,
)

from pydantic import (
    BaseModel,
    computed_field,
    Field,
)

from .precheck import SkipWorkflowReason

StepStatus = Literal["ok", "fail", "skip_tool_not_found", "skip_replacement_params"]

SKIP_STATUSES: frozenset = frozenset({"skip_tool_not_found", "skip_replacement_params"})
ConnectionStatus = Literal["ok", "invalid", "skip"]


# -- Step-level results --


class StepResultBase(BaseModel):
    """Fields common to every per-step result."""

    step: str
    tool_id: Optional[str] = None
    version: Optional[str] = None


class ValidationStepResult(StepResultBase):
    status: StepStatus
    errors: List[str] = []


class CleanStepResult(StepResultBase):
    removed_state_keys: List[str] = []
    removed_step_keys: List[str] = []
    skipped: bool = False
    skip_reason: str = ""

    @computed_field  # type: ignore[prop-decorator]
    @property
    def display_label(self) -> str:
        label = self.tool_id or "unknown"
        if self.version:
            label += f" {self.version}"
        return label


# -- Workflow-level results --


class WorkflowResultBase(BaseModel):
    """Fields common to every per-workflow result."""

    path: str = Field(exclude=True)
    relative_path: str = Field(serialization_alias="path")
    category: str
    error: Optional[str] = None
    skipped_reason: Optional[SkipWorkflowReason] = None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def name(self) -> str:
        """Basename of ``relative_path`` — saves templates a ``basename`` filter."""
        return os.path.basename(self.relative_path)


class WorkflowValidationResult(WorkflowResultBase):
    step_results: List[ValidationStepResult] = Field(default=[], serialization_alias="results")
    connection_report: Optional["ConnectionValidationReport"] = None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def summary(self) -> Optional[Dict[str, int]]:
        if self.error or self.skipped_reason:
            return None
        return {
            "ok": sum(1 for sr in self.step_results if sr.status == "ok"),
            "fail": sum(1 for sr in self.step_results if sr.status == "fail"),
            "skip": sum(1 for sr in self.step_results if sr.status in SKIP_STATUSES),
        }

    @computed_field  # type: ignore[prop-decorator]
    @property
    def failures(self) -> Optional[List[Dict[str, Optional[str]]]]:
        """Flat failure list for templates (one entry per error message).

        Returns ``None`` when the workflow was skipped or errored — same
        convention as ``summary`` — so templates branch on a single sentinel.
        """
        if self.error or self.skipped_reason:
            return None
        out: List[Dict[str, Optional[str]]] = []
        for sr in self.step_results:
            if sr.status != "fail":
                continue
            for err in sr.errors:
                out.append({"step": sr.step, "tool_id": sr.tool_id, "message": err})
        return out


class WorkflowCleanResult(WorkflowResultBase):
    step_results: List[CleanStepResult] = Field(default=[], serialization_alias="results")
    total_removed: int = 0

    @computed_field  # type: ignore[prop-decorator]
    @property
    def steps_affected(self) -> int:
        return sum(1 for sr in self.step_results if sr.removed_state_keys or sr.removed_step_keys)


# -- Connection validation report models --


class ConnectionResult(BaseModel):
    """Single connection between two steps.

    status and mapping are orthogonal:
    - status: whether the connection is valid (ok/invalid/skip)
    - mapping: what collection type is being mapped over (None = direct match)
    """

    source_step: str
    source_output: str
    target_step: str
    target_input: str
    status: ConnectionStatus
    mapping: Optional[str] = None
    errors: List[str] = []


class ResolvedOutputType(BaseModel):
    """Resolved collection type for a step output."""

    name: str
    collection_type: Optional[str] = None  # None = plain dataset


class ConnectionStepResult(StepResultBase):
    """Connection validation result for one step."""

    step_type: str = "tool"
    map_over: Optional[str] = None
    connections: List[ConnectionResult] = []
    resolved_outputs: List[ResolvedOutputType] = []
    errors: List[str] = []


class ConnectionValidationReport(BaseModel):
    """Connection validation results for one workflow."""

    valid: bool
    step_results: List[ConnectionStepResult] = []
    summary: Dict[str, int] = {}

    @computed_field  # type: ignore[prop-decorator]
    @property
    def has_details(self) -> bool:
        """True iff any step has connection data or step-level errors.

        Precomputed here so templates don't need a mutable accumulator loop
        (Jinja2 namespaces aren't in the Jinja2/Nunjucks shared subset).
        """
        return any(sr.connections or sr.errors for sr in self.step_results)


# -- Tree-level (directory) reports --


class TreeReportBase(BaseModel):
    """Shared root for directory-level reports."""

    root: str

    def by_category(self) -> Dict[str, list]:
        groups: Dict[str, list] = {}
        for r in self._workflow_results():
            cat = r.category or "(root)"
            groups.setdefault(cat, []).append(r)
        return groups

    @computed_field  # type: ignore[prop-decorator]
    @property
    def categories(self) -> List[Dict[str, Any]]:
        """Templates-facing grouping: ``[{name, results}]`` sorted by name.

        Lives in JSON so Jinja/Nunjucks templates can iterate without a method call.
        """
        return [{"name": name, "results": results} for name, results in sorted(self.by_category().items())]

    def _workflow_results(self) -> list:
        raise NotImplementedError


class TreeValidationReport(TreeReportBase):
    results: List[WorkflowValidationResult] = Field(default=[], serialization_alias="workflows")

    def _workflow_results(self) -> list:
        return self.results

    @computed_field  # type: ignore[prop-decorator]
    @property
    def all_failures(self) -> List[Dict[str, Optional[str]]]:
        """Cross-workflow failure list so templates can render a grouped appendix."""
        out: List[Dict[str, Optional[str]]] = []
        for r in self.results:
            for f in r.failures or ():
                out.append({"workflow": r.relative_path, **f})
        return out

    @computed_field  # type: ignore[prop-decorator]
    @property
    def summary(self) -> Dict[str, int]:
        ok = fail = skip = error = skipped = 0
        for r in self.results:
            if r.skipped_reason:
                skipped += 1
                continue
            if r.error:
                error += 1
                continue
            for sr in r.step_results:
                if sr.status == "ok":
                    ok += 1
                elif sr.status == "fail":
                    fail += 1
                elif sr.status in SKIP_STATUSES:
                    skip += 1
        return {
            "ok": ok,
            "fail": fail,
            "skip": skip,
            "error": error,
            "skipped": skipped,
        }


class TreeCleanReport(TreeReportBase):
    results: List[WorkflowCleanResult] = Field(default=[], serialization_alias="workflows")

    def _workflow_results(self) -> list:
        return self.results

    @computed_field  # type: ignore[prop-decorator]
    @property
    def summary(self) -> Dict[str, int]:
        total_keys = sum(r.total_removed for r in self.results if not r.skipped_reason)
        skipped = sum(1 for r in self.results if r.skipped_reason)
        affected = sum(1 for r in self.results if r.total_removed > 0 and not r.skipped_reason)
        errors = sum(1 for r in self.results if r.error and not r.skipped_reason)
        clean = len(self.results) - affected - errors - skipped
        return {"total_keys": total_keys, "affected": affected, "clean": clean, "errors": errors, "skipped": skipped}


# -- Single-workflow wrappers (for JSON serialization of single-file runs) --


class SingleCleanReport(BaseModel):
    """JSON shape for single-file cleaning."""

    workflow: str
    results: List[CleanStepResult]
    before_content: Optional[str] = None
    after_content: Optional[str] = None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_removed(self) -> int:
        return sum(len(r.removed_state_keys) + len(r.removed_step_keys) for r in self.results)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def steps_with_removals(self) -> int:
        return sum(1 for r in self.results if r.removed_state_keys or r.removed_step_keys)


class SingleValidationReport(BaseModel):
    """JSON shape for single-file validation."""

    workflow: str
    results: List[ValidationStepResult]
    connection_report: Optional["ConnectionValidationReport"] = None
    skipped_reason: Optional[str] = None
    structure_errors: List[str] = Field(default_factory=list)
    encoding_errors: List[str] = Field(default_factory=list)
    clean_report: Optional[SingleCleanReport] = None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def summary(self) -> Dict[str, int]:
        return {
            "ok": sum(1 for r in self.results if r.status == "ok"),
            "fail": sum(1 for r in self.results if r.status == "fail"),
            "skip": sum(1 for r in self.results if r.status in SKIP_STATUSES),
        }


# -- Helpers for wrapping single-file results into tree reports --


def wrap_single_validation(
    workflow_path: str,
    results: List[ValidationStepResult],
    connection_report: Optional["ConnectionValidationReport"] = None,
) -> TreeValidationReport:
    """Wrap single-file results into a TreeValidationReport for Markdown rendering."""
    return TreeValidationReport(
        root=workflow_path,
        results=[
            WorkflowValidationResult(
                path=workflow_path,
                relative_path=os.path.basename(workflow_path),
                category="",
                step_results=results,
                connection_report=connection_report,
            )
        ],
    )


# -- Lint models --


class LintWorkflowResult(WorkflowResultBase):
    """Per-workflow lint result combining structural + stateful checks."""

    lint_errors: int = 0
    lint_warnings: int = 0
    step_results: List[ValidationStepResult] = Field(default_factory=list, serialization_alias="results")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def step_counts(self) -> Optional[Dict[str, int]]:
        """State-step tallies, mirroring ``WorkflowValidationResult.summary``."""
        if self.error or self.skipped_reason:
            return None
        return {
            "ok": sum(1 for sr in self.step_results if sr.status == "ok"),
            "fail": sum(1 for sr in self.step_results if sr.status == "fail"),
            "skip": sum(1 for sr in self.step_results if sr.status in SKIP_STATUSES),
        }


class SingleLintReport(BaseModel):
    """JSON shape for single-file lint."""

    workflow: str
    lint_errors: int = 0
    lint_warnings: int = 0
    lint_error_messages: List[str] = Field(default_factory=list)
    lint_warning_messages: List[str] = Field(default_factory=list)
    results: List[ValidationStepResult] = []
    structure_errors: List[str] = Field(default_factory=list)
    encoding_errors: List[str] = Field(default_factory=list)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def summary(self) -> Dict[str, int]:
        return {
            "lint_errors": self.lint_errors,
            "lint_warnings": self.lint_warnings,
            "state_ok": sum(1 for r in self.results if r.status == "ok"),
            "state_fail": sum(1 for r in self.results if r.status == "fail"),
            "state_skip": sum(1 for r in self.results if r.status in SKIP_STATUSES),
        }


class LintTreeReport(TreeReportBase):
    """Tree-level lint report combining structural + stateful results."""

    results: List[LintWorkflowResult] = Field(default_factory=list, serialization_alias="workflows")

    def _workflow_results(self) -> list:
        return self.results

    @computed_field  # type: ignore[prop-decorator]
    @property
    def summary(self) -> Dict[str, int]:
        lint_errors = sum(r.lint_errors for r in self.results)
        lint_warnings = sum(r.lint_warnings for r in self.results)
        state_ok = sum(
            sum(1 for sr in r.step_results if sr.status == "ok")
            for r in self.results
            if not r.error and not r.skipped_reason
        )
        state_fail = sum(
            sum(1 for sr in r.step_results if sr.status == "fail")
            for r in self.results
            if not r.error and not r.skipped_reason
        )
        state_skip = sum(
            sum(1 for sr in r.step_results if sr.status in SKIP_STATUSES)
            for r in self.results
            if not r.error and not r.skipped_reason
        )
        errors = sum(1 for r in self.results if r.error)
        skipped = sum(1 for r in self.results if r.skipped_reason)
        return {
            "lint_errors": lint_errors,
            "lint_warnings": lint_warnings,
            "state_ok": state_ok,
            "state_fail": state_fail,
            "state_skip": state_skip,
            "errors": errors,
            "skipped": skipped,
        }


def wrap_single_lint(
    workflow_path: str,
    lint_errors: int,
    lint_warnings: int,
    step_results: List[ValidationStepResult],
) -> LintTreeReport:
    """Wrap single-file lint results into a LintTreeReport for Markdown rendering."""
    return LintTreeReport(
        root=workflow_path,
        results=[
            LintWorkflowResult(
                path=workflow_path,
                relative_path=os.path.basename(workflow_path),
                category="",
                lint_errors=lint_errors,
                lint_warnings=lint_warnings,
                step_results=step_results,
            )
        ],
    )


# -- Workflow-test file validation (gxwf validate-tests) --


class TestsDiagnostic(BaseModel):
    path: str
    message: str
    severity: Literal["error", "warning", "info"] = "error"
    category: Optional[str] = None


class SingleTestsValidationReport(BaseModel):
    """JSON shape for single-file workflow-test validation."""

    tests_file: str
    valid: bool
    diagnostics: List[TestsDiagnostic] = []
    load_error: Optional[str] = None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def error_count(self) -> int:
        return sum(1 for d in self.diagnostics if d.severity == "error")


class WorkflowTestsResult(BaseModel):
    path: str = Field(exclude=True)
    relative_path: str = Field(serialization_alias="path")
    category: str = ""
    valid: bool = True
    diagnostics: List[TestsDiagnostic] = []
    load_error: Optional[str] = None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def name(self) -> str:
        return os.path.basename(self.relative_path)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def error_count(self) -> int:
        return sum(1 for d in self.diagnostics if d.severity == "error")


class TestsTreeReport(TreeReportBase):
    results: List[WorkflowTestsResult] = Field(default=[], serialization_alias="tests_files")

    def _workflow_results(self) -> list:
        return self.results

    @computed_field  # type: ignore[prop-decorator]
    @property
    def summary(self) -> Dict[str, int]:
        total = len(self.results)
        invalid = sum(1 for r in self.results if not r.valid)
        load_errors = sum(1 for r in self.results if r.load_error)
        diagnostics = sum(len(r.diagnostics) for r in self.results)
        return {
            "total": total,
            "valid": total - invalid,
            "invalid": invalid,
            "load_errors": load_errors,
            "diagnostics": diagnostics,
        }


def wrap_single_tests_validation(
    tests_path: str,
    valid: bool,
    diagnostics: List[TestsDiagnostic],
    load_error: Optional[str] = None,
) -> TestsTreeReport:
    """Wrap single-file tests validation into a TestsTreeReport for Markdown rendering."""
    return TestsTreeReport(
        root=tests_path,
        results=[
            WorkflowTestsResult(
                path=tests_path,
                relative_path=os.path.basename(tests_path),
                category="",
                valid=valid,
                diagnostics=diagnostics,
                load_error=load_error,
            )
        ],
    )


def wrap_single_clean(workflow_path: str, step_results: List[CleanStepResult]) -> TreeCleanReport:
    """Wrap single-file results into a TreeCleanReport for Markdown rendering."""
    total = sum(len(r.removed_state_keys) + len(r.removed_step_keys) for r in step_results)
    return TreeCleanReport(
        root=workflow_path,
        results=[
            WorkflowCleanResult(
                path=workflow_path,
                relative_path=os.path.basename(workflow_path),
                category="",
                step_results=step_results,
                total_removed=total,
            )
        ],
    )
