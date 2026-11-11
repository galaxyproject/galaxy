"""
Actions to be run at job completion (or output hda creation, as in the case of
immediate_actions listed below.
"""

import datetime
import re
from dataclasses import dataclass

from markupsafe import escape

from galaxy.model import (
    DatasetInstance,
    HistoryDatasetAssociation,
    HistoryDatasetCollectionAssociation,
    Job,
    PostJobActionAssociation,
)
from galaxy.schema.notifications import (
    completion_notification_request,
    JobCompletionNotificationContent,
)
from galaxy.util import send_mail
from galaxy.util.custom_logging import get_logger

log = get_logger(__name__)

RENAME_INPUT_REFERENCE_PATTERN = re.compile(r"#\{([^}]*)\}")
# A deleting job becomes deleted without running its post job actions, so it counts as settled too.
MAPPED_OVER_SETTLED_STATES = (*Job.settled_states, Job.states.DELETING)


class DefaultJobAction:
    """
    Base job action.
    """

    name = "DefaultJobAction"
    verbose_name = "Default Job"
    # Whether execute_on_mapped_over below is actually implemented. Steps that
    # apply actions without a job to hang them off of can only run actions that
    # set this, so ActionBox warns rather than silently dropping the others.
    supports_mapped_over = False

    @classmethod
    def execute(cls, app, sa_session, action, job, replacement_dict=None, final_job_state=None):
        pass

    @classmethod
    def execute_on_mapped_over(
        cls, trans, sa_session, action, step_inputs, step_outputs, replacement_dict, final_job_state=None
    ):
        pass

    @staticmethod
    def mapped_over_dataset_instances(
        step_output: HistoryDatasetAssociation | HistoryDatasetCollectionAssociation,
    ) -> list[DatasetInstance]:
        """Dataset instances an action should act on for a mapped over step output.

        Handles both collection and single dataset outputs, and drops skipped
        placeholders - mutating those breaks skip detection downstream.
        """
        instances: list[DatasetInstance | None]
        if isinstance(step_output, HistoryDatasetCollectionAssociation):
            instances = step_output.dataset_instances
        else:
            instances = [step_output]
        return [instance for instance in instances if instance is not None and not instance.is_skipped]

    @classmethod
    def get_short_str(cls, pja):
        if pja.action_arguments:
            return f"{pja.action_type} -> {escape(pja.action_arguments)}"
        else:
            return f"{pja.action_type}"


@dataclass
class JobCompletionSummary:
    """What completed: the outputs of the jobs and how many jobs ended in each state."""

    outputs: list[str]
    state_counts: dict[str, int]
    # Whether the jobs were mapped over a collection; ``outputs`` are then the output collections.
    mapped_over: bool

    @property
    def job_count(self) -> int:
        return sum(self.state_counts.values())

    def describe(self) -> str:
        outputs = ",\n".join(self.outputs)
        if not self.mapped_over:
            return f"Your Galaxy job generating dataset(s):\n\n{outputs}\n\nis complete"
        jobs, are = ("job", "is") if self.job_count == 1 else ("jobs", "are")
        states = ", ".join(f"{count} {state}" for state, count in sorted(self.state_counts.items()))
        return (
            f"Your {self.job_count} Galaxy {jobs} generating collection(s):\n\n{outputs}\n\n{are} complete ({states})"
        )


class EmailAction(DefaultJobAction):
    """
    This action notifies the galaxy user responsible for a job when it completes.

    The notification goes through the notification system when it can deliver by email,
    and is sent as a plain email otherwise.
    """

    name = "EmailAction"
    verbose_name = "Email Notification"

    @classmethod
    def execute(cls, app, sa_session, action, job, replacement_dict=None, final_job_state=None):
        """Runs after the commit that settles ``job`` (see ``ActionBox.after_commit_actions``)."""
        try:
            implicit_collection_jobs_association = job.implicit_collection_jobs_association
            if implicit_collection_jobs_association is None:
                summary = cls._job_completed(job)
            else:
                # A job mapped over a collection: notify once for the whole map-over, not once per job.
                summary = cls._map_over_completed(job, implicit_collection_jobs_association.implicit_collection_jobs)
            if summary:
                if cls._can_notify(app):
                    cls._notify(app, job, summary)
                else:
                    cls._send_email(app, job, summary)
        except Exception:
            log.exception("EmailAction PJA Failed")

    @staticmethod
    def _job_completed(job) -> JobCompletionSummary | None:
        """What completed, for a job not mapped over; None while it waits for the user to resume it."""
        if job.state == job.states.PAUSED:
            return None
        return JobCompletionSummary(
            outputs=[ds.dataset.display_name() for ds in job.output_datasets],
            state_counts={job.state: 1},
            mapped_over=False,
        )

    @staticmethod
    def _map_over_completed(job, implicit_collection_jobs) -> JobCompletionSummary | None:
        """What completed, for the map-over of ``job``; None while some of its jobs still have to run.

        Every job checks after its own settled state is committed, so the last one to commit
        sees all jobs settled. Jobs that commit within moments of each other may both see
        that, and the user gets the summary twice.
        """
        if job.state in (job.states.DELETING, job.states.DELETED):
            # Cancelled by the user; cancelling a running map-over would otherwise report once per job.
            return None
        if implicit_collection_jobs.populated_state == implicit_collection_jobs.populated_states.NEW:
            # More jobs are still to be created.
            return None
        if implicit_collection_jobs.has_job_not_in_states(MAPPED_OVER_SETTLED_STATES):
            return None
        return JobCompletionSummary(
            outputs=[
                assoc.dataset_collection_instance.name
                for assoc in job.output_dataset_collection_instances
                if assoc.dataset_collection_instance.name
            ],
            state_counts=implicit_collection_jobs.job_state_counts(),
            mapped_over=True,
        )

    @staticmethod
    def _can_notify(app) -> bool:
        # The notification system has an email channel only with Celery (NotificationManager.can_send_notifications_async);
        # without it, users would lose the email they asked for.
        return bool(app.config.enable_notification_system and app.config.enable_celery_tasks)

    @staticmethod
    def _notify(app, job, summary: JobCompletionSummary):
        """Queue a job completion notification, delivered by the channels the user's preferences allow."""
        # Mapped over jobs reach their invocation step through their implicit collection jobs.
        invocation_step = job.effective_workflow_invocation_step
        content = JobCompletionNotificationContent(
            history_id=app.security.encode_id(job.history_id),
            history_name=job.history.name or "Unnamed history",
            outputs=summary.outputs,
            job_count=summary.job_count,
            state_counts=summary.state_counts,
            invocation_id=app.security.encode_id(invocation_step.workflow_invocation_id) if invocation_step else None,
        )
        request = completion_notification_request(job.user_id, content, app.config.galaxy_infrastructure_url)
        app.notification_manager.send_notification_internal(request)

    @staticmethod
    def _send_email(app, job, summary: JobCompletionSummary):
        history_id_encoded = app.security.encode_id(job.history_id)
        link = f"{app.config.galaxy_infrastructure_url}/histories/view?id={history_id_encoded}"
        subject = f"Galaxy job completion notification from history '{job.history.name}'"
        body = (
            f"{summary.describe()} as of {datetime.datetime.now().strftime('%H:%M')}. "
            f"Click the link below to access your data: \n{link}\n\n"
            "Please remember to cite Galaxy using our primary publication "
            '(<a href="https://gxy.io/p/latest-nar">https://gxy.io/p/latest-nar</a>) '
            "in any publication based on your analysis."
        )
        # Mapped over jobs reach their invocation step through their implicit collection jobs.
        if invocation_step := job.effective_workflow_invocation_step:
            invocation_id_encoded = app.security.encode_id(invocation_step.workflow_invocation_id)
            link_invocation = (
                f"{app.config.galaxy_infrastructure_url}/workflows/invocations/report?id={invocation_id_encoded}"
            )
            body += f"\n\nWorkflow Invocation Report:\n{link_invocation}"
        send_mail(app.config.email_from, job.get_user_email(), subject, body, app.config)

    @classmethod
    def get_short_str(cls, pja):
        if pja.action_arguments and "host" in pja.action_arguments:
            return (
                f"Email the current user from server {escape(pja.action_arguments['host'])} when this job is complete."
            )
        else:
            return "Email the current user when this job is complete."


class ValidateOutputsAction(DefaultJobAction):
    """
    This action validates the produced outputs against the expected datatype.
    """

    name = "ValidateOutputsAction"
    verbose_name = "Validate Tool Outputs"

    @classmethod
    def execute(cls, app, sa_session, action, job, replacement_dict=None, final_job_state=None):
        # no-op: needs to inject metadata handling parameters ahead of time.
        pass

    @classmethod
    def get_short_str(cls, pja):
        return "Validate tool outputs."


class ChangeDatatypeAction(DefaultJobAction):
    name = "ChangeDatatypeAction"
    supports_mapped_over = True
    verbose_name = "Change Datatype"

    @classmethod
    def execute_on_mapped_over(
        cls, trans, sa_session, action, step_inputs, step_outputs, replacement_dict, final_job_state=None
    ):
        if action.action_arguments and action.action_arguments.get("newtype"):
            newtype = action.action_arguments["newtype"]
            for name, step_output in step_outputs.items():
                if action.output_name == "" or name == action.output_name:
                    for dataset_instance in cls.mapped_over_dataset_instances(step_output):
                        trans.app.datatypes_registry.change_datatype(dataset_instance, newtype)

    @classmethod
    def execute(cls, app, sa_session, action, job, replacement_dict=None, final_job_state=None):
        if job.state == job.states.SKIPPED:
            # Don't change datatype, must remain expression.json
            return
        for dataset_assoc in job.output_datasets:
            if action.output_name == "" or dataset_assoc.name == action.output_name:
                app.datatypes_registry.change_datatype(dataset_assoc.dataset, action.action_arguments["newtype"])
                return
        for dataset_collection_assoc in job.output_dataset_collection_instances:
            if action.output_name == "" or dataset_collection_assoc.name == action.output_name:
                dataset_instances = dataset_collection_assoc.dataset_collection_instance.dataset_instances
                if dataset_instances:
                    for dataset_instance in dataset_instances:
                        if dataset_instance:
                            app.datatypes_registry.change_datatype(dataset_instance, action.action_arguments["newtype"])
                else:
                    # dynamic collection, add as PJA
                    pjaa = PostJobActionAssociation(action, job)
                    sa_session.add(pjaa)
                return

    @classmethod
    def get_short_str(cls, pja):
        return "Set the datatype of output '{}' to '{}'".format(
            escape(pja.output_name), escape(pja.action_arguments["newtype"])
        )


class RenameDatasetAction(DefaultJobAction):
    name = "RenameDatasetAction"
    supports_mapped_over = True
    verbose_name = "Rename Dataset"

    @classmethod
    def execute_on_mapped_over(
        cls, trans, sa_session, action, step_inputs, step_outputs, replacement_dict, final_job_state=None
    ):
        # Prevent renaming a dataset to the empty string.
        input_names = {}
        #  Lookp through inputs find one with "to_be_replaced" input
        #  variable name, and get the replacement name
        for input_key, step_input in step_inputs.items():
            if step_input and hasattr(step_input, "name"):
                input_names[input_key] = step_input.name

        if new_name := cls._gen_new_name(action, input_names, replacement_dict):
            for name, step_output in step_outputs.items():
                if action.output_name == "" or name == action.output_name:
                    step_output.name = new_name

    @classmethod
    def _gen_new_name(self, action, input_names, replacement_dict):
        new_name = None

        if action.action_arguments and action.action_arguments.get("newname", ""):
            new_name = action.action_arguments["newname"]
            #  TODO: Unify and simplify replacement options.
            #      Add interface through workflow editor UI

            #  Resolve each #{...} reference to an input to rename
            #  using that input's name.
            #  Proper syntax is #{input_file_variable | option 1 | option n}
            #    where
            #      input_file_variable = is the name of an module input variable
            #      |  = the delimiter for added options. Optional if no options.
            #      options = basename, upper, lower
            #      basename = keep all of the file name except the extension
            #                 (everything before the final ".")
            #      upper = force the file name to upper case
            #      lower = force the file name to lower case
            #  suggested additions:
            #      "replace" option so you can replace a portion of the name.

            def resolve(match: re.Match[str]) -> str:
                to_be_replaced = match.group(1)
                input_file_var = to_be_replaced
                #  Pull out the piped controls and store them for later
                #  parsing.
                tokens = to_be_replaced.split("|")
                operations = []
                if len(tokens) > 1:
                    input_file_var = tokens[0].strip()

                    for i in range(1, len(tokens)):
                        operations.append(tokens[i].strip())

                # Treat . as special symbol (breaks parameter names anyway)
                # to allow access to repeat elements, for instance first
                # repeat in cat1 would be something like queries_0.input2.
                input_file_var = input_file_var.replace(".", "|")

                replacement = None
                if input_file_var in input_names:
                    replacement = input_names[input_file_var]
                else:
                    for input_name, _replacement in input_names.items():
                        if input_name.endswith(f"|{input_file_var}"):
                            # best effort attempt at matching up unqualified input
                            replacement = _replacement
                            break

                # In case name was None.
                replacement = replacement or ""
                #  Do operations on replacement
                #  Any control that is not defined will be ignored.
                #  This should be moved out to a class or module function
                for operation in operations:
                    # Basename returns everything prior to the final '.'
                    if operation == "basename":
                        fields = replacement.split(".")
                        replacement = fields[0]
                        if len(fields) > 1:
                            temp = ""
                            for i in range(1, len(fields) - 1):
                                temp += f".{fields[i]}"
                            replacement += temp
                    elif operation == "upper":
                        replacement = replacement.upper()
                    elif operation == "lower":
                        replacement = replacement.lower()

                return replacement

            new_name = RENAME_INPUT_REFERENCE_PATTERN.sub(resolve, new_name)

            if replacement_dict:
                for k, v in replacement_dict.items():
                    new_name = new_name.replace(f"${{{k}}}", v)

        return new_name

    @classmethod
    def execute(cls, app, sa_session, action, job, replacement_dict=None, final_job_state=None):
        input_names = {}
        #  Loop through inputs find one with "to_be_replaced" input
        #  variable name, and get the replacement name
        for input_assoc in job.input_datasets:
            if input_assoc.dataset:
                input_names[input_assoc.name] = input_assoc.dataset.name

        # Ditto for collections...
        for input_assoc in job.input_dataset_collections:
            # Either a HDCA or a DCE - only HDCA has a name.
            has_collection = input_assoc.dataset_collection
            if has_collection and hasattr(has_collection, "name"):
                input_names[input_assoc.name] = has_collection.name

        if new_name := cls._gen_new_name(action, input_names, replacement_dict):
            for dataset_assoc in job.output_datasets:
                if action.output_name == "" or dataset_assoc.name == action.output_name:
                    dataset_assoc.dataset.name = new_name

            for dataset_collection_assoc in job.output_dataset_collection_instances:
                if action.output_name == "" or dataset_collection_assoc.name == action.output_name:
                    dataset_collection_assoc.dataset_collection_instance.name = new_name

    @classmethod
    def get_short_str(cls, pja):
        # Prevent renaming a dataset to the empty string.
        if pja.action_arguments and pja.action_arguments.get("newname", ""):
            return "Rename output '{}' to '{}'.".format(
                escape(pja.output_name), escape(pja.action_arguments["newname"])
            )
        else:
            return "Rename action used without a new name specified.  Output name will be unchanged."


class HideDatasetAction(DefaultJobAction):
    name = "HideDatasetAction"
    supports_mapped_over = True
    verbose_name = "Hide Dataset"

    @classmethod
    def execute(cls, app, sa_session, action, job, replacement_dict=None, final_job_state=None):
        if final_job_state != job.states.ERROR:
            for output_association in job.output_datasets + job.output_dataset_collection_instances:
                if action.output_name == "" or output_association.name == action.output_name:
                    output_association.item.visible = False

    @classmethod
    def execute_on_mapped_over(
        cls, trans, sa_session, action, step_inputs, step_outputs, replacement_dict, final_job_state=None
    ):
        for name, step_output in step_outputs.items():
            if action.output_name == "" or name == action.output_name:
                step_output.visible = False

    @classmethod
    def get_short_str(cls, pja):
        return f"Hide output '{escape(pja.output_name)}'."


class DeleteDatasetAction(DefaultJobAction):
    # This is disabled for right now.  Deleting a dataset in the middle of a workflow causes errors (obviously) for the subsequent steps using the data.
    name = "DeleteDatasetAction"
    supports_mapped_over = True
    verbose_name = "Delete Dataset"

    @classmethod
    def execute(cls, app, sa_session, action, job, replacement_dict=None, final_job_state=None):
        for output_association in job.output_datasets + job.output_dataset_collection_instances:
            if action.output_name == "" or output_association.name == action.output_name:
                output_association.item.deleted = True

    @classmethod
    def execute_on_mapped_over(
        cls, trans, sa_session, action, step_inputs, step_outputs, replacement_dict, final_job_state=None
    ):
        for name, step_output in step_outputs.items():
            if action.output_name == "" or name == action.output_name:
                step_output.deleted = True

    @classmethod
    def get_short_str(cls, pja):
        return "Delete this dataset after creation."


class ColumnSetAction(DefaultJobAction):
    name = "ColumnSetAction"
    supports_mapped_over = True
    verbose_name = "Assign Columns"

    @classmethod
    def _apply_column_set(cls, dataset, action_arguments):
        for k, v in action_arguments.items():
            if v:
                if not isinstance(v, int):
                    if v[0] == "c":
                        v = v[1:]
                    v = int(v)
                if v != 0:
                    setattr(dataset.metadata, k, v)

    @classmethod
    def execute_on_mapped_over(
        cls, trans, sa_session, action, step_inputs, step_outputs, replacement_dict, final_job_state=None
    ):
        if action.action_arguments:
            for name, step_output in step_outputs.items():
                if action.output_name == "" or name == action.output_name:
                    for dataset_instance in cls.mapped_over_dataset_instances(step_output):
                        cls._apply_column_set(dataset_instance, action.action_arguments)

    @classmethod
    def execute(cls, app, sa_session, action, job, replacement_dict=None, final_job_state=None):
        for dataset_assoc in job.output_datasets:
            if action.output_name == "" or dataset_assoc.name == action.output_name:
                cls._apply_column_set(dataset_assoc.dataset, action.action_arguments)

    @classmethod
    def get_short_str(cls, pja):
        return f"Set the following metadata values:<br/>{'<br/>'.join(f'{escape(k)} : {escape(v)}' for k, v in pja.action_arguments.items())}"


class SetMetadataAction(DefaultJobAction):
    name = "SetMetadataAction"
    # DBTODO Setting of Metadata is currently broken and disabled.  It should not be used (yet).

    @classmethod
    def execute(cls, app, sa_session, action, job, replacement_dict=None, final_job_state=None):
        for data in job.output_datasets:
            data.set_metadata(action.action_arguments["newtype"])


class DeleteIntermediatesAction(DefaultJobAction):
    name = "DeleteIntermediatesAction"
    verbose_name = "Delete Non-Output Completed Intermediate Steps"

    @classmethod
    def execute(cls, app, sa_session, action, job, replacement_dict=None, final_job_state=None):
        # TODO Optimize this later.  Just making it work for now.
        # TODO Support purging as well as deletion if user_purge is enabled.
        # Dataset candidates for deletion must be
        # 1) Created by the workflow.
        # 2) Not have any job_to_input_dataset associations with states other
        # than OK or DELETED.  If a step errors, we don't want to delete/purge it
        # automatically.
        # 3) Not marked as a workflow output.
        # POTENTIAL ISSUES:  When many outputs are being finish()ed
        # concurrently, sometimes non-terminal steps won't be cleaned up
        # because of the lag in job state updates.
        if not job.workflow_invocation_step:
            log.debug("This job is not part of a workflow invocation, delete intermediates aborted.")
            return
        wfi = job.workflow_invocation_step.workflow_invocation
        sa_session.refresh(wfi)
        if wfi.active:
            log.debug("Workflow still scheduling so new jobs may appear, skipping deletion of intermediate files.")
            # Still evaluating workflow so we don't yet have all workflow invocation
            # steps to start looking at.
            return
        outputs_defined = wfi.workflow.has_outputs_defined()
        if outputs_defined:
            wfi_steps = [
                wfistep
                for wfistep in wfi.steps
                if not wfistep.workflow_step.workflow_outputs and wfistep.workflow_step.type == "tool"
            ]
            jobs_to_check = []
            for wfi_step in wfi_steps:
                sa_session.refresh(wfi_step)
                wfi_step_job = wfi_step.job
                if wfi_step_job:
                    jobs_to_check.append(wfi_step_job)
                else:
                    log.debug(f"No job found yet for wfi_step {wfi_step}, (step {wfi_step.workflow_step})")
            for j2c in jobs_to_check:
                creating_jobs = []
                for input_dataset in j2c.input_datasets:
                    if not input_dataset.dataset:
                        log.debug(
                            f"PJA Async Issue: No dataset attached to input_dataset {input_dataset.id} during handling of workflow invocation {wfi}"
                        )
                    elif not input_dataset.dataset.creating_job:
                        log.debug(
                            f"PJA Async Issue: No creating job attached to dataset {input_dataset.dataset.id} during handling of workflow invocation {wfi}"
                        )
                    else:
                        creating_jobs.append((input_dataset, input_dataset.dataset.creating_job))
                for input_dataset, creating_job in creating_jobs:
                    sa_session.refresh(creating_job)
                    sa_session.refresh(input_dataset)
                for input_dataset in [
                    x.dataset
                    for (x, creating_job) in creating_jobs
                    if creating_job.workflow_invocation_step
                    and creating_job.workflow_invocation_step.workflow_invocation == wfi
                ]:
                    # note that the above input_dataset is a reference to a
                    # job.input_dataset.dataset at this point
                    safe_to_delete = True
                    for job_to_check in [d_j.job for d_j in input_dataset.dependent_jobs]:
                        if job_to_check != job and job_to_check.state not in [job.states.OK, job.states.DELETED]:
                            log.trace(
                                f"Workflow Intermediates cleanup attempted, but non-terminal state '{job_to_check.state}' detected for job {job_to_check.id}"
                            )
                            safe_to_delete = False
                    if safe_to_delete:
                        # Support purging here too.
                        input_dataset.mark_deleted()
        else:
            # No workflow outputs defined, so we can't know what to delete.
            # We could make this work differently in the future
            pass

    @classmethod
    def get_short_str(cls, pja):
        return "Delete parent datasets of this step created in this workflow that aren't flagged as outputs."


class TagDatasetAction(DefaultJobAction):
    name = "TagDatasetAction"
    supports_mapped_over = True
    verbose_name = "Add tag to dataset"
    action = "Add"
    direction = "to"

    @classmethod
    def execute_on_mapped_over(
        cls, trans, sa_session, action, step_inputs, step_outputs, replacement_dict, final_job_state=None
    ):
        if action.action_arguments:
            tags = [
                t.replace("#", "name:") if t.startswith("#") else t
                for t in [t.strip() for t in action.action_arguments.get("tags", "").split(",") if t.strip()]
            ]
            if tags and step_outputs:
                tag_handler = trans.tag_handler
                for name, step_output in step_outputs.items():
                    if action.output_name == "" or name == action.output_name:
                        cls._execute(tag_handler, trans.user, step_output, tags)

    @classmethod
    def execute(cls, app, sa_session, action, job, replacement_dict=None, final_job_state=None):
        if action.action_arguments:
            tags = [
                t.replace("#", "name:") if t.startswith("#") else t
                for t in [t.strip() for t in action.action_arguments.get("tags", "").split(",") if t.strip()]
            ]
            if tags:
                tag_handler = app.tag_handler.create_tag_handler_session(job.galaxy_session)
                for dataset_assoc in job.output_datasets:
                    if action.output_name == "" or dataset_assoc.name == action.output_name:
                        cls._execute(tag_handler, job.user, dataset_assoc.dataset, tags)

                for dataset_collection_assoc in job.output_dataset_collection_instances:
                    if action.output_name == "" or dataset_collection_assoc.name == action.output_name:
                        cls._execute(tag_handler, job.user, dataset_collection_assoc.dataset_collection_instance, tags)

    @classmethod
    def _execute(cls, tag_handler, user, output, tags):
        tag_handler.add_tags_from_list(user, output, tags, flush=False)

    @classmethod
    def get_short_str(cls, pja):
        if pja.action_arguments and pja.action_arguments.get("tags", ""):
            return "{} tag(s) '{}' {} '{}'.".format(
                cls.action, escape(pja.action_arguments["tags"]), cls.direction, escape(pja.output_name)
            )
        else:
            return f"{cls.action} Tag action used without a tag specified.  No tag will be added."


class RemoveTagDatasetAction(TagDatasetAction):
    name = "RemoveTagDatasetAction"
    verbose_name = "Remove tag from dataset"
    action = "Remove"
    direction = "from"

    @classmethod
    def _execute(cls, tag_handler, user, output, tags):
        tag_handler.remove_tags_from_list(user, output, tags, flush=False)


class ActionBox:
    actions: dict[str, type[DefaultJobAction]] = {
        "RenameDatasetAction": RenameDatasetAction,
        "HideDatasetAction": HideDatasetAction,
        "ChangeDatatypeAction": ChangeDatatypeAction,
        "ColumnSetAction": ColumnSetAction,
        "EmailAction": EmailAction,
        "DeleteIntermediatesAction": DeleteIntermediatesAction,
        "TagDatasetAction": TagDatasetAction,
        "RemoveTagDatasetAction": RemoveTagDatasetAction,
    }
    public_actions = [
        "RenameDatasetAction",
        "ChangeDatatypeAction",
        "ColumnSetAction",
        "EmailAction",
        "DeleteIntermediatesAction",
        "TagDatasetAction",
        "RemoveTagDatasetAction",
    ]
    # Actions that can be applied ahead of the job execution while workflow is still
    # being scheduled and jobs created.
    immediate_actions = ["ChangeDatatypeAction", "RenameDatasetAction", "TagDatasetAction", "RemoveTagDatasetAction"]
    # Actions that read the committed state of other jobs, so they run after the commit that
    # settles the job (finished, failed, copied from a cached job or paused) rather than in it.
    after_commit_actions = ["EmailAction"]
    # Actions not run with the other post job actions in the commit that settles the job.
    deferred_actions = immediate_actions + after_commit_actions
    # Actions that will be applied to implicit mapped over collection outputs and not
    # just individual outputs when steps include mapped over tools and implicit collection outputs.
    mapped_over_output_actions = [
        "RenameDatasetAction",
        "HideDatasetAction",
        "TagDatasetAction",
        "RemoveTagDatasetAction",
    ]

    @classmethod
    def get_short_str(cls, action) -> str:
        if action.action_type in cls.actions:
            return cls.actions[action.action_type].get_short_str(action)
        else:
            return "Unknown Action"

    @classmethod
    def handle_incoming(cls, incoming):
        npd = {}
        for key, val in incoming.items():
            if key.startswith("pja"):
                sp = key.split("__")
                ao_key = sp[2] + sp[1]
                # flag / output_name / pjatype / desc
                if ao_key not in npd:
                    npd[ao_key] = {"action_type": sp[2], "output_name": sp[1], "action_arguments": {}}
                if len(sp) > 3:
                    if sp[3] == "output_name":
                        npd[ao_key]["output_name"] = val
                    else:
                        npd[ao_key]["action_arguments"][sp[3]] = val
            else:
                # Not pja stuff.
                pass
        return npd

    @classmethod
    def execute_on_mapped_over(
        cls, trans, sa_session, pja, step_inputs, step_outputs, replacement_dict=None, final_job_state=None
    ):
        action = cls.actions.get(pja.action_type)
        if action is None:
            return
        if not action.supports_mapped_over:
            log.warning(
                "Ignoring post job action %s on workflow step %s output '%s', it cannot be applied to a step "
                "output that has no job attached to it.",
                pja.action_type,
                pja.workflow_step_id,
                pja.output_name,
            )
            return
        action.execute_on_mapped_over(
            trans, sa_session, pja, step_inputs, step_outputs, replacement_dict, final_job_state=final_job_state
        )

    @classmethod
    def has_after_commit_actions(cls, job) -> bool:
        """Whether ``job`` has ``after_commit_actions``; check before the commit, while they are loaded."""
        return any(pjaa.post_job_action.action_type in cls.after_commit_actions for pjaa in job.post_job_actions)

    @classmethod
    def execute_after_commit(cls, app, sa_session, jobs):
        """Run the ``after_commit_actions`` of ``jobs``, whose settled states must be committed.

        For mapped over jobs they report on the whole map-over, so they run for one job of each map-over.
        Failures are logged, not raised: the jobs are already settled and committed.
        """
        reported_map_over_ids = set()
        for job in jobs:
            try:
                actions = [
                    pjaa.post_job_action
                    for pjaa in job.post_job_actions
                    if pjaa.post_job_action.action_type in cls.after_commit_actions
                ]
                if not actions:
                    continue
                if implicit_collection_jobs_association := job.implicit_collection_jobs_association:
                    map_over_id = implicit_collection_jobs_association.implicit_collection_jobs_id
                    if map_over_id in reported_map_over_ids:
                        continue
                    reported_map_over_ids.add(map_over_id)
                for action in actions:
                    cls.execute(app, sa_session, action, job)
            except Exception:
                log.exception("Running after-commit post job actions failed for job %s", job.id)

    @classmethod
    def execute(cls, app, sa_session, pja, job, replacement_dict=None, final_job_state=None):
        if pja.action_type in cls.actions:
            cls.actions[pja.action_type].execute(
                app, sa_session, pja, job, replacement_dict, final_job_state=final_job_state
            )
