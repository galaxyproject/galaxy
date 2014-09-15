"""
Actions to be run at job completion.  Currently only used in workflows.
"""

import datetime
import logging
from galaxy.util import send_mail
from galaxy.util.json import dumps

log = logging.getLogger( __name__ )


def get_form_template(action_type, title, content, help, on_output=True ):
    if on_output:
        form = """
            if (pja.action_type == "%s"){
                p_str = "<div class='pjaForm toolForm'><span class='action_tag' style='display:none'>"+ pja.action_type + pja.output_name + "</span><div class='toolFormTitle'> %s <br/> on " + pja.output_name + "\
                <div style='float: right;' class='buttons'><img src='/static/images/history-buttons/delete_icon.png'></div></div><div class='toolFormBody'>";
                %s
                p_str += "</div><div class='toolParamHelp'>%s</div></div>";
            }""" % (action_type, title, content, help)
    else:
        form = """
            if (pja.action_type == "%s"){
                p_str = "<div class='pjaForm toolForm'><span class='action_tag' style='display:none'>"+ pja.action_type + "</span><div class='toolFormTitle'> %s \
                <div style='float: right;' class='buttons'><img src='/static/images/history-buttons/delete_icon.png'></div></div><div class='toolFormBody'>";
                %s
                p_str += "</div><div class='toolParamHelp'>%s</div></div>";
            }""" % (action_type, title, content, help)
    return form


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
    def get_config_form(cls, trans):
        return "<p>Default Job Action Config Form</p>"

    @classmethod
    def get_short_str(cls, pja):
        if pja.action_arguments:
            return "%s -> %s" % (pja.action_type, pja.action_arguments)
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
        if action.action_arguments and 'host' in action.action_arguments:
            host = action.action_arguments['host']
        else:
            host = 'usegalaxy.org'
        frm = 'galaxy-noreply@%s' % host
        to = job.user.email
        subject = "Galaxy workflow step notification '%s'" % (job.history.name)
        outdata = ', '.join(ds.dataset.display_name() for ds in job.output_datasets)
        body = "Your Galaxy job generating dataset '%s' is complete as of %s." % (outdata, datetime.datetime.now().strftime( "%I:%M" ))
        try:
            send_mail( frm, to, subject, body, app.config )
        except Exception, e:
            log.error("EmailAction PJA Failed, exception: %s" % e)

    @classmethod
    def get_config_form(cls, trans):
        form = """
            p_str += "<label for='pja__"+pja.output_name+"__EmailAction'>There are no additional options for this action.  You will be emailed upon job completion.</label>\
                        <input type='hidden' value='%s' name='pja__"+pja.output_name+"__EmailAction__host'/><input type='hidden' name='pja__"+pja.output_name+"__EmailAction'/>";
            """ % trans.request.host
        return get_form_template(cls.name, cls.verbose_name, form, "This action will send an email notifying you when the job is done.", on_output=False)

    @classmethod
    def get_short_str(cls, pja):
        if pja.action_arguments and 'host' in pja.action_arguments:
            return "Email the current user from server %s when this job is complete." % pja.action_arguments['host']
        else:
            return "Email the current user when this job is complete."


class ChangeDatatypeAction(DefaultJobAction):
    name = "ChangeDatatypeAction"
    verbose_name = "Change Datatype"

    @classmethod
    def execute(cls, app, sa_session, action, job, replacement_dict):
        for dataset_assoc in job.output_datasets:
            if action.output_name == '' or dataset_assoc.name == action.output_name:
                app.datatypes_registry.change_datatype( dataset_assoc.dataset, action.action_arguments['newtype'])

    @classmethod
    def get_config_form(cls, trans):
        dt_list = ""
        dtnames = [ dtype_name for dtype_name, dtype_value in trans.app.datatypes_registry.datatypes_by_extension.iteritems()]
        dtnames.sort()
        for dt_name in dtnames:
            dt_list += """<option id='pja__"+pja.output_name+"__ChangeDatatypeAction__newtype__%s' value='%s'>%s</option>""" % (dt_name, dt_name, dt_name)
        ps = """
            p_str += "<label for='pja__"+pja.output_name+"__ChangeDatatypeAction__newtype'>New Datatype:</label>\
                <select id='pja__"+pja.output_name+"__ChangeDatatypeAction__newtype' name='pja__"+pja.output_name+"__ChangeDatatypeAction__newtype'>\
                %s\
                </select>";
            if (pja.action_arguments !== undefined && pja.action_arguments.newtype !== undefined){
                 p_str += "<scrip" + "t type='text/javascript'>$('#pja__" + pja.output_name + "__ChangeDatatypeAction__newtype').val('" + pja.action_arguments.newtype + "');</scrip" + "t>";
            }
            """ % dt_list
        # Note the scrip + t hack above.  Is there a better way?
        return get_form_template(cls.name, cls.verbose_name, ps, 'This action will change the datatype of the output to the indicated value.')

    @classmethod
    def get_short_str(cls, pja):
        return "Set the datatype of output '%s' to '%s'" % (pja.output_name, pja.action_arguments['newtype'])


class RenameDatasetAction(DefaultJobAction):
    name = "RenameDatasetAction"
    verbose_name = "Rename Dataset"

    @classmethod
    def execute(cls, app, sa_session, action, job, replacement_dict):
        # Prevent renaming a dataset to the empty string.
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

            if new_name.find("#{") > -1:
                to_be_replaced = ""
                #  This assumes a single instance of #{variable} will exist
                start_pos = new_name.find("#{") + 2
                end_pos = new_name.find("}")
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
                replacement = ""
                #  Lookp through inputs find one with "to_be_replaced" input
                #  variable name, and get the replacement name
                for input_assoc in job.input_datasets:
                    if input_assoc.name == input_file_var:
                        replacement = input_assoc.dataset.name

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
                for k, v in replacement_dict.iteritems():
                    new_name = new_name.replace("${%s}" % k, v)
            for dataset_assoc in job.output_datasets:
                if action.output_name == '' or dataset_assoc.name == action.output_name:
                    dataset_assoc.dataset.name = new_name

    @classmethod
    def get_config_form(cls, trans):
        form = """
            if (pja.action_arguments && pja.action_arguments.newname){
                p_str += "<label for='pja__"+pja.output_name+"__RenameDatasetAction__newname'>New output name:</label>\
                          <input type='text' name='pja__"+pja.output_name+"__RenameDatasetAction__newname' value=\\"" + pja.action_arguments.newname.replace(/"/g, "&quot;") + "\\"/>";
            }
            else{
                p_str += "<label for='pja__"+pja.output_name+"__RenameDatasetAction__newname'>New output name:</label>\
                          <input type='text' name='pja__"+pja.output_name+"__RenameDatasetAction__newname' value=''/>";
            }
            inputlist = [];
            $.each(node.input_terminals, function(i, v){
                inputlist.push(v.name);
            });
            if (inputlist !== []){
                p_str += "Available inputs are: <strong>" + inputlist.join(', ') + "</strong>";
            }else{
                p_str += "No inputs are available for templating into this action.";
            }
            """
        return get_form_template(cls.name, cls.verbose_name, form, "This action will rename the result dataset.  See <a href='https://wiki.galaxyproject.org/Learn/AdvancedWorkflow/Variables'>the wiki</a> for usage information.")

    @classmethod
    def get_short_str(cls, pja):
        # Prevent renaming a dataset to the empty string.
        if pja.action_arguments and pja.action_arguments.get('newname', ''):
            return "Rename output '%s' to '%s'." % (pja.output_name, pja.action_arguments['newname'])
        else:
            return "Rename action used without a new name specified.  Output name will be unchanged."


class HideDatasetAction(DefaultJobAction):
    name = "HideDatasetAction"
    verbose_name = "Hide Dataset"

    @classmethod
    def execute(cls, app, sa_session, action, job, replacement_dict):
        for dataset_assoc in job.output_datasets:
            if dataset_assoc.dataset.state != dataset_assoc.dataset.states.ERROR and ( action.output_name == '' or dataset_assoc.name == action.output_name ):
                dataset_assoc.dataset.visible = False

    @classmethod
    def get_config_form(cls, trans):
        return """
               if (pja.action_type == "HideDatasetAction"){
                   p_str += "<input type='hidden' name='pja__"+pja.output_name+"__HideDatasetAction'/>";
               }
               """

    @classmethod
    def get_short_str(cls, pja):
        return "Hide output '%s'." % pja.output_name


class DeleteDatasetAction(DefaultJobAction):
    # This is disabled for right now.  Deleting a dataset in the middle of a workflow causes errors (obviously) for the subsequent steps using the data.
    name = "DeleteDatasetAction"
    verbose_name = "Delete Dataset"

    @classmethod
    def execute(cls, app, sa_session, action, job, replacement_dict):
        for dataset_assoc in job.output_datasets:
            if action.output_name == '' or dataset_assoc.name == action.output_name:
                dataset_assoc.dataset.deleted = True

    @classmethod
    def get_config_form(cls, trans):
        form = """
            p_str += "<label for='pja__"+pja.output_name+"__DeleteDatasetAction'>There are no additional options for this action.  This dataset will be marked deleted.</label>\
                        <input type='hidden' name='pja__"+pja.output_name+"__DeleteDatasetAction'/>";
            """
        return get_form_template(cls.name, cls.verbose_name, form, "This action will rename the result dataset.")

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
                    if v != '':
                        # Try to use both pure integer and 'cX' format.
                        if v[0] == 'c':
                            v = v[1:]
                        v = int(v)
                        if v != 0:
                            setattr(dataset_assoc.dataset.metadata, k, v)

    @classmethod
    def get_config_form(cls, trans):
        form = """
            if (pja.action_arguments !== undefined){
                (pja.action_arguments.chromCol === undefined) ? chromCol = "" : chromCol=pja.action_arguments.chromCol;
                (pja.action_arguments.startCol === undefined) ? startCol = "" : startCol=pja.action_arguments.startCol;
                (pja.action_arguments.endCol === undefined) ? endCol = "" : endCol=pja.action_arguments.endCol;
                (pja.action_arguments.strandCol === undefined) ? strandCol = "" : strandCol=pja.action_arguments.strandCol;
                (pja.action_arguments.nameCol === undefined) ? nameCol = "" : nameCol=pja.action_arguments.nameCol;
            }else{
                chromCol = '';
                startCol = '';
                endCol = '';
                strandCol = '';
                nameCol = '';
            }
            p_str += "<p>Leave any of these fields blank if they do not need to be set.</p>\
                    <label for='pja__"+pja.output_name+"__ColumnSetAction__chromCol'>Chrom Column</label>\
                        <input type='text' value='" + chromCol + "' name='pja__"+pja.output_name+"__ColumnSetAction__chromCol'/>\
                    <label for='pja__"+pja.output_name+"__ColumnSetAction__startCol'>Start Column</label>\
                        <input type='text' value='" + startCol + "' name='pja__"+pja.output_name+"__ColumnSetAction__startCol'/>\
                    <label for='pja__"+pja.output_name+"__ColumnSetAction__endCol'>End Column</label>\
                        <input type='text' value='" + endCol + "' name='pja__"+pja.output_name+"__ColumnSetAction__endCol'/>\
                    <label for='pja__"+pja.output_name+"__ColumnSetAction__strandCol'>Strand Column</label>\
                        <input type='text' value='" + strandCol + "' name='pja__"+pja.output_name+"__ColumnSetAction__strandCol'/>\
                    <label for='pja__"+pja.output_name+"__ColumnSetAction__nameCol'>Name Column</label>\
                        <input type='text' value='" + nameCol + "' name='pja__"+pja.output_name+"__ColumnSetAction__nameCol'/>\";
            """
        return get_form_template(cls.name, cls.verbose_name, form, "This action will set column assignments in the output dataset.  Blank fields are ignored.")

    @classmethod
    def get_short_str(cls, pja):
        return "Set the following metadata values:<br/>" + "<br/>".join(['%s : %s' % (k, v) for k, v in pja.action_arguments.iteritems()])


class SetMetadataAction(DefaultJobAction):
    name = "SetMetadataAction"
    # DBTODO Setting of Metadata is currently broken and disabled.  It should not be used (yet).

    @classmethod
    def execute(cls, app, sa_session, action, job, replacement_dict):
        for data in job.output_datasets:
            data.set_metadata( action.action_arguments['newtype'] )

    @classmethod
    def get_config_form(cls, trans):
        #         dt_list = ""
        #         mdict = {}
        #         for dtype_name, dtype_value in trans.app.datatypes_registry.datatypes_by_extension.iteritems():
        #             for mn, mt in dtype_value.metadata_spec.items():
        #                 if mt.visible:
        #                     mdict[mt.desc] = mt.param.get_html(value= mn).replace('"', "'").strip().replace('\n','')
        #         for k, v in mdict.items():
        #             dt_list += "<p><strong>" + k + ":</strong><br/>" + v + "</p>"
        #         form = """
        #           p_str += "%s";
        #   """ % dt_list
        # return get_form_template('SetMetadataAction', 'Set Metadata', form, "This action will change metadata for the dataset.")
        form = """
          p_str += "<p>Leave any of these fields blank if they do not need to be set.</p><label for='pja__"+pja.output_name+"__SetMetadataAction__chromCol'>Chrom Column</label>\
                        <input type='text' name='pja__"+pja.output_name+"__SetMetadataAction__chromCol'/>\
                    <label for='pja__"+pja.output_name+"__SetMetadataAction__startCol'>Start Column</label>\
                        <input type='text' name='pja__"+pja.output_name+"__SetMetadataAction__startCol'/>\
                    <label for='pja__"+pja.output_name+"__SetMetadataAction__endCol'>End Column</label>\
                        <input type='text' name='pja__"+pja.output_name+"__SetMetadataAction__endCol'/>\
                    <label for='pja__"+pja.output_name+"__SetMetadataAction__comment_lines'>Comment Lines</label>\
                        <input type='text' name='pja__"+pja.output_name+"__SetMetadataAction__comment_lines'/>\
                      ";
            """
        return get_form_template(cls.name, cls.verbose_name, form, "This action will set metadata in the output dataset.")


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
        wfi = job.workflow_invocation_step.workflow_invocation
        if wfi.workflow.has_outputs_defined():
            jobs_to_check = [wfistep.job for wfistep in wfi.steps if not wfistep.workflow_step.workflow_outputs]
            for j2c in jobs_to_check:
                for input_dataset in [x.dataset for x in j2c.input_datasets if x.dataset.creating_job.workflow_invocation_step and x.dataset.creating_job.workflow_invocation_step.workflow_invocation == wfi]:
                    safe_to_delete = True
                    for job_to_check in [d_j.job for d_j in input_dataset.dependent_jobs]:
                        if job_to_check != job and job_to_check.state not in [job.states.OK, job.states.DELETED]:
                            log.debug("Workflow Intermediates cleanup attempted, but non-terminal state '%s' detected for job %s" % (job_to_check.state, job_to_check.id))
                            safe_to_delete = False
                    if safe_to_delete:
                        # Support purging here too.
                        input_dataset.mark_deleted()
        else:
            # No workflow outputs defined, so we can't know what to delete.
            # We could make this work differently in the future
            pass

    @classmethod
    def get_config_form(cls, trans):
        form = """
            p_str += "<label for='pja__"+pja.output_name+"__DeleteIntermediatesAction'>There are no additional options for this action.</label>\
                        <input type='hidden' name='pja__"+pja.output_name+"__DeleteIntermediatesAction'/>";
            """
        return get_form_template(cls.name, cls.verbose_name, form, "All non-output steps of this workflow will have datasets deleted if they are no longer being used as job inputs when the job this PostJobAction is attached to is finished.  You *must* be using workflow outputs (the snowflake) in your workflow for this to have any effect.", on_output=False)

    @classmethod
    def get_short_str(cls, pja):
        return "Delete parent datasets of this step created in this workflow that aren't flagged as outputs."


class ActionBox(object):

    actions = { "RenameDatasetAction": RenameDatasetAction,
                "HideDatasetAction": HideDatasetAction,
                "ChangeDatatypeAction": ChangeDatatypeAction,
                "ColumnSetAction": ColumnSetAction,
                "EmailAction": EmailAction,
                "DeleteIntermediatesAction": DeleteIntermediatesAction,
                }
    public_actions = ['RenameDatasetAction', 'ChangeDatatypeAction',
                      'ColumnSetAction', 'EmailAction',
                      'DeleteIntermediatesAction']
    immediate_actions = ['ChangeDatatypeAction', 'RenameDatasetAction']

    @classmethod
    def get_short_str(cls, action):
        if action.action_type in ActionBox.actions:
            return ActionBox.actions[action.action_type].get_short_str(action)
        else:
            return "Unknown Action"

    @classmethod
    def handle_incoming(cls, incoming):
        npd = {}
        for key, val in incoming.iteritems():
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
        return dumps(npd)

    @classmethod
    def get_add_list(cls):
        addlist = "<select id='new_pja_list' name='new_pja_list'>"
        for action in ActionBox.public_actions:
            addlist += "<option value='%s'>%s</option>" % (ActionBox.actions[action].name, ActionBox.actions[action].verbose_name)
        addlist += "</select>"
        return addlist

    @classmethod
    def get_forms(cls, trans):
        forms = ""
        for action in ActionBox.actions:
            forms += ActionBox.actions[action].get_config_form(trans)
        return forms

    @classmethod
    def execute(cls, app, sa_session, pja, job, replacement_dict=None):
        if pja.action_type in ActionBox.actions:
            ActionBox.actions[pja.action_type].execute(app, sa_session, pja, job, replacement_dict)
