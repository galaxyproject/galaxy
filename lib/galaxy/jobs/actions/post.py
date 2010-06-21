import logging, threading, time
from Queue import Queue, Empty

from galaxy.util.json import from_json_string, to_json_string

from galaxy.web.form_builder import *

log = logging.getLogger( __name__ )

# DBTODO This still needs refactoring and general cleanup.

class DefaultJobAction(object):
    name = "DefaultJobAction"

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
        

class ChangeDatatypeAction(DefaultJobAction):
    name = "ChangeDatatypeAction"

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
            if (pja.action_type == "ChangeDatatypeAction"){
                p_str = "<div class='pjaForm toolForm'><span class='action_tag' style='display:none'>"+ pja.action_type + pja.output_name + "</span><div class='toolFormTitle'>" + pja.action_type + " <br/> on " + pja.output_name + "\
    			<div style='float: right;' class='buttons'><img src='../images/delete_icon.png'></div></div>\
    			<div class='toolFormBody'><label for='pja__"+pja.output_name+"__ChangeDatatypeAction__newtype'>New Datatype:</label><select id='pja__"+pja.output_name+"__ChangeDatatypeAction__newtype' name='pja__"+pja.output_name+"__ChangeDatatypeAction__newtype'>\
		        %s\
		        </select>";
		        if (pja.action_arguments != undefined && pja.action_arguments.newtype != undefined){
                     p_str += "<scrip" + "t type='text/javascript'>$('#pja__" + pja.output_name + "__ChangeDatatypeAction__newtype').val('" + pja.action_arguments.newtype + "');</scrip" + "t>"
		        }
		        p_str += "</div><div class='toolParamHelp'>This action will change the datatype of the output to the indicated value.</div></div>";
    		}
		    """ % dt_list
            # Note the scrip + t hack above.  Is there a better way?
        return ps

class RenameDatasetAction(DefaultJobAction):
    name = "RenameDatasetAction"

    @classmethod
    def execute(cls, trans, action, job):
        for dataset_assoc in job.output_datasets:
            if action.output_name == '' or dataset_assoc.name == action.output_name:
                dataset_assoc.dataset.name = action.action_arguments['newname']

    @classmethod
    def get_config_form(cls, trans):
        return """
            if (pja.action_type == "RenameDatasetAction"){
    			p_str = "<div class='pjaForm toolForm'><span class='action_tag' style='display:none'>"+ pja.action_type + pja.output_name + "</span><div class='toolFormTitle'>"+ pja.action_type + " <br/> on " + pja.output_name + "\
    			<div style='float: right;' class='buttons'><img src='../images/delete_icon.png'></div></div><div class='toolFormBody'>";
    			if ((pja.action_arguments != undefined) && (pja.action_arguments.newname != undefined)){
    				p_str += "<label for='pja__"+pja.output_name+"__RenameDatasetAction__newname'>New output name:</label><input type='text' name='pja__"+pja.output_name+"__RenameDatasetAction__newname' value='"+pja.action_arguments.newname + "'/>";
    			}
    			else{
    				p_str += "<label for='pja__"+pja.output_name+"__RenameDatasetAction__newname'>New output name:</label><input type='text' name='pja__"+pja.output_name+"__RenameDatasetAction__newname' value='New Name'/>";
    			}
    			p_str += "</div><div class='toolParamHelp'>This action will rename the result dataset.</div></div>";
    		}
		    """

class HideDatasetAction(DefaultJobAction):
    name = "HideDatasetAction"

    @classmethod
    def execute(cls, trans, action, job):
        for dataset_assoc in job.output_datasets:
            if action.output_name == '' or dataset_assoc.name == action.output_name:
                dataset_assoc.dataset.visible=False

    @classmethod
    def get_config_form(cls, trans):
        return """
            if (pja.action_type == "HideDatasetAction"){
            	p_str = "<div class='pjaForm toolForm'><span class='action_tag' style='display:none'>"+ pja.action_type + pja.output_name + "</span><div class='toolFormTitle'>"+ pja.action_type + " <br/> on " + pja.output_name + "\
            	<div style='float: right;' class='buttons'><img src='../images/delete_icon.png'></div></div><div class='toolFormBody'>";
            	p_str += "<label for='pja__"+pja.output_name+"__HideDatasetAction'>There are no additional options for this action.</label><input type='hidden' name='pja__"+pja.output_name+"__HideDatasetAction'/>";
            	p_str += "</div><div class='toolParamHelp'>This action will *hide* the result dataset from your history.</div></div>";
            }
            """

class SetMetadataAction(DefaultJobAction):
    name = "SetMetadataAction"
    # DBTODO Setting of Metadata is currently broken and disabled.  It should not be used (yet).
    
    @classmethod
    def execute(cls, trans, action, job):
        for data in self.job.output_datasets:
            data.set_metadata( action.action_arguments['newtype'] )
            
    @classmethod
    def get_config_form(cls, trans):
        dt_list = ""
        mdict = {}
        for dtype_name, dtype_value in trans.app.datatypes_registry.datatypes_by_extension.iteritems():
            for mn, mt in dtype_value.metadata_spec.items():
                if mt.visible:
                    mdict[mt.desc] = mt.param.get_html(value= mn).replace('"', "'").strip().replace('\n','')
        for k, v in mdict.items():
            dt_list += "<p><strong>" + k + ":</strong><br/>" + v + "</p>"
        return """
            if (pja.action_type == "SetMetadataAction"){
            	p_str = "<div class='pjaForm toolForm'><span class='action_tag' style='display:none'>"+ pja.action_type + pja.output_name + "</span><div class='toolFormTitle'>"+ pja.action_type + " <br/> on " + pja.output_name + "\
            	<div style='float: right;' class='buttons'><img src='../images/delete_icon.png'></div></div>\
            	<div class='toolFormBody'>\
            	%s\
            	</div><div class='toolParamHelp'>This tool sets metadata in output.</div></div>";
            }
    		""" % dt_list

ACTIONS = { "RenameDatasetAction" : RenameDatasetAction,
            "HideDatasetAction" : HideDatasetAction,
            # "ChangeDatatypeAction": ChangeDatatypeAction, 
            # "SetMetadataAction" : SetMetadataAction, 
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
            return "Unknown PostJobAction"

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
            addlist += "<option value='%s'>%s</option>" % (ACTIONS[action].name, ACTIONS[action].name)
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
        ACTIONS[pja.action_type].execute(trans, pja, job)
