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
    # Empty form field
    empty_field = { 'label': '', 
                    'helptext': '', 
                    'visible': True,
                    'required': False,
                    'type': BaseField.form_field_types()[0],
                    'selectlist': [],
                    'layout': 'none' }
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
        all_forms = trans.sa_session.query( trans.app.model.FormDefinitionCurrent )
        if show_filter == 'All':
            forms_list = all_forms
        elif show_filter == 'Deleted':
            forms_list = [form for form in all_forms if form.deleted]
        else:
            forms_list = [form for form in all_forms if not form.deleted]
        return trans.fill_template( '/admin/forms/manage_forms.mako', 
                                    fdc_list=forms_list,
                                    all_forms=all_forms,
                                    show_filter=show_filter,
                                    msg=msg,
                                    messagetype=messagetype )
    def __form_types_widget(self, trans, selected='none'):
        form_type_selectbox = SelectField( 'form_type_selectbox', 
                                           refresh_on_change=True, 
                                           refresh_on_change_values=[trans.app.model.FormDefinition.types.SAMPLE] )
        if selected == 'none':
            form_type_selectbox.add_option('Select one', 'none', selected=True)
        else:
            form_type_selectbox.add_option('Select one', 'none')
        for ft in trans.app.model.FormDefinition.types.items():
            if selected == ft[1]:
                form_type_selectbox.add_option(ft[1], ft[1], selected=True)
            else:
                form_type_selectbox.add_option(ft[1], ft[1])
        return form_type_selectbox
    
    @web.expose
    @web.require_admin
    def new( self, trans, **kwd ):
        params = util.Params( kwd )
        msg = util.restore_text( params.get( 'msg', ''  ) )
        messagetype = params.get( 'messagetype', 'done' )
        self.__imported_from_file = False
        if params.get( 'create_form_button', False ):   
            fd, msg = self.__save_form( trans, fdc_id=None, **kwd )
            if not fd:
                return trans.response.send_redirect( web.url_for( controller='forms',
                                                                  action='new',
                                                                  msg=msg,
                                                                  messagetype='error' ) )  
            self.__get_saved_form( fd )
            if self.__imported_from_file:
                return trans.response.send_redirect( web.url_for( controller='forms',
                                                                  action='edit',
                                                                  show_form=True,
                                                                  form_id=fd.id) )                  
            else:
                return trans.response.send_redirect( web.url_for( controller='forms',
                                                                  action='edit',
                                                                  form_id=fd.id,
                                                                  add_field_button='Add field',
                                                                  name=fd.name,
                                                                  description=fd.desc,
                                                                  form_type_selectbox=fd.type ) )  
        inputs = [ ( 'Name', TextField( 'name', 40, 'New Form' ) ),
                   ( 'Description', TextField( 'description', 40, '' ) ),
                   ( 'Type', self.__form_types_widget(trans, selected=params.get( 'form_type', 'none' )) ),
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
        fd = trans.sa_session.query( trans.app.model.FormDefinition ).get( int( util.restore_text( params.form_id ) ) )
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
        fd = trans.sa_session.query( trans.app.model.FormDefinition ).get( int( util.restore_text( params.form_id ) ) )
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
        try:
            fd = trans.sa_session.query( trans.app.model.FormDefinition ).get( int( params.get( 'form_id', None ) ) )
        except:
            return trans.response.send_redirect( web.url_for( controller='forms',
                                                              action='manage',
                                                              msg='Invalid form',
                                                              messagetype='error' ) )
        #
        # Show the form for editing
        #
        if params.get( 'show_form', False ):
            current_form = self.__get_saved_form( fd )
            return self.__show( trans=trans, form=fd, current_form=current_form, 
                                msg=msg, messagetype=messagetype, **kwd )
        #
        # Add a layout grid
        #
        elif params.get( 'add_layout_grid', False ):
            current_form = self.__get_form( trans, **kwd )
            current_form['layout'].append('')
            # show the form again
            return self.__show( trans=trans, form=fd, current_form=current_form, 
                                msg=msg, messagetype=messagetype, **kwd )
        #
        # Delete a layout grid
        #
        elif params.get( 'remove_layout_grid_button', False ):
            current_form = self.__get_form( trans, **kwd )
            index = int( kwd[ 'remove_layout_grid_button' ].split( ' ' )[2] ) - 1
            del current_form['layout'][index]
            return self.__show( trans=trans, form=fd, current_form=current_form, 
                                msg=msg, messagetype=messagetype, **kwd )
        #
        # Add a field
        #
        elif params.get( 'add_field_button', False ):
            current_form = self.__get_form( trans, **kwd )
            current_form['fields'].append( self.empty_field )
            # show the form again with one empty field
            return self.__show( trans=trans, form=fd, current_form=current_form, 
                                msg=msg, messagetype=messagetype, **kwd )
        #
        # Delete a field
        #
        elif params.get( 'remove_button', False ):
            current_form = self.__get_form( trans, **kwd )
            # find the index of the field to be removed from the remove button label
            index = int( kwd[ 'remove_button' ].split( ' ' )[2] ) - 1
            del current_form['fields'][index]
            return self.__show( trans=trans, form=fd, current_form=current_form, 
                                msg=msg, messagetype=messagetype, **kwd )
        #
        # Save changes
        #
        elif params.get( 'save_changes_button', False ):
            fd_new, msg = self.__save_form( trans, fdc_id=fd.form_definition_current.id, **kwd )
            # if validation error encountered while saving the form, show the 
            # unsaved form, with the error message
            if not fd_new:
                current_form = self.__get_form( trans, **kwd )
                return self.__show( trans=trans, form=fd, current_form=current_form, 
                                    msg=msg, messagetype='error', **kwd )
            # everything went fine. form saved successfully. Show the saved form
            fd = fd_new
            current_form = self.__get_saved_form( fd )
            msg = "The form '%s' has been updated with the changes." % fd.name
            return self.__show( trans=trans, form=fd, current_form=current_form, 
                                msg=msg, messagetype=messagetype, **kwd )
        #
        # Show form read-only
        #
        elif params.get( 'read_only', False ):           
            return trans.fill_template( '/admin/forms/show_form_read_only.mako',
                                        form=fd,
                                        msg=msg,
                                        messagetype=messagetype )
        #
        # Add SelectField option
        #
        elif 'Add' in kwd.values():
            return self.__add_selectbox_option(trans, fd, msg, messagetype, **kwd)
        #
        # Remove SelectField option
        #
        elif 'Remove' in kwd.values():
            return self.__remove_selectbox_option(trans, fd, msg, messagetype, **kwd)
        #
        # Refresh page
        #
        elif params.get( 'refresh', False ):
            current_form = self.__get_form( trans, **kwd )
            return self.__show( trans=trans, form=fd, current_form=current_form, 
                                msg=msg, messagetype=messagetype, **kwd )
            
    def __add_selectbox_option( self, trans, fd, msg, messagetype, **kwd ):
        '''
        This method adds a selectbox option. The kwd dict searched for
        the field index which needs to be removed
        '''
        current_form = self.__get_form( trans, **kwd )
        index = -1
        for k, v in kwd.items():
            if v == 'Add':
                # extract the field index from the
                # button name of format: 'addoption_<field>'
                index = int(k.split('_')[1])
                break
        if index == -1:
            # something wrong happened
            return self.__show( trans=trans, form=fd, current_form=current_form, 
                                msg='Error in adding selectfield option', 
                                messagetype='error', **kwd )
        # add an empty option
        current_form[ 'fields' ][ index ][ 'selectlist' ].append( '' )
        return self.__show( trans=trans, form=fd, current_form=current_form, 
                            msg=msg, messagetype=messagetype, **kwd )
    def __remove_selectbox_option( self, trans, fd, msg, messagetype, **kwd ):
        '''
        This method removes a selectbox option. The kwd dict searched for
        the field index and option index which needs to be removed
        '''
        current_form = self.__get_form( trans, **kwd )
        option = -1
        for k, v in kwd.items():
            if v == 'Remove':
                # extract the field & option indices from the
                # button name of format: 'removeoption_<field>_<option>'
                index = int(k.split('_')[1])
                option = int(k.split('_')[2])
                break
        if option == -1:
            # something wrong happened
            return self.__show( trans=trans, form=fd, current_form=current_form, 
                                msg='Error in removing selectfield option', 
                                messagetype='error', **kwd )
        # remove the option
        del current_form[ 'fields' ][ index ][ 'selectlist' ][ option ]
        return self.__show( trans=trans, form=fd, current_form=current_form, 
                            msg=msg, messagetype=messagetype, **kwd )

    
    def __get_field(self, index, **kwd):
        '''
        This method retrieves all the user-entered details of a field and
        returns a dict.
        '''
        params = util.Params( kwd )
        name = util.restore_text( params.get( 'field_name_%i' % index, '' ) )
        helptext = util.restore_text( params.get( 'field_helptext_%i' % index, '' ) )
        required =  params.get( 'field_required_%i' % index, False )
        field_type = util.restore_text( params.get( 'field_type_%i' % index, '' ) )
        layout = params.get( 'field_layout_%i' % index, '' )
        if field_type == 'SelectField':
            selectlist = self.__get_selectbox_options(index, **kwd)
            return {'label': name, 
                    'helptext': helptext, 
                    'visible': True,
                    'required': required,
                    'type': field_type,
                    'selectlist': selectlist,
                    'layout': layout }
        return {'label': name, 
                'helptext': helptext, 
                'visible': True,
                'required': required,
                'type': field_type,
                'layout': layout}
    def __get_selectbox_options(self, index, **kwd):
        '''
        This method gets all the options entered by the user for field when
        the fieldtype is SelectField 
        '''
        params = util.Params( kwd )
        ctr=0
        sb_options = []
        while True:
            if kwd.has_key( 'field_'+str(index)+'_option_'+str(ctr) ):
                option = params.get( 'field_'+str(index)+'_option_'+str(ctr), None ) 
                sb_options.append(util.restore_text(option))
                ctr = ctr+1
            else:
                return sb_options
    def __get_saved_form(self, fd):
        '''
        This retrieves the saved form and returns a dictionary containing the name, 
        desc, type, layout & fields of the form
        '''
        return dict(name = fd.name,
                    desc = fd.desc,
                    type = fd.type,
                    layout = list(copy.deepcopy(fd.layout)),
                    fields = list(copy.deepcopy(fd.fields)))
    def __get_form(self, trans, **kwd):
        '''
        This method gets all the user-entered form details and returns a 
        dictionary containing the name, desc, type, layout & fields of the form
        '''
        params = util.Params( kwd )
        name = util.restore_text( params.name ) 
        desc = util.restore_text( params.description ) or ""
        form_type = util.restore_text( params.form_type_selectbox )
        # get the user entered layout grids 
        layout = []
        index = 0
        while True:
            if kwd.has_key( 'grid_layout%i' % index ):
                grid_name = util.restore_text( params.get( 'grid_layout%i' % index, '' ) )
                layout.append( grid_name )
                index = index + 1
            else:
                break
        # for csv file import
        csv_file = params.get( 'file_data', '' )
        fields = []
        if csv_file == '':
            # get the user entered fields
            index = 0
            while True:
                if kwd.has_key( 'field_name_%i' % index ):
                    fields.append( self.__get_field( index, **kwd ) )
                    index = index + 1
                else:
                    break
            fields = fields
        else:
            fields, layout = self.__import_fields(trans, csv_file, form_type)
        return dict(name = name,
                    desc = desc,
                    type = form_type,
                    layout = layout,
                    fields = fields)
        
    def __import_fields(self, trans, csv_file, form_type):
        '''
        "company","name of the company", "True", "required", "TextField",,
        "due date","turnaround time", "True", "optional", "SelectField","24 hours, 1 week, 1 month"
        '''
        import csv
        fields = []
        layouts = set()
        try:
            reader = csv.reader(csv_file.file)
            if form_type == trans.app.model.FormDefinition.types.SAMPLE:
                for row in reader:
                    options = row[5].split(',')
                    fields.append({'label': row[0], 
                                   'helptext': row[1], 
                                   'visible': row[2],
                                   'required': row[3],
                                   'type': row[4],
                                   'selectlist': options,
                                   'layout':row[6]})
                    layouts.add(row[6])
            else:
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
        self.__imported_from_file = True
        return fields, list(layouts)
    def __validate_form(self, **kwd):
        '''
        This method checks the following text inputs are filled out by the user
        - the name of form
        - form type
        '''
        params = util.Params( kwd )
        # form name
        if not util.restore_text( params.name ):
            return None, 'Form name must be filled.'
        # form type
        if util.restore_text( params.form_type_selectbox ) == 'none': 
            return None, 'Form type must be selected.'        
        return True, ''
    def __save_form(self, trans, fdc_id=None, **kwd):
        '''
        This method saves the current form 
        '''
        # check the form for invalid inputs
        flag, msg = self.__validate_form(**kwd)
        if not flag:
            return None, msg
        current_form = self.__get_form( trans, **kwd )
        # validate fields
        for field in current_form[ 'fields' ]:
            if not field[ 'label' ]:
                return None, "All the field label(s) must be completed."
        # create a new form definition
        fd = trans.app.model.FormDefinition(name=current_form[ 'name' ], 
                                            desc=current_form[ 'desc' ], 
                                            fields=current_form[ 'fields' ], 
                                            form_definition_current=None, 
                                            form_type=current_form[ 'type' ], 
                                            layout=current_form[ 'layout' ] )
        if fdc_id: # save changes to the existing form    
            # change the pointer in the form_definition_current table to point 
            # to this new record
            fdc = trans.sa_session.query( trans.app.model.FormDefinitionCurrent ).get( fdc_id )
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
        def __init__(self, layout_grids, index, field=None, field_type=None):
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
            self.layout_grids = layout_grids
            if layout_grids:
                self.layout_selectbox = SelectField('field_layout_'+str(index))
                for index, grid_name in enumerate(layout_grids):
                    self.layout_selectbox.add_option("%i. %s" %(index+1, grid_name), index)            
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
            # layout
            if self.layout_grids:
                self.layout_selectbox = SelectField('field_layout_'+str(self.index))
                for i, grid_name in enumerate(self.layout_grids):
                    if field['layout'] == str(i):
                        self.layout_selectbox.add_option("%i. %s" %(i+1, grid_name), i, selected=True)
                    else:
                        self.layout_selectbox.add_option("%i. %s" %(i+1, grid_name), i)
        def selectbox_ui(self, field):
            self.selectbox_options = []
            if field['selectlist']:
                for ctr, option in enumerate(field['selectlist']):
                    self.selectbox_options.append(('Option '+str(ctr+1),
                                                   TextField('field_'+str(self.index)+'_option_'+str(ctr), 
                                                            40, option)))
        def get(self):
            if self.layout_grids:
                return [( 'Label', self.label ),
                        ( 'Help text', self.helptext ),
                        ( 'Type', self.fieldtype, self.selectbox_options),
                        ( '', self.required),
                        ( 'Select the grid layout to place this field', self.layout_selectbox)]
            return [( 'Label', self.label ),
                    ( 'Help text', self.helptext ),
                    ( 'Type', self.fieldtype, self.selectbox_options),
                    ( '', self.required)]
        def __repr__(self):
            return str(self.index)+'.'+self.label 
        def label(self):
            return str(self.index)+'.'+self.label 
        
    def __show( self, trans, form, current_form, msg='', messagetype='done', **kwd ):
        '''
        This method displays the form and any of the changes made to it,
        The empty_form param allows for this method to simulate clicking
        the "add_field_button" on the edit_form.mako page so that the page
        is displayed with the first field to be added, saving a mouse click.
        '''
        params = util.Params( kwd )
        # name & description
        form_details = [ ( 'Name', TextField( 'name', 40, current_form[ 'name' ] ) ),
                         ( 'Description', TextField( 'description', 40, current_form[ 'desc' ] ) ),
                         ( 'Type', self.__form_types_widget(trans, selected=current_form[ 'type' ]) ) ]
        form_layout = []
        if current_form[ 'type' ] == trans.app.model.FormDefinition.types.SAMPLE:
            for index, lg in enumerate(current_form[ 'layout' ]):
                form_layout.append( TextField( 'grid_layout%i' % index, 40, lg )) 
        # fields
        field_details = []
        for index, field in enumerate( current_form[ 'fields' ] ):
            if current_form['type'] == trans.app.model.FormDefinition.types.SAMPLE:
                field_ui = self.FieldUI( current_form['layout'], index, field )
            else:
                field_ui = self.FieldUI( None, index, field )
            field_details.append( field_ui.get() )
        return trans.fill_template( '/admin/forms/edit_form.mako',
                                    form_details=form_details,
                                    field_details=field_details,
                                    form=form,
                                    field_types=BaseField.form_field_types(),
                                    msg=msg,
                                    messagetype=messagetype,
                                    current_form_type=current_form[ 'type' ],
                                    layout_grids=form_layout )

# Common methods for all components that use forms
def get_all_forms( trans, all_versions=False, filter=None, form_type='All' ):
    '''
    Return all the latest forms from the form_definition_current table 
    if all_versions is set to True. Otherwise return all the versions
    of all the forms from the form_definition table.
    '''
    if all_versions:
        return trans.sa_session.query( trans.app.model.FormDefinition )
    if filter:
        fdc_list = trans.sa_session.query( trans.app.model.FormDefinitionCurrent ).filter_by( **filter )
    else:
        fdc_list = trans.sa_session.query( trans.app.model.FormDefinitionCurrent )
    if form_type == 'All':
        return [ fdc.latest_form for fdc in fdc_list ]
    else:
        return [ fdc.latest_form for fdc in fdc_list if fdc.latest_form.type == form_type ]
