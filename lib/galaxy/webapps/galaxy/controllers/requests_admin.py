from __future__ import absolute_import
import logging
import os

from galaxy import model, util
from galaxy.web.base.controller import BaseUIController, UsesFormDefinitionsMixin, web
from galaxy.web.form_builder import build_select_field
from galaxy.web.framework.helpers import time_ago, grids
from .requests_common import RequestsGrid, invalid_id_redirect
from markupsafe import escape


log = logging.getLogger( __name__ )


class AdminRequestsGrid( RequestsGrid ):
    class UserColumn( grids.TextColumn ):
        def get_value( self, trans, grid, request ):
            return escape(request.user.email)
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
            return escape(sample_dataset.name)

    class SizeColumn( grids.TextColumn ):
        def get_value( self, trans, grid, sample_dataset ):
            return sample_dataset.size

    class StatusColumn( grids.TextColumn ):
        def get_value( self, trans, grid, sample_dataset ):
            return sample_dataset.status

    class ExternalServiceColumn( grids.TextColumn ):
        def get_value( self, trans, grid, sample_dataset ):
            try:
                return escape(sample_dataset.external_service.name)
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
            status = 'error'
            message = 'A reason for rejecting the request is required.'
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
        message = 'Sequencing request (%s) has been rejected.' % request.name
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
            sample = trans.sa_session.query( trans.model.Sample ).get( trans.security.decode_id( sample_id ) )
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
        self.datatx_grid.title = 'Manage "%s" datasets' % sample.name
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
            message = "Message queue transfer is no longer supported, please set enable_beta_job_managers = True in galaxy.ini"
            status = "error"
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
    # Methods for building SelectFields used on various admin_requests forms

    def __build_sample_id_select_field( self, trans, request, selected_value ):
        return build_select_field( trans, request.samples, 'name', 'sample_id', selected_value=selected_value, refresh_on_change=False )


# Methods for building SelectFields used on various admin_requests forms - used outside this controller =====
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
