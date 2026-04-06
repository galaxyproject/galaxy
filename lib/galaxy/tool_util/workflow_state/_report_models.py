"""Pydantic models for structured CLI report output.

Shared base types for validation and cleaning reports, plus
tool-specific result models. JSON serialization is handled by
Pydantic's model_dump(by_alias=True); text and Markdown formatters
consume these models directly via field names.
"""

import os
from typing import (
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

StepStatus = Literal["ok", "fail", "skip_tool_not_found"]
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
    removed_keys: List[str] = []
    skipped: bool = False
    skip_reason: str = ""


# -- Workflow-level results --


class WorkflowResultBase(BaseModel):
    """Fields common to every per-workflow result."""

    path: str = Field(exclude=True)
    relative_path: str = Field(serialization_alias="path")
    category: str
    error: Optional[str] = None
    skipped_reason: Optional[SkipWorkflowReason] = None


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
            "skip_tool_not_found": sum(1 for sr in self.step_results if sr.status == "skip_tool_not_found"),
        }


class WorkflowCleanResult(WorkflowResultBase):
    step_results: List[CleanStepResult] = Field(default=[], serialization_alias="results")
    total_removed: int = 0


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

    def _workflow_results(self) -> list:
        raise NotImplementedError


class TreeValidationReport(TreeReportBase):
    results: List[WorkflowValidationResult] = Field(default=[], serialization_alias="workflows")

    def _workflow_results(self) -> list:
        return self.results

    @computed_field  # type: ignore[prop-decorator]
    @property
    def summary(self) -> Dict[str, int]:
        ok = fail = skip_tool_not_found = error = skipped = 0
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
                elif sr.status == "skip_tool_not_found":
                    skip_tool_not_found += 1
        return {
            "ok": ok,
            "fail": fail,
            "skip_tool_not_found": skip_tool_not_found,
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


class SingleValidationReport(BaseModel):
    """JSON shape for single-file validation."""

    workflow: str
    results: List[ValidationStepResult]
    connection_report: Optional["ConnectionValidationReport"] = None
    skipped_reason: Optional[str] = None
    structure_errors: List[str] = Field(default_factory=list)
    encoding_errors: List[str] = Field(default_factory=list)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def summary(self) -> Dict[str, int]:
        return {
            "ok": sum(1 for r in self.results if r.status == "ok"),
            "fail": sum(1 for r in self.results if r.status == "fail"),
            "skip_tool_not_found": sum(1 for r in self.results if r.status == "skip_tool_not_found"),
        }


class SingleCleanReport(BaseModel):
    """JSON shape for single-file cleaning."""

    workflow: str
    results: List[CleanStepResult]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_removed(self) -> int:
        return sum(len(r.removed_keys) for r in self.results)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def steps_with_removals(self) -> int:
        return sum(1 for r in self.results if r.removed_keys)


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


class SingleLintReport(BaseModel):
    """JSON shape for single-file lint."""

    workflow: str
    lint_errors: int = 0
    lint_warnings: int = 0
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
            "state_skip": sum(1 for r in self.results if r.status == "skip_tool_not_found"),
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
            sum(1 for sr in r.step_results if sr.status == "skip_tool_not_found")
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


def wrap_single_clean(workflow_path: str, step_results: List[CleanStepResult]) -> TreeCleanReport:
    """Wrap single-file results into a TreeCleanReport for Markdown rendering."""
    total = sum(len(r.removed_keys) for r in step_results)
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
