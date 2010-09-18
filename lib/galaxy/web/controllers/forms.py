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
                    link=( lambda item: iff( item.deleted, None, dict( operation="view", id=item.id ) ) ),
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
        grids.GridAction( "Create new form", dict( controller='forms', 
                                                      action='new' ) )
    ]

class Forms( BaseController ):
    # Empty form field
    empty_field = { 'label': '', 
                    'helptext': '', 
                    'visible': True,
                    'required': False,
                    'type': BaseField.form_field_types()[0],
                    'selectlist': [],
                    'layout': 'none',
                    'default': '' }
    forms_grid = FormsGrid()

    @web.expose
    @web.require_admin
    def manage( self, trans, **kwd ):
        if 'operation' in kwd:
            operation = kwd['operation'].lower()
            if not kwd.get( 'id', None ):
                return trans.response.send_redirect( web.url_for( controller='forms',
                                                                  action='manage',
                                                                  status='error',
                                                                  message="Invalid form ID") )
            if operation == "view":
                return self.__view( trans, **kwd )
            elif operation == "delete":
                return self.__delete( trans, **kwd )
            elif operation == "undelete":
                return self.__undelete( trans, **kwd )
            elif operation == "edit":
                return self.edit( trans, **kwd )
        return self.forms_grid( trans, **kwd )
    def __view(self, trans, **kwd):
        try:
            fdc = trans.sa_session.query( trans.app.model.FormDefinitionCurrent )\
                                  .get( trans.security.decode_id(kwd['id']) )
        except:
            return trans.response.send_redirect( web.url_for( controller='forms',
                                                              action='manage',
                                                              message='Invalid form',
                                                              status='error' ) )
        return trans.fill_template( '/admin/forms/show_form_read_only.mako',
                                    form=fdc.latest_form )
    def __form_types_widget(self, trans, selected='none'):
        form_type_selectbox = SelectField( 'form_type_selectbox', 
                                           refresh_on_change=True, 
                                           refresh_on_change_values=[trans.app.model.FormDefinition.types.SAMPLE] )
        if selected == 'none':
            form_type_selectbox.add_option('Select one', 'none', selected=True)
        else:
            form_type_selectbox.add_option('Select one', 'none')
        fd_types = trans.app.model.FormDefinition.types.items()
        fd_types.sort()
        for ft in fd_types:
            if selected == ft[1]:
                form_type_selectbox.add_option(ft[1], ft[1], selected=True)
            else:
                form_type_selectbox.add_option(ft[1], ft[1])
        return form_type_selectbox
    
    @web.expose
    @web.require_admin
    def new( self, trans, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        self.__imported_from_file = False
        if params.get( 'create_form_button', False ):   
            fd, message = self.__save_form( trans, fdc_id=None, **kwd )
            if not fd:
                return trans.response.send_redirect( web.url_for( controller='forms',
                                                                  action='new',
                                                                  message=message,
                                                                  status='error',
                                                                  name=util.restore_text( params.get( 'name', '' ) ),
                                                                  description=util.restore_text( params.get( 'description', '' ) ) ))
            self.__get_saved_form( fd )
            if self.__imported_from_file:
                return trans.response.send_redirect( web.url_for( controller='forms',
                                                                  action='edit',
                                                                  id=trans.security.encode_id(fd.current.id)) )                  
            else:
                return trans.response.send_redirect( web.url_for( controller='forms',
                                                                  action='edit',
                                                                  id=trans.security.encode_id(fd.current.id),
                                                                  add_field_button='Add field',
                                                                  name=fd.name,
                                                                  description=fd.desc,
                                                                  form_type_selectbox=fd.type ) )  
        inputs = [ ( 'Name', TextField( 'name', 40, util.restore_text( params.get( 'name', '' ) ) ) ),
                   ( 'Description', TextField( 'description', 40, util.restore_text( params.get( 'description', '' ) ) ) ),
                   ( 'Type', self.__form_types_widget(trans, selected=params.get( 'form_type', 'none' )) ),
                   ( 'Import from csv file (Optional)', FileField( 'file_data', 40, '' ) ) ]
        return trans.fill_template( '/admin/forms/create_form.mako', 
                                    inputs=inputs,
                                    message=message,
                                    status=status )     
    def __delete( self, trans, **kwd ):
        id_list = util.listify( kwd['id'] )
        delete_failed = []
        for id in id_list:
            try:
                fdc = trans.sa_session.query( trans.app.model.FormDefinitionCurrent ).get( trans.security.decode_id(id) )
            except:
                return trans.response.send_redirect( web.url_for( controller='forms',
                                                                  action='manage',
                                                                  message='Invalid form',
                                                                  status='error' ) )
            fdc.deleted = True
            trans.sa_session.add( fdc )
            trans.sa_session.flush()
        return trans.response.send_redirect( web.url_for( controller='forms',
                                                          action='manage',
                                                          message='%i form(s) is deleted.' % len(id_list), 
                                                          status='done') )
    def __undelete( self, trans, **kwd ):
        id_list = util.listify( kwd['id'] )
        delete_failed = []
        for id in id_list:
            try:
                fdc = trans.sa_session.query( trans.app.model.FormDefinitionCurrent ).get( trans.security.decode_id(id) )
            except:
                return trans.response.send_redirect( web.url_for( controller='forms',
                                                                  action='manage',
                                                                  message='Invalid form',
                                                                  status='error' ) )
            fdc.deleted = False
            trans.sa_session.add( fdc )
            trans.sa_session.flush()
        return trans.response.send_redirect( web.url_for( controller='forms',
                                                          action='manage',
                                                          message='%i form(s) is undeleted.' % len(id_list), 
                                                          status='done') )
    @web.expose
    def edit( self, trans, response_redirect=None, **kwd ):
        '''
        This callback method is for handling form editing.  The value of response_redirect
        should be an URL that is defined by the caller.  This allows for redirecting as desired
        when the form changes have been saved.  For an example of how this works, see the 
        edit_template() method in the library_common controller.
        '''
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        try:
            fdc = trans.sa_session.query( trans.app.model.FormDefinitionCurrent ).get( trans.security.decode_id(kwd['id']) )
        except:
            return trans.response.send_redirect( web.url_for( controller='forms',
                                                              action='manage',
                                                              message='Invalid form',
                                                              status='error' ) )
        fd = fdc.latest_form
        #
        # Save changes
        #
        if params.get( 'save_changes_button', False ):
            fd_new, message = self.__save_form( trans, fdc_id=fd.form_definition_current.id, **kwd )
            # if validation error encountered while saving the form, show the 
            # unsaved form, with the error message
            if not fd_new:
                current_form = self.__get_form( trans, **kwd )
                return self.__show( trans=trans, form=fd, current_form=current_form, 
                                    message=message, status='error', response_redirect=response_redirect, **kwd )
            # everything went fine. form saved successfully. Show the saved form or redirect
            # to response_redirect if appropriate.
            if response_redirect:
                return trans.response.send_redirect( response_redirect )
            fd = fd_new
            current_form = self.__get_saved_form( fd )
            message = "The form '%s' has been updated with the changes." % fd.name
            return self.__show( trans=trans, form=fd, current_form=current_form, 
                                message=message, status=status, response_redirect=response_redirect, **kwd )
        #
        # Add a layout grid
        #
        elif params.get( 'add_layout_grid', False ):
            current_form = self.__get_form( trans, **kwd )
            current_form['layout'].append('')
            # show the form again
            return self.__show( trans=trans, form=fd, current_form=current_form, 
                                message=message, status=status, response_redirect=response_redirect, **kwd )
        #
        # Delete a layout grid
        #
        elif params.get( 'remove_layout_grid_button', False ):
            current_form = self.__get_form( trans, **kwd )
            index = int( kwd[ 'remove_layout_grid_button' ].split( ' ' )[2] ) - 1
            del current_form['layout'][index]
            return self.__show( trans=trans, form=fd, current_form=current_form, 
                                message=message, status=status, response_redirect=response_redirect, **kwd )
        #
        # Add a field
        #
        elif params.get( 'add_field_button', False ):
            current_form = self.__get_form( trans, **kwd )
            current_form['fields'].append( self.empty_field )
            # show the form again with one empty field
            return self.__show( trans=trans, form=fd, current_form=current_form, 
                                message=message, status=status, response_redirect=response_redirect, **kwd )
        #
        # Delete a field
        #
        elif params.get( 'remove_button', False ):
            current_form = self.__get_form( trans, **kwd )
            # find the index of the field to be removed from the remove button label
            index = int( kwd[ 'remove_button' ].split( ' ' )[2] ) - 1
            del current_form['fields'][index]
            return self.__show( trans=trans, form=fd, current_form=current_form, 
                                message=message, status=status, response_redirect=response_redirect, **kwd )
        #
        # Add SelectField option
        #
        elif 'Add' in kwd.values():
            return self.__add_selectbox_option(trans, fd, message, status, response_redirect=response_redirect, **kwd)
        #
        # Remove SelectField option
        #
        elif 'Remove' in kwd.values():
            return self.__remove_selectbox_option(trans, fd, message, status, response_redirect=response_redirect, **kwd)
        #
        # Refresh page
        #
        elif params.get( 'refresh', False ):
            current_form = self.__get_form( trans, **kwd )
            return self.__show( trans=trans, form=fd, current_form=current_form, 
                                message=message, status=status, response_redirect=response_redirect, **kwd )
        #
        # Show the form for editing
        #
        else:
            current_form = self.__get_saved_form( fd )
            return self.__show( trans=trans, form=fd, current_form=current_form, 
                                message=message, status=status, response_redirect=response_redirect, **kwd )
            
    def __add_selectbox_option( self, trans, fd, message, status, response_redirect=None, **kwd ):
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
                                message='Error in adding selectfield option', 
                                status='error', response_redirect=response_redirect, **kwd )
        # add an empty option
        current_form[ 'fields' ][ index ][ 'selectlist' ].append( '' )
        return self.__show( trans=trans, form=fd, current_form=current_form, 
                            message=message, status=status, response_redirect=response_redirect, **kwd )
    def __remove_selectbox_option( self, trans, fd, message, status, response_redirect=None, **kwd ):
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
                                message='Error in removing selectfield option', 
                                status='error', response_redirect=response_redirect, **kwd )
        # remove the option
        del current_form[ 'fields' ][ index ][ 'selectlist' ][ option ]
        return self.__show( trans=trans, form=fd, current_form=current_form, 
                            message=message, status=status, response_redirect=response_redirect, **kwd )

    
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
        default = params.get( 'field_default_%i' % index, '' )
        if field_type == 'SelectField':
            selectlist = self.__get_selectbox_options(index, **kwd)
            return {'label': name, 
                    'helptext': helptext, 
                    'visible': True,
                    'required': required,
                    'type': field_type,
                    'selectlist': selectlist,
                    'layout': layout,
                    'default': default }
        return {'label': name, 
                'helptext': helptext, 
                'visible': True,
                'required': required,
                'type': field_type,
                'layout': layout,
                'default': default}
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
            for row in reader:
                if len(row) < 7: # ignore bogus rows
		    continue
                options = row[5].split(',')
                if len(row) >= 8:
                    fields.append({'label': row[0], 
                                   'helptext': row[1], 
                                   'visible': row[2],
                                   'required': row[3],
                                   'type': row[4],
                                   'selectlist': options,
                                   'layout':row[6],
                                   'default': row[7]})
                    layouts.add(row[6])             
                else:
                    fields.append({'label': row[0], 
                                   'helptext': row[1], 
                                   'visible': row[2],
                                   'required': row[3],
                                   'type': row[4],
                                   'selectlist': options,
                                   'default': row[6]})
        except:
            return trans.response.send_redirect( web.url_for( controller='forms',
                                                              action='new',
                                                              status='error',
                                                              message='Error in importing <b>%s</b> file' % csv_file.file))
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
        flag, message = self.__validate_form(**kwd)
        if not flag:
            return None, message
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
        trans.sa_session.add( fdc )
        trans.sa_session.flush()
        message = "The new form named '%s' has been created. " % (fd.name)
        return fd, message
    
    class FieldUI(object):
        def __init__(self, trans, layout_grids, index, field=None, field_type=None, form_type=None):
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
            # if the form is for defining samples, then use the sample field types
            # which does not include TextArea & AddressField
            if form_type == trans.app.model.FormDefinition.types.SAMPLE:
                for ft in BaseField.sample_field_types():
                    self.fieldtype.add_option(ft, ft)
            else:
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
            # default value
            self.default = TextField('field_default_'+str(index), 40, '')
            if field:
                self.fill(trans, field, field_type, form_type)
        def fill(self, trans, field, field_type=None, form_type=None):
            # label
            self.label.value = field['label']
            # helptext
            self.helptext.value = field['helptext']
            # default value
            self.default.value = field.get('default', '')
            # type
            self.fieldtype = SelectField('field_type_'+str(self.index), 
                                         refresh_on_change=True, 
                                         refresh_on_change_values=['SelectField'])
            if field_type:
                field['type'] = unicode(field_type)
            if field_type == 'SelectField' and not field['selectlist']:
                field['selectlist'] = ['', '']
            # if the form is for defining samples, then use the sample field types
            # which does not include TextArea & AddressField
            if form_type == trans.app.model.FormDefinition.types.SAMPLE:
                for ft in BaseField.sample_field_types():
                    if ft == field['type']:
                        self.fieldtype.add_option(ft, ft, selected=True)
                        if ft == 'SelectField':
                            self.selectbox_ui(field)
                    else:
                        self.fieldtype.add_option(ft, ft)
            else:
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
                        ( 'Default value', self.default ),
                        ( '', self.required),
                        ( 'Select the grid layout to place this field', self.layout_selectbox)]
            return [( 'Label', self.label ),
                    ( 'Help text', self.helptext ),
                    ( 'Type', self.fieldtype, self.selectbox_options),
                    ( 'Default value', self.default ),
                    ( '', self.required)]
        def __repr__(self):
            return str(self.index)+'.'+self.label 
        def label(self):
            return str(self.index)+'.'+self.label 
        
    def __show( self, trans, form, current_form, message='', status='done', response_redirect=None, **kwd ):
        '''
        This method displays the form and any of the changes made to it,
        The empty_form param allows for this method to simulate clicking
        the "add_field_button" on the edit_form.mako page so that the page
        is displayed with the first field to be added, saving a mouse click.
        '''
        params = util.Params( kwd )
        # name & description
        # TODO: RC, I've changed Type to be a hidden field since it should not be displayed on the edit_form.mako
        # template.  Make sure this is the optimal solution for this problem.  See my additional TODO in edit_form.mako.
        form_details = [ ( 'Name', TextField( 'name', 40, current_form[ 'name' ] ) ),
                         ( 'Description', TextField( 'description', 40, current_form[ 'desc' ] ) ),
                         ( 'Type', HiddenField( 'form_type_selectbox', current_form['type']) ) ]
        form_layout = []
        if current_form[ 'type' ] == trans.app.model.FormDefinition.types.SAMPLE:
            for index, lg in enumerate(current_form[ 'layout' ]):
                form_layout.append( TextField( 'grid_layout%i' % index, 40, lg )) 
        # fields
        field_details = []
        for index, field in enumerate( current_form[ 'fields' ] ):
            if current_form['type'] == trans.app.model.FormDefinition.types.SAMPLE:
                field_ui = self.FieldUI( trans, current_form['layout'], index, field, form_type=current_form['type'] )
            else:
                field_ui = self.FieldUI( trans, None, index, field, form_type=current_form['type'] )
            field_details.append( field_ui.get() )
        return trans.fill_template( '/admin/forms/edit_form.mako',
                                    form_details=form_details,
                                    field_details=field_details,
                                    form=form,
                                    field_types=BaseField.form_field_types(),
                                    message=message,
                                    status=status,
                                    current_form_type=current_form[ 'type' ],
                                    layout_grids=form_layout,
                                    response_redirect=response_redirect )
