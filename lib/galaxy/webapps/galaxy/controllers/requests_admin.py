from __future__ import absolute_import

from galaxy.web.base.controller import *
from galaxy.web.framework.helpers import time_ago, iff, grids
from galaxy.model.orm import *
from galaxy import model, util
from galaxy.web.form_builder import *
from .requests_common import RequestsGrid, invalid_id_redirect
from galaxy import eggs
eggs.require("amqp")
import amqp
import logging, os, pexpect, ConfigParser

log = logging.getLogger( __name__ )

class AdminRequestsGrid( RequestsGrid ):
    class UserColumn( grids.TextColumn ):
        def get_value( self, trans, grid, request ):
            return request.user.email
    # Grid definition
    columns = [ col for col in RequestsGrid.columns ]
    columns.append( UserColumn( "User",
                                model_class=model.User,
                                key='username' ) )
    operations = [ operation for operation in RequestsGrid.operations ]
    operations.append( grids.GridOperation( "Edit", allow_multiple=False, condition=( lambda item: not item.deleted ) ) )
    operations.append( grids.GridOperation( "Reject", allow_multiple=False, condition=( lambda item: not item.deleted and item.is_submitted ) ) )
    operations.append( grids.GridOperation( "Delete", allow_multiple=True, condition=( lambda item: not item.deleted ) ) )
    operations.append( grids.GridOperation( "Undelete", condition=( lambda item: item.deleted ) ) )
    global_actions = [
        grids.GridAction( "Create new request", dict( controller='requests_common',
                                                      action='create_request',
                                                      cntrller='requests_admin' ) )
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
    class ExternalServiceColumn( grids.TextColumn ):
        def get_value( self, trans, grid, sample_dataset ):
            try:
                return sample_dataset.external_service.name
            except:
                return 'None'
    # Grid definition
    title = "Sample Datasets"
    template = "admin/requests/sample_datasets_grid.mako"
    model_class = model.SampleDataset
    default_sort_key = "-create_time"
    num_rows_per_page = 50
    preserve_state = True
    use_paging = False
    columns = [
        NameColumn( "Name",
                    link=( lambda item: dict( operation="view", id=item.id ) ),
                    attach_popup=True,
                    filterable="advanced" ),
        SizeColumn( "Size",
                    filterable="advanced" ),
        grids.GridColumn( "Last Updated",
                          key="update_time",
                          format=time_ago ),
        ExternalServiceColumn( 'External service',
                               link=( lambda item: dict( operation="view_external_service", id=item.external_service.id ) ), ),
        StatusColumn( "Transfer Status",
                      filterable="advanced",
                      label_id_prefix='datasetTransferStatus-' ),
    ]
    columns.append( grids.MulticolFilterColumn( "Search",
                                                cols_to_filter=[ columns[0] ],
                                                key="free-text-search",
                                                visible=False,
                                                filterable="standard" ) )
    operations = [
        grids.GridOperation( "Transfer",
                             allow_multiple=True,
                             condition=( lambda item: item.status in [ model.SampleDataset.transfer_status.NOT_STARTED ] ) ),
        grids.GridOperation( "Rename",
                             allow_multiple=True,
                             allow_popup=False,
                             condition=( lambda item: item.status in [ model.SampleDataset.transfer_status.NOT_STARTED ] ) ),
        grids.GridOperation( "Delete",
                             allow_multiple=True,
                             condition=( lambda item: item.status in [ model.SampleDataset.transfer_status.NOT_STARTED ] ) )
    ]
    def apply_query_filter( self, trans, query, **kwd ):
        sample_id = kwd.get( 'sample_id', None )
        if not sample_id:
            return query
        return query.filter_by( sample_id=trans.security.decode_id( sample_id ) )

class RequestsAdmin( BaseUIController, UsesFormDefinitionsMixin ):
    request_grid = AdminRequestsGrid()
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
            if operation == "add_samples":
                return trans.response.send_redirect( web.url_for( controller='requests_common',
                                                                  action='add_samples',
                                                                  cntrller='requests_admin',
                                                                  **kwd ) )
            if operation == "edit_samples":
                return trans.response.send_redirect( web.url_for( controller='requests_common',
                                                                  action='edit_samples',
                                                                  cntrller='requests_admin',
                                                                  **kwd ) )
            if operation == "view_request":
                return trans.response.send_redirect( web.url_for( controller='requests_common',
                                                                  action='view_request',
                                                                  cntrller='requests_admin',
                                                                  **kwd ) )
            if operation == "view_request_history":
                return trans.response.send_redirect( web.url_for( controller='requests_common',
                                                                  action='view_request_history',
                                                                  cntrller='requests_admin',
                                                                  **kwd ) )
            if operation == "reject":
                return self.reject_request( trans, **kwd )
            if operation == "view_type":
                return trans.response.send_redirect( web.url_for( controller='request_type',
                                                                  action='view_request_type',
                                                                  **kwd ) )
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
    @web.expose
    @web.require_admin
    def reject_request( self, trans, **kwd ):
        params = util.Params( kwd )
        request_id = params.get( 'id', '' )
        status = params.get( 'status', 'done' )
        message = params.get( 'message', 'done' )
        if params.get( 'cancel_reject_button', False ):
            return trans.response.send_redirect( web.url_for( controller='requests_common',
                                                              action='view_request',
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
        event_comment = "Sequencing request marked rejected by %s. Reason: %s " % ( trans.user.email, comment )
        event = trans.model.RequestEvent( request, request.states.REJECTED, event_comment )
        trans.sa_session.add( event )
        trans.sa_session.flush()
        message='Sequencing request (%s) has been rejected.' % request.name
        return trans.response.send_redirect( web.url_for( controller='requests_admin',
                                                          action='browse_requests',
                                                          status=status,
                                                          message=message,
                                                          **kwd ) )
    # Data transfer from sequencer/external_service
    @web.expose
    @web.require_admin
    def manage_datasets( self, trans, **kwd ):
        def handle_error( **kwd ):
            kwd[ 'status' ] = 'error'
            return trans.response.send_redirect( web.url_for( controller='requests_admin',
                                                              action='manage_datasets',
                                                              **kwd ) )
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        # When this method is called due to a grid operation, the sample ID
        # will be in the param 'id'.  But when this method is called via a
        # redirect from another method, the ID will be in 'sample_id'.  So,
        # check for 'id' if 'sample_id' is not provided.
        sample_id = params.get( 'sample_id', None )
        if sample_id is None:
            sample_id = params.get( 'id', None )
        try:
            sample = trans.sa_session.query( trans.model.Sample ).get( trans.security.decode_id ( sample_id ) )
        except:
            return invalid_id_redirect( trans, 'requests_admin', sample_id, 'sample' )
        if 'operation' in kwd:
            operation = kwd[ 'operation' ].lower()
            sample_dataset_id = params.get( 'id', None )
            if not sample_dataset_id:
                message = 'Select at least 1 dataset to %s.' % operation
                kwd[ 'message' ] = message
                del kwd[ 'operation' ]
                handle_error( **kwd )
            id_list = util.listify( sample_dataset_id )
            selected_sample_datasets = []
            for sample_dataset_id in id_list:
                try:
                    sample_dataset = trans.sa_session.query( trans.model.SampleDataset ).get( trans.security.decode_id( sample_dataset_id ) )
                except:
                    return invalid_id_redirect( trans, 'requests_admin', sample_dataset_id, 'sample dataset' )
                selected_sample_datasets.append( sample_dataset )
            if operation == "view":
                return trans.fill_template( '/admin/requests/view_sample_dataset.mako',
                                            cntrller='requests_admin',
                                            sample_dataset=selected_sample_datasets[0] )
            elif operation == "delete":
                not_deleted = []
                for sample_dataset in selected_sample_datasets:
                    # Make sure the dataset has been transferred before deleting it.
                    if sample_dataset in sample_dataset.sample.untransferred_dataset_files:
                        # Save the sample dataset
                        sample = sample_dataset.sample
                        trans.sa_session.delete( sample_dataset )
                        trans.sa_session.flush()
                    else:
                        not_deleted.append( sample_dataset.name )
                message = '%i datasets have been deleted.' % ( len( id_list ) - len( not_deleted ) )
                if not_deleted:
                    status = 'warning'
                    message = message + '  %s could not be deleted because their transfer status is not "Not Started". ' % str( not_deleted )
                return trans.response.send_redirect( web.url_for( controller='requests_admin',
                                                                  action='manage_datasets',
                                                                  sample_id=trans.security.encode_id( sample.id ),
                                                                  status=status,
                                                                  message=message ) )
            elif operation == "rename":
                # If one of the selected sample datasets is in the NOT_STARTED state,
                # then display an error message.  A NOT_STARTED state implies the dataset
                # has not yet been transferred.
                no_datasets_transferred = True
                for selected_sample_dataset in selected_sample_datasets:
                    if selected_sample_dataset in selected_sample_dataset.sample.untransferred_dataset_files:
                        no_datasets_transferred = False
                        break
                if no_datasets_transferred:
                    status = 'error'
                    message = 'A dataset can be renamed only if it has been transferred.'
                    return trans.response.send_redirect( web.url_for( controller='requests_admin',
                                                                      action='manage_datasets',
                                                                      sample_id=trans.security.encode_id( selected_sample_datasets[0].sample.id ),
                                                                      status=status,
                                                                      message=message ) )
                return trans.fill_template( '/admin/requests/rename_datasets.mako',
                                            sample=selected_sample_datasets[0].sample,
                                            id_list=id_list )
            elif operation == "transfer":
                self.initiate_data_transfer( trans,
                                             trans.security.encode_id( selected_sample_datasets[0].sample.id ),
                                             sample_datasets=selected_sample_datasets )
            elif operation == "view_external_service":
                return trans.response.send_redirect( web.url_for( controller='external_service',
                                                                  action='view_external_service',
                                                                  **kwd ) )

        # Render the grid view
        request_id = trans.security.encode_id( sample.request.id )
        library_id = trans.security.encode_id( sample.library.id )
        self.datatx_grid.title = 'Manage "%s" datasets'  % sample.name
        self.datatx_grid.global_actions = [ grids.GridAction( "Browse target data library",
                                                              dict( controller='library_common',
                                                                    action='browse_library',
                                                                    cntrller='library_admin',
                                                                    id=library_id ) ),
                                            grids.GridAction( "Browse this request",
                                                              dict( controller='requests_common',
                                                                    action='view_request',
                                                                    cntrller='requests_admin',
                                                                    id=request_id ) ) ]
        return self.datatx_grid( trans, **kwd )
    @web.expose
    @web.require_admin
    def rename_datasets( self, trans, **kwd ):
        # This method is called from the DataTransferGrid when a user is renaming 1 or more
        # SampleDatasets.
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        sample_id = kwd.get( 'sample_id', None )
        try:
            sample = trans.sa_session.query( trans.model.Sample ).get( trans.security.decode_id( sample_id ) )
        except:
            return invalid_id_redirect( trans, 'requests_admin', sample_id, 'sample' )
        # id_list is list of SampleDataset ids, which is a subset of all
        # of the SampleDatasets associated with the Sample.  The user may
        # or may not have selected all of the SampleDatasets for renaming.
        id_list = util.listify( kwd.get( 'id_list', [] ) )
        # Get all of the SampleDatasets
        sample_datasets = []
        for sample_dataset_id in id_list:
            sample_dataset = trans.sa_session.query( trans.app.model.SampleDataset ).get( trans.security.decode_id( sample_dataset_id ) )
            sample_datasets.append( sample_dataset )
        if params.get( 'rename_datasets_button', False ):
            incorrect_dataset_names = []
            for sample_dataset in sample_datasets:
                encoded_id = trans.security.encode_id( sample_dataset.id )
                selected_option = util.restore_text( params.get( 'rename_datasets_for_sample_%s' % encoded_id, '' ) )
                new_name = util.restore_text( params.get( 'new_name_%s' % encoded_id, '' ) )
                if not new_name:
                    incorrect_dataset_names.append( sample_dataset.name )
                    continue
                new_name = util.sanitize_for_filename( new_name )
                if selected_option == 'none':
                    sample_dataset.name = new_name
                else:
                    sample_dataset.name = '%s_%s' % ( selected_option, new_name )
                trans.sa_session.add( sample_dataset )
                trans.sa_session.flush()
            if len( sample_datasets ) == len( incorrect_dataset_names ):
                status = 'error'
                message = 'All datasets renamed incorrectly.'
            elif len( incorrect_dataset_names ):
                status = 'done'
                message = 'Changes saved successfully. The following datasets were renamed incorrectly: %s.' % str( incorrect_dataset_names )
            else:
                message = 'Changes saved successfully.'
            return trans.fill_template( '/admin/requests/rename_datasets.mako',
                                        sample=sample,
                                        id_list=id_list,
                                        message=message,
                                        status=status )
        return trans.response.send_redirect( web.url_for( controller='requests_admin',
                                                          action='manage_datasets',
                                                          sample_id=sample_id ) )
    @web.expose
    @web.require_admin
    def select_datasets_to_transfer( self, trans, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', '' ) )
        status = params.get( 'status', 'done' )
        request_id = kwd.get( 'request_id', None )
        external_service_id = kwd.get( 'external_service_id', None )
        files = []
        request = trans.sa_session.query( trans.model.Request ).get( trans.security.decode_id( request_id ) )
        external_service = trans.sa_session.query( trans.model.ExternalService ).get( trans.security.decode_id( external_service_id ) )
        # Load the data transfer settings
        external_service.load_data_transfer_settings( trans )
        scp_configs = external_service.data_transfer[ trans.model.ExternalService.data_transfer_protocol.SCP ]
        selected_datasets_to_transfer = util.restore_text( params.get( 'selected_datasets_to_transfer', '' ) )
        if selected_datasets_to_transfer:
            selected_datasets_to_transfer = selected_datasets_to_transfer.split(',')
        else:
            selected_datasets_to_transfer = []
        sample_id = kwd.get( 'sample_id', 'none' )
        sample_id_select_field = self.__build_sample_id_select_field( trans, request, sample_id )
        if sample_id != 'none':
            sample = trans.sa_session.query( trans.model.Sample ).get( trans.security.decode_id( sample_id ) )
        else:
            sample = None
        # The __get_files() method redirects here with a status of 'error' and a message if there
        # was a problem retrieving the files.
        if params.get( 'select_datasets_to_transfer_button', False ):
            # Get the sample that was sequenced to produce these datasets.
            if sample_id == 'none':
                del kwd[ 'select_datasets_to_transfer_button' ]
                message = 'Select the sample that was sequenced to produce the datasets you want to transfer.'
                kwd[ 'message' ] = message
                kwd[ 'status' ] = 'error'
                return trans.response.send_redirect( web.url_for( controller='requests_admin',
                                                                  action='select_datasets_to_transfer',
                                                                  **kwd ) )
            if not sample.library:
                # Display an error if a sample has been selected that
                # has not yet been associated with a destination library.
                message = 'Select a target data library and folder for the sample before selecting the datasets.'
                status = 'error'
                return trans.response.send_redirect( web.url_for( controller='requests_common',
                                                                  action='edit_samples',
                                                                  cntrller='requests_admin',
                                                                  id=trans.security.encode_id( request.id ),
                                                                  status=status,
                                                                  message=message ) )
            # Save the sample datasets
            sample_dataset_file_names = self.__create_sample_datasets( trans, sample, selected_datasets_to_transfer, external_service )
            if sample_dataset_file_names:
                message = 'Datasets (%s) have been selected for sample (%s)' % \
                    ( str( sample_dataset_file_names )[1:-1].replace( "'", "" ), sample.name )
            return trans.response.send_redirect( web.url_for( controller='requests_admin',
                                                              action='manage_datasets',
                                                              request_id=request_id,
                                                              sample_id=sample_id,
                                                              message=message,
                                                              status=status ) )
        return trans.fill_template( '/admin/requests/select_datasets_to_transfer.mako',
                                    cntrller='requests_admin',
                                    request=request,
                                    external_service=external_service,
                                    scp_configs=scp_configs,
                                    sample=sample,
                                    sample_id_select_field=sample_id_select_field,
                                    status=status,
                                    message=message )
    @web.json
    def get_file_details( self, trans, request_id, external_service_id, folder_path ):
        def print_ticks( d ):
            # pexpect timeout method
            pass
        # Avoid caching
        trans.response.headers['Pragma'] = 'no-cache'
        trans.response.headers['Expires'] = '0'
        request = trans.sa_session.query( trans.model.Request ).get( trans.security.decode_id( request_id ) )
        external_service = trans.sa_session.query( trans.model.ExternalService ).get( trans.security.decode_id( external_service_id ) )
        external_service.load_data_transfer_settings( trans )
        scp_configs = external_service.data_transfer[ trans.model.ExternalService.data_transfer_protocol.SCP ]
        cmd  = 'ssh %s@%s "ls -oghp \'%s\'"' % ( scp_configs[ 'user_name' ],
                                                 scp_configs[ 'host' ],
                                                 folder_path )
        # Handle the authentication message if ssh keys are not set - the message is
        # something like: "Are you sure you want to continue connecting (yes/no)."
        output = pexpect.run( cmd,
                              events={ '\(yes\/no\)\.*' : 'yes\r\n',
                                       '.ssword:*' : scp_configs[ 'password' ] + '\r\n',
                                       pexpect.TIMEOUT : print_ticks },
                              timeout=10 )
        for password_str in [ 'Password:\r\n', 'password:\r\n' ]:
            # Eliminate the output created using ssh from the tree
            if password_str in output:
                output = output.replace( password_str, '' )
        return unicode( output.replace( '\r\n', '<br/>' ) )
    @web.json
    def open_folder( self, trans, request_id, external_service_id, key ):
        # Avoid caching
        trans.response.headers['Pragma'] = 'no-cache'
        trans.response.headers['Expires'] = '0'
        request = trans.sa_session.query( trans.model.Request ).get( trans.security.decode_id( request_id ) )
        external_service = trans.sa_session.query( trans.model.ExternalService ).get( trans.security.decode_id( external_service_id ) )
        folder_path = key
        files_list = self.__get_files( trans, request, external_service, folder_path )
        folder_contents = []
        for filename in files_list:
            is_folder = False
            if filename and filename[-1] == os.sep:
                is_folder = True
            if filename:
                full_path = os.path.join( folder_path, filename )
                node = { "title": filename,
                         "isFolder": is_folder,
                         "isLazy": is_folder,
                         "tooltip": full_path,
                         "key": full_path }
                folder_contents.append( node )
        return folder_contents
    def __get_files( self, trans, request, external_service, folder_path ):
        # Retrieves the filenames to be transferred from the remote host.
        ok = True
        external_service.load_data_transfer_settings( trans )
        scp_configs = external_service.data_transfer[ trans.model.ExternalService.data_transfer_protocol.SCP ]
        if not scp_configs[ 'host' ] or not scp_configs[ 'user_name' ] or not scp_configs[ 'password' ]:
            status = 'error'
            message = "Error in external service login information."
            ok = False
        def print_ticks( d ):
            pass
        cmd  = 'ssh %s@%s "ls -p \'%s\'"' % ( scp_configs[ 'user_name' ], scp_configs[ 'host' ], folder_path )
        # Handle the authentication message if keys are not set - the message is
        # something like: "Are you sure you want to continue connecting (yes/no)."
        output = pexpect.run( cmd,
                              events={ '\(yes\/no\)\.*' : 'yes\r\n',
                                      '.ssword:*' : scp_configs[ 'password' ] + '\r\n',
                                       pexpect.TIMEOUT : print_ticks },
                              timeout=10 )
        if 'No such file or directory' in output:
            status = 'error'
            message = "No folder named (%s) exists on the external service." % folder_path
            ok = False
        if ok:
            if 'assword:' in output:
                # Eliminate the output created using ssh from the tree
                output_as_list = output.splitlines()[ 1: ]
            else:
                output_as_list = output.splitlines()
            return output_as_list
        return trans.response.send_redirect( web.url_for( controller='requests_admin',
                                                          action='select_datasets_to_transfer',
                                                          request_id=trans.security.encode_id( request.id ),
                                                          external_service_id=trans.security.encode_id( external_service.id ),
                                                          status=status,
                                                          message=message ) )
    def __create_sample_datasets( self, trans, sample, selected_datasets_to_transfer, external_service ):
        external_service.load_data_transfer_settings( trans )
        scp_configs = external_service.data_transfer[ trans.model.ExternalService.data_transfer_protocol.SCP ]
        sample_dataset_file_names = []
        if selected_datasets_to_transfer:
            for filepath in selected_datasets_to_transfer:
                # FIXME: handle folder selection - ignore folders for now
                if filepath[-1] != os.sep:
                    name = self.__rename_dataset( sample, filepath.split( '/' )[-1], scp_configs )
                    status = trans.app.model.SampleDataset.transfer_status.NOT_STARTED
                    size = sample.get_untransferred_dataset_size( filepath, scp_configs )
                    sample_dataset = trans.model.SampleDataset( sample=sample,
                                                                file_path=filepath,
                                                                status=status,
                                                                name=name,
                                                                error_msg='',
                                                                size=size,
                                                                external_service=external_service )
                    trans.sa_session.add( sample_dataset )
                    trans.sa_session.flush()
                    sample_dataset_file_names.append( str( sample_dataset.name ) )
        return sample_dataset_file_names
    def __rename_dataset( self, sample, filepath, scp_configs ):
        name = filepath.split( '/' )[-1]
        options = sample.request.type.rename_dataset_options
        option = scp_configs.get( 'rename_dataset', options.NO )
        if option == options.SAMPLE_NAME:
            new_name = sample.name + '_' + name
        if option == options.EXPERIMENT_AND_SAMPLE_NAME:
            new_name = sample.request.name + '_' + sample.name + '_' + name
        if option == options.EXPERIMENT_NAME:
            new_name = sample.request.name + '_' + name
        else:
            new_name = name
        return util.sanitize_for_filename( new_name )
    def __ensure_library_add_permission( self, trans, target_library, target_folder ):
        """
        Ensures the current admin user has ADD_LIBRARY permission on the target data library and folder.
        """
        current_user_roles = trans.user.all_roles()
        current_user_private_role = trans.app.security_agent.get_private_user_role( trans.user )
        flush_needed = False
        if not trans.app.security_agent.can_add_library_item( current_user_roles, target_library ):
            lp = trans.model.LibraryPermissions( trans.app.security_agent.permitted_actions.LIBRARY_ADD.action,
                                                 target_library,
                                                 current_user_private_role )
            trans.sa_session.add( lp )
            flush_needed = True
        if not trans.app.security_agent.can_add_library_item( current_user_roles, target_folder ):
            lfp = trans.model.LibraryFolderPermissions( trans.app.security_agent.permitted_actions.LIBRARY_ADD.action,
                                                        target_folder,
                                                        current_user_private_role )
            trans.sa_session.add( lfp )
            flush_needed = True
        if flush_needed:
            trans.sa_session.flush()
    def __create_data_transfer_messages( self, trans, sample, selected_sample_datasets ):
        """
        Creates the xml messages to send to the rabbitmq server. It returns a dictionary of messages
        keyed by the external service used to transfer the datasets
        """
        # Create the xml message based on the following template
        xml = \
            ''' <data_transfer>
                    <galaxy_host>%(GALAXY_HOST)s</galaxy_host>
                    <api_key>%(API_KEY)s</api_key>
                    <data_host>%(DATA_HOST)s</data_host>
                    <data_user>%(DATA_USER)s</data_user>
                    <data_password>%(DATA_PASSWORD)s</data_password>
                    <request_id>%(REQUEST_ID)s</request_id>
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
        # Here we group all the sample_datasets by the external service used to transfer them.
        # The idea is to bundle up the sample_datasets which uses the same external service and
        # send a single AMQP message to the galaxy_listener
        dataset_elements = {}
        for sample_dataset in selected_sample_datasets:
            external_service = sample_dataset.external_service
            if sample_dataset.status == trans.app.model.SampleDataset.transfer_status.NOT_STARTED:
                if not dataset_elements.has_key( external_service ):
                    dataset_elements[ external_service ] = ''
                dataset_elements[ external_service ] += dataset_xml % dict( ID=str( sample_dataset.id ),
                                                                      NAME=sample_dataset.name,
                                                                      FILE=sample_dataset.file_path )
                # update the dataset transfer status
                sample_dataset.status = trans.app.model.SampleDataset.transfer_status.IN_QUEUE
                trans.sa_session.add( sample_dataset )
                trans.sa_session.flush()
        # Finally prepend the external service info to the sets of sample datasets
        messages = []
        for external_service, dataset_elem in dataset_elements.items():
            external_service.load_data_transfer_settings( trans )
            scp_configs = external_service.data_transfer[ trans.model.ExternalService.data_transfer_protocol.SCP ]
            # Check data transfer settings
            err_msg = self.__validate_data_transfer_settings( trans, sample.request.type, scp_configs )
            if err_msg:
                return trans.response.send_redirect( web.url_for( controller='requests_admin',
                                                                  action='manage_datasets',
                                                                  sample_id=trans.security.encode_id( sample.id ),
                                                                  status='error',
                                                                  message=err_msg ) )
            message = xml % dict( GALAXY_HOST=trans.request.host,
                                  API_KEY=trans.user.api_keys[0].key,
                                  DATA_HOST=scp_configs[ 'host' ],
                                  DATA_USER=scp_configs[ 'user_name' ],
                                  DATA_PASSWORD=scp_configs[ 'password' ],
                                  REQUEST_ID=str( sample.request.id ),
                                  SAMPLE_ID=str( sample.id ),
                                  LIBRARY_ID=str( sample.library.id ),
                                  FOLDER_ID=str( sample.folder.id ),
                                  DATASETS=dataset_elem )
            messages.append( message.replace( '\n', '' ).replace( '\r', '' ) )
        return messages
    def __validate_data_transfer_settings( self, trans, request_type, scp_configs ):
        err_msg = ''
        # check the external service login info
        if not scp_configs.get( 'host', '' ) \
            or not scp_configs.get( 'user_name', '' ) \
            or not scp_configs.get( 'password', '' ):
            err_msg += "Error in external service login information. "
        if not trans.user.api_keys:
            err_msg += "Set your API Key in your User Preferences to transfer datasets. "
        # Check if library_import_dir is set
        if not trans.app.config.library_import_dir:
            err_msg = "'The library_import_dir' setting is not correctly set in the Galaxy config file. "
        # Check the RabbitMQ server settings in the config file
        for k, v in trans.app.config.amqp.items():
            if not v:
                err_msg += 'Set RabbitMQ server settings in the "galaxy_amqp" section of the Galaxy config file, specifically "%s" is not set.' % k
                break
        return err_msg
    @web.expose
    @web.require_admin
    def initiate_data_transfer( self, trans, sample_id, sample_datasets=[], sample_dataset_id='' ):
        # Initiate the transfer of the datasets from the external service to the target Galaxy data library.
        # The admin user must have LIBRARY_ADD permission for the target library and folder
        try:
            sample = trans.sa_session.query( trans.model.Sample ).get( trans.security.decode_id( sample_id ) )
        except:
            return invalid_id_redirect( trans, 'requests_admin', sample_id, 'sample' )
        message = ""
        status = "done"
        # Make sure the current admin user has LIBRARY_ADD permission on the target data library and folder.
        self.__ensure_library_add_permission( trans, sample.library, sample.folder )
        if sample_dataset_id and not sample_datasets:
            # Either a list of SampleDataset objects or a comma-separated string of
            # encoded SampleDataset ids can be received.  If the latter, parse the
            # sample_dataset_id string to build the list of sample_datasets.
            id_list = util.listify( sample_dataset_id )
            for sample_dataset_id in id_list:
                sample_dataset = trans.sa_session.query( trans.model.SampleDataset ).get( trans.security.decode_id( sample_dataset_id ) )
                sample_datasets.append( sample_dataset )
        if trans.app.config.enable_beta_job_managers:
            # For now, assume that all SampleDatasets use the same external service ( this may not be optimal ).
            if sample_datasets:
                external_service_type_id = sample_datasets[0].external_service.external_service_type_id
                # Here external_service_type_id will be something like '454_life_sciences'
                external_service = sample.request.type.get_external_service( external_service_type_id )
                external_service_type = external_service.get_external_service_type( trans )
                external_service.load_data_transfer_settings( trans )
                # For now only scp is supported.
                scp_configs = external_service.data_transfer[ trans.model.ExternalService.data_transfer_protocol.SCP ]
                if not scp_configs[ 'automatic_transfer' ]:
                    deferred_plugin = 'ManualDataTransferPlugin'
                else:
                    raise Exception( "Automatic data transfer using scp is not yet supported." )
            trans.app.job_manager.deferred_job_queue.plugins[ deferred_plugin ].create_job( trans,
                                                                                            sample=sample,
                                                                                            sample_datasets=sample_datasets,
                                                                                            external_service=external_service,
                                                                                            external_service_type=external_service_type )
        else:
            # TODO: Using RabbitMq for now, but eliminate this entire block when we replace RabbitMq with Galaxy's
            # own messaging engine.  We're holding off on using the new way to transfer files manually until we
            # implement a Galaxy-proprietary messaging engine because the deferred job plugins currently perform
            # constant db hits to check for deferred jobs that are not in a finished state.
            # Create the message
            messages = self.__create_data_transfer_messages( trans, sample, sample_datasets )
            # Send the messages
            for rmq_msg in messages:
                try:
                    conn = amqp.Connection( host=trans.app.config.amqp[ 'host' ] + ":" + trans.app.config.amqp[ 'port' ],
                                            userid=trans.app.config.amqp[ 'userid' ],
                                            password=trans.app.config.amqp[ 'password' ],
                                            virtual_host=trans.app.config.amqp[ 'virtual_host' ])
                    chan = conn.channel()
                    msg = amqp.Message( rmq_msg,
                                        content_type='text/plain',
                                        application_headers={ 'msg_type': 'data_transfer' } )
                    msg.properties[ "delivery_mode" ] = 2
                    chan.basic_publish( msg,
                                        exchange=trans.app.config.amqp[ 'exchange' ],
                                        routing_key=trans.app.config.amqp[ 'routing_key' ] )
                    chan.close()
                    conn.close()
                except Exception, e:
                    message = "Error sending the data transfer message to the Galaxy AMQP message queue:<br/>%s" % str(e)
                    status = "error"
            if not message:
                message = "%i datasets have been queued for transfer from the external service." % len( sample_datasets )
                status = "done"
        return trans.response.send_redirect( web.url_for( controller='requests_admin',
                                                          action='manage_datasets',
                                                          sample_id=trans.security.encode_id( sample.id ),
                                                          message=message,
                                                          status=status ) )
    @web.expose
    def update_sample_dataset_status(self, trans, cntrller, sample_dataset_ids, new_status, error_msg=None ):
        # check if the new status is a valid transfer status
        possible_status_list = [ v[1] for v in trans.app.model.SampleDataset.transfer_status.items() ]
        if new_status not in possible_status_list:
            trans.response.status = 400
            return 400, "The requested transfer status ( %s ) is not a valid transfer status." % new_status
        for id in util.listify( sample_dataset_ids ):
            try:
                sd_id = trans.security.decode_id( id )
                sample_dataset = trans.sa_session.query( trans.app.model.SampleDataset ).get( sd_id )
            except:
                trans.response.status = 400
                return 400, "Invalid sample dataset id ( %s ) specified." % str( id )
            sample_dataset.status = new_status
            sample_dataset.error_msg = error_msg
            trans.sa_session.add( sample_dataset )
            trans.sa_session.flush()
        return 200, 'Done'
    # ===== Methods for building SelectFields used on various admin_requests forms
    def __build_sample_id_select_field( self, trans, request, selected_value ):
        return build_select_field( trans, request.samples, 'name', 'sample_id', selected_value=selected_value, refresh_on_change=False )

# ===== Methods for building SelectFields used on various admin_requests forms - used outside this controller =====
def build_rename_datasets_for_sample_select_field( trans, sample_dataset, selected_value='none' ):
    options = []
    for option_index, option in enumerate( sample_dataset.file_path.split( os.sep )[ :-1 ] ):
        option = option.strip()
        if option:
           options.append( option )
    return build_select_field( trans,
                               objs=options,
                               label_attr='self',
                               select_field_name='rename_datasets_for_sample_%s' % trans.security.encode_id( sample_dataset.id ),
                               selected_value=selected_value,
                               refresh_on_change=False )
