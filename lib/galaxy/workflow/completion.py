"""
Workflow invocation completion detection logic.

This module provides functions to determine when a workflow invocation
has completed (all jobs reached terminal states) and to compute
summary statistics about job outcomes.
"""

from typing import TYPE_CHECKING

from galaxy.schema.invocation import (
    InvocationState,
    InvocationStepState,
)
from galaxy.schema.schema import JobState

if TYPE_CHECKING:
    from galaxy.model import (
        WorkflowInvocation,
        WorkflowInvocationStep,
    )


# Job states considered "terminal" for workflow completion purposes.
# These are states where the job will not change further without external intervention.
TERMINAL_JOB_STATES = frozenset(
    [
        JobState.OK.value,
        JobState.ERROR.value,
        JobState.DELETED.value,
        JobState.SKIPPED.value,
        JobState.PAUSED.value,
        JobState.STOPPED.value,
    ]
)

# Job states that indicate successful completion (no errors)
SUCCESSFUL_JOB_STATES = frozenset(
    [
        JobState.OK.value,
        JobState.SKIPPED.value,
    ]
)


def is_job_terminal(job) -> bool:
    """Check if a job is in a terminal state."""
    return job.state in TERMINAL_JOB_STATES


def is_invocation_complete(invocation: "WorkflowInvocation") -> bool:
    """
    Check if all jobs in a workflow invocation have reached terminal states.

    For subworkflows, leverages the subworkflow's completion state rather than
    re-checking all nested jobs. This is more efficient for deeply nested workflows.

    Args:
        invocation: The workflow invocation to check.

    Returns:
        True if all jobs have completed (in any terminal state), False otherwise.
    """
    # Must be in SCHEDULED state first (all steps have been scheduled)
    if invocation.state != InvocationState.SCHEDULED.value:
        return False

    for step in invocation.steps:
        if not is_step_complete(step):
            return False

    return True


def is_step_complete(step: "WorkflowInvocationStep") -> bool:
    """
    Check if a workflow invocation step is complete.

    For subworkflow steps, checks the subworkflow's completion state.
    For tool steps, checks that all associated jobs are in terminal states.

    Args:
        step: The workflow invocation step to check.

    Returns:
        True if the step is complete, False otherwise.
    """
    # Subworkflow step - check subworkflow's completion state
    if step.workflow_step.type == "subworkflow":
        return _is_subworkflow_step_complete(step)

    # Tool/module step - check job states
    jobs = step.jobs
    if not jobs:
        # Steps without jobs (e.g., input steps, pause steps, parameter steps)
        # are considered complete once they're in SCHEDULED state
        return step.state == InvocationStepState.SCHEDULED.value

    return all(is_job_terminal(job) for job in jobs)


def _is_subworkflow_step_complete(step: "WorkflowInvocationStep") -> bool:
    """
    Check if a subworkflow step is complete.

    Leverages the subworkflow's own completion state if available,
    otherwise recursively checks the subworkflow's completion.

    Args:
        step: The subworkflow step to check.

    Returns:
        True if the subworkflow is complete, False otherwise.
    """
    # Find the subworkflow invocation associated with this step
    subworkflow_assoc = next(
        (s for s in step.workflow_invocation.subworkflow_invocations if s.workflow_step_id == step.workflow_step_id),
        None,
    )

    if not subworkflow_assoc:
        # No subworkflow invocation found - step may not have been executed yet
        return False

    sub_invocation = subworkflow_assoc.subworkflow_invocation

    # Leverage subworkflow's completion state if available
    # This avoids redundant checking of deeply nested workflows
    if sub_invocation.state == InvocationState.COMPLETED.value:
        return True

    # Otherwise recursively check the subworkflow
    return is_invocation_complete(sub_invocation)


def compute_job_state_summary(invocation: "WorkflowInvocation") -> dict[str, int]:
    """
    Compute summary of job states for an invocation (including subworkflows).

    Recursively collects job states from all steps, including nested subworkflows.

    Args:
        invocation: The workflow invocation to summarize.

    Returns:
        A dictionary mapping job state strings to counts.
        Example: {"ok": 5, "error": 1, "skipped": 2}
    """
    summary: dict[str, int] = {}

    def collect_jobs(inv: "WorkflowInvocation") -> None:
        for step in inv.steps:
            if step.workflow_step.type == "subworkflow":
                # Recursively collect from subworkflow
                subworkflow_assoc = next(
                    (s for s in inv.subworkflow_invocations if s.workflow_step_id == step.workflow_step_id),
                    None,
                )
                if subworkflow_assoc:
                    collect_jobs(subworkflow_assoc.subworkflow_invocation)
            else:
                # Collect job states from this step
                for job in step.jobs:
                    state = str(job.state)
                    summary[state] = summary.get(state, 0) + 1

    collect_jobs(invocation)
    return summary


def are_all_jobs_successful(job_state_summary: dict[str, int]) -> bool:
    """
    Check if all jobs in a summary completed successfully.

    A job is considered successful if it's in OK or SKIPPED state.

    Args:
        job_state_summary: A dictionary mapping job states to counts.

    Returns:
        True if all jobs are in successful states, False otherwise.
    """
    for state_str in job_state_summary.keys():
        # Check if this state is a successful state
        try:
            state = JobState(state_str)
            if state not in SUCCESSFUL_JOB_STATES:
                return False
        except ValueError:
            # Unknown state, consider it not successful
            return False
    return True
