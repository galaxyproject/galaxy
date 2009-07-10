from galaxy.web.base.controller import *
from galaxy.model.orm import *
from galaxy.datatypes import sniff
from galaxy import util
import logging, os, sys
from galaxy.web.form_builder import * 
from galaxy.tools.parameters.basic import parameter_types 
from elementtree.ElementTree import XML, Element
from galaxy.util.odict import odict
import copy

log = logging.getLogger( __name__ )


class Forms( BaseController ):
    @web.expose
    @web.require_admin
    def index( self, trans, **kwd ):
        params = util.Params( kwd )
        msg = util.restore_text( params.get( 'msg', ''  ) )
        messagetype = params.get( 'messagetype', 'done' )
        return trans.fill_template( "/sample/index.mako",
                                    default_action=params.get( 'default_action', None ),
                                    msg=msg,
                                    messagetype=messagetype )
    @web.expose
    @web.require_admin
    def manage( self, trans, **kwd ):       
        params = util.Params( kwd )
        msg = util.restore_text( params.get( 'msg', ''  ) )
        messagetype = params.get( 'messagetype', 'done' )
        return self._show_forms_list(trans, msg, messagetype)
    def _show_forms_list(self, trans, msg, messagetype):
        fdc_list = trans.app.model.FormDefinitionCurrent.query().all()
        return trans.fill_template( '/admin/forms/manage_forms.mako', 
                                    fdc_list=fdc_list,
                                    deleted=False,
                                    show_deleted=False,
                                    msg=msg,
                                    messagetype=messagetype )
    def _get_all_forms(self, trans, all_versions=False):
        '''
        This method returns all the latest forms from the 
        form_definition_current table if all_versions is set to True. Otherwise
        this method return all the versions of all the forms from form_definition
        table
        '''
        if all_versions:
            return trans.app.model.FormDefinition.query().all()
        else:
            fdc_list = trans.app.model.FormDefinitionCurrent.query().all()
            return [fdc.latest_form for fdc in fdc_list]
    @web.expose
    @web.require_admin
    def new( self, trans, **kwd ):
        params = util.Params( kwd )
        msg = util.restore_text( params.get( 'msg', ''  ) )
        messagetype = params.get( 'messagetype', 'done' )   
        if params.get('new', False) and not params.get('create_form', False):
            self.current_form = {}
            self.current_form['name'] = 'New Form'
            self.current_form['desc'] = ''
            self.current_form['fields'] = []
            inputs = [ ( 'Name', TextField('name', 40,self.current_form['name'] ) ),
                       ( 'Description', TextField('description', 40, self.current_form['desc']) ) ]
            return trans.fill_template( '/admin/forms/create_form.mako', 
                                        inputs=inputs,
                                        msg=msg,
                                        messagetype=messagetype )     
        elif params.get('create_form', False) == 'True':   
            if 'submitted' in params.new:
                self.num_add_fields = 0
                fd, msg = self.__save_form(trans, params)
                self.__get_saved_form(fd)
                return self._show_forms_list(trans, msg, messagetype)
    @web.expose
    @web.require_admin
    def edit( self, trans, **kwd ):
        '''
        This callback method is for handling all the editing functions like:
        remaning fields, adding/deleting fields, changing fields attributes 
        '''
        params = util.Params( kwd )
        msg = util.restore_text( params.get( 'msg', ''  ) )
        messagetype = params.get( 'messagetype', 'done' )
        fd = trans.app.model.FormDefinition.get(int(util.restore_text( params.form_id )))
        # SHOW THE FORM FOR EDITING.
        if params.get('show_form', False) == 'True':
            self.__get_saved_form(fd)
            # the following two dicts store the unsaved select box options
            self.del_options = {}
            self.add_options = {}
            return self.__show(trans, params, fd)
        # DELETE FIELD
        elif params.get('remove_button', False):
            self.__update_current_form(params)
            index = int(params.get('remove_button', None).split(' ')[2])-1
            self.__remove_field(index)
            return self.__show(trans, params, fd)            
        # SAVE CHANGES
        elif params.get('save_changes_button', False) == 'Save':
            self.__update_current_form(params)
            fd_new, msg = self.__save_form(trans, params, fd.form_definition_current.id)
            if not fd_new:
                return self.__show(trans, params, fd, msg, 'error')
            else:
                fd = fd_new
            msg = "The form '%s' has been updated with the changes." % fd.name
            return self.__show(trans, params, fd, msg)
        #ADD A FIELD
        elif params.get('add_field_button', False) == 'Add field':
            self.__update_current_form(params)
            self.__add_field()
            # show the form again with one empty field
            return self.__show(trans, params, fd)
        # SHOW FORM READ ONLY
        elif params.get('read_only', False):           
            return trans.fill_template( '/admin/forms/show_form_read_only.mako',
                                        form=fd,
                                        msg=msg,
                                        messagetype=messagetype )
        # REFRESH PAGE, SelectField is selected/deselected as the type of a field
        elif params.get('refresh', False) == 'true':
            self.__update_current_form(params)
            return self.__show(trans, params, fd)
        # REMOVE SelectField OPTION
        elif params.get('select_box_options', False) == 'remove':
            #self.__update_current_form(params)
            index = int(params.get( 'field_index', None ))
            option = int(params.get( 'option_index', None ))
            del self.current_form['fields'][index]['selectlist'][option]
            return self.__show(trans, params, fd)
        # ADD SelectField OPTION
        elif params.get('select_box_options', False) == 'add':
            #self.__update_current_form(params)
            index = int(params.get( 'field_index', None ))
            self.current_form['fields'][index]['selectlist'].append('')
            return self.__show(trans, params, fd)           
    def __remove_field(self, index):
        del self.current_form['fields'][index]
    def __add_field(self):
        '''
        add an empty field to the fields list
        '''
        empty_field = { 'label': '', 
                        'helptext': '', 
                        'visible': True,
                        'required': False,
                        'type': BaseField.form_field_types()[0],
                        'selectlist': '' }
        self.current_form['fields'].append(empty_field)
    def __get_field(self, params, index):
        name = util.restore_text( params.get( 'field_name_%i' % index, None ) )
        helptext = util.restore_text( params.get( 'field_helptext_%i' % index, None ) )
        required = util.restore_text( params.get( 'field_required_%i' % index, False ) )
        field_type = util.restore_text( params.get( 'field_type_%i' % index, None ) )
        if field_type == 'SelectField':
            selectlist = self.__get_selectbox_options(params, index)
        else:
            selectlist = None
        return {'label': name, 
                'helptext': helptext, 
                'visible': True,
                'required': required,
                'type': field_type,
                'selectlist': selectlist }
    def __get_selectbox_options(self, params, index):
        '''
        This method gets all the options entered by the user for field when
        the fieldtype is SelectField 
        '''
        ctr=0
        sb_options = []
        while True:
            option = util.restore_text( params.get( 'field_'+str(index)+'_option_'+str(ctr), None ) )
            ctr = ctr+1
            if option:
                sb_options.append(option)
            else:
                return sb_options
    def __get_saved_form(self, fd):
        self.current_form = {}
        self.current_form['name'] = fd.name
        self.current_form['desc'] = fd.desc
        self.current_form['fields'] = list(copy.deepcopy(fd.fields))
    def __validate_form(self, params):
        '''
        This method checks the following text inputs are filled out by the user
        - the name of form
        - name of all the fields
        '''
        # form name
        if not util.restore_text( params.name ):
            return None, 'Form name must be filled.'
        # fields
        for i in range( len(self.current_form['fields']) ):
            if not util.restore_text(params.get( 'field_name_%i' % i, None )):
                return None, "All the field label(s) must be completed."
        return True, ''
    def __get_form(self, params):
        name = util.restore_text( params.name ) 
        desc = util.restore_text( params.description ) or ""
        # set form fields
        fields = []
        for i in range( len(self.current_form['fields']) ):
            fields.append(self.__get_field(params, i))
        fields = fields
        return name, desc, fields
    def __update_current_form(self, params):
        name, desc, fields = self.__get_form(params)
        self.current_form = {}
        self.current_form['name'] = name
        self.current_form['desc'] = desc
        self.current_form['fields'] = fields
        
    def __save_form(self, trans, params, fdc_id=None):
        '''
        This method saves the current form 
        '''
        # check the form for invalid inputs
        flag, msg = self.__validate_form(params)
        if not flag:
            return None, msg
        fd = trans.app.model.FormDefinition()
        fd.name, fd.desc, fd.fields = self.__get_form(params)
        if fdc_id: # save changes to the existing form    
            # change the pointer in the form_definition_current table to point 
            # to this new record
            fdc = trans.app.model.FormDefinitionCurrent.get(fdc_id)
        else: # create a new form
            fdc = trans.app.model.FormDefinitionCurrent()
        # create corresponding row in the form_definition_current table
        fd.form_definition_current = fdc
        fdc.latest_form = fd
        trans.sa_session.save_or_update( fdc )
        trans.sa_session.flush()
        msg = "The new form named '%s' has been created. " % (fd.name)
        request_types = trans.app.model.RequestType.query().all()
        if not request_types:
            msg = msg + "Now you can create requests to associate with this form."
        return fd, msg
    
    class FieldUI(object):
        def __init__(self, index, field=None, field_type=None):
            '''
            This method returns a list of widgets which describes a field. This 
            includes label, helptext, type, & required/optional
            '''
            self.index = index
            self.label = TextField('field_name_'+str(index), 40, '')
            self.helptext = TextField('field_helptext_'+str(index), 40, '')
            self.fieldtype = SelectField('field_type_'+str(index), 
                                         refresh_on_change=True, 
                                         refresh_on_change_values=['SelectField'])
            self.selectbox_options = []
            for ft in BaseField.form_field_types():
                self.fieldtype.add_option(ft, ft)
            self.required = SelectField('field_required_'+str(index), display='radio')
            self.required.add_option('Required', 'true')
            self.required.add_option('Optional', 'true', selected=True)
            if field:
                self.fill(field, field_type)
        def fill(self, field, field_type=None):
            # label
            self.label.value = field['label']
            # helptext
            self.helptext.value = field['helptext']
            # type
            self.fieldtype = SelectField('field_type_'+str(self.index), 
                                         refresh_on_change=True, 
                                         refresh_on_change_values=['SelectField'])
            if field_type:
                field['type'] = unicode(field_type)
            if field_type == 'SelectField' and not field['selectlist']:
                field['selectlist'] = ['', '']
            for ft in BaseField.form_field_types():
                if ft == field['type']:
                    self.fieldtype.add_option(ft, ft, selected=True)
                    if ft == 'SelectField':
                        self.selectbox_ui(field)
                else:
                    self.fieldtype.add_option(ft, ft)
            # required/optional
            if field['required']:
                self.required = SelectField('required_'+str(self.index), display='radio')
                self.required.add_option('Required', 'true', selected=True)
                self.required.add_option('Optional', 'true')
        def selectbox_ui(self, field):
            self.selectbox_options = []
            if field['selectlist']:
                for ctr, option in enumerate(field['selectlist']):
                    self.selectbox_options.append(('Option '+str(ctr+1),
                                                   TextField('field_'+str(self.index)+'_option_'+str(ctr), 
                                                            40, option)))
        def get(self):
            return [( 'Label', self.label ),
                    ( 'Help text', self.helptext ),
                    ( 'Type', self.fieldtype, self.selectbox_options),
                    ( '', self.required)]
        def __repr__(self):
            return str(self.index)+'.'+self.label 
        def label(self):
            return str(self.index)+'.'+self.label 
        
    def __show(self, trans, params, form, msg=None, messagetype='done'):
        '''
        This method displays the form and any of the changes made to it
        '''
        # name & description
        form_details = [ ( 'Name', TextField('name', 40, self.current_form['name']) ),
                         ( 'Description', TextField('description', 40, self.current_form['desc']) ) ]
        # fields
        field_details = []
        for index, field in enumerate(self.current_form['fields']):
            field_ui = self.FieldUI(index, field)
            field_details.append( field_ui.get() )
        return trans.fill_template( '/admin/forms/edit_form.mako',
                                    form_details=form_details,
                                    field_details=field_details,
                                    form=form,
                                    field_types=BaseField.form_field_types(),
                                    msg=msg,
                                    messagetype=messagetype )
