from galaxy.web.base.controller import *
from galaxy.web.framework.helpers import time_ago, iff, grids
from galaxy.model.orm import *
from galaxy.datatypes import sniff
from galaxy import util
from galaxy.util.streamball import StreamBall
from galaxy.util.odict import odict
import logging, tempfile, zipfile, tarfile, os, sys
from galaxy.web.form_builder import * 
from datetime import datetime, timedelta
from cgi import escape, FieldStorage

log = logging.getLogger( __name__ )

class RequestsListGrid( grids.Grid ):
    title = "Sequencing Requests"
    template = '/requests/grid.mako'
    model_class = model.Request
    default_sort_key = "-create_time"
    show_filter = model.Request.states.UNSUBMITTED
    columns = [
        grids.GridColumn( "Name", key="name",
                          link=( lambda item: iff( item.deleted, None, dict( operation="show_request", id=item.id ) ) ),
                          attach_popup=True ),
        grids.GridColumn( "Description", key='desc'),
        grids.GridColumn( "Sample(s)", method='number_of_samples', 
                          link=( lambda item: iff( item.deleted, None, dict( operation="show_request", id=item.id ) ) ), ),
        grids.GridColumn( "Type", key="request_type_id", method='get_request_type'),
        grids.GridColumn( "Last update", key="update_time", format=time_ago ),
        grids.GridColumn( "State", key='state'),
    ]
    operations = [
        grids.GridOperation( "Submit", allow_multiple=False, condition=( lambda item: not item.deleted and item.unsubmitted() and item.samples )  ),
        grids.GridOperation( "Edit", allow_multiple=False, condition=( lambda item: not item.deleted and item.unsubmitted() )  ),
        grids.GridOperation( "Delete", allow_multiple=False, condition=( lambda item: not item.deleted and item.unsubmitted() )  ),
        grids.GridOperation( "Undelete", allow_multiple=False, condition=( lambda item: item.deleted )  )

    ]
    standard_filters = [
        grids.GridColumnFilter( model.Request.states.UNSUBMITTED, 
                                args=dict( state=model.Request.states.UNSUBMITTED, deleted=False ) ),
        grids.GridColumnFilter( model.Request.states.SUBMITTED, 
                                args=dict( state=model.Request.states.SUBMITTED, deleted=False ) ),
        grids.GridColumnFilter( model.Request.states.COMPLETE, args=dict( state=model.Request.states.COMPLETE, deleted=False ) ),
        grids.GridColumnFilter( "Deleted", args=dict( deleted=True ) ),
        grids.GridColumnFilter( "All", args={} )
    ]
    #default_filter = dict( deleted=False )
    def get_current_item( self, trans ):
        return None
    def get_request_type(self, trans, request):
        return request.type.name
    def apply_default_filter( self, trans, query, **kwargs ):
        query = query.filter_by( user=trans.user )
        if self.default_filter:
            return query.filter_by( **self.default_filter )
        else:
            return query
    def number_of_samples(self, trans, request):
        return str(len(request.samples))
    def get_state(self, trans, request):
            return request.state

class Requests( BaseController ):
    request_grid = RequestsListGrid()

    @web.expose
    @web.require_login( "create/submit sequencing requests" )
    def index( self, trans ):
        return trans.fill_template( "requests/index.mako" )

    @web.expose
    @web.require_login( "create/submit sequencing requests" )
    def list( self, trans, **kwargs ):
        '''
        List all request made by the current user
        '''
        status = message = None
        self.request_grid.default_filter = dict(state=trans.app.model.Request.states.UNSUBMITTED, 
                                                deleted=False)
        if 'operation' in kwargs:
            operation = kwargs['operation'].lower()
            if operation == "show_request":
                id = trans.security.decode_id(kwargs['id'])
                return self.__show_request(trans, id, kwargs.get('add_sample', False))
            elif operation == "submit":
                id = trans.security.decode_id(kwargs['id'])
                return self.__submit_request(trans, id)
            elif operation == "delete":
                id = trans.security.decode_id(kwargs['id'])
                return self.__delete_request(trans, id)
            elif operation == "undelete":
                id = trans.security.decode_id(kwargs['id'])
                return self.__undelete_request(trans, id)
            elif operation == "edit":
                id = trans.security.decode_id(kwargs['id'])
                return self.__edit_request(trans, id)
        if 'show_filter' in kwargs.keys():
            if kwargs['show_filter'] == 'All':
                self.request_grid.default_filter = {}
            elif kwargs['show_filter'] == 'Deleted':
                self.request_grid.default_filter = dict(deleted=True)
            else:
                self.request_grid.default_filter = dict(state=kwargs['show_filter'], deleted=False)
        self.request_grid.show_filter = kwargs.get('show_filter', trans.app.model.Request.states.UNSUBMITTED)
        # Render the list view
        return self.request_grid( trans, **kwargs )
    
    def __show_request(self, trans, id, add_sample=False):
        try:
            request = trans.sa_session.query( trans.app.model.Request ).get( id )
        except:
            return trans.response.send_redirect( web.url_for( controller='requests',
                                                              action='list',
                                                              status='error',
                                                              message="Invalid request ID",
                                                              **kwd) )
        current_samples = []
        for s in request.samples:
            current_samples.append([s.name, s.values.content])
        if add_sample:
            current_samples.append(['Sample_%i' % (len(current_samples)+1),['' for field in request.type.sample_form.fields]])
        return trans.fill_template( '/requests/show_request.mako',
                                    request=request,
                                    request_details=self.request_details(trans, id),
                                    current_samples = current_samples,
                                    sample_copy=self.__copy_sample(current_samples), 
                                    details='hide', edit_mode='False')
    def request_details(self, trans, id):
        '''
        Shows the request details
        '''
        request = trans.sa_session.query( trans.app.model.Request ).get( id )
        # list of widgets to be rendered on the request form
        request_details = []
        # main details
        request_details.append(dict(label='Description', 
                                    value=request.desc, 
                                    helptext=''))
        request_details.append(dict(label='Type', 
                                    value=request.type.name, 
                                    helptext=''))
        request_details.append(dict(label='State', 
                                    value=request.state, 
                                    helptext=''))
        request_details.append(dict(label='Date created', 
                                    value=request.create_time, 
                                    helptext=''))
        # library associated        
        if request.library:
            value = request.library.name
        else:
            value = None
        request_details.append( dict( label='Data library', 
                                      value=value, 
                                      helptext='Data library where the resultant dataset will be stored' ) )
        # folder associated
        if request.folder:
            value = request.folder.name
        else:
            value = None
        request_details.append( dict( label='Data library folder', 
                                      value=value, 
                                      helptext='Data library folder where the resultant dataset will be stored' ) )
        # form fields
        for index, field in enumerate(request.type.request_form.fields):
            if field['required']:
                req = 'Required'
            else:
                req = 'Optional'
            if field['type'] == 'AddressField':
                if request.values.content[index]:
                    request_details.append(dict(label=field['label'],
                                                value=trans.sa_session.query( trans.app.model.UserAddress ).get( int( request.values.content[index] ) ).get_html(),
                                                helptext=field['helptext']+' ('+req+')'))
                else:
                    request_details.append(dict(label=field['label'],
                                                value=None,
                                                helptext=field['helptext']+' ('+req+')'))

            else: 
                request_details.append(dict(label=field['label'],
                                            value=request.values.content[index],
                                            helptext=field['helptext']+' ('+req+')'))
        return request_details   
    def __update_samples(self, request, **kwd):
        '''
        This method retrieves all the user entered sample information and
        returns an list of all the samples and their field values
        '''
        params = util.Params( kwd )
        current_samples = []
        for s in request.samples:
            current_samples.append([s.name, s.values.content])
        index = len(request.samples) 
        while True:
            if params.get( 'sample_%i_name' % index, ''  ):
                sample_index = index
                sample_name = util.restore_text( params.get( 'sample_%i_name' % sample_index, ''  ) )
                sample_values = []
                for field_index in range(len(request.type.sample_form.fields)):
                    sample_values.append(util.restore_text( params.get( 'sample_%i_field_%i' % (sample_index, field_index), ''  ) ))
                current_samples.append([sample_name, sample_values])
                index = index + 1
            else:
                break
        details = params.get( 'details', 'hide' )
        edit_mode = params.get( 'edit_mode', 'False' )
        return current_samples, details, edit_mode
    def __copy_sample(self, current_samples):
        copy_list = SelectField('copy_sample')
        copy_list.add_option('None', -1, selected=True)  
        for i, s in enumerate(current_samples):
            copy_list.add_option(s[0], i)
        return copy_list   
    @web.expose
    @web.require_login( "create/submit sequencing requests" )
    def show_request(self, trans, **kwd):
        params = util.Params( kwd )
        msg = util.restore_text( params.get( 'msg', ''  ) )
        messagetype = params.get( 'messagetype', 'done' )
        try:
            request = trans.sa_session.query( trans.app.model.Request ).get( int( params.get( 'request_id', None ) ) )
        except:
            return trans.response.send_redirect( web.url_for( controller='requests',
                                                              action='list',
                                                              status='error',
                                                              message="Invalid request ID",
                                                              **kwd) )
        # get the user entered sample details
        current_samples, details, edit_mode = self.__update_samples( request, **kwd )
        if params.get('import_samples_button', False) == 'Import samples':
            try:
                file_obj = params.get('file_data', '')
                import csv
                reader = csv.reader(file_obj.file)
                for row in reader:
                    current_samples.append([row[0], row[1:]])  
                return trans.fill_template( '/requests/show_request.mako',
                                            request=request,
                                            request_details=self.request_details(trans, request.id),
                                            current_samples=current_samples,
                                            sample_copy=self.__copy_sample(current_samples), 
                                            details=details,
                                            edit_mode=edit_mode)
            except:
                return trans.response.send_redirect( web.url_for( controller='requests',
                                                                  action='list',
                                                                  status='error',
                                                                  message='Error in importing samples file',
                                                                  **kwd))
        elif params.get('add_sample_button', False) == 'Add New':
            # add an empty or filled sample
            # if the user has selected a sample no. to copy then copy the contents 
            # of the src sample to the new sample else an empty sample
            src_sample_index = int(params.get( 'copy_sample', -1  ))
            if src_sample_index == -1:
                # empty sample
                current_samples.append(['Sample_%i' % (len(current_samples)+1),['' for field in request.type.sample_form.fields]])
            else:
                current_samples.append([current_samples[src_sample_index][0]+'_%i' % (len(current_samples)+1),
                                                                  [val for val in current_samples[src_sample_index][1]]])
            return trans.fill_template( '/requests/show_request.mako',
                                        request=request,
                                        request_details=self.request_details(trans, request.id),
                                        current_samples=current_samples,
                                        sample_copy=self.__copy_sample(current_samples), 
                                        details=details,
                                        edit_mode=edit_mode)
        elif params.get('save_samples_button', False) == 'Save':
            # check for duplicate sample names
            msg = ''
            for index in range(len(current_samples)-len(request.samples)):
                sample_index = index + len(request.samples)
                sample_name = current_samples[sample_index][0]
                if not sample_name.strip():
                    msg = 'Please enter the name of sample number %i' % sample_index
                    break
                count = 0
                for i in range(len(current_samples)):
                    if sample_name == current_samples[i][0]:
                        count = count + 1
                if count > 1: 
                    msg = "This request has <b>%i</b> samples with the name <b>%s</b>.\nSamples belonging to a request must have unique names." % (count, sample_name)
                    break
            if msg:
                return trans.fill_template( '/requests/show_request.mako',
                                            request=request,
                                            request_details=self.request_details(trans, request.id),
                                            current_samples = current_samples,
                                            sample_copy=self.__copy_sample(current_samples), 
                                            details=details, edit_mode=edit_mode,
                                            messagetype='error', msg=msg)
            # save all the new/unsaved samples entered by the user
            if edit_mode == 'False':
                for index in range(len(current_samples)-len(request.samples)):
                    sample_index = len(request.samples)
                    sample_name = util.restore_text( params.get( 'sample_%i_name' % sample_index, ''  ) )
                    sample_values = []
                    for field_index in range(len(request.type.sample_form.fields)):
                        sample_values.append(util.restore_text( params.get( 'sample_%i_field_%i' % (sample_index, field_index), ''  ) ))
                    form_values = trans.app.model.FormValues(request.type.sample_form, sample_values)
                    form_values.flush()                    
                    s = trans.app.model.Sample(sample_name, '', request, form_values)
                    s.flush()
            else:
                for sample_index in range(len(current_samples)):
                    sample_name = current_samples[sample_index][0]
                    new_sample_name = util.restore_text( params.get( 'sample_%i_name' % sample_index, ''  ) )
                    sample_values = []
                    for field_index in range(len(request.type.sample_form.fields)):
                        sample_values.append(util.restore_text( params.get( 'sample_%i_field_%i' % (sample_index, field_index), ''  ) ))
                    sample = request.has_sample(sample_name)
                    if sample:
                        form_values = trans.sa_session.query( trans.app.model.FormValues ).get( sample.values.id )
                        form_values.content = sample_values
                        form_values.flush()
                        sample.name = new_sample_name
                        sample.flush()
            return trans.response.send_redirect( web.url_for( controller='requests',
                                                          action='list',
                                                          operation='show_request',
                                                          id=trans.security.encode_id(request.id)) )
        elif params.get('edit_samples_button', False) == 'Edit samples':
            edit_mode = 'True'
            return trans.fill_template( '/requests/show_request.mako',
                                        request=request,
                                        request_details=self.request_details(trans, request.id),
                                        current_samples=current_samples,
                                        sample_copy=self.__copy_sample(current_samples), 
                                        details=details,
                                        edit_mode=edit_mode)
        elif params.get('cancel_changes_button', False) == 'Cancel':
            return trans.response.send_redirect( web.url_for( controller='requests',
                                                          action='list',
                                                          operation='show_request',
                                                          id=trans.security.encode_id(request.id)) )

            
    @web.expose
    @web.require_login( "create/submit sequencing requests" )
    def delete_sample(self, trans, **kwd):
        params = util.Params( kwd )
        msg = util.restore_text( params.get( 'msg', ''  ) )
        messagetype = params.get( 'messagetype', 'done' )
        request = trans.sa_session.query( trans.app.model.Request ).get( int( params.get( 'request_id', 0 ) ) )
        current_samples, details, edit_mode = self.__update_samples( request, **kwd )
        sample_index = int(params.get('sample_id', 0))
        sample_name = current_samples[sample_index][0]
        s = request.has_sample(sample_name)
        if s:
            trans.sa_session.delete( s )
            s.flush()
            request.flush()
        del current_samples[sample_index]  
        return trans.fill_template( '/requests/show_request.mako',
                                    request=request,
                                    request_details=self.request_details(trans, request.id),
                                    current_samples = current_samples,
                                    sample_copy=self.__copy_sample(current_samples), 
                                    details=details,
                                    edit_mode=edit_mode)
        
    @web.expose
    @web.require_login( "create/submit sequencing requests" )
    def toggle_request_details(self, trans, **kwd):
        params = util.Params( kwd )
        msg = util.restore_text( params.get( 'msg', ''  ) )
        messagetype = params.get( 'messagetype', 'done' )
        # TODO: Fix the following - can we get a Request.id == 0???
        request = trans.sa_session.query( trans.app.model.Request ).get(int(params.get('request_id', 0)))
        current_samples, details, edit_mode = self.__update_samples( request, **kwd )
        return trans.fill_template( '/requests/show_request.mako',
                                    request=request,
                                    request_details=self.request_details(trans, request.id),
                                    current_samples = current_samples,
                                    sample_copy=self.__copy_sample(current_samples), 
                                    details=details,
                                    edit_mode=edit_mode)
    def __select_request_type(self, trans, rtid):
        requesttype_list = trans.sa_session.query( trans.app.model.RequestType )\
                                           .order_by( trans.app.model.RequestType.name.asc() )
        rt_ids = ['none']
        for rt in requesttype_list:
            if not rt.deleted:
                rt_ids.append(str(rt.id))
        select_reqtype = SelectField('select_request_type', 
                                     refresh_on_change=True, 
                                     refresh_on_change_values=rt_ids[1:])
        if rtid == 'none':
            select_reqtype.add_option('Select one', 'none', selected=True)
        else:
            select_reqtype.add_option('Select one', 'none')
        for rt in requesttype_list:
            if not rt.deleted:
                if rtid == rt.id:
                    select_reqtype.add_option(rt.name, rt.id, selected=True)
                else:
                    select_reqtype.add_option(rt.name, rt.id)
        return select_reqtype
    @web.expose
    @web.require_login( "create/submit sequencing requests" )
    def new(self, trans, **kwd):
        params = util.Params( kwd )
        msg = util.restore_text( params.get( 'msg', ''  ) )
        messagetype = params.get( 'messagetype', 'done' )
        if params.get('select_request_type', False) == 'True':
            return trans.fill_template( '/requests/new_request.mako',
                                        select_request_type=self.__select_request_type(trans, 'none'),                                 
                                        widgets=[],                                   
                                        msg=msg,
                                        messagetype=messagetype)
        elif params.get('create', False) == 'True':
            if params.get('create_request_button', False) == 'Save' \
               or params.get('create_request_samples_button', False) == 'Add samples':
                request_type = trans.sa_session.query( trans.app.model.RequestType ).get( int( params.select_request_type ) )
                if not util.restore_text(params.get('name', '')):
                    msg = 'Please enter the <b>Name</b> of the request'
                    kwd['create'] = 'True'
                    kwd['messagetype'] = 'error'
                    kwd['msg'] = msg
                    kwd['create_request_button'] = None
                    kwd['create_request_samples_button'] = None
                    return trans.response.send_redirect( web.url_for( controller='requests',
                                                                      action='new',
                                                                      **kwd) )
                request = self.__save_request(trans, None, **kwd)
                msg = 'The new request named %s has been created' % request.name
                if params.get('create_request_button', False) == 'Save':
                    return trans.response.send_redirect( web.url_for( controller='requests',
                                                                      action='list',
                                                                      message=msg ,
                                                                      status='done') )
                elif params.get('create_request_samples_button', False) == 'Add samples':
                    new_kwd = {}
                    new_kwd['id'] = trans.security.encode_id(request.id)
                    new_kwd['operation'] = 'show_request'
                    new_kwd['add_sample'] = True
                    return trans.response.send_redirect( web.url_for( controller='requests',
                                                                      action='list',
                                                                      msg=msg ,
                                                                      messagetype='done',
                                                                      **new_kwd) )
            else:
                return self.__show_request_form(trans, **kwd)
        elif params.get('refresh', False) == 'true':
            return self.__show_request_form(trans, **kwd)
    def __show_request_form(self, trans, **kwd):
        params = util.Params( kwd )
        msg = util.restore_text( params.get( 'msg', ''  ) )
        messagetype = params.get( 'messagetype', 'done' )
        try:
            request_type = trans.sa_session.query( trans.app.model.RequestType ).get( int( params.select_request_type ) )
        except:
            return trans.fill_template( '/requests/new_request.mako',
                                        select_request_type=self.__select_request_type(trans, 'none'),                                 
                                        widgets=[],                                   
                                        msg=msg,
                                        messagetype=messagetype)
        form_values = None
        select_request_type = self.__select_request_type(trans, request_type.id)
        # list of widgets to be rendered on the request form
        widgets = []
        widgets.append(dict(label='Name of the Experiment', 
                            widget=TextField('name', 40, 
                                             util.restore_text( params.get( 'name', ''  ) )), 
                            helptext='(Required)'))
        widgets.append(dict(label='Description', 
                            widget=TextField('desc', 40,
                                             util.restore_text( params.get( 'desc', ''  ) )), 
                            helptext='(Optional)'))
       
        # libraries selectbox
        libui = self.__library_ui(trans, request=None, **kwd)
        widgets = widgets + libui
        widgets = widgets + request_type.request_form.get_widgets( trans.user, **kwd )
        return trans.fill_template( '/requests/new_request.mako',
                                    select_request_type=select_request_type,
                                    request_type=request_type,
                                    widgets=widgets,
                                    msg=msg,
                                    messagetype=messagetype)
    def __library_ui(self, trans, request=None, **kwd):
        '''
        This method creates the data library & folder selectbox for new &
        editing requests. First we get a list of all the libraries accessible to
        the current user and display it in a selectbox. If the user has select an
        existing library then display all the accessible sub folders of the selected 
        data library. 
        '''
        params = util.Params( kwd )
        lib_id = params.get( 'library_id', 'none'  )
        selected_lib = None
        # if editing a request and the user has already associated a library to
        # this request, then set the selected_lib to the request.library
        if request and lib_id == 'none':
            if request.library:
                lib_id = str(request.library.id)
                selected_lib = request.library
        # get all permitted libraries for this user
        all_libraries = trans.sa_session.query( trans.app.model.Library ) \
                                        .filter( trans.app.model.Library.table.c.deleted == False ) \
                                        .order_by( trans.app.model.Library.name )
        user, roles = trans.get_user_and_roles()
        actions_to_check = [ trans.app.security_agent.permitted_actions.LIBRARY_ADD ]
        libraries = odict()
        for library in all_libraries:
            can_show, hidden_folder_ids = trans.app.security_agent.show_library_item( user, roles, library, actions_to_check )
            if can_show:
                libraries[ library ] = hidden_folder_ids
        # create data library selectbox with refresh on change enabled
        lib_id_list = ['new'] + [str(lib.id) for lib in libraries.keys()]
        lib_list = SelectField( 'library_id', refresh_on_change=True, refresh_on_change_values=lib_id_list )
        # fill up the options in the Library selectbox
        # first option 'none' is the value for "Select one" option
        if lib_id == 'none':
            lib_list.add_option('Select one', 'none', selected=True)
        else:
            lib_list.add_option('Select one', 'none')
        # add all the libraries available to the user to the library selectbox
        for lib, hidden_folder_ids in libraries.items():
            if str(lib.id) == lib_id:
                lib_list.add_option(lib.name, lib.id, selected=True)
                selected_lib, selected_hidden_folder_ids = lib, hidden_folder_ids.split(',')
            else:
                lib_list.add_option(lib.name, lib.id)
            lib_list.refresh_on_change_values.append(lib.id)
        # new library option
        if lib_id == 'new':
            lib_list.add_option('Create a new data library', 'new', selected=True)
        else:
            lib_list.add_option('Create a new data library', 'new')
        # data library widget
        lib_widget = dict(label='Data library', 
                          widget=lib_list, 
                          helptext='Data library where the resultant dataset will be stored.')
        # show the folder widget only if the user has selected a valid library above
        if selected_lib:
            # when editing a request, either the user has already selected a subfolder or not
            if request:
                if request.folder:
                    current_fid = request.folder.id
                else: 
                    # when a folder not yet associated with the request then the 
                    # the current folder is set to the root_folder of the 
                    # parent data library if present. 
                    if request.library:
                        current_fid = request.library.root_folder.id
                    else:
                        current_fid = params.get( 'folder_id', 'none'  )
            else:
                current_fid = params.get( 'folder_id', 'none'  )
            # create the folder selectbox
            folder_list = SelectField( 'folder_id')
            # first option
            if lib_id == 'none':
                folder_list.add_option('Select one', 'none', selected=True)
            else:
                folder_list.add_option('Select one', 'none')
            # get all show-able folders for the selected library
            showable_folders = trans.app.security_agent.get_showable_folders( user, roles, 
                                                                              selected_lib, 
                                                                              actions_to_check, 
                                                                              selected_hidden_folder_ids )
            # add all the folders to the folder selectbox
            for f in showable_folders:
                if str(f.id) == str(current_fid):
                    folder_list.add_option(f.name, f.id, selected=True)
                else:
                    folder_list.add_option(f.name, f.id)
            # folder widget
            folder_widget = dict(label='Folder', 
                                 widget=folder_list, 
                                 helptext='Folder of the selected data library where the resultant dataset will be stored.')
        if lib_id == 'new':
            new_lib = dict(label='Create a new data library', 
                           widget=TextField('new_library_name', 40,
                                     util.restore_text( params.get( 'new_library_name', ''  ) )), 
                           helptext='Enter a name here to request a new data library')
            return [lib_widget, new_lib]
        else:
            if selected_lib:
                return [lib_widget, folder_widget]
            else:
                return [lib_widget]
    def __validate(self, trans, request):
        '''
        Validates the request entered by the user 
        '''
        empty_fields = []
        # check rest of the fields of the form
        for index, field in enumerate(request.type.request_form.fields):
            if field['required'] == 'required' and request.values.content[index] in ['', None]:
                empty_fields.append(field['label'])
        if empty_fields:
            msg = 'Fill the following fields of the request <b>%s</b> before submitting<br/>' % request.name
            for ef in empty_fields:
                msg = msg + '<b>' +ef + '</b><br/>'
            return msg
        return None
    def __save_request(self, trans, request=None, **kwd):
        '''
        This method saves a new request if request_id is None. 
        '''
        params = util.Params( kwd )
        request_type = trans.sa_session.query( trans.app.model.RequestType ).get( int( params.select_request_type ) )
        name = util.restore_text(params.get('name', ''))
        desc = util.restore_text(params.get('desc', ''))
        # library
        try:
            library = trans.sa_session.query( trans.app.model.Library ).get( int( params.get( 'library_id', None ) ) )
        except:
            library = None
        try:
            folder = trans.sa_session.query( trans.app.model.LibraryFolder ).get( int( params.get( 'folder_id', None ) ) )
        except:
            if library:
                folder = library.root_folder
            else:
                folder = None
        # fields
        values = []
        for index, field in enumerate(request_type.request_form.fields):
            if field['type'] == 'AddressField':
                value = util.restore_text(params.get('field_%i' % index, ''))
                if value == 'new':
                    # save this new address in the list of this user's addresses
                    user_address = trans.app.model.UserAddress( user=trans.user )
                    user_address.desc = util.restore_text(params.get('field_%i_short_desc' % index, ''))
                    user_address.name = util.restore_text(params.get('field_%i_name' % index, ''))
                    user_address.institution = util.restore_text(params.get('field_%i_institution' % index, ''))
                    user_address.address = util.restore_text(params.get('field_%i_address1' % index, ''))+' '+util.restore_text(params.get('field_%i_address2' % index, ''))
                    user_address.city = util.restore_text(params.get('field_%i_city' % index, ''))
                    user_address.state = util.restore_text(params.get('field_%i_state' % index, ''))
                    user_address.postal_code = util.restore_text(params.get('field_%i_postal_code' % index, ''))
                    user_address.country = util.restore_text(params.get('field_%i_country' % index, ''))
                    user_address.phone = util.restore_text(params.get('field_%i_phone' % index, ''))
                    user_address.flush()
                    trans.sa_session.refresh( trans.user )
                    values.append(int(user_address.id))
                elif value == unicode('none'):
                    values.append('')
                else:
                    values.append(int(value))
            elif field['type'] == 'CheckboxField':
                values.append(CheckboxField.is_checked( params.get('field_%i' % index, '') )) 
            else:
                values.append(util.restore_text(params.get('field_%i' % index, '')))
        form_values = trans.app.model.FormValues(request_type.request_form, values)
        form_values.flush()
        if not request:
            request = trans.app.model.Request(name, desc, request_type, 
                                              trans.user, form_values,
                                              library=library, folder=folder, 
                                              state=trans.app.model.Request.states.UNSUBMITTED)
            request.flush()
        else:
            request.name = name
            request.desc = desc
            request.type = request_type
            request.user = trans.user
            request.values = form_values
            request.library = library
            request.folder = folder
            request.state = trans.app.model.Request.states.UNSUBMITTED
            request.flush()
        return request
    @web.expose
    @web.require_login( "create/submit sequencing requests" )
    def edit(self, trans, **kwd):
        params = util.Params( kwd )
        msg = util.restore_text( params.get( 'msg', ''  ) )
        messagetype = params.get( 'messagetype', 'done' )
        try:
            request = trans.sa_session.query( trans.app.model.Request ).get( int( params.get( 'request_id', None ) ) )
        except:
            return trans.response.send_redirect( web.url_for( controller='requests',
                                                              action='list',
                                                              status='error',
                                                              message="Invalid request ID",
                                                              **kwd) )
        if params.get('show', False) == 'True':
            return self.__edit_request(trans, request.id, **kwd)
        elif params.get('save_changes_request_button', False) == 'Save changes' \
             or params.get('edit_samples_button', False) == 'Edit samples':
                request_type = trans.sa_session.query( trans.app.model.RequestType ).get( int( params.select_request_type ) )
                if not util.restore_text(params.get('name', '')):
                    msg = 'Please enter the <b>Name</b> of the request'
                    kwd['messagetype'] = 'error'
                    kwd['msg'] = msg
                    kwd['show'] = 'True'
                    return trans.response.send_redirect( web.url_for( controller='requests',
                                                                      action='edit',
                                                                      **kwd) )
                request = self.__save_request(trans, request, **kwd)
                msg = 'The changes made to the request named %s has been saved' % request.name
                if params.get('save_changes_request_button', False) == 'Save changes':
                    return trans.response.send_redirect( web.url_for( controller='requests',
                                                                      action='list',
                                                                      message=msg ,
                                                                      status='done') )
                elif params.get('edit_samples_button', False) == 'Edit samples':
                    new_kwd = {}
                    new_kwd['request_id'] = request.id
                    new_kwd['edit_samples_button'] = 'Edit samples'
                    return trans.response.send_redirect( web.url_for( controller='requests',
                                                                      action='show_request',
                                                                      msg=msg ,
                                                                      messagetype='done',
                                                                      **new_kwd) )
        elif params.get('refresh', False) == 'true':
            return self.__edit_request(trans, request.id, **kwd)
            
    def __edit_request(self, trans, id, **kwd):
        try:
            request = trans.sa_session.query( trans.app.model.Request ).get( id )
        except:
            msg = "Invalid request ID"
            log.warn( msg )
            return trans.response.send_redirect( web.url_for( controller='requests',
                                                              action='list',
                                                              status='error',
                                                              message=msg) )
        params = util.Params( kwd )
        msg = util.restore_text( params.get( 'msg', ''  ) )
        messagetype = params.get( 'messagetype', 'done' )
        select_request_type = self.__select_request_type(trans, request.type.id)
        # list of widgets to be rendered on the request form
        widgets = []
        if util.restore_text( params.get( 'name', ''  ) ):
            name = util.restore_text( params.get( 'name', ''  ) )
        else:
            name = request.name
        widgets.append(dict(label='Name', 
                            widget=TextField('name', 40, name), 
                            helptext='(Required)'))
        if util.restore_text( params.get( 'desc', ''  ) ):
            desc = util.restore_text( params.get( 'desc', ''  ) )
        else:
            desc = request.desc
        widgets.append(dict(label='Description', 
                            widget=TextField('desc', 40, desc), 
                            helptext='(Optional)'))
        # libraries selectbox
        libui = self.__library_ui(trans, request, **kwd)
        widgets = widgets + libui
        widgets = widgets + request.type.request_form.get_widgets( trans.user, request.values.content, **kwd )
        return trans.fill_template( '/requests/edit_request.mako',
                                    select_request_type=select_request_type,
                                    request_type=request.type,
                                    request=request,
                                    widgets=widgets,
                                    msg=msg,
                                    messagetype=messagetype)
        return self.__show_request_form(trans)
    def __delete_request(self, trans, id):
        try:
            request = trans.sa_session.query( trans.app.model.Request ).get( id )
        except:
            msg = "Invalid request ID"
            log.warn( msg )
            return trans.response.send_redirect( web.url_for( controller='requests',
                                                              action='list',
                                                              status='error',
                                                              message=msg,
                                                              **kwd) )
        # change request's submitted field
        if not request.unsubmitted():
            return trans.response.send_redirect( web.url_for( controller='requests',
                                                              action='list',
                                                              status='error',
                                                              message='This request cannot be deleted as it is already been submitted',
                                                              **kwd) )
        request.deleted = True
        request.flush()
        kwd = {}
        kwd['id'] = trans.security.encode_id(request.id)
        return trans.response.send_redirect( web.url_for( controller='requests',
                                                          action='list',
                                                          status='done',
                                                          message='The request <b>%s</b> has been deleted.' % request.name,                                                          
                                                          **kwd) )
    def __undelete_request(self, trans, id):
        try:
            request = trans.sa_session.query( trans.app.model.Request ).get( id )
        except:
            msg = "Invalid request ID"
            log.warn( msg )
            return trans.response.send_redirect( web.url_for( controller='requests',
                                                              action='list',
                                                              status='error',
                                                              message=msg,
                                                              **kwd) )
        # change request's submitted field
        request.deleted = False
        request.flush()
        kwd = {}
        kwd['id'] = trans.security.encode_id(request.id)
        return trans.response.send_redirect( web.url_for( controller='requests',
                                                          action='list',
                                                          status='done',
                                                          message='The request <b>%s</b> has been undeleted.' % request.name,                                                          
                                                          **kwd) )
    def __submit_request(self, trans, id):
        try:
            request = trans.sa_session.query( trans.app.model.Request ).get( id )
        except:
            msg = "Invalid request ID"
            log.warn( msg )
            return trans.response.send_redirect( web.url_for( controller='requests',
                                                              action='list',
                                                              status='error',
                                                              message=msg,
                                                              **kwd) )
        msg = self.__validate(trans, request)
        if msg:
            return trans.response.send_redirect( web.url_for( controller='requests',
                                                              action='edit',
                                                              messagetype = 'error',
                                                              msg=msg,
                                                              request_id=request.id,
                                                              show='True') )
        # get the new state
        new_state = request.type.states[0]
        for s in request.samples:
            event = trans.app.model.SampleEvent(s, new_state, 'Samples submitted to the system')
            event.flush()
        # change request's submitted field
        request.state = request.states.SUBMITTED
        request.flush()
        kwd = {}
        kwd['id'] = trans.security.encode_id(request.id)
        kwd['status'] = 'done'
        kwd['message'] = 'The request <b>%s</b> has been submitted.' % request.name
        return trans.response.send_redirect( web.url_for( controller='requests',
                                                          action='list',
                                                          show_filter=trans.app.model.Request.states.SUBMITTED,
                                                          **kwd) )
    @web.expose
    @web.require_login( "create/submit sequencing requests" )
    def show_events(self, trans, **kwd):
        params = util.Params( kwd )
        try:
            sample_id = int(params.get('sample_id', False))
            sample = trans.sa_session.query( trans.app.model.Sample ).get( sample_id )
        except:
            msg = "Invalid sample ID"
            return trans.response.send_redirect( web.url_for( controller='requests',
                                                              action='list',
                                                              status='error',
                                                              message=msg,
                                                              **kwd) )
        events_list = []
        all_events = sample.events
        for event in all_events:
            delta = datetime.utcnow() - event.update_time
            if delta > timedelta( minutes=60 ):
                last_update = '%s hours' % int( delta.seconds / 60 / 60 )
            else:
                last_update = '%s minutes' % int( delta.seconds / 60 )
            events_list.append((event.state.name, event.state.desc, last_update, event.comment))
        return trans.fill_template( '/sample/sample_events.mako', 
                                    events_list=events_list,
                                    sample_name=sample.name,
                                    request=sample.request)
