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
        show_filter = params.get( 'show_filter', 'Active' )
        return self._show_forms_list(trans, msg, messagetype, show_filter)
    def _show_forms_list(self, trans, msg, messagetype, show_filter='Active'):
        fdc_list = trans.app.model.FormDefinitionCurrent.query().all()
        if show_filter == 'All':
            forms_list = fdc_list
        elif show_filter == 'Deleted':
            forms_list = [form for form in fdc_list if form.deleted]
        else:
            forms_list = [form for form in fdc_list if not form.deleted]
        return trans.fill_template( '/admin/forms/manage_forms.mako', 
                                    fdc_list=forms_list,
                                    show_filter=show_filter,
                                    msg=msg,
                                    messagetype=messagetype )
    @web.expose
    @web.require_admin
    def new( self, trans, **kwd ):
        params = util.Params( kwd )
        msg = util.restore_text( params.get( 'msg', ''  ) )
        messagetype = params.get( 'messagetype', 'done' )
        if params.get( 'create_form_button', False ):   
            fd, msg = self.__save_form( trans, fdc_id=None, **kwd )
            self.__get_saved_form( fd )
            return trans.response.send_redirect( web.url_for( controller='forms',
                                                              action='edit',
                                                              form_id=fd.id,
                                                              show_form=True ) )  
        self.current_form = {}
        self.current_form[ 'name' ] = 'New Form'
        self.current_form[ 'desc' ] = ''
        self.current_form[ 'fields' ] = []
        inputs = [ ( 'Name', TextField( 'name', 40, self.current_form[ 'name' ] ) ),
                   ( 'Description', TextField( 'description', 40, self.current_form[ 'desc' ] ) ),
                   ( 'Import from csv file (Optional)', FileField( 'file_data', 40, '' ) ) ]
        return trans.fill_template( '/admin/forms/create_form.mako', 
                                    inputs=inputs,
                                    msg=msg,
                                    messagetype=messagetype )     
    @web.expose
    @web.require_admin
    def delete( self, trans, **kwd ):
        params = util.Params( kwd )
        msg = util.restore_text( params.get( 'msg', ''  ) )
        messagetype = params.get( 'messagetype', 'done' )
        fd = trans.app.model.FormDefinition.get(int(util.restore_text( params.form_id )))
        fd.form_definition_current.deleted = True
        fd.form_definition_current.flush()
        return self._show_forms_list(trans, 
                                     msg='The form definition named %s is deleted.' % fd.name, 
                                     messagetype='done')
    @web.expose
    @web.require_admin
    def undelete( self, trans, **kwd ):
        params = util.Params( kwd )
        msg = util.restore_text( params.get( 'msg', ''  ) )
        messagetype = params.get( 'messagetype', 'done' )
        fd = trans.app.model.FormDefinition.get(int(util.restore_text( params.form_id )))
        fd.form_definition_current.deleted = False
        fd.form_definition_current.flush()
        return self._show_forms_list(trans, 
                                     msg='The form definition named %s is undeleted.' % fd.name, 
                                     messagetype='done')
    @web.expose
    @web.require_admin
    def edit( self, trans, **kwd ):
        '''
        This callback method is for handling all the editing functions like
        renaming fields, adding/deleting fields, changing fields attributes.
        '''
        params = util.Params( kwd )
        msg = util.restore_text( params.get( 'msg', ''  ) )
        messagetype = params.get( 'messagetype', 'done' )
        form_id = params.get( 'form_id', None )
        if not form_id:
            msg = 'Invalid form id %s' % str( form_id )
            trans.response.send_redirect( web.url_for( controller='forms',
                                                       action='manage',
                                                       msg=msg,
                                                       messagetype='error' ) )
        fd = trans.app.model.FormDefinition.get( int( params.form_id ) )
        # Show the form for editing
        if params.get( 'show_form', False ):
            self.__get_saved_form( fd )
            # The following two dicts store the unsaved select box options
            self.del_options = {}
            self.add_options = {}
            if fd.fields:
                return self.__show( trans=trans, form=fd, msg=msg, messagetype=messagetype, **kwd )
            else:
                # If the form is empty, we'll simulate a click on the add_field_button so the
                # form will be displayed with the field choice, saving a mouse click.
                return self.__show( trans=trans, form=fd, msg=msg, messagetype=messagetype, empty_form=True, **kwd )
        # Delete a field
        elif params.get( 'remove_button', False ):
            self.__update_current_form( trans, **kwd )
            index = int( kwd[ 'remove_button' ].split( ' ' )[2] ) - 1
            self.__remove_field( index )
            return self.__show( trans=trans, form=fd, msg=msg, messagetype=messagetype, **kwd )          
        # Save changes
        elif params.get( 'save_changes_button', False ):
            self.__update_current_form( trans, **kwd )
            fd_new, msg = self.__save_form( trans, fd.form_definition_current.id, **kwd )
            if not fd_new:
                return self.__show( trans=trans, form=fd, msg=msg, messagetype='error', **kwd )
            else:
                fd = fd_new
            msg = "The form '%s' has been updated with the changes." % fd.name
            return self.__show( trans=trans, form=fd, msg=msg, messagetype=messagetype, **kwd )
        #Add a field
        elif params.get( 'add_field_button', False ):
            self.__update_current_form( trans, **kwd )
            self.__add_field()
            # show the form again with one empty field
            return self.__show( trans=trans, form=fd, msg=msg, messagetype=messagetype, **kwd )
        # Show form read-only
        elif params.get( 'read_only', False ):           
            return trans.fill_template( '/admin/forms/show_form_read_only.mako',
                                        form=fd,
                                        msg=msg,
                                        messagetype=messagetype )
        # Refresh page, SelectField is selected/deselected as the type of a field
        elif params.get( 'refresh', False ):
            self.__update_current_form( trans, **kwd )
            return self.__show( trans=trans, form=fd, msg=msg, messagetype=messagetype, **kwd )
        # Remove SelectField option
        elif params.get( 'select_box_options', False ) == 'remove':
            index = int( kwd[ 'field_index' ] )
            option = int( kwd[ 'option_index' ] )
            del self.current_form[ 'fields' ][ index ][ 'selectlist' ][ option ]
            return self.__show( trans=trans, form=fd, msg=msg, messagetype=messagetype, **kwd )
        # Add SelectField option
        elif params.get( 'select_box_options', False ) == 'add':
            index = int( kwd[ 'field_index' ] )
            self.current_form[ 'fields' ][ index ][ 'selectlist' ].append( '' )
            return self.__show( trans=trans, form=fd, msg=msg, messagetype=messagetype, **kwd )           
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
                        'selectlist': [] }
        self.current_form['fields'].append(empty_field)
    def __get_field(self, index, **kwd):
        params = util.Params( kwd )
        #TODO: RC this needs to be handled so that it does not throw an exception.
        # To reproduce, create a new form, click the "add field" button, click the
        # browser back arrow, then click the "add field" button again.
        # You should never attempt to "restore_text()" on a None object...
        name = util.restore_text( params.get( 'field_name_%i' % index, '' ) )
        helptext = util.restore_text( params.get( 'field_helptext_%i' % index, '' ) )
        required =  params.get( 'field_required_%i' % index, False )
        field_type = util.restore_text( params.get( 'field_type_%i' % index, '' ) )
        if field_type == 'SelectField':
            selectlist = self.__get_selectbox_options(index, **kwd)
            return {'label': name, 
                    'helptext': helptext, 
                    'visible': True,
                    'required': required,
                    'type': field_type,
                    'selectlist': selectlist }
        return {'label': name, 
                'helptext': helptext, 
                'visible': True,
                'required': required,
                'type': field_type}
    def __get_selectbox_options(self, index, **kwd):
        '''
        This method gets all the options entered by the user for field when
        the fieldtype is SelectField 
        '''
        params = util.Params( kwd )
        ctr=0
        sb_options = []
        while True:
            option = params.get( 'field_'+str(index)+'_option_'+str(ctr), None ) 
            ctr = ctr+1
            if option:
                sb_options.append(util.restore_text(option))
            else:
                return sb_options
    def __get_saved_form(self, fd):
        self.current_form = {}
        self.current_form['name'] = fd.name
        self.current_form['desc'] = fd.desc
        self.current_form['fields'] = list(copy.deepcopy(fd.fields))
    def __validate_form(self, **kwd):
        '''
        This method checks the following text inputs are filled out by the user
        - the name of form
        - name of all the fields
        '''
        params = util.Params( kwd )
        # form name
        if not util.restore_text( params.name ):
            return None, 'Form name must be filled.'
        # fields
        for i in range( len(self.current_form['fields']) ):
            if not util.restore_text(params.get( 'field_name_%i' % i, None )):
                return None, "All the field label(s) must be completed."
        return True, ''
    def __get_form(self, trans, **kwd):
        params = util.Params( kwd )
        name = util.restore_text( params.name ) 
        desc = util.restore_text( params.description ) or ""
        csv_file = params.get( 'file_data', '' )
        if csv_file == '':
            # set form fields
            fields = []
            for i in range( len(self.current_form['fields']) ):
                fields.append(self.__get_field(i, **kwd))
            fields = fields
        else:
            fields = self.__import_fields(trans, csv_file)
        return name, desc, fields
    def __update_current_form(self, trans, **kwd):
        name, desc, fields = self.__get_form(trans, **kwd)
        self.current_form = {}
        self.current_form['name'] = name
        self.current_form['desc'] = desc
        self.current_form['fields'] = fields
        
    def __import_fields(self, trans, csv_file):
        '''
        "company","name of the company", "True", "required", "TextField",,
        "due date","turnaround time", "True", "optional", "SelectField","24 hours, 1 week, 1 month"
        '''
        import csv
        fields = []
        try:
            reader = csv.reader(csv_file.file)
            for row in reader:
                options = row[5].split(',')
                fields.append({'label': row[0], 
                               'helptext': row[1], 
                               'visible': row[2],
                               'required': row[3],
                               'type': row[4],
                               'selectlist': options})
        except:
            return trans.response.send_redirect( web.url_for( controller='forms',
                                                              action='new',
                                                              status='error',
                                                              message='Error in importing <b>%s</b> file' % csv_file,
                                                              **kwd))
        return fields

    def __save_form(self, trans, fdc_id=None, **kwd):
        '''
        This method saves the current form 
        '''
        # check the form for invalid inputs
        flag, msg = self.__validate_form(**kwd)
        if not flag:
            return None, msg
        fd = trans.app.model.FormDefinition()
        fd.name, fd.desc, fd.fields = self.__get_form(trans, **kwd)
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
            self.required.add_option('Required', 'required')
            self.required.add_option('Optional', 'optional', selected=True)
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
            if field['required'] == 'required':
                self.required = SelectField('field_required_'+str(self.index), display='radio')
                self.required.add_option('Required', 'required', selected=True)
                self.required.add_option('Optional', 'optional')
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
        
    def __show( self, trans, form, msg='', messagetype='done', empty_form=False, **kwd ):
        '''
        This method displays the form and any of the changes made to it,
        The empty_form param allows for this method to simulate clicking
        the "add_field_button" on the edit_form.mako page so that the page
        is displayed with the first field to be added, saving a mouse click.
        '''
        if empty_form:
            # Send params that will simulate a button click on the add_field_button
            # button on edit_form.mako.
            param_dict = { 'form_id' : str( form.id ),
                           'num_fields' : '0',
                           'refresh' : 'true',
                           'name' : form.name,
                           'description' : form.desc,
                           'add_field_button' : 'Add field' }
            self.edit( trans, **param_dict )
        params = util.Params( kwd )
        # name & description
        form_details = [ ( 'Name', TextField( 'name', 40, self.current_form[ 'name' ] ) ),
                         ( 'Description', TextField( 'description', 40, self.current_form[ 'desc' ] ) ) ]
        # fields
        field_details = []
        for index, field in enumerate( self.current_form[ 'fields' ] ):
            field_ui = self.FieldUI( index, field )
            field_details.append( field_ui.get() )
        return trans.fill_template( '/admin/forms/edit_form.mako',
                                    form_details=form_details,
                                    field_details=field_details,
                                    form=form,
                                    field_types=BaseField.form_field_types(),
                                    msg=msg,
                                    messagetype=messagetype )

# Common methods for all components that use forms
def get_all_forms( trans, all_versions=False, filter=None ):
    '''
    Return all the latest forms from the form_definition_current table 
    if all_versions is set to True. Otherwise return all the versions
    of all the forms from the form_definition table.
    
    TODO: when we add the concept of a form_definition_type ( e.g., 
    'request_header', 'request_sample', 'library_template' ), filter
    the query if received filter is not None.
    '''
    if all_versions:
        return trans.app.model.FormDefinition.query().all()
    if filter:
        fdc_list = trans.app.model.FormDefinitionCurrent.query().filter_by(**filter)
    else:
        fdc_list = trans.app.model.FormDefinitionCurrent.query().all()
    return [ fdc.latest_form for fdc in fdc_list ]


def get_form_widgets( trans, form, contents=[], **kwd ):
    '''
    Return the list of widgets that comprise a form definition,
    including field contents if any.
    '''
    params = util.Params( kwd )
    widgets = []
    for index, field in enumerate( form.fields ):
        field_name = 'field_%i' % index
        # determine the value of the field
        if field_name in kwd:
            # the user had already filled out this field and the same form is re-rendered 
            # due to some reason like required fields have been left out.
            if field[ 'type' ] == 'CheckboxField':
                value = CheckboxField.is_checked( util.restore_text( params.get( field_name, False ) ) )
            else:
                value = util.restore_text( params.get( field_name, ''  ) )
        elif contents:
            # this field has a saved value
            value = str(contents[ index ])
        else:
            # if none of the above, then leave the field empty
            if field[ 'type' ] == 'CheckboxField':
                # Since we do not have contents, set checkbox value to False
                value = False
            else:
                # Set other field types to empty string
                value = ''
        # create the field widget
        field_widget = eval( field[ 'type' ] )( field_name )
        if field[ 'type' ] == 'TextField':
            field_widget.set_size( 40 )
            field_widget.value = value
        elif field[ 'type' ] == 'TextArea':
            field_widget.set_size( 3, 40 )
            field_widget.value = value
        elif field['type'] == 'AddressField':
            field_widget.user = trans.user
            field_widget.value = value
            field_widget.params = params
        elif field[ 'type' ] == 'SelectField':
            for option in field[ 'selectlist' ]:
                if option == value:
                    field_widget.add_option( option, option, selected=True )
                else:
                    field_widget.add_option( option, option )
        elif field[ 'type' ] == 'CheckboxField':
            field_widget.checked = value
        if field[ 'required' ] == 'required':
            req = 'Required'
        else:
            req = 'Optional'
        widgets.append( dict( label=field[ 'label' ],
                              widget=field_widget,
                              helptext='%s (%s)' % ( field[ 'helptext' ], req ) ) )
    return widgets
