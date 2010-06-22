import logging, threading, time
from Queue import Queue, Empty

from galaxy.util.json import from_json_string, to_json_string

from galaxy.web.form_builder import *


#  For email notification PJA
from email.MIMEText import MIMEText
import smtplib

log = logging.getLogger( __name__ )

# DBTODO This still needs refactoring and general cleanup.

def get_form_template(action_type, title, content, help, on_output = True ):
    if on_output:
        form = """
            if (pja.action_type == "%s"){
            	p_str = "<div class='pjaForm toolForm'><span class='action_tag' style='display:none'>"+ pja.action_type + pja.output_name + "</span><div class='toolFormTitle'> %s <br/> on " + pja.output_name + "\
            	<div style='float: right;' class='buttons'><img src='../images/delete_icon.png'></div></div><div class='toolFormBody'>";
                %s
                p_str += "</div><div class='toolParamHelp'>%s</div></div>";
            }""" % (action_type, title, content, help)
    else:
    	form =  """
            if (pja.action_type == "%s"){
            	p_str = "<div class='pjaForm toolForm'><span class='action_tag' style='display:none'>"+ pja.action_type + "</span><div class='toolFormTitle'> %s \
            	<div style='float: right;' class='buttons'><img src='../images/delete_icon.png'></div></div><div class='toolFormBody'>";
                %s
                p_str += "</div><div class='toolParamHelp'>%s</div></div>";
            }""" % (action_type, title, content, help)
    return form

# def get_field(action, argument, i_type, label = None):
#     fstr = ''
#     fname = """pja__"+pja.output_name+"__%s__%s""" % (action, argument)
#     if label:
#         fstr += """<label for='pja__"+pja.output_name+"__ColumnSetAction__chromCol'>Chrom Column</label>"""
#     fstr += """<input type='text' value=" + chromCol + " name='pja__"+pja.output_name+"__ColumnSetAction__chromCol'/>"""

class DefaultJobAction(object):
    name = "DefaultJobAction"
    verbose_name = "Default Job"

    @classmethod
    def execute(cls, job):
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
    name = "EmailAction"
    verbose_name = "Email Notification"
    @classmethod
    def execute(cls, trans, action, job):
        smtp_server = trans.app.config.smtp_server
        if smtp_server is None:
            return trans.show_error_message( "Mail is not configured for this galaxy instance, workflow action aborted." )
        # Build the email message
        msg = MIMEText( "Your job '%s' at Galaxy instance %s is complete as of %s." % (job.history.name, trans.request.host, job.update_time))
        msg[ 'To' ] = job.user.email
        msg[ 'From' ] = job.user.email
        msg[ 'Subject' ] = "Galaxy workflow step notification '%s'"
        try:
            s = smtplib.SMTP()
            s.connect( smtp_server )
            s.sendmail( frm, [ to ], msg.as_string() )
            s.close()
            return trans.show_ok_message( "Your error report has been sent" )
        except Exception, e:
            return trans.show_error_message( "An error occurred sending the report by email: %s" % str( e ) )

    @classmethod
    def get_config_form(cls, trans):
        form = """
        	p_str += "<label for='pja__"+pja.output_name+"__EmailAction'>There are no additional options for this action.  You will be emailed upon job completion.</label>\
        	            <input type='hidden' name='pja__"+pja.output_name+"__EmailAction'/>";
            """
        return get_form_template(cls.name, cls.verbose_name, form, "This action will send an email notifying you when the job is done.", on_output = False)


class ChangeDatatypeAction(DefaultJobAction):
    name = "ChangeDatatypeAction"
    verbose_name = "Change Datatype"
    @classmethod
    def execute(cls, trans, action, job):
        for dataset_assoc in job.output_datasets:
            if action.output_name == '' or dataset_assoc.name == action.output_name:
                trans.app.datatypes_registry.change_datatype( dataset_assoc.dataset, action.action_arguments['newtype'])

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
	        if (pja.action_arguments != undefined && pja.action_arguments.newtype != undefined){
                 p_str += "<scrip" + "t type='text/javascript'>$('#pja__" + pja.output_name + "__ChangeDatatypeAction__newtype').val('" + pja.action_arguments.newtype + "');</scrip" + "t>";
	        }
		    """ % dt_list
            # Note the scrip + t hack above.  Is there a better way?
        return get_form_template(cls.name, cls.verbose_name, ps, 'This action will change the datatype of the output to the indicated value.')

class RenameDatasetAction(DefaultJobAction):
    name = "RenameDatasetAction"
    verbose_name = "Rename Dataset"
    
    @classmethod
    def execute(cls, trans, action, job):
        for dataset_assoc in job.output_datasets:
            if action.output_name == '' or dataset_assoc.name == action.output_name:
                dataset_assoc.dataset.name = action.action_arguments['newname']

    @classmethod
    def get_config_form(cls, trans):
        form = """
			if ((pja.action_arguments != undefined) && (pja.action_arguments.newname != undefined)){
				p_str += "<label for='pja__"+pja.output_name+"__RenameDatasetAction__newname'>New output name:</label>\
				          <input type='text' name='pja__"+pja.output_name+"__RenameDatasetAction__newname' value='"+pja.action_arguments.newname + "'/>";
			}
			else{
				p_str += "<label for='pja__"+pja.output_name+"__RenameDatasetAction__newname'>New output name:</label>\
				          <input type='text' name='pja__"+pja.output_name+"__RenameDatasetAction__newname' value=''/>";
			}
		    """
        return get_form_template(cls.name, cls.verbose_name, form, "This action will rename the result dataset.")

class HideDatasetAction(DefaultJobAction):
    name = "HideDatasetAction"
    verbose_name = "Hide Dataset"
    
    @classmethod
    def execute(cls, trans, action, job):
        for dataset_assoc in job.output_datasets:
            if action.output_name == '' or dataset_assoc.name == action.output_name:
                dataset_assoc.dataset.visible=False

    @classmethod
    def get_config_form(cls, trans):
        form = """
        	p_str += "<label for='pja__"+pja.output_name+"__HideDatasetAction'>There are no additional options for this action.</label>\
        	            <input type='hidden' name='pja__"+pja.output_name+"__HideDatasetAction'/>";
            """
        return get_form_template(cls.name, cls.verbose_name, form, "This action will rename the result dataset.")

class DeleteDatasetAction(DefaultJobAction):
    # This is disabled for right now.  Deleting a dataset in the middle of a workflow causes errors (obviously) for the subsequent steps using the data.
    name = "DeleteDatasetAction"
    verbose_name = "Delete Dataset"

    @classmethod
    def execute(cls, trans, action, job):
        for dataset_assoc in job.output_datasets:
            if action.output_name == '' or dataset_assoc.name == action.output_name:
                dataset_assoc.dataset.deleted=True

    @classmethod
    def get_config_form(cls, trans):
        form = """
        	p_str += "<label for='pja__"+pja.output_name+"__DeleteDatasetAction'>There are no additional options for this action.  This dataset will be marked deleted.</label>\
        	            <input type='hidden' name='pja__"+pja.output_name+"__DeleteDatasetAction'/>";
            """
        return get_form_template(cls.name, cls.verbose_name, form, "This action will rename the result dataset.")


class ColumnSetAction(DefaultJobAction):
    name = "ColumnSetAction"
    verbose_name = "Assign Columns"
    @classmethod
    def execute(cls, trans, action, job):
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
            var chrom_col = ''
            if (pja.action_arguments != undefined){
                (pja.action_arguments.chromCol == undefined) ? chromCol = "" : chromCol=pja.action_arguments.chromCol;
                (pja.action_arguments.startCol == undefined) ? startCol = "" : startCol=pja.action_arguments.startCol;
                (pja.action_arguments.endCol == undefined) ? endCol = "" : endCol=pja.action_arguments.endCol;
                (pja.action_arguments.strandCol == undefined) ? strandCol = "" : strandCol=pja.action_arguments.strandCol;
                (pja.action_arguments.nameCol == undefined) ? nameCol = "" : nameCol=pja.action_arguments.nameCol;
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


class SetMetadataAction(DefaultJobAction):
    name = "SetMetadataAction"
    # DBTODO Setting of Metadata is currently broken and disabled.  It should not be used (yet).
    
    @classmethod
    def execute(cls, trans, action, job):
        for data in self.job.output_datasets:
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

ACTIONS = { "RenameDatasetAction" : RenameDatasetAction,
            "HideDatasetAction" : HideDatasetAction,
            "ChangeDatatypeAction": ChangeDatatypeAction, 
            "ColumnSetAction" : ColumnSetAction,
            "EmailAction" : EmailAction,
            # "SetMetadataAction" : SetMetadataAction,
            # "DeleteDatasetAction" : DeleteDatasetAction,
             }
            
class ActionBox(object):
    @classmethod
    def execute(cls, action, job):
        if action.action_type in ACTIONS:
            ACTIONS[action.action_type].execute(action, job, trans)
        else:
            return False
    
    @classmethod
    def get_short_str(cls, action):
        if action.action_type in ACTIONS:
            return ACTIONS[action.action_type].get_short_str(action)
        else:
            return "Unknown Action"

    @classmethod
    def handle_incoming(cls, incoming):
        npd = {}
        for key, val in incoming.iteritems():
            if key.startswith('pja'):
                sp = key.split('__')
                # flag / output_name / pjatype / desc
                if not sp[2] in npd:
                    npd[sp[2]] = {'action_type' : sp[2],
                                  'output_name' : sp[1],
                                  'action_arguments' : {}}
                if len(sp) > 3:
                    if sp[3] == 'output_name':
                        npd[sp[2]]['output_name'] = val
                    else:
                        npd[sp[2]]['action_arguments'][sp[3]] = val
            else:
                # Not pja stuff.
                pass
        return to_json_string(npd)
            
    @classmethod
    def get_add_list(cls):
        addlist = "<select id='new_pja_list' name='new_pja_list'>"
        for action in ACTIONS:
            addlist += "<option value='%s'>%s</option>" % (ACTIONS[action].name, ACTIONS[action].verbose_name)
        addlist += "</select>"
        return addlist
        
    @classmethod
    def get_forms(cls, trans):
        forms = ""
        for action in ACTIONS:
            forms += ACTIONS[action].get_config_form(trans)
        return forms
    
    @classmethod
    def execute(cls, trans, pja, job):
        if ACTIONS.has_key(pja.action_type):
            ACTIONS[pja.action_type].execute(trans, pja, job)
