from galaxy.web.base.controller import *
from galaxy.model.orm import *
from galaxy.datatypes import sniff
from galaxy import model, util
import logging, os, sys
from galaxy.web.form_builder import *
from galaxy.tools.parameters.basic import parameter_types
from elementtree.ElementTree import XML, Element
from galaxy.util.odict import odict
import copy
from galaxy.web.framework.helpers import time_ago, iff, grids

log = logging.getLogger( __name__ )

VALID_FIELDNAME_RE = re.compile( "^[a-zA-Z0-9\_]+$" )

class FormsGrid( grids.Grid ):
    # Custom column types
    class NameColumn( grids.TextColumn ):
        def get_value(self, trans, grid, form):
            return form.latest_form.name
    class DescriptionColumn( grids.TextColumn ):
        def get_value(self, trans, grid, form):
            return form.latest_form.desc
    class TypeColumn( grids.TextColumn ):
        def get_value(self, trans, grid, form):
            return form.latest_form.type
    # Grid definition
    title = "Forms"
    template = "admin/forms/grid.mako"
    model_class = model.FormDefinitionCurrent
    default_sort_key = "-create_time"
    num_rows_per_page = 50
    preserve_state = True
    use_paging = True
    default_filter = dict( deleted="False" )
    columns = [
        NameColumn( "Name",
                    key="name",
                    model_class=model.FormDefinition,
                    link=( lambda item: iff( item.deleted, None, dict( operation="view_latest_form_definition",
                                                                       id=item.id ) ) ),
                    attach_popup=True,
                    filterable="advanced" ),
        DescriptionColumn( "Description",
                           key='desc',
                           model_class=model.FormDefinition,
                           filterable="advanced" ),
        TypeColumn( "Type" ),
        grids.DeletedColumn( "Deleted",
                       key="deleted",
                       visible=False,
                       filterable="advanced" )
    ]
    columns.append( grids.MulticolFilterColumn( "Search",
                                                cols_to_filter=[ columns[0], columns[1] ],
                                                key="free-text-search",
                                                visible=False,
                                                filterable="standard" ) )
    operations = [
        grids.GridOperation( "Edit", allow_multiple=False, condition=( lambda item: not item.deleted )  ),
        grids.GridOperation( "Delete", allow_multiple=True, condition=( lambda item: not item.deleted )  ),
        grids.GridOperation( "Undelete", condition=( lambda item: item.deleted ) ),
    ]
    global_actions = [
        grids.GridAction( "Create new form", dict( controller='forms', action='create_form_definition' ) )
    ]
    
    def build_initial_query( self, trans, **kwargs ):
        return trans.sa_session.query( self.model_class ).join (model.FormDefinition, self.model_class.latest_form_id == model.FormDefinition.id)

class Forms( BaseUIController ):
    # Empty TextField
    empty_field = { 'name': '',
                    'label': '',
                    'helptext': '',
                    'visible': True,
                    'required': False,
                    'type': model.TextField.__name__,
                    'selectlist': [],
                    'layout': 'none',
                    'default': '' }
    forms_grid = FormsGrid()

    @web.expose
    @web.require_admin
    def browse_form_definitions( self, trans, **kwd ):
        if 'operation' in kwd:
            operation = kwd['operation'].lower()
            if not kwd.get( 'id', None ):
                return trans.response.send_redirect( web.url_for( controller='forms',
                                                                  action='browse_form_definitions',
                                                                  status='error',
                                                                  message="Invalid form ID") )
            if operation == "view_latest_form_definition":
                return self.view_latest_form_definition( trans, **kwd )
            elif operation == "delete":
                return self.delete_form_definition( trans, **kwd )
            elif operation == "undelete":
                return self.undelete_form_definition( trans, **kwd )
            elif operation == "edit":
                return self.edit_form_definition( trans, **kwd )
        return self.forms_grid( trans, **kwd )
    @web.expose
    @web.require_admin
    def view_latest_form_definition( self, trans, **kwd ):
        '''Displays the layout of the latest version of the form definition'''
        form_definition_current_id = kwd.get( 'id', None )
        try:
            form_definition_current = trans.sa_session.query( trans.app.model.FormDefinitionCurrent ) \
                                                      .get( trans.security.decode_id( form_definition_current_id ) )
        except:
            return trans.response.send_redirect( web.url_for( controller='forms',
                                                              action='browse_form_definitions',
                                                              message='Invalid form',
                                                              status='error' ) )
        return trans.fill_template( '/admin/forms/view_form_definition.mako',
                                    form_definition=form_definition_current.latest_form )
    @web.expose
    @web.require_admin
    def create_form_definition( self, trans, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        self.__imported_from_file = False
        if params.get( 'create_form_button', False ):
            form_definition, message = self.save_form_definition( trans, form_definition_current_id=None, **kwd )
            if not form_definition:
                return trans.response.send_redirect( web.url_for( controller='forms',
                                                                  action='create_form_definition',
                                                                  message=message,
                                                                  status='error',
                                                                  name=util.restore_text( params.get( 'name', '' ) ),
                                                                  description=util.restore_text( params.get( 'description', '' ) ) ))
            if self.__imported_from_file:
                return trans.response.send_redirect( web.url_for( controller='forms',
                                                                  action='edit_form_definition',
                                                                  id=trans.security.encode_id( form_definition.current.id )) )
            else:
                return trans.response.send_redirect( web.url_for( controller='forms',
                                                                  action='edit_form_definition',
                                                                  id=trans.security.encode_id( form_definition.current.id ),
                                                                  add_field_button='Add field',
                                                                  name=form_definition.name,
                                                                  description=form_definition.desc,
                                                                  form_type_select_field=form_definition.type ) )
        inputs = [ ( 'Name', TextField( 'name', 40, util.restore_text( params.get( 'name', '' ) ) ) ),
                   ( 'Description', TextField( 'description', 40, util.restore_text( params.get( 'description', '' ) ) ) ),
                   ( 'Type', self.__build_form_types_widget( trans, selected=params.get( 'form_type', 'none' ) ) ),
                   ( 'Import from csv file (Optional)', FileField( 'file_data', 40, '' ) ) ]
        return trans.fill_template( '/admin/forms/create_form.mako',
                                    inputs=inputs,
                                    message=message,
                                    status=status )
    @web.expose
    @web.require_admin
    def edit_form_definition( self, trans, response_redirect=None, **kwd ):
        '''
        This callback method is for handling form editing.  The value of response_redirect
        should be an URL that is defined by the caller.  This allows for redirecting as desired
        when the form changes have been saved.  For an example of how this works, see the
        edit_template() method in the base controller.
        '''
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        try:
            form_definition_current = trans.sa_session.query( trans.app.model.FormDefinitionCurrent ).get( trans.security.decode_id(kwd['id']) )
        except:
            return trans.response.send_redirect( web.url_for( controller='forms',
                                                              action='browse_form_definitions',
                                                              message='Invalid form',
                                                              status='error' ) )
        form_definition = form_definition_current.latest_form
        # TODO: eliminate the need for this refresh param.
        if params.get( 'refresh', False ):
            # Refresh
            current_form = self.get_current_form( trans, **kwd )
        else:
            # Show the saved form for editing
            current_form = self.get_saved_form( form_definition )
        # Save changes
        if params.get( 'save_changes_button', False ):
            new_form_definition, message = self.save_form_definition( trans, form_definition_current_id=form_definition.form_definition_current.id, **kwd )
            # if validation error encountered while saving the form, show the
            # unsaved form, with the error message
            if not new_form_definition:
                status = 'error'
            else:
                # everything went fine. form saved successfully. Show the saved form or redirect
                # to response_redirect if appropriate.
                if response_redirect:
                    return trans.response.send_redirect( response_redirect )
                form_definition = new_form_definition
                current_form = self.get_saved_form( form_definition )
                message = "The form '%s' has been updated with the changes." % form_definition.name
        # Add a layout grid
        elif params.get( 'add_layout_grid_button', False ):
            current_form[ 'layout' ].append( '' )
        # Delete a layout grid
        elif params.get( 'remove_layout_grid_button', False ):
            index = int( kwd[ 'remove_layout_grid_button' ].split( ' ' )[2] ) - 1
            del current_form[ 'layout' ][index]
        # Add a field
        elif params.get( 'add_field_button', False ):
            field_index = len( current_form[ 'fields' ] ) + 1
            self.empty_field[ 'name' ] = '%i_field_name' % field_index
            self.empty_field[ 'label' ] = 'Field label %i' % field_index
            current_form[ 'fields' ].append( self.empty_field )
        # Delete a field
        elif params.get( 'remove_button', False ):
            # find the index of the field to be removed from the remove button label
            index = int( kwd[ 'remove_button' ].split( ' ' )[2] ) - 1
            del current_form[ 'fields' ][ index ]
        # Add SelectField option
        elif 'Add' in kwd.values():
            current_form, status, message = self.__add_select_field_option( trans=trans,
                                                                            current_form=current_form,
                                                                            **kwd)
        # Remove SelectField option
        elif 'Remove' in kwd.values():
            current_form, status, message = self.__remove_select_field_option( trans=trans,
                                                                               current_form=current_form,
                                                                               **kwd)
        return self.show_editable_form_definition( trans=trans,
                                                   form_definition=form_definition,
                                                   current_form=current_form,
                                                   message=message,
                                                   status=status,
                                                   response_redirect=response_redirect,
                                                   **kwd )
    def get_saved_form( self, form_definition ):
        '''
        This retrieves the saved form and returns a dictionary containing the name,
        desc, type, layout & fields of the form
        '''
        if form_definition.type == form_definition.types.SAMPLE:
            return dict( name=form_definition.name,
                         desc=form_definition.desc,
                         type=form_definition.type,
                         layout=list( copy.deepcopy( form_definition.layout ) ),
                         fields=list( copy.deepcopy( form_definition.fields ) ) )
        return dict( name=form_definition.name,
                     desc=form_definition.desc,
                     type=form_definition.type,
                     layout=[],
                     fields=list( copy.deepcopy( form_definition.fields ) ) )

    def get_current_form( self, trans, **kwd ):
        '''
        This method gets all the unsaved user-entered form details and returns a
        dictionary containing the name, desc, type, layout & fields of the form
        '''
        params = util.Params( kwd )
        name = util.restore_text( params.name )
        desc = util.restore_text( params.description ) or ""
        form_type = util.restore_text( params.form_type_select_field )
        # get the user entered layout grids in it is a sample form definition
        layout = []
        if form_type == trans.model.FormDefinition.types.SAMPLE:
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
                if kwd.has_key( 'field_label_%i' % index ):
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
    def save_form_definition( self, trans, form_definition_current_id=None, **kwd ):
        '''
        This method saves the current form
        '''
        # check the form for invalid inputs
        flag, message = self.__validate_form( **kwd )
        if not flag:
            return None, message
        current_form = self.get_current_form( trans, **kwd )
        # validate fields
        field_names_dict = {}
        for field in current_form[ 'fields' ]:
            if not field[ 'label' ]:
                return None, "All the field labels must be completed."
            if not VALID_FIELDNAME_RE.match( field[ 'name' ] ):
                return None, "'%s' is not a valid field name." % field[ 'name' ]
            if field_names_dict.has_key( field[ 'name' ] ):
                return None, "Each field name must be unique in the form definition. '%s' is not unique." % field[ 'name' ]
            else:
                field_names_dict[ field[ 'name' ] ] = 1
        # if type is sample form, it should have at least one layout grid
        if current_form[ 'type' ] == trans.app.model.FormDefinition.types.SAMPLE and not len( current_form[ 'layout' ] ):
            current_form[ 'layout' ] = [ 'Layout1' ]
        # create a new form definition
        form_definition = trans.app.model.FormDefinition( name=current_form[ 'name' ],
                                                          desc=current_form[ 'desc' ],
                                                          fields=current_form[ 'fields' ],
                                                          form_definition_current=None,
                                                          form_type=current_form[ 'type' ],
                                                          layout=current_form[ 'layout' ] )
        if form_definition_current_id: # save changes to the existing form
            # change the pointer in the form_definition_current table to point
            # to this new record
            form_definition_current = trans.sa_session.query( trans.app.model.FormDefinitionCurrent ).get( form_definition_current_id )
        else: # create a new form
            form_definition_current = trans.app.model.FormDefinitionCurrent()
        # create corresponding row in the form_definition_current table
        form_definition.form_definition_current = form_definition_current
        form_definition_current.latest_form = form_definition
        trans.sa_session.add( form_definition_current )
        trans.sa_session.flush()
        message = "The new form named '%s' has been created. " % (form_definition.name)
        return form_definition, message
    def show_editable_form_definition( self, trans, form_definition, current_form, message='', status='done', response_redirect=None, **kwd ):
        """
        Displays the form and any of the changes made to it in edit mode. In this method
        all the widgets are build for all name, description and all the fields of a form
        definition.
        """
        params = util.Params( kwd )
        # name & description
        form_details = [ ( 'Name', TextField( 'name', 40, current_form[ 'name' ] ) ),
                         ( 'Description', TextField( 'description', 40, current_form[ 'desc' ] ) ),
                         ( 'Type', HiddenField( 'form_type_select_field', current_form['type']) ) ]
        form_layout = []
        if current_form[ 'type' ] == trans.app.model.FormDefinition.types.SAMPLE:
            for index, layout_name in enumerate( current_form[ 'layout' ] ):
                form_layout.append( TextField( 'grid_layout%i' % index, 40, layout_name ))
        # fields
        field_details = []
        for field_index, field in enumerate( current_form[ 'fields' ] ):
            field_widgets = self.build_form_definition_field_widgets( trans=trans,
                                                                      layout_grids=current_form['layout'],
                                                                      field_index=field_index,
                                                                      field=field,
                                                                      form_type=current_form['type'] )
            field_details.append( field_widgets )
        return trans.fill_template( '/admin/forms/edit_form_definition.mako',
                                    form_details=form_details,
                                    field_details=field_details,
                                    form_definition=form_definition,
                                    field_types=trans.model.FormDefinition.supported_field_types,
                                    message=message,
                                    status=status,
                                    current_form_type=current_form[ 'type' ],
                                    layout_grids=form_layout,
                                    response_redirect=response_redirect )
    @web.expose
    @web.require_admin
    def delete_form_definition( self, trans, **kwd ):
        id_list = util.listify( kwd['id'] )
        delete_failed = []
        for id in id_list:
            try:
                form_definition_current = trans.sa_session.query( trans.app.model.FormDefinitionCurrent ).get( trans.security.decode_id(id) )
            except:
                return trans.response.send_redirect( web.url_for( controller='forms',
                                                                  action='browse_form_definitions',
                                                                  message='Invalid form',
                                                                  status='error' ) )
            form_definition_current.deleted = True
            trans.sa_session.add( form_definition_current )
            trans.sa_session.flush()
        return trans.response.send_redirect( web.url_for( controller='forms',
                                                          action='browse_form_definitions',
                                                          message='%i forms have been deleted.' % len(id_list),
                                                          status='done') )
    @web.expose
    @web.require_admin
    def undelete_form_definition( self, trans, **kwd ):
        id_list = util.listify( kwd['id'] )
        delete_failed = []
        for id in id_list:
            try:
                form_definition_current = trans.sa_session.query( trans.app.model.FormDefinitionCurrent ).get( trans.security.decode_id(id) )
            except:
                return trans.response.send_redirect( web.url_for( controller='forms',
                                                                  action='browse_form_definitions',
                                                                  message='Invalid form',
                                                                  status='error' ) )
            form_definition_current.deleted = False
            trans.sa_session.add( form_definition_current )
            trans.sa_session.flush()
        return trans.response.send_redirect( web.url_for( controller='forms',
                                                          action='browse_form_definitions',
                                                          message='%i forms have been undeleted.' % len(id_list),
                                                          status='done') )
    def build_form_definition_field_widgets( self, trans, layout_grids, field_index, field, form_type ):
        '''
        This method returns a list of widgets which describes a form definition field. This
        includes the field label, helptext, type, selectfield options, required/optional & layout
        '''
        # field label
        label = TextField( 'field_label_'+str( field_index ), 40, field['label'] )
        # help text
        helptext = TextField( 'field_helptext_'+str( field_index ), 40, field['helptext'] )
        # field type
        field_type_select_field = SelectField( 'field_type_'+str( field_index ),
                                            refresh_on_change=True,
                                            refresh_on_change_values=[ SelectField.__name__ ] )
        # fill up the field type selectfield options
        field_type_options = []
        # if the form is for defining samples, then use the sample field types
        # which does not include TextArea & AddressField
        if form_type == trans.model.FormDefinition.types.SAMPLE:
            for supported_field_type in trans.model.Sample.supported_field_types:
                if supported_field_type.__name__ == field[ 'type' ]:
                    field_type_select_field.add_option( supported_field_type.__name__,
                                                     supported_field_type.__name__,
                                                     selected=True )
                    if supported_field_type.__name__ == SelectField.__name__:
                        # when field type is Selectfield, add option Textfields
                        field_type_options = self.__build_field_type_select_field_options( field, field_index )
                else:
                    field_type_select_field.add_option( supported_field_type.__name__,
                                                     supported_field_type.__name__ )
        else:
            for supported_field_type in trans.model.FormDefinition.supported_field_types:
                if supported_field_type.__name__ == field[ 'type' ]:
                    field_type_select_field.add_option( supported_field_type.__name__,
                                                     supported_field_type.__name__,
                                                     selected=True )
                    if supported_field_type.__name__ == SelectField.__name__:
                        # when field type is Selectfield, add option Textfields
                        field_type_options = self.__build_field_type_select_field_options( field, field_index )
                else:
                    field_type_select_field.add_option( supported_field_type.__name__,
                                                     supported_field_type.__name__ )
        # required/optional radio button
        required = SelectField( 'field_required_'+str(field_index), display='radio' )
        if field[ 'required' ] == 'required':
            required.add_option( 'Required', 'required', selected=True )
            required.add_option( 'Optional', 'optional' )
        else:
            required.add_option( 'Required', 'required' )
            required.add_option( 'Optional', 'optional', selected=True )
        # layout grid option select_field
        if layout_grids and form_type == trans.model.FormDefinition.types.SAMPLE:
            layout_select_field = SelectField( 'field_layout_'+str( field_index ) )
            for index, grid_name in enumerate( layout_grids ):
                if str( field.get( 'layout', None ) ) == str( index ): #existing behavior: integer indexes are stored as strings.
                    grid_selected = True
                else:
                    grid_selected = False
                layout_select_field.add_option("%i. %s" %( index+1, grid_name ), index, selected=grid_selected )
        # default value
        default_value = TextField( 'field_default_'+str(field_index),
                                   40,
                                   field.get( 'default', '' ) )
        # field name
        name = TextField( 'field_name_' + str( field_index ), 40, field[ 'name' ] )
        name_helptext = "The field name must be unique for each field and must contain only alphanumeric characters and underscore ."
        if layout_grids and form_type == trans.model.FormDefinition.types.SAMPLE:
            return [ ( 'Field label', label ),
                     ( 'Help text', helptext ),
                     ( 'Type', field_type_select_field, "Add options below", field_type_options ),
                     ( 'Default value', default_value ),
                     ( '', required ),
                     ( 'Select the grid layout to place this field', layout_select_field ),
                     ( 'Field name', name, name_helptext ) ]
        return [ ( 'Field label', label ),
                 ( 'Help text', helptext ),
                 ( 'Type', field_type_select_field, "Add options below", field_type_options),
                 ( 'Default value', default_value ),
                 ( '', required),
                 ( 'Field name', name, name_helptext ) ]
    def __build_field_type_select_field_options( self, field, field_index ):
        '''
        Returns a list of TextFields, one for each select field option
        '''
        field_type_options = []
        if field[ 'selectlist' ]:
            for ctr, option in enumerate( field[ 'selectlist' ] ):
                option_textfield = TextField( 'field_'+str( field_index )+'_option_'+str( ctr ), 40, option )
                field_type_options.append( ( 'Option '+str( ctr+1 ), option_textfield ) )
        return field_type_options
    def __add_select_field_option( self, trans, current_form, **kwd ):
        '''
        This method adds a select_field option. The kwd dict searched for
        the field index which needs to be removed
        '''
        message=''
        status='ok',
        index = -1
        for k, v in kwd.items():
            if v == 'Add':
                # extract the field index from the
                # button name of format: 'addoption_<field>'
                index = int(k.split('_')[1])
                break
        if index == -1:
            # something wrong happened
            message='Error in adding selectfield option',
            status='error',
            return current_form, status, message
        # add an empty option
        current_form[ 'fields' ][ index ][ 'selectlist' ].append( '' )
        return current_form, status, message
    def __remove_select_field_option( self, trans, current_form, **kwd ):
        '''
        This method removes a select_field option. The kwd dict searched for
        the field index and option index which needs to be removed
        '''
        message=''
        status='ok',
        option = -1
        for k, v in kwd.items():
            if v == 'Remove':
                # extract the field & option indices from the
                # button name of format: 'removeoption_<field>_<option>'
                index = int( k.split( '_' )[1] )
                option = int( k.split( '_' )[2] )
                break
        if option == -1:
            # something wrong happened
            message='Error in removing selectfield option',
            status='error',
            return current_form, status, message
        # remove the option
        del current_form[ 'fields' ][ index ][ 'selectlist' ][ option ]
        return current_form, status, message
    def __get_select_field_options( self, index, **kwd ):
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
                sb_options.append( util.restore_text( option ) )
                ctr = ctr+1
            else:
                return sb_options
    def __get_field( self, index, **kwd ):
        '''
        This method retrieves all the user-entered details of a field and
        returns a dict.
        '''
        params = util.Params( kwd )
        label = util.restore_text( params.get( 'field_label_%i' % index, '' ) )
        name = util.restore_text( params.get( 'field_name_%i' % index, '' ) )
        helptext = util.restore_text( params.get( 'field_helptext_%i' % index, '' ) )
        required =  params.get( 'field_required_%i' % index, False )
        field_type = util.restore_text( params.get( 'field_type_%i' % index, '' ) )
        layout = params.get( 'field_layout_%i' % index, '0' )
        default = util.restore_text( params.get( 'field_default_%i' % index, '' ) )
        if not name.strip():
            name = '%i_field_name' % index
        if field_type == 'SelectField':
            options = self.__get_select_field_options(index, **kwd)
            return { 'name': name,
                     'label': label,
                     'helptext': helptext,
                     'visible': True,
                     'required': required,
                     'type': field_type,
                     'selectlist': options,
                     'layout': layout,
                     'default': default }
        return { 'name': name,
                 'label': label,
                 'helptext': helptext,
                 'visible': True,
                 'required': required,
                 'type': field_type,
                 'layout': layout,
                 'default': default }
    def __import_fields( self, trans, csv_file, form_type ):
        '''
        "company","name of the company", "True", "required", "TextField",,
        "due date","turnaround time", "True", "optional", "SelectField","24 hours, 1 week, 1 month"
        '''
        import csv
        fields = []
        layouts = set()
        try:
            reader = csv.reader(csv_file.file)
            index = 1
            for row in reader:
                if len(row) < 7: # ignore bogus rows
                    continue
                options = row[5].split(',')
                if len(row) >= 8:
                    fields.append( { 'name': '%i_field_name' % index,
                                     'label': row[0],
                                     'helptext': row[1],
                                     'visible': row[2],
                                     'required': row[3],
                                     'type': row[4],
                                     'selectlist': options,
                                     'layout':row[6],
                                     'default': row[7] } )
                    layouts.add(row[6])
                else:
                    fields.append( { 'name': '%i_field_name' % index,
                                     'label': row[0],
                                     'helptext': row[1],
                                     'visible': row[2],
                                     'required': row[3],
                                     'type': row[4],
                                     'selectlist': options,
                                     'default': row[6] } )
                index = index + 1
        except:
            return trans.response.send_redirect( web.url_for( controller='forms',
                                                              action='create_form',
                                                              status='error',
                                                              message='Error in importing <b>%s</b> file' % csv_file.file))
        self.__imported_from_file = True
        return fields, list(layouts)
    def __validate_form( self, **kwd ):
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
        if util.restore_text( params.form_type_select_field ) == 'none':
            return None, 'Form type must be selected.'
        return True, ''
    def __build_form_types_widget( self, trans, selected='none' ):
        form_type_select_field = SelectField( 'form_type_select_field' )
        if selected == 'none':
            form_type_select_field.add_option( 'Select one', 'none', selected=True )
        else:
            form_type_select_field.add_option( 'Select one', 'none' )
        fd_types = trans.app.model.FormDefinition.types.items()
        fd_types.sort()
        for ft in fd_types:
            if selected == ft[1]:
                form_type_select_field.add_option( ft[1], ft[1], selected=True )
            else:
                form_type_select_field.add_option( ft[1], ft[1] )
        return form_type_select_field

