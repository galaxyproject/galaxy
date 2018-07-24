"""
Actions to be run at job completion (or output hda creation, as in the case of
immediate_actions listed below.  Currently only used in workflows.
"""
import datetime
import socket

from markupsafe import escape

from galaxy.util import send_mail
from galaxy.util.logging import get_logger

log = get_logger(__name__)


class DefaultJobAction(object):
    """
    Base job action.
    """
    name = "DefaultJobAction"
    verbose_name = "Default Job"

    @classmethod
    def execute(cls, app, sa_session, action, job, replacement_dict=None):
        pass

    @classmethod
    def get_short_str(cls, pja):
        if pja.action_arguments:
            return "%s -> %s" % (pja.action_type, escape(pja.action_arguments))
        else:
            return "%s" % pja.action_type


class EmailAction(DefaultJobAction):
    """
    This action sends an email to the galaxy user responsible for a job.
    """
    name = "EmailAction"
    verbose_name = "Email Notification"

    @classmethod
    def execute(cls, app, sa_session, action, job, replacement_dict):
        frm = app.config.email_from
        if frm is None:
            if action.action_arguments and 'host' in action.action_arguments:
                host = action.action_arguments['host']
            else:
                host = socket.getfqdn()
            frm = 'galaxy-no-reply@%s' % host
        to = job.user.email
        subject = "Galaxy workflow step notification '%s'" % (job.history.name)
        outdata = ', '.join(ds.dataset.display_name() for ds in job.output_datasets)
        body = "Your Galaxy job generating dataset '%s' is complete as of %s." % (outdata, datetime.datetime.now().strftime("%I:%M"))
        try:
            send_mail(frm, to, subject, body, app.config)
        except Exception as e:
            log.error("EmailAction PJA Failed, exception: %s" % e)

    @classmethod
    def get_short_str(cls, pja):
        if pja.action_arguments and 'host' in pja.action_arguments:
            return "Email the current user from server %s when this job is complete." % escape(pja.action_arguments['host'])
        else:
            return "Email the current user when this job is complete."


class ChangeDatatypeAction(DefaultJobAction):
    name = "ChangeDatatypeAction"
    verbose_name = "Change Datatype"

    @classmethod
    def execute(cls, app, sa_session, action, job, replacement_dict):
        for dataset_assoc in job.output_datasets:
            if action.output_name == '' or dataset_assoc.name == action.output_name:
                app.datatypes_registry.change_datatype(dataset_assoc.dataset, action.action_arguments['newtype'])

    @classmethod
    def get_short_str(cls, pja):
        return "Set the datatype of output '%s' to '%s'" % (escape(pja.output_name),
                                                            escape(pja.action_arguments['newtype']))


class RenameDatasetAction(DefaultJobAction):
    name = "RenameDatasetAction"
    verbose_name = "Rename Dataset"

    @classmethod
    def execute_on_mapped_over(cls, trans, sa_session, action, step_inputs, step_outputs, replacement_dict):
        # Prevent renaming a dataset to the empty string.
        input_names = {}
        #  Lookp through inputs find one with "to_be_replaced" input
        #  variable name, and get the replacement name
        for input_key, step_input in step_inputs.items():
            if step_input and hasattr(step_input, "name"):
                input_names[input_key] = step_input.name

        new_name = cls._gen_new_name(action, input_names, replacement_dict)
        if new_name:
            for name, step_output in step_outputs.items():
                if action.output_name == '' or name == action.output_name:
                    step_output.name = new_name

    @classmethod
    def _gen_new_name(self, action, input_names, replacement_dict):
        new_name = None

        if action.action_arguments and action.action_arguments.get('newname', ''):
            new_name = action.action_arguments['newname']
            #  TODO: Unify and simplify replacement options.
            #      Add interface through workflow editor UI

            #  The following if statement will process a request to rename
            #  using an input file name.
            #  TODO: Replace all matching code with regex
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
            #      "replace" option so you can replace a portion of the name,
            #      support multiple #{name} in one rename action...

            start_pos = 0
            while new_name.find("#{", start_pos) > -1:
                to_be_replaced = ""
                #  This assumes a single instance of #{variable} will exist
                start_pos = new_name.find("#{", start_pos) + 2
                end_pos = new_name.find("}", start_pos)
                to_be_replaced = new_name[start_pos:end_pos]
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

                replacement = input_names.get(input_file_var, "")

                # In case name was None.
                replacement = replacement or ''
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
                                temp += "." + fields[i]
                            replacement += temp
                    elif operation == "upper":
                        replacement = replacement.upper()
                    elif operation == "lower":
                        replacement = replacement.lower()

                new_name = new_name.replace("#{%s}" % to_be_replaced, replacement)

            if replacement_dict:
                for k, v in replacement_dict.items():
                    new_name = new_name.replace("${%s}" % k, v)

        return new_name

    @classmethod
    def execute(cls, app, sa_session, action, job, replacement_dict):
        input_names = {}
        #  Lookp through inputs find one with "to_be_replaced" input
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

        new_name = cls._gen_new_name(action, input_names, replacement_dict)
        if new_name:
            for dataset_assoc in job.output_datasets:
                if action.output_name == '' or dataset_assoc.name == action.output_name:
                    dataset_assoc.dataset.name = new_name

            for dataset_collection_assoc in job.output_dataset_collection_instances:
                if action.output_name == '' or dataset_collection_assoc.name == action.output_name:
                    dataset_collection_assoc.dataset_collection_instance.name = new_name

    @classmethod
    def get_short_str(cls, pja):
        # Prevent renaming a dataset to the empty string.
        if pja.action_arguments and pja.action_arguments.get('newname', ''):
            return "Rename output '%s' to '%s'." % (escape(pja.output_name),
                                                    escape(pja.action_arguments['newname']))
        else:
            return "Rename action used without a new name specified.  Output name will be unchanged."


class HideDatasetAction(DefaultJobAction):
    name = "HideDatasetAction"
    verbose_name = "Hide Dataset"

    @classmethod
    def execute(cls, app, sa_session, action, job, replacement_dict):
        for dataset_assoc in job.output_datasets:
            if dataset_assoc.dataset.state != dataset_assoc.dataset.states.ERROR and (action.output_name == '' or dataset_assoc.name == action.output_name):
                dataset_assoc.dataset.visible = False

        for dataset_collection_assoc in job.output_dataset_collection_instances:
            if action.output_name == '' or dataset_collection_assoc.name == action.output_name:
                dataset_collection_assoc.dataset_collection_instance.visible = False

    @classmethod
    def execute_on_mapped_over(cls, trans, sa_session, action, step_inputs, step_outputs, replacement_dict):
        for name, step_output in step_outputs.items():
            if action.output_name == '' or name == action.output_name:
                step_output.visible = False

    @classmethod
    def get_short_str(cls, pja):
        return "Hide output '%s'." % escape(pja.output_name)


class DeleteDatasetAction(DefaultJobAction):
    # This is disabled for right now.  Deleting a dataset in the middle of a workflow causes errors (obviously) for the subsequent steps using the data.
    name = "DeleteDatasetAction"
    verbose_name = "Delete Dataset"

    @classmethod
    def execute(cls, app, sa_session, action, job, replacement_dict):
        for dataset_assoc in job.output_datasets:
            if action.output_name == '' or dataset_assoc.name == action.output_name:
                dataset_assoc.dataset.deleted = True

        for dataset_collection_assoc in job.output_dataset_collection_instances:
            if action.output_name == '' or dataset_collection_assoc.name == action.output_name:
                dataset_collection_assoc.dataset_collection_instance.deleted = True

    @classmethod
    def execute_on_mapped_over(cls, trans, sa_session, action, step_inputs, step_outputs, replacement_dict):
        for name, step_output in step_outputs.items():
            if action.output_name == '' or name == action.output_name:
                step_output.deleted = True

    @classmethod
    def get_short_str(cls, pja):
        return "Delete this dataset after creation."


class ColumnSetAction(DefaultJobAction):
    name = "ColumnSetAction"
    verbose_name = "Assign Columns"

    @classmethod
    def execute(cls, app, sa_session, action, job, replacement_dict):
        for dataset_assoc in job.output_datasets:
            if action.output_name == '' or dataset_assoc.name == action.output_name:
                for k, v in action.action_arguments.items():
                    if v:
                        # Try to use both pure integer and 'cX' format.
                        if v[0] == 'c':
                            v = v[1:]
                        v = int(v)
                        if v != 0:
                            setattr(dataset_assoc.dataset.metadata, k, v)

    @classmethod
    def get_short_str(cls, pja):
        return "Set the following metadata values:<br/>" + "<br/>".join('%s : %s' % (escape(k), escape(v)) for k, v in pja.action_arguments.items())


class SetMetadataAction(DefaultJobAction):
    name = "SetMetadataAction"
    # DBTODO Setting of Metadata is currently broken and disabled.  It should not be used (yet).

    @classmethod
    def execute(cls, app, sa_session, action, job, replacement_dict):
        for data in job.output_datasets:
            data.set_metadata(action.action_arguments['newtype'])


class DeleteIntermediatesAction(DefaultJobAction):
    name = "DeleteIntermediatesAction"
    verbose_name = "Delete Non-Output Completed Intermediate Steps"

    @classmethod
    def execute(cls, app, sa_session, action, job, replacement_dict):
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
        sa_session.flush()
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
            wfi_steps = [wfistep for wfistep in wfi.steps if not wfistep.workflow_step.workflow_outputs and wfistep.workflow_step.type == "tool"]
            jobs_to_check = []
            for wfi_step in wfi_steps:
                sa_session.refresh(wfi_step)
                wfi_step_job = wfi_step.job
                if wfi_step_job:
                    jobs_to_check.append(wfi_step_job)
                else:
                    log.debug("No job found yet for wfi_step %s, (step %s)" % (wfi_step, wfi_step.workflow_step))
            for j2c in jobs_to_check:
                creating_jobs = []
                for input_dataset in j2c.input_datasets:
                    if not input_dataset.dataset:
                        log.debug("PJA Async Issue: No dataset attached to input_dataset %s during handling of workflow invocation %s" % (input_dataset.id, wfi))
                    elif not input_dataset.dataset.creating_job:
                        log.debug("PJA Async Issue: No creating job attached to dataset %s during handling of workflow invocation %s" % (input_dataset.dataset.id, wfi))
                    else:
                        creating_jobs.append((input_dataset, input_dataset.dataset.creating_job))
                for (input_dataset, creating_job) in creating_jobs:
                    sa_session.refresh(creating_job)
                    sa_session.refresh(input_dataset)
                for input_dataset in [x.dataset for (x, creating_job) in creating_jobs if creating_job.workflow_invocation_step and creating_job.workflow_invocation_step.workflow_invocation == wfi]:
                    # note that the above input_dataset is a reference to a
                    # job.input_dataset.dataset at this point
                    safe_to_delete = True
                    for job_to_check in [d_j.job for d_j in input_dataset.dependent_jobs]:
                        if job_to_check != job and job_to_check.state not in [job.states.OK, job.states.DELETED]:
                            log.trace("Workflow Intermediates cleanup attempted, but non-terminal state '%s' detected for job %s" % (job_to_check.state, job_to_check.id))
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
    verbose_name = "Add tag to dataset"
    action = "Add"
    direction = "to"

    @classmethod
    def execute_on_mapped_over(cls, trans, sa_session, action, step_inputs, step_outputs, replacement_dict):
        if action.action_arguments:
            tags = [t.replace('#', 'name:') if t.startswith('#') else t for t in [t.strip() for t in action.action_arguments.get('tags', '').split(',') if t.strip()]]
            if tags:
                for name, step_output in step_outputs.items():
                    if action.output_name == '' or name == action.output_name:
                        cls._execute(trans.app, trans.user, step_output, tags)

    @classmethod
    def execute(cls, app, sa_session, action, job, replacement_dict):
        if action.action_arguments:
            tags = [t.replace('#', 'name:') if t.startswith('#') else t for t in [t.strip() for t in action.action_arguments.get('tags', '').split(',') if t.strip()]]
            if tags:
                for dataset_assoc in job.output_datasets:
                    if action.output_name == '' or dataset_assoc.name == action.output_name:
                        cls._execute(app, job.user, dataset_assoc.dataset, tags)

                for dataset_collection_assoc in job.output_dataset_collection_instances:
                    if action.output_name == '' or dataset_collection_assoc.name == action.output_name:
                        cls._execute(app, job.user, dataset_collection_assoc.dataset_collection_instance, tags)

            sa_session.flush()

    @classmethod
    def _execute(cls, app, user, output, tags):
        app.tag_handler.add_tags_from_list(user, output, tags)

    @classmethod
    def get_short_str(cls, pja):
        if pja.action_arguments and pja.action_arguments.get('tags', ''):
            return "%s tag(s) '%s' %s '%s'." % (cls.action,
                                                escape(pja.action_arguments['tags']),
                                                cls.direction,
                                                escape(pja.output_name))
        else:
            return "%s Tag action used without a tag specified.  No tag will be added." % cls.action


class RemoveTagDatasetAction(TagDatasetAction):
    name = "RemoveTagDatasetAction"
    verbose_name = "Remove tag from dataset"
    action = "Remove"
    direction = "from"

    @classmethod
    def _execute(cls, app, user, output, tags):
        app.tag_handler.remove_tags_from_list(user, output, tags)


class ActionBox(object):

    actions = {"RenameDatasetAction": RenameDatasetAction,
               "HideDatasetAction": HideDatasetAction,
               "ChangeDatatypeAction": ChangeDatatypeAction,
               "ColumnSetAction": ColumnSetAction,
               "EmailAction": EmailAction,
               "DeleteIntermediatesAction": DeleteIntermediatesAction,
               "TagDatasetAction": TagDatasetAction,
               "RemoveTagDatasetAction": RemoveTagDatasetAction}
    public_actions = ['RenameDatasetAction', 'ChangeDatatypeAction',
                      'ColumnSetAction', 'EmailAction',
                      'DeleteIntermediatesAction', 'TagDatasetAction',
                      'RemoveTagDatasetAction']
    # Actions that can be applied ahead of the job execution while workflow is still
    # being scheduled and jobs created.
    immediate_actions = ['ChangeDatatypeAction', 'RenameDatasetAction',
                         'TagDatasetAction', 'RemoveTagDatasetAction']
    # Actions that will be applied to implicit mapped over collection outputs and not
    # just individual outputs when steps include mapped over tools and implicit collection outputs.
    mapped_over_output_actions = ['RenameDatasetAction', 'HideDatasetAction',
                                  'TagDatasetAction', 'RemoveTagDatasetAction']

    @classmethod
    def get_short_str(cls, action):
        if action.action_type in ActionBox.actions:
            return ActionBox.actions[action.action_type].get_short_str(action)
        else:
            return "Unknown Action"

    @classmethod
    def handle_incoming(cls, incoming):
        npd = {}
        for key, val in incoming.items():
            if key.startswith('pja'):
                sp = key.split('__')
                ao_key = sp[2] + sp[1]
                # flag / output_name / pjatype / desc
                if ao_key not in npd:
                    npd[ao_key] = {'action_type': sp[2],
                                   'output_name': sp[1],
                                   'action_arguments': {}}
                if len(sp) > 3:
                    if sp[3] == 'output_name':
                        npd[ao_key]['output_name'] = val
                    else:
                        npd[ao_key]['action_arguments'][sp[3]] = val
            else:
                # Not pja stuff.
                pass
        return npd

    @classmethod
    def execute_on_mapped_over(cls, trans, sa_session, pja, step_inputs, step_outputs, replacement_dict=None):
        if pja.action_type in ActionBox.actions:
            ActionBox.actions[pja.action_type].execute_on_mapped_over(trans, sa_session, pja, step_inputs, step_outputs, replacement_dict)

    @classmethod
    def execute(cls, app, sa_session, pja, job, replacement_dict=None):
        if pja.action_type in ActionBox.actions:
            ActionBox.actions[pja.action_type].execute(app, sa_session, pja, job, replacement_dict)
