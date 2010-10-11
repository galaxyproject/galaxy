from galaxy.web.base.controller import *
from galaxy.web.framework.helpers import time_ago, iff, grids
from galaxy.model.orm import *
from galaxy import model, util
from galaxy.web.form_builder import *
from galaxy.web.controllers.requests_common import RequestsGrid, invalid_id_redirect
from amqplib import client_0_8 as amqp
import logging, os, pexpect, ConfigParser

log = logging.getLogger( __name__ )

class UserColumn( grids.TextColumn ):
    def get_value( self, trans, grid, request ):
        return request.user.email

class AdminRequestsGrid( RequestsGrid ):
    columns = [ col for col in RequestsGrid.columns ]
    columns.append( UserColumn( "User",
                                model_class=model.User,
                                key='username' ) )
    operations = [ operation for operation in RequestsGrid.operations ]
    operations.append( grids.GridOperation( "Edit", allow_multiple=False, condition=( lambda item: not item.deleted ) ) )
    operations.append( grids.GridOperation( "Reject", allow_multiple=False, condition=( lambda item: not item.deleted and item.is_submitted ) ) )
    operations.append( grids.GridOperation( "Delete", allow_multiple=True, condition=( lambda item: not item.deleted ) ) )
    operations.append( grids.GridOperation( "Undelete", condition=( lambda item: item.deleted ) ) )
    operations.append( grids.GridOperation( "Purge",
                                            allow_multiple=False,
                                            confirm="This will permanently delete this sequencing request. Click OK to proceed.",
                                            condition=( lambda item: item.deleted ) ) )
    global_actions = [
        grids.GridAction( "Create new request", dict( controller='requests_common',
                                                      action='create_request', 
                                                      cntrller='requests_admin' ) )
    ]

class RequestTypeGrid( grids.Grid ):
    # Custom column types
    class NameColumn( grids.TextColumn ):
        def get_value(self, trans, grid, request_type):
            return request_type.name
    class DescriptionColumn( grids.TextColumn ):
        def get_value(self, trans, grid, request_type):
            return request_type.desc
    class RequestFormColumn( grids.TextColumn ):
        def get_value(self, trans, grid, request_type):
            return request_type.request_form.name
    class SampleFormColumn( grids.TextColumn ):
        def get_value(self, trans, grid, request_type):
            return request_type.sample_form.name

    # Grid definition
    title = "Sequencer Configurations"
    template = "admin/requests/grid.mako"
    model_class = model.RequestType
    default_sort_key = "-create_time"
    num_rows_per_page = 50
    preserve_state = True
    use_paging = True
    default_filter = dict( deleted="False" )
    columns = [
        NameColumn( "Name", 
                    key="name",
                    link=( lambda item: iff( item.deleted, None, dict( operation="view", id=item.id ) ) ),
                    attach_popup=True,
                    filterable="advanced" ),
        DescriptionColumn( "Description",
                           key='desc',
                           filterable="advanced" ),
        RequestFormColumn( "Request Form", 
                           link=( lambda item: iff( item.deleted, None, dict( operation="view_form", id=item.request_form.id ) ) ) ),
        SampleFormColumn( "Sample Form", 
                           link=( lambda item: iff( item.deleted, None, dict( operation="view_form", id=item.sample_form.id ) ) ) ),
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
        grids.GridOperation( "Permissions", allow_multiple=False, condition=( lambda item: not item.deleted  )  ),
        grids.GridOperation( "Delete", allow_multiple=True, condition=( lambda item: not item.deleted  )  ),
        grids.GridOperation( "Undelete", condition=( lambda item: item.deleted ) ),    
    ]
    global_actions = [
        grids.GridAction( "Create new sequencer configuration", dict( controller='requests_admin', action='create_request_type' ) )
    ]

class DataTransferGrid( grids.Grid ):
    # Custom column types
    class NameColumn( grids.TextColumn ):
        def get_value( self, trans, grid, sample_dataset ):
            return sample_dataset.name
    class SizeColumn( grids.TextColumn ):
        def get_value( self, trans, grid, sample_dataset ):
            return sample_dataset.size
    class StatusColumn( grids.TextColumn ):
        def get_value( self, trans, grid, sample_dataset ):
            return sample_dataset.status
    # Grid definition
    title = "Sample Datasets"
    # TODO: can this be grid.mako???
    template = "admin/requests/datasets_grid.mako"
    model_class = model.SampleDataset
    default_sort_key = "-create_time"
    num_rows_per_page = 50
    preserve_state = True
    use_paging = True
    columns = [
        NameColumn( "Name", 
                    #key="name", 
                    link=( lambda item: dict( operation="view", id=item.id ) ),
                    attach_popup=True,
                    filterable="advanced" ),
        SizeColumn( "Size",
                    #key='size',
                    filterable="advanced" ),
        grids.GridColumn( "Last Updated", key="update_time", format=time_ago ),
        StatusColumn( "Status",
                      #key='status',
                      filterable="advanced" ),
    ]
    columns.append( grids.MulticolFilterColumn( "Search", 
                                                cols_to_filter=[ columns[0] ], 
                                                key="free-text-search",
                                                visible=False,
                                                filterable="standard" ) )
    operations = [
        grids.GridOperation( "Start Transfer", allow_multiple=True, condition=( lambda item: item.status in [ model.Sample.transfer_status.NOT_STARTED ] ) ),
        grids.GridOperation( "Rename", allow_multiple=True, allow_popup=False, condition=( lambda item: item.status in [ model.Sample.transfer_status.NOT_STARTED ] ) ),
        grids.GridOperation( "Delete", allow_multiple=True, condition=( lambda item: item.status in [ model.Sample.transfer_status.NOT_STARTED ] )  ),
    ]
    def apply_query_filter( self, trans, query, **kwd ):
        sample_id = kwd.get( 'sample_id', None )
        if not sample_id:
            return query
        return query.filter_by( sample_id=trans.security.decode_id( sample_id ) )

class RequestsAdmin( BaseController, UsesFormDefinitionWidgets ):
    request_grid = AdminRequestsGrid()
    requesttype_grid = RequestTypeGrid()
    datatx_grid = DataTransferGrid()

    @web.expose
    @web.require_admin
    def index( self, trans ):
        return trans.fill_template( "/admin/requests/index.mako" )
    @web.expose
    @web.require_admin
    def browse_requests( self, trans, **kwd ):
        if 'operation' in kwd:
            operation = kwd['operation'].lower()
            if operation == "edit":
                return trans.response.send_redirect( web.url_for( controller='requests_common',
                                                                  action='edit_basic_request_info',
                                                                  cntrller='requests_admin',
                                                                  **kwd ) )
            if operation == "manage_request":
                return trans.response.send_redirect( web.url_for( controller='requests_common',
                                                                  action='manage_request',
                                                                  cntrller='requests_admin',
                                                                  **kwd ) )
            if operation == "reject":
                return self.reject_request( trans, **kwd )
            if operation == "view_type":
                return self.view_request_type( trans, **kwd )
            if operation == "delete":
                return trans.response.send_redirect( web.url_for( controller='requests_common',
                                                                  action='delete_request',
                                                                  cntrller='requests_admin',
                                                                  **kwd ) )
            if operation == "undelete":
                return trans.response.send_redirect( web.url_for( controller='requests_common',
                                                                  action='undelete_request',
                                                                  cntrller='requests_admin',
                                                                  **kwd ) )
        # Render the list view
        return self.request_grid( trans, **kwd )
    @web.json
    def get_file_details( self, trans, id, folder_path ):
        def print_ticks( d ):
            # TODO: why is this method here?  Add comments!
            pass
        # Avoid caching
        trans.response.headers['Pragma'] = 'no-cache'
        trans.response.headers['Expires'] = '0'
        request = trans.sa_session.query( trans.model.Request ).get( int( id ) )
        datatx_info = request.type.datatx_info
        cmd  = 'ssh %s@%s "ls -oghp \'%s\'"' % ( datatx_info['username'],
                                                 datatx_info['host'],
                                                 folder_path )
        output = pexpect.run( cmd,
                              events={ '.ssword:*' : datatx_info[ 'password'] + '\r\n', pexpect.TIMEOUT : print_ticks }, 
                              timeout=10 )
        return unicode( output.replace( '\n', '<br/>' ) )
    @web.json
    def open_folder( self, trans, id, folder_path ):
        def print_ticks( d ):
            pass
        # Avoid caching
        trans.response.headers['Pragma'] = 'no-cache'
        trans.response.headers['Expires'] = '0'
        request = trans.sa_session.query( trans.model.Request ).get( int( id ) )
        return self.__get_files( trans, request.type, folder_path )
    @web.expose
    @web.require_admin
    def reject( self, trans, **kwd ):
        params = util.Params( kwd )
        request_id = params.get( 'id', '' )
        status = params.get( 'status', 'done' )
        message = params.get( 'message', 'done' )
        if params.get( 'cancel_reject_button', False ):
            return trans.response.send_redirect( web.url_for( controller='requests_common',
                                                              action='manage_request',
                                                              cntrller='requests_admin',
                                                              id=request_id ) )
        try:
            request = trans.sa_session.query( trans.model.Request ).get( trans.security.decode_id( request_id ) )
        except:
            return invalid_id_redirect( trans, 'requests_admin', request_id )
        # Validate
        comment = util.restore_text( params.get( 'comment', '' ) )
        if not comment:
            status='error'
            message='A reason for rejecting the request is required.'
            return trans.fill_template( '/admin/requests/reject.mako', 
                                        cntrller='requests_admin',
                                        request=request,
                                        status=status,
                                        message=message )
        # Create an event with state 'Rejected' for this request
        event = trans.model.RequestEvent( request, request.states.REJECTED, comment )
        trans.sa_session.add( event )
        trans.sa_session.flush()
        message='Request (%s) has been rejected.' % request.name
        return trans.response.send_redirect( web.url_for( controller='requests_admin',
                                                          action='browse_requests',
                                                          status=status,
                                                          message=message,
                                                          **kwd ) )
    # Data transfer from sequencer
    @web.expose
    @web.require_admin
    def manage_datasets( self, trans, **kwd ):
        if 'operation' in kwd:
            operation = kwd[ 'operation' ].lower()
            dataset_id = kwd.get( 'id', None )
            if not dataset_id:
                return invalid_id_redirect( trans, 'requests_admin', dataset_id )
            id_list = util.listify( dataset_id )
            if operation == "view":
                sample_dataset_id = trans.security.decode_id( kwd['id'] )
                sample_dataset = trans.sa_session.query( trans.model.SampleDataset ).get( sample_dataset_id )
                return trans.fill_template( '/admin/requests/dataset.mako',
                                            sample_dataset=sample_dataset )
            elif operation == "delete":
                not_deleted = []
                for id in id_list:
                    sample_dataset = trans.sa_session.query( trans.model.SampleDataset ).get( trans.security.decode_id( id ) )
                    sample_id = sample_dataset.sample_id
                    if sample_dataset.status == sample_dataset.sample.transfer_status.NOT_STARTED:
                        trans.sa_session.delete( sample_dataset )
                        trans.sa_session.flush()
                    else:
                        not_deleted.append( sample_dataset.name )
                message = '%i datasets have been successfully deleted. ' % ( len( id_list ) - len( not_deleted ) )
                status = 'done'
                if not_deleted:
                    status = 'warning'
                    message = message + '%s could not be deleted because their transfer status is not "Not Started". ' % str( not_deleted )
                return trans.response.send_redirect( web.url_for( controller='requests_admin',
                                                                  action='manage_datasets',
                                                                  sample_id=trans.security.encode_id( sample_id ),
                                                                  status=status,
                                                                  message=message ) )
            elif operation == "rename":
                sample_dataset_id = id_list[0]
                sample_dataset = trans.sa_session.query( trans.model.SampleDataset ).get( trans.security.decode_id( sample_dataset_id ) )
                return trans.fill_template( '/admin/requests/rename_datasets.mako', 
                                            sample=sample_dataset.sample,
                                            id_list=id_list )
            elif operation == "start transfer":
                sample_dataset_id = id_list[0]
                sample_dataset = trans.sa_session.query( trans.model.SampleDataset ).get( trans.security.decode_id( sample_dataset_id ) )
                self.__start_datatx( trans, sample_dataset.sample, id_list )
        # Render the grid view
        sample_id = kwd.get( 'sample_id', None )
        try:
            sample = trans.sa_session.query( trans.model.Sample ).get( trans.security.decode_id ( sample_id ) )
        except:
            return invalid_id_redirect( trans, 'requests_admin', sample_id )
        self.datatx_grid.title = 'Datasets of sample "%s"' % sample.name
        self.datatx_grid.global_actions = [ grids.GridAction( "Refresh", 
                                                              dict( controller='requests_admin', 
                                                                    action='manage_datasets',
                                                                    sample_id=sample_id ) ),
                                            grids.GridAction( "Select datasets", 
                                                              dict( controller='requests_admin', 
                                                                    action='get_data',
                                                                    request_id=trans.security.encode_id( sample.request.id ),
                                                                    folder_path=sample.request.type.datatx_info[ 'data_dir' ],
                                                                    sample_id=sample_id,
                                                                    show_page=True ) ),
                                            grids.GridAction( 'Data library "%s"' % sample.library.name, 
                                                              dict( controller='library_common', 
                                                                    action='browse_library', 
                                                                    cntrller='library_admin', 
                                                                    id=trans.security.encode_id( sample.library.id ) ) ),
                                            grids.GridAction( "Browse this request", 
                                                              dict( controller='requests_common', 
                                                                    action='manage_request',
                                                                    cntrller='requests_admin',
                                                                    id=trans.security.encode_id( sample.request.id ) ) ) ]
        return self.datatx_grid( trans, **kwd )
    @web.expose
    @web.require_admin
    def rename_datasets( self, trans, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        sample_id = kwd.get( 'sample_id', None )
        try:
            sample = trans.sa_session.query( trans.model.Sample ).get( trans.security.decode_id( sample_id ) )
        except:
            return invalid_id_redirect( trans, 'requests_admin', sample_id )
        if params.get( 'save_button', False ):
            id_list = util.listify( kwd['id_list'] )
            for id in id_list:
                sample_dataset = trans.sa_session.query( trans.model.SampleDataset ).get( trans.security.decode_id( id ) )
                prepend = util.restore_text( params.get( 'prepend_%i' % sample_dataset.id, ''  ) )
                name = util.restore_text( params.get( 'name_%i' % sample_dataset.id, sample_dataset.name ) )
                if prepend == 'None':
                    sample_dataset.name = name
                else: 
                    sample_dataset.name = '%s_%s' % ( prepend, name )
                trans.sa_session.add( sample_dataset )
                trans.sa_session.flush()
            return trans.fill_template( '/admin/requests/rename_datasets.mako', 
                                        sample=sample,
                                        id_list=id_list,
                                        message='Changes saved successfully.',
                                        status='done' )
        return trans.response.send_redirect( web.url_for( controller='requests_admin',
                                                          action='manage_datasets',
                                                          sample_id=sample_id ) )
    def __get_files( self, trans, request_type, folder_path ):
        # Retrieves the filenames to be transferred from the remote host.
        # FIXME: sample is used in this method, but no sample obj is received...
        datatx_info = request_type.datatx_info
        if not datatx_info[ 'host' ] or not datatx_info[ 'username' ] or not datatx_info[ 'password' ]:
            status = 'error'
            message = "Error in sequencer login information." 
            return trans.response.send_redirect( web.url_for( controller='requests_common',
                                                              action='view_dataset_transfer', 
                                                              cntrller='requests_admin' ,
                                                              sample_id=trans.security.encode_id( sample.id ),
                                                              status=status,
                                                              message=message ) )
        def print_ticks( d ):
            pass
        cmd  = 'ssh %s@%s "ls -p \'%s\'"' % ( datatx_info['username'], datatx_info['host'], folder_path )
        output = pexpect.run( cmd,
                              events={ '.ssword:*' : datatx_info['password'] + '\r\n', pexpect.TIMEOUT : print_ticks }, 
                              timeout=10 )
        if 'No such file or directory' in output:
            status = 'error'
            message = "No folder named (%s) exists on the sequencer." % folder_path
            return trans.response.send_redirect( web.url_for( controller='requests_common',
                                                              action='view_dataset_transfer',
                                                              cntrller='requests_admin' ,
                                                              sample_id=trans.security.encode_id( sample.id ),
                                                              folder_path=folder_path,
                                                              status=status,
                                                              message=message ) ) 
        
        return output.splitlines()
    def __check_path( self, a_path ):
        # Return a valid folder_path
        if a_path and not a_path.endswith( os.sep ):
            a_path += os.sep
        return a_path
    def __build_sample_id_select_field( self, request, selected_value ):
        return build_select_field( trans, request.samples, 'name', 'sample_id', selected_value=selected_value, refresh_on_change=False )
    @web.expose
    @web.require_admin
    def get_data( self, trans, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', '' ) )
        status = params.get( 'status', 'done' )
        request_id = kwd.get( 'request_id', None )
        try:
            request = trans.sa_session.query( trans.model.Request ).get( request_id  )
        except:
            return invalid_id_redirect( trans, 'requests_admin', request_id )
        files_list = util.listify( params.get( 'files_list', '' ) ) 
        folder_path = util.restore_text( params.get( 'folder_path', request.type.datatx_info[ 'data_dir' ] ) )
        selected_value = kwd.get( 'sample_id', 'none' )
        sample_id_select_field = self.__build_sample_id_select_field( request, selected_value )
        if not folder_path:
            return trans.fill_template( '/admin/requests/dataset_transfer.mako',
                                        cntrller='requests_admin',
                                        request=request,
                                        sample_id_select_field=sample_id_select_field,
                                        files=[], 
                                        folder_path=folder_path )
        folder_path = self.__check_path( folder_path )
        sample_id = kwd.get( 'sample_id', None )
        if params.get( 'show_page', False ):
            if sample_id:
                sample = trans.sa_session.query( trans.model.Sample ).get( trans.security.decode_id( sample_id ) )
                if sample.datasets:
                    folder_path = os.path.dirname( sample.datasets[-1].file_path )
            return trans.fill_template( '/admin/requests/dataset_transfer.mako',
                                        cntrller='requests_admin',
                                        request=request,
                                        sample_id_select_field=sample_id_select_field,
                                        files=[], 
                                        folder_path=folder_path,
                                        status=status,
                                        message=message )
        elif params.get( 'browse_button', False ):
            # get the filenames from the remote host
            files = self.__get_files( trans, request.type, folder_path )
            return trans.fill_template( '/admin/requests/dataset_transfer.mako',
                                        cntrller='requests_admin',
                                        request=request,
                                        sample_id_select_field=sample_id_select_field,
                                        files=files, 
                                        folder_path=folder_path,
                                        status=status,
                                        message=message )
        elif params.get( 'folder_up', False ):
            # get the filenames from the remote host
            files = self.__get_files( trans, request.type, folder_path )
            return trans.fill_template( '/admin/requests/dataset_transfer.mako',
                                        cntrller='requests_admin',
                                        request=request,
                                        sample_id_select_field=sample_id_select_field,
                                        files=files, 
                                        folder_path=folder_path,
                                        status=status,
                                        message=message )
        elif params.get( 'open_folder', False ):
            if len( files_list ) == 1:
                folder_path = os.path.join( folder_path, files_list[0] )
                folder_path = self.__check_path( folder_path )
            # get the filenames from the remote host
            files = self.__get_files( trans, request.type, folder_path )
            return trans.fill_template( '/admin/requests/dataset_transfer.mako',
                                        cntrller='requests_admin',
                                        request=request,
                                        sample_id_select_field=sample_id_select_field,
                                        files=files, 
                                        folder_path=folder_path,
                                        status=status,
                                        message=message )
        elif params.get( 'select_show_datasets_button', False ):
            sample = trans.sa_session.query( trans.model.Sample ).get( trans.security.decode_id( sample_id ) )
            retval = self.__save_sample_datasets( trans, sample, files_list, folder_path )
            if retval:
                message = 'The datasets %s have been selected for sample <b>%s</b>' % ( str( retval )[1:-1].replace( "'", "" ), sample.name )
            return trans.response.send_redirect( web.url_for( controller='requests_admin',
                                                              action='manage_datasets',
                                                              sample_id=sample_id,
                                                              message=message,
                                                              status=status ) )
        elif params.get( 'select_more_button', False ):
            sample = trans.sa_session.query( trans.model.Sample ).get( trans.security.decode_id( sample_id ) )
            retval = self.__save_sample_datasets( trans, sample, files_list, folder_path )
            if retval:
                message='The datasets %s have been selected for sample <b>%s</b>' % ( str( retval )[1:-1].replace( "'", "" ), sample.name )
            return trans.response.send_redirect( web.url_for( controller='requests_admin',
                                                              action='get_data', 
                                                              request_id=trans.security.encode_id( sample.request.id ),
                                                              folder_path=folder_path,
                                                              sample_id=sample_id,
                                                              open_folder=True,
                                                              message=message,
                                                              status=status ) )
        return trans.response.send_redirect( web.url_for( controller='requests_admin',
                                                          action='get_data', 
                                                          request_id=trans.security.encode_id( sample.request.id ),
                                                          folder_path=folder_path,
                                                          show_page=True ) )
    def __save_sample_datasets( self, trans, sample, files_list, folder_path ):
        files = []
        if files_list:
            for f in files_list:
                filepath = os.path.join( folder_path, f )
                if f[-1] == os.sep:
                    # the selected item is a folder so transfer all the folder contents
                    # FIXME 
                    #self.__get_files_in_dir(trans, sample, filepath)
                    return trans.response.send_redirect( web.url_for( controller='requests_admin',
                                                                      action='get_data', 
                                                                      request=sample.request,
                                                                      folder_path=folder_path,
                                                                      open_folder=True ) )
                else:
                    sample_dataset = trans.model.SampleDataset( sample=sample,
                                                                file_path=filepath,
                                                                status=sample.transfer_status.NOT_STARTED,
                                                                name=self.__dataset_name( sample, filepath.split( '/' )[-1] ),
                                                                error_msg='',
                                                                size=sample.dataset_size( filepath ) )
                    trans.sa_session.add( sample_dataset )
                    trans.sa_session.flush()
                    files.append( str( sample_dataset.name ) )
        return files
    def __dataset_name( self, sample, filepath ):
        name = filepath.split( '/' )[-1]
        options = sample.request.type.rename_dataset_options
        option = sample.request.type.datatx_info.get( 'rename_dataset', options.NO ) 
        if option == options.NO:
            return name
        elif option == options.SAMPLE_NAME:
            return sample.name + '_' + name
        elif option == options.EXPERIMENT_AND_SAMPLE_NAME:
            return sample.request.name + '_' + sample.name + '_' + name
        elif opt == options.EXPERIMENT_NAME:
            return sample.request.name + '_' + name
    def __setup_datatx_user( self, trans, library, folder ):
        """
        Sets up the datatx user:
        - Checks if the user exists, if not creates them.
        - Checks if the user had ADD_LIBRARY permission on the target library
          and the target folder, if not sets up the permissions.
        """
        # Retrieve the upload user login information from the config file
        config = ConfigParser.ConfigParser()
        config.read( 'transfer_datasets.ini' )
        email = config.get( "data_transfer_user_login_info", "email" )
        password = config.get( "data_transfer_user_login_info", "password" )
        # check if the user already exists
        datatx_user = trans.sa_session.query( trans.model.User ) \
                                      .filter( trans.model.User.table.c.email==email ) \
                                      .first()
        if not datatx_user:
            # if not create the user
            datatx_user = trans.model.User( email=email, password=passsword )
            if trans.app.config.use_remote_user:
                datatx_user.external = True
            trans.sa_session.add( datatx_user )
            trans.sa_session.flush()
            trans.app.security_agent.create_private_user_role( datatx_user )
            trans.app.security_agent.user_set_default_permissions( datatx_user, history=False, dataset=False )
        datatx_user_roles = datatx_user.all_roles()
        datatx_user_private_role = trans.app.security_agent.get_private_user_role( datatx_user )
        # Make sure this user has LIBRARY_ADD permissions on the target library and folder.
        # If not, give them permission.
        if not trans.app.security_agent.can_add_library_item( datatx_user_roles, library ):
            lp = trans.model.LibraryPermissions( trans.app.security_agent.permitted_actions.LIBRARY_ADD.action,
                                                 library, 
                                                 datatx_user_private_role )
            trans.sa_session.add( lp )
        if not trans.app.security_agent.can_add_library_item( datatx_user_roles, folder ):
            lfp = trans.model.LibraryFolderPermissions( trans.app.security_agent.permitted_actions.LIBRARY_ADD.action,
                                                        folder, 
                                                        datatx_user_private_role )
            trans.sa_session.add( dp )
            trans.sa_session.flush()
        return datatx_user
    def __send_message( self, trans, datatx_info, sample, id_list ):
        """Ceates an xml message and sends it to the rabbitmq server"""
        # Create the xml message based on the following template
        xml = \
            ''' <data_transfer>
                    <data_host>%(DATA_HOST)s</data_host>
                    <data_user>%(DATA_USER)s</data_user>
                    <data_password>%(DATA_PASSWORD)s</data_password>
                    <sample_id>%(SAMPLE_ID)s</sample_id>
                    <library_id>%(LIBRARY_ID)s</library_id>
                    <folder_id>%(FOLDER_ID)s</folder_id>
                    %(DATASETS)s
                </data_transfer>'''
        dataset_xml = \
            '''<dataset>
                   <dataset_id>%(ID)s</dataset_id>
                   <name>%(NAME)s</name>
                   <file>%(FILE)s</file>
               </dataset>'''
        datasets = ''
        for id in id_list:
            sample_dataset = trans.sa_session.query( trans.model.SampleDataset ).get( trans.security.decode_id( id ) )
            if sample_dataset.status == sample.transfer_status.NOT_STARTED:
                datasets = datasets + dataset_xml % dict( ID=str( sample_dataset.id ),
                                                          NAME=sample_dataset.name,
                                                          FILE=sample_dataset.file_path )
                sample_dataset.status = sample.transfer_status.IN_QUEUE
                trans.sa_session.add( sample_dataset )
                trans.sa_session.flush()
        data = xml % dict( DATA_HOST=datatx_info['host'],
                           DATA_USER=datatx_info['username'],
                           DATA_PASSWORD=datatx_info['password'],
                           SAMPLE_ID=str(sample.id),
                           LIBRARY_ID=str(sample.library.id),
                           FOLDER_ID=str(sample.folder.id),
                           DATASETS=datasets )
        # Send the message 
        conn = amqp.Connection( host=trans.app.config.amqp['host'] + ":" + trans.app.config.amqp['port'], 
                                userid=trans.app.config.amqp['userid'], 
                                password=trans.app.config.amqp['password'], 
                                virtual_host=trans.app.config.amqp['virtual_host'], 
                                insist=False )    
        chan = conn.channel()
        msg = amqp.Message( data.replace( '\n', '' ).replace( '\r', '' ), 
                            content_type='text/plain', 
                            application_headers={'msg_type': 'data_transfer'} )
        msg.properties["delivery_mode"] = 2
        chan.basic_publish( msg,
                            exchange=trans.app.config.amqp['exchange'],
                            routing_key=trans.app.config.amqp['routing_key'] )
        chan.close()
        conn.close()
    def __start_datatx( self, trans, sample, id_list ):
        datatx_user = self.__setup_datatx_user( trans, sample.library, sample.folder )
        # Validate sequencer information
        datatx_info = sample.request.type.datatx_info
        if not datatx_info['host'] or not datatx_info['username'] or not datatx_info['password']:
            message = "Error in sequencer login information."
            status = "error"
        else:
            self.__send_message( trans, datatx_info, sample, id_list )
            message = "%i datasets have been queued for transfer from the sequencer. Click on <b>Refresh</b> button above to get the latest transfer status." % len( id_list )
            status = "done"
        return trans.response.send_redirect( web.url_for( controller='requests_admin',
                                                          action='manage_datasets',
                                                          sample_id=trans.security.encode_id( sample.id ),
                                                          status=status,
                                                          message=message) )
    # Request Type Stuff
    @web.expose
    @web.require_admin
    def manage_request_types( self, trans, **kwd ):
        if 'operation' in kwd:
            operation = kwd['operation'].lower()
            obj_id = kwd.get( 'id', None )
            if obj_id is None:
                return invalid_id_redirect( trans, 'requests_admin', obj_id, action='manage_request_types' )
            if operation == "view":
                return self.__view_request_type( trans, **kwd )
            elif operation == "view_form":
                return self.__view_form( trans, **kwd )
            elif operation == "delete":
                return self.__delete_request_type( trans, **kwd )
            elif operation == "undelete":
                return self.__undelete_request_type( trans, **kwd )
            elif operation == "clone":
                return self.__clone_request_type( trans, **kwd )
            elif operation == "permissions":
                return self.__show_request_type_permissions( trans, **kwd )
        # Render the grid view
        return self.requesttype_grid( trans, **kwd )
    def __view_request_type( self, trans, **kwd ):
        request_type_id = kwd.get( 'id', None )
        try:
            request_type = trans.sa_session.query( trans.model.RequestType ).get( trans.security.decode_id( request_type_id ) )
        except:
            return invalid_id_redirect( trans, 'requests_admin', request_type_id, action='manage_request_types' )
        forms = self.get_all_forms( trans )
        rename_dataset_selectbox = self.__build_rename_dataset_select_list( trans, request_type )
        return trans.fill_template( '/admin/requests/view_request_type.mako', 
                                    request_type=request_type,
                                    forms=forms,
                                    rename_dataset_selectbox=rename_dataset_selectbox )
    def __view_form(self, trans, **kwd):
        form_definition_id = kwd.get( 'id', None )
        try:
            form_definition = trans.sa_session.query( trans.model.FormDefinition ).get( trans.security.decode_id( form_definition_id ) )
        except:
            return invalid_id_redirect( trans, 'requests_admin', form_definition_id, action='manage_request_types' )
        return trans.fill_template( '/admin/forms/show_form_read_only.mako',
                                    form_definition=form_definition )
    @web.expose
    @web.require_admin
    def create_request_type( self, trans, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )   
        if params.get( 'add_state_button', False ):
            rt_info_widgets, rt_states_widgets = self.__create_request_type_form( trans, **kwd )
            rt_states_widgets.append( ( "", "" ) )
            rename_dataset_selectbox = self.__build_rename_dataset_select_list( trans )
            return trans.fill_template( '/admin/requests/create_request_type.mako', 
                                        rt_info_widgets=rt_info_widgets,
                                        rt_states_widgets=rt_states_widgets,
                                        rename_dataset_selectbox=rename_dataset_selectbox,
                                        message=message,
                                        status=status )
        elif params.get( 'remove_state_button', False ):
            rt_info_widgets, rt_states_widgets = self.__create_request_type_form( trans, **kwd )
            index = int( params.get( 'remove_state_button', '' ).split(" ")[2] )
            del rt_states_widgets[ index-1 ]
            rename_dataset_selectbox = self.__build_rename_dataset_select_list( trans )
            return trans.fill_template( '/admin/requests/create_request_type.mako', 
                                        rt_info_widgets=rt_info_widgets,
                                        rt_states_widgets=rt_states_widgets,
                                        rename_dataset_selectbox=rename_dataset_selectbox,
                                        message=message,
                                        status=status )
        elif params.get( 'save_request_type', False ):
            request_type, message = self.__save_request_type( trans, **kwd )
            if not request_type:
                return trans.fill_template( '/admin/requests/create_request_type.mako', 
                                            message=message,
                                            status='error' )
            message = 'Sequencer configuration <b>%s</b> has been created' % request_type.name
            return trans.response.send_redirect( web.url_for( controller='requests_admin',
                                                              action='manage_request_types',
                                                              message=message,
                                                              status=status ) )
        elif params.get( 'save_changes', False ):
            request_type_id = kwd.get( 'rt_id', None )
            try:
                request_type = trans.sa_session.query( trans.model.RequestType ).get( trans.security.decode_id( request_type_id ) )
            except:
                return invalid_id_redirect( trans, 'requests_admin', request_type_id, action='manage_request_types' )
            # Data transfer info - make sure password is retrieved from kwd rathe rthan Params since Params may have munged the characters.
            request_type.datatx_info = dict( host=util.restore_text( params.get( 'host', '' ) ),
                                             username=util.restore_text( params.get( 'username', '' ) ),
                                             password=kwd.get( 'password', '' ),
                                             data_dir=util.restore_text( params.get( 'data_dir', '' ) ),
                                             rename_dataset=util.restore_text( params.get( 'rename_dataset', False ) ) )
            data_dir = self.__check_path( request_type.datatx_info[ 'data_dir' ] )
            request_type.datatx_info[ 'data_dir' ] = data_dir
            trans.sa_session.add( request_type )
            trans.sa_session.flush()
            message = 'Changes made to sequencer configuration <b>%s</b> has been saved' % request_type.name
            return trans.response.send_redirect( web.url_for( controller='requests_admin',
                                                              action='manage_request_types',
                                                              operation='view',
                                                              id=request_type_id,
                                                              message=message,
                                                              status=status ) )
        else:
            rt_info_widgets, rt_states_widgets = self.__create_request_type_form( trans, **kwd )
            rename_dataset_selectbox = self.__build_rename_dataset_select_list( trans )
            return trans.fill_template( '/admin/requests/create_request_type.mako',
                                        rt_info_widgets=rt_info_widgets,
                                        rt_states_widgets=rt_states_widgets,
                                        rename_dataset_selectbox=rename_dataset_selectbox,
                                        message=message,
                                        status=status )
    def __create_request_type_form( self, trans, **kwd ):
        request_forms = self.get_all_forms( trans, 
                                            filter=dict( deleted=False ),
                                            form_type=trans.model.FormDefinition.types.REQUEST )
        sample_forms = self.get_all_forms( trans, 
                                           filter=dict( deleted=False ),
                                           form_type=trans.model.FormDefinition.types.SAMPLE )
        if not request_forms or not sample_forms:
            return [],[]
        params = util.Params( kwd )
        rt_info_widgets = []
        rt_info_widgets.append( dict( label='Name', 
                                      widget=TextField( 'name', 40, util.restore_text( params.get( 'name', '' ) ) ) ) )
        rt_info_widgets.append( dict( label='Description', 
                                      widget=TextField( 'desc', 40, util.restore_text( params.get( 'desc', '' ) ) ) ) )
        rf_selectbox = SelectField( 'request_form_id' )
        for fd in request_forms:
            if str( fd.id ) == params.get( 'request_form_id', ''  ):
                rf_selectbox.add_option( fd.name, fd.id, selected=True )
            else:
                rf_selectbox.add_option( fd.name, fd.id )
        rt_info_widgets.append( dict( label='Request form', 
                                      widget=rf_selectbox ) )
        sf_selectbox = SelectField( 'sample_form_id' )
        for fd in sample_forms:
            if str( fd.id ) == params.get( 'sample_form_id', ''  ):
                sf_selectbox.add_option( fd.name, fd.id, selected=True )
            else:
                sf_selectbox.add_option( fd.name, fd.id )
        rt_info_widgets.append( dict( label='Sample form', 
                                      widget=sf_selectbox ) )
        # Possible sample states
        rt_states = []
        i=0
        while True:
            if kwd.has_key( 'state_name_%i' % i ):
                rt_states.append( ( params.get( 'state_name_%i' % i, ''  ), 
                                    params.get( 'state_desc_%i' % i, ''  ) ) )
                i += 1
            else:
                break
        return rt_info_widgets, rt_states
    def __build_rename_dataset_select_list( self, trans, rt=None ):
        if rt:
            sel_opt = rt.datatx_info.get( 'rename_dataset', trans.model.RequestType.rename_dataset_options.NO )
        else:
            sel_opt = trans.model.RequestType.rename_dataset_options.NO
        rename_dataset_selectbox = SelectField( 'rename_dataset' )
        for opt, opt_name in trans.model.RequestType.rename_dataset_options.items():
            if sel_opt == opt_name: 
                rename_dataset_selectbox.add_option( opt_name, opt_name, selected=True )
            else:
                rename_dataset_selectbox.add_option( opt_name, opt_name )
        return rename_dataset_selectbox  
    def __save_request_type(self, trans, **kwd):
        params = util.Params( kwd )
        name = util.restore_text( params.get( 'name', ''  ) )
        desc = util.restore_text( params.get( 'desc', '' ) )
        request_form_id = params.get( 'request_form_id', None )
        request_form = trans.sa_session.query( trans.model.FormDefinition ).get( int( request_form_id ) )
        sample_form_id = params.get( 'sample_form_id', None )
        sample_form = trans.sa_session.query( trans.model.FormDefinition ).get( int( sample_form_id ) )
        data_dir = util.restore_text( params.get( 'data_dir', ''  ) )
        data_dir = self.__check_path( data_dir )
        # Data transfer info - Make sure password is retrieved from kwd rather than Params
        # since Params may have munged the characters.
        datatx_info = dict( host=util.restore_text( params.get( 'host', ''  ) ),
                            username=util.restore_text( params.get( 'username', ''  ) ),
                            password=kwd.get( 'password', '' ),
                            data_dir=data_dir,
                            rename_dataset=util.restore_text( params.get( 'rename_dataset', '' ) ) )
        request_type = trans.model.RequestType( name=name, desc=desc, request_form=request_form, sample_form=sample_form, datatx_info=datatx_info ) 
        trans.sa_session.add( request_type )
        trans.sa_session.flush()
        # set sample states
        ss_list = trans.sa_session.query( trans.model.SampleState ) \
                                  .filter( trans.model.SampleState.table.c.request_type_id == request_type.id )
        for ss in ss_list:
            trans.sa_session.delete( ss )
            trans.sa_session.flush()
        i = 0
        while True:
            if kwd.has_key( 'state_name_%i' % i ):
                name = util.restore_text( params.get( 'state_name_%i' % i, None ) )
                desc = util.restore_text( params.get( 'state_desc_%i' % i, None ) )
                ss = trans.model.SampleState( name, desc, request_type ) 
                trans.sa_session.add( ss )
                trans.sa_session.flush()
                i = i + 1
            else:
                break
        message = "The new sequencer configuration named '%s' with %s states has been created" % ( request_type.name, i )
        return request_type, message
    def __delete_request_type( self, trans, **kwd ):
        rt_id = kwd.get( 'id', '' )
        rt_id_list = util.listify( rt_id )
        for rt_id in rt_id_list:
            try:
                request_type = trans.sa_session.query( trans.model.RequestType ).get( trans.security.decode_id( rt_id ) )
            except:
                return invalid_id_redirect( trans, 'requests_admin', rt_id, action='manage_request_types' )
            request_type.deleted = True
            trans.sa_session.add( request_type )
            trans.sa_session.flush()
        status = 'done'
        message = '%i sequencer configurations has been deleted' % len( rt_id_list )
        return trans.response.send_redirect( web.url_for( controller='requests_admin',
                                                          action='manage_request_types',
                                                          message=message,
                                                          status='done' ) )
    def __undelete_request_type( self, trans, **kwd ):
        rt_id = kwd.get( 'id', '' )
        rt_id_list = util.listify( rt_id )
        for rt_id in rt_id_list:
            try:
                request_type = trans.sa_session.query( trans.model.RequestType ).get( trans.security.decode_id( rt_id ) )
            except:
                return invalid_id_redirect( trans, 'requests_admin', rt_id, action='manage_request_types' )
            request_type.deleted = False
            trans.sa_session.add( request_type )
            trans.sa_session.flush()
        status = 'done'
        message = '%i sequencer configurations have been undeleted' % len( rt_id_list )
        return trans.response.send_redirect( web.url_for( controller='requests_admin',
                                                          action='manage_request_types',
                                                          message=message,
                                                          status=status ) )
    def __show_request_type_permissions( self, trans, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        request_type_id = kwd.get( 'id', '' )
        try:
            request_type = trans.sa_session.query( trans.model.RequestType ).get( trans.security.decode_id( request_type_id ) )
        except:
            return invalid_id_redirect( trans, 'requests_admin', request_type_id, action='manage_request_types' )
        roles = trans.sa_session.query( trans.model.Role ) \
                                .filter( trans.model.Role.table.c.deleted==False ) \
                                .order_by( trans.model.Role.table.c.name )
        if params.get( 'update_roles_button', False ):
            permissions = {}
            for k, v in trans.model.RequestType.permitted_actions.items():
                in_roles = [ trans.sa_session.query( trans.model.Role ).get( x ) for x in util.listify( params.get( k + '_in', [] ) ) ]
                permissions[ trans.app.security_agent.get_action( v.action ) ] = in_roles
            trans.app.security_agent.set_request_type_permissions( request_type, permissions )
            trans.sa_session.refresh( request_type )
            message = "Permissions updated for sequencer configuration '%s'" % request_type.name
        return trans.fill_template( '/admin/requests/request_type_permissions.mako',
                                    request_type=request_type,
                                    roles=roles,
                                    status=status,
                                    message=message )
