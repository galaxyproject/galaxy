import logging
from datetime import datetime
from typing import TYPE_CHECKING

from galaxy import model
from galaxy.jobs.runners import JobState
from ._safe_eval import safe_eval

if TYPE_CHECKING:
    from galaxy.app import GalaxyManagerApplication
    from galaxy.jobs import ResubmitConfigDict
    from galaxy.jobs.runners import BaseJobRunner

__all__ = ("failure",)

log = logging.getLogger(__name__)

MESSAGES = dict(
    walltime_reached="it reached the walltime",
    memory_limit_reached="it exceeded the amount of allocated memory",
    unknown_error="it encountered an unknown error",
    tool_detected="it encountered a tool detected error condition",
)


def failure(app: "GalaxyManagerApplication", job_runner: "BaseJobRunner", job_state: JobState) -> None:
    # Leave handler quickly if no resubmit conditions specified or if the runner state doesn't allow resubmission.
    resubmit_definitions = job_state.job_destination.resubmit
    if not resubmit_definitions:
        return

    runner_state = getattr(job_state, "runner_state", None) or JobState.runner_states.UNKNOWN_ERROR
    if runner_state not in (
        JobState.runner_states.WALLTIME_REACHED,
        JobState.runner_states.MEMORY_LIMIT_REACHED,
        JobState.runner_states.JOB_OUTPUT_NOT_RETURNED_FROM_CLUSTER,
        JobState.runner_states.TOOL_DETECT_ERROR,
        JobState.runner_states.UNKNOWN_ERROR,
    ):
        # not set or not a handleable runner state
        return

    _handle_resubmit_definitions(resubmit_definitions, app, job_runner, job_state)


def _handle_resubmit_definitions(
    resubmit_definitions: list["ResubmitConfigDict"],
    app: "GalaxyManagerApplication",
    job_runner: "BaseJobRunner",
    job_state: JobState,
) -> None:
    runner_state = getattr(job_state, "runner_state", None) or JobState.runner_states.UNKNOWN_ERROR

    # Setup environment for evaluating resubmission conditions and related expression.
    expression_context = _ExpressionContext(job_state)

    # Intercept jobs that hit the walltime and have a walltime or
    # nonspecific resubmit destination configured
    for resubmit in resubmit_definitions:
        condition = resubmit.get("condition", None)
        if condition and not expression_context.safe_eval(condition):
            # There is a resubmit defined for the destination but
            # its condition is not for the encountered state
            continue

        if (external_id := getattr(job_state, "job_id", None)) is not None:
            job_log_prefix = f"({job_state.job_wrapper.job_id}/{external_id})"
        else:
            job_log_prefix = f"({job_state.job_wrapper.job_id})"

        # Is destination needed here, might these be serialized to the database?
        if (destination := resubmit.get("environment")) is not None:
            new_destination = app.job_config.get_destination(destination)
        else:
            new_destination = job_state.job_destination
        log.info(
            "%s Job will be resubmitted to '%s' because %s at the '%s' destination",
            job_log_prefix,
            new_destination.id,
            MESSAGES[runner_state],
            job_state.job_wrapper.job_destination.id,
        )

        # Resolve dynamic if necessary, and cache the destination to prevent
        # rerunning dynamic after resubmit
        new_destination = job_state.job_wrapper.set_cached_job_destination(new_destination)
        # Reset job state
        job_state.job_wrapper.clear_working_directory()
        job = job_state.job_wrapper.get_job()
        if handler := resubmit.get("handler"):
            log.debug("%s Job reassigned to handler %s", job_log_prefix, handler)
            job.set_handler(handler)
            job_runner.sa_session.add(job)
            # Is this safe to do here?
            job_runner.sa_session.commit()
        # Handle delaying before resubmission if needed.
        raw_delay = resubmit.get("delay")
        if raw_delay:
            delay = str(expression_context.safe_eval(str(raw_delay)))
            try:
                # ensure result acts like a number when persisted.
                float(delay)
                new_destination.params["__resubmit_delay_seconds"] = str(delay)
            except ValueError:
                log.warning(f"Cannot delay job with delay [{delay}], does not appear to be a number.")
        job_state.job_wrapper.set_job_destination(new_destination)
        # Clear external ID (state change below flushes the change)
        job.job_runner_external_id = None
        # Allow the UI to query for resubmitted state
        job_state.runner_state_handled = True
        info = f"This job was resubmitted to the queue because {MESSAGES[runner_state]} on its compute resource."
        job_runner.mark_as_resubmitted(job_state, info=info)
        return


class _ExpressionContext:
    def __init__(self, job_state):
        self._job_state = job_state
        self._lazy_context = None

    def safe_eval(self, condition):
        if condition.isdigit():
            return int(condition)

        if self._lazy_context is None:
            runner_state = getattr(self._job_state, "runner_state", None) or JobState.runner_states.UNKNOWN_ERROR
            attempt = 1
            now = datetime.utcnow()
            last_running_state = None
            last_queued_state = None
            for state in self._job_state.job_wrapper.get_job().state_history:
                if state.state == model.Job.states.RUNNING:
                    last_running_state = state
                elif state.state == model.Job.states.QUEUED:
                    last_queued_state = state
                elif state.state == model.Job.states.RESUBMITTED:
                    attempt = attempt + 1

            seconds_running = 0
            seconds_since_queued = 0
            if last_running_state:
                seconds_running = (now - last_running_state.create_time).total_seconds()
            if last_queued_state:
                seconds_since_queued = (now - last_queued_state.create_time).total_seconds()

            self._lazy_context = {
                "walltime_reached": runner_state == JobState.runner_states.WALLTIME_REACHED,
                "memory_limit_reached": runner_state == JobState.runner_states.MEMORY_LIMIT_REACHED,
                "unknown_error": runner_state == JobState.runner_states.UNKNOWN_ERROR,
                "tool_detected_failure": runner_state == JobState.runner_states.TOOL_DETECT_ERROR,
                "any_failure": True,
                "any_potential_job_failure": True,  # Add a hook here - later on allow tools to describe things that are definitely input problems.
                "attempt": attempt,
                "seconds_running": seconds_running,
                "seconds_since_queued": seconds_since_queued,
            }

        # Small optimization to eliminate the need to parse AST and eval for simple variables.
        if condition in self._lazy_context:
            return self._lazy_context[condition]
        else:
            return safe_eval(condition, self._lazy_context)
