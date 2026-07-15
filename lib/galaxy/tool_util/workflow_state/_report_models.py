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

StepStatus = Literal["ok", "fail", "skip"]


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


class WorkflowValidationResult(WorkflowResultBase):
    step_results: List[ValidationStepResult] = Field(default=[], serialization_alias="results")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def summary(self) -> Optional[Dict[str, int]]:
        if self.error:
            return None
        return {
            "ok": sum(1 for sr in self.step_results if sr.status == "ok"),
            "fail": sum(1 for sr in self.step_results if sr.status == "fail"),
            "skip": sum(1 for sr in self.step_results if sr.status == "skip"),
        }


class WorkflowCleanResult(WorkflowResultBase):
    step_results: List[CleanStepResult] = Field(default=[], serialization_alias="results")
    total_removed: int = 0


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
        ok = fail = skip = error = 0
        for r in self.results:
            if r.error:
                error += 1
                continue
            for sr in r.step_results:
                if sr.status == "ok":
                    ok += 1
                elif sr.status == "fail":
                    fail += 1
                elif sr.status == "skip":
                    skip += 1
        return {"ok": ok, "fail": fail, "skip": skip, "error": error}


class TreeCleanReport(TreeReportBase):
    results: List[WorkflowCleanResult] = Field(default=[], serialization_alias="workflows")

    def _workflow_results(self) -> list:
        return self.results

    @computed_field  # type: ignore[prop-decorator]
    @property
    def summary(self) -> Dict[str, int]:
        total_keys = sum(r.total_removed for r in self.results)
        affected = sum(1 for r in self.results if r.total_removed > 0)
        errors = sum(1 for r in self.results if r.error)
        clean = len(self.results) - affected - errors
        return {"total_keys": total_keys, "affected": affected, "clean": clean, "errors": errors}


# -- Single-workflow wrappers (for JSON serialization of single-file runs) --


class SingleValidationReport(BaseModel):
    """JSON shape for single-file validation."""

    workflow: str
    results: List[ValidationStepResult]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def summary(self) -> Dict[str, int]:
        return {
            "ok": sum(1 for r in self.results if r.status == "ok"),
            "fail": sum(1 for r in self.results if r.status == "fail"),
            "skip": sum(1 for r in self.results if r.status == "skip"),
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


def wrap_single_validation(workflow_path: str, results: List[ValidationStepResult]) -> TreeValidationReport:
    """Wrap single-file results into a TreeValidationReport for Markdown rendering."""
    return TreeValidationReport(
        root=workflow_path,
        results=[
            WorkflowValidationResult(
                path=workflow_path,
                relative_path=os.path.basename(workflow_path),
                category="",
                step_results=results,
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
