from galaxy.web.base.controller import *
from galaxy.web.framework.helpers import time_ago, iff, grids
from galaxy.model.orm import *
from galaxy import model, util
from galaxy.web.form_builder import *
import logging, os, csv

log = logging.getLogger( __name__ )

class RequestsGrid( grids.Grid ):
    # Custom column types
    class NameColumn( grids.TextColumn ):
        def get_value( self, trans, grid, request ):
            return request.name
    class DescriptionColumn( grids.TextColumn ):
        def get_value(self, trans, grid, request):
            return request.desc
    class SamplesColumn( grids.GridColumn ):
        def get_value(self, trans, grid, request):
            return str( len( request.samples ) )
    class TypeColumn( grids.TextColumn ):
        def get_value( self, trans, grid, request ):
            return request.type.name
    class StateColumn( grids.StateColumn ):
        def get_value(self, trans, grid, request ):
            state = request.state
            if state == request.states.REJECTED:
                state_color = 'error'
            elif state == request.states.NEW:
                state_color = 'new'
            elif state == request.states.SUBMITTED:
                state_color = 'running'
            elif state == request.states.COMPLETE:
                state_color = 'ok'
            else:
                state_color = state
            return '<div class="count-box state-color-%s">%s</div>' % ( state_color, state )
        def filter( self, trans, user, query, column_filter ):
            """ Modify query to filter request by state. """
            if column_filter == "All":
                return query
            if column_filter:
                return query.join( model.RequestEvent.table ) \
                            .filter( self.model_class.table.c.id == model.RequestEvent.table.c.request_id ) \
                            .filter( model.RequestEvent.table.c.state == column_filter ) \
                            .filter( model.RequestEvent.table.c.id.in_( select( columns=[ func.max( model.RequestEvent.table.c.id ) ],
                                                                                from_obj=model.RequestEvent.table,
                                                                                group_by=model.RequestEvent.table.c.request_id ) ) )
        def get_accepted_filters( self ):
            """ Returns a list of accepted filters for this column. """
            # TODO: is this method necessary?
            accepted_filter_labels_and_vals = [ model.Request.states.get( state ) for state in model.Request.states ]
            accepted_filter_labels_and_vals.append( "All" )
            accepted_filters = []
            for val in accepted_filter_labels_and_vals:
                label = val.lower()
                args = { self.key: val }
                accepted_filters.append( grids.GridColumnFilter( label, args ) )
            return accepted_filters
        
    # Grid definition
    title = "Sequencing Requests"
    template = "requests/grid.mako"
    model_class = model.Request
    default_sort_key = "-update_time"
    num_rows_per_page = 50
    preserve_state = True
    use_paging = True
    default_filter = dict( state="All", deleted="False" )
    columns = [
        NameColumn( "Name", 
                    key="name", 
                    link=( lambda item: iff( item.deleted, None, dict( operation="manage_request", id=item.id ) ) ),
                    attach_popup=True, 
                    filterable="advanced" ),
        DescriptionColumn( "Description",
                           key='desc',
                           filterable="advanced" ),
        SamplesColumn( "Samples", 
                       link=( lambda item: iff( item.deleted, None, dict( operation="manage_request", id=item.id ) ) ) ),
        TypeColumn( "Sequencer",
                    link=( lambda item: iff( item.deleted, None, dict( operation="view_type", id=item.type.id ) ) ) ),
        grids.GridColumn( "Last Updated", key="update_time", format=time_ago ),
        grids.DeletedColumn( "Deleted", 
                             key="deleted", 
                             visible=False, 
                             filterable="advanced" ),
        StateColumn( "State", 
                     key='state',
                     filterable="advanced",
                     link=( lambda item: iff( item.deleted, None, dict( operation="events", id=item.id ) ) )
                   )
    ]
    columns.append( grids.MulticolFilterColumn( "Search", 
                                                cols_to_filter=[ columns[0], columns[1] ], 
                                                key="free-text-search",
                                                visible=False,
                                                filterable="standard" ) )
    operations = [
        grids.GridOperation( "Submit",
                             allow_multiple=False,
                             condition=( lambda item: not item.deleted and item.is_unsubmitted and item.samples ),
                             confirm="Samples cannot be added to this request after it is submitted. Click OK to submit."  )
        ]

class RequestsCommon( BaseController, UsesFormDefinitionWidgets ):
    @web.json
    def sample_state_updates( self, trans, ids=None, states=None, cntrller=None ):
        # TODO fix this mthod - cntrller is required in the signature.
        # Avoid caching
        trans.response.headers['Pragma'] = 'no-cache'
        trans.response.headers['Expires'] = '0'
        # Create new HTML for any that have changed
        rval = {}
        if ids is not None and states is not None:
            ids = map( int, ids.split( "," ) )
            states = states.split( "," )
            for id, state in zip( ids, states ):
                sample = trans.sa_session.query( self.app.model.Sample ).get( id )
                if sample.state.name != state:
                    rval[ id ] = { "state": sample.state.name,
                                   "datasets": len( sample.datasets ),
                                   "html_state": unicode( trans.fill_template( "requests/common/sample_state.mako",
                                                                               sample=sample,
                                                                               cntrller=cntrller ),
                                                                               'utf-8' ),
                                   "html_datasets": unicode( trans.fill_template( "requests/common/sample_datasets.mako",
                                                                                  sample=sample,
                                                                                  cntrller=cntrller ),
                                                                                  'utf-8' ) }
        return rval
    @web.expose
    @web.require_login( "create sequencing requests" )
    def create_request( self, trans, cntrller, **kwd ):
        params = util.Params( kwd )
        is_admin = cntrller == 'requests_admin' and trans.user_is_admin()
        message = util.restore_text( params.get( 'message', '' ) )
        status = params.get( 'status', 'done' )
        request_type_id = params.get( 'request_type_id', 'none' )
        if request_type_id != 'none':
            request_type = trans.sa_session.query( trans.model.RequestType ).get( trans.security.decode_id( request_type_id ) )
        else:
            request_type = None
        # user_id will not be 'none' if an admin user is submitting this request on behalf of another user
        # and they selected that user's id from the user_id SelectField.
        user_id = params.get( 'user_id', 'none' )
        if user_id != 'none':
            user = trans.sa_session.query( trans.model.User ).get( trans.security.decode_id( user_id ) )
        elif not is_admin:
            user = trans.user
        else:
            user = None
        if params.get( 'create_request_button', False ) or params.get( 'add_sample_button', False ):
            name = util.restore_text( params.get( 'name', '' ) )
            if is_admin and user_id == 'none':
                message = 'Select the user on behalf of whom you are submitting this request.'
                status = 'error'
            elif not name:
                message = 'Enter the name of the request.'
                status = 'error'
            else:
                request = self.__save_request( trans, cntrller, **kwd )
                message = 'The request has been created.'
                if params.get( 'create_request_button', False ):
                    return trans.response.send_redirect( web.url_for( controller=cntrller,
                                                                      action='browse_requests',
                                                                      message=message ,
                                                                      status='done' ) )
                elif params.get( 'add_sample_button', False ):
                    return self.__add_sample( trans, cntrller, request, **kwd )
        request_type_select_field = self.__build_request_type_id_select_field( trans, selected_value=request_type_id )
        # Widgets to be rendered on the request form
        widgets = []
        if request_type is not None or status == 'error':
            # Either the user selected a request_type or an error exists on the form.
            if is_admin:
                widgets.append( dict( label='Select user',
                                      widget=self.__build_user_id_select_field( trans, selected_value=user_id ),
                                      helptext='Submit the request on behalf of the selected user (Required)'))
            widgets.append( dict( label='Name of the Experiment', 
                                  widget=TextField( 'name', 40, util.restore_text( params.get( 'name', ''  ) ) ), 
                                  helptext='(Required)') )
            widgets.append( dict( label='Description', 
                                  widget=TextField( 'desc', 40, util.restore_text( params.get( 'desc', ''  ) )), 
                                  helptext='(Optional)') )
            if request_type is not None:
                widgets += request_type.request_form.get_widgets( user, **kwd )
            # In case there is an error on the form, make sure to populate widget fields with anything the user
            # may have already entered.
            self.populate_widgets_from_kwd( trans, widgets, **kwd )
        return trans.fill_template( '/requests/common/create_request.mako',
                                    cntrller=cntrller,
                                    request_type_select_field=request_type_select_field,
                                    request_type_select_field_selected=request_type_id,                               
                                    widgets=widgets,
                                    message=message,
                                    status=status )
    @web.expose
    @web.require_login( "edit sequencing requests" )
    def edit_basic_request_info( self, trans, cntrller, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        request_id = params.get( 'id', None )
        try:
            request = trans.sa_session.query( trans.model.Request ).get( trans.security.decode_id( request_id ) )
        except:
            return invalid_id_redirect( trans, cntrller, request_id )
        name = util.restore_text( params.get( 'name', '' ) )
        desc = util.restore_text( params.get( 'desc', ''  ) )
        if params.get( 'edit_basic_request_info_button', False ) or params.get( 'edit_samples_button', False ):
            if not name:
                status = 'error'
                message = 'Enter the name of the request'
            else:
                request = self.__save_request( trans, cntrller, request=request, **kwd )
                message = 'The changes made to request (%s) have been saved.' % request.name
        # Widgets to be rendered on the request form
        widgets = []
        widgets.append( dict( label='Name', 
                              widget=TextField( 'name', 40, request.name ), 
                              helptext='(Required)' ) )
        widgets.append( dict( label='Description', 
                              widget=TextField( 'desc', 40, request.desc ), 
                              helptext='(Optional)' ) )
        widgets = widgets + request.type.request_form.get_widgets( request.user, request.values.content, **kwd )
        # In case there is an error on the form, make sure to populate widget fields with anything the user
        # may have already entered.
        self.populate_widgets_from_kwd( trans, widgets, **kwd )
        return trans.fill_template( 'requests/common/edit_basic_request_info.mako',
                                    cntrller=cntrller,
                                    request_type=request.type,
                                    request=request,
                                    widgets=widgets,
                                    message=message,
                                    status=status )
    def __save_request( self, trans, cntrller, request=None, **kwd ):
        """
        Saves changes to an existing request, or creates a new 
        request if received request is None.
        """
        params = util.Params( kwd )
        request_type_id = params.get( 'request_type_id', None )
        is_admin = cntrller == 'requests_admin' and trans.user_is_admin()
        if request is None:
            # We're creating a new request, so we need the associated request_type
            request_type = trans.sa_session.query( trans.model.RequestType ).get( trans.security.decode_id( request_type_id ) )
            if is_admin:
                # The admin user is creating a request on behalf of another user
                user_id = params.get( 'user_id', '' )
                user = trans.sa_session.query( trans.model.User ).get( trans.security.decode_id( user_id ) )
            else:
                user = trans.user
        else:
            # We're saving changes to an existing request
            user = request.user
            request_type = request.type
        name = util.restore_text( params.get( 'name', '' ) )
        desc = util.restore_text( params.get( 'desc', '' ) )
        notification = dict( email=[ user.email ], sample_states=[ request_type.state.id ], body='', subject='' )
        values = []
        for index, field in enumerate( request_type.request_form.fields ):
            field_type = field[ 'type' ]
            field_value = params.get( 'field_%i' % index, '' )
            if field[ 'type' ] == 'AddressField':
                value = util.restore_text( field_value )
                if value == 'new':
                    # Save this new address in the list of this user's addresses
                    user_address = trans.model.UserAddress( user=user )
                    self.save_widget_field( trans, user_address, index, **kwd )
                    trans.sa_session.refresh( user )
                    values.append( int( user_address.id ) )
                elif value in [ '', 'none', 'None', None ]:
                    values.append( '' )
                else:
                    values.append( int( value ) )
            elif field[ 'type' ] == 'CheckboxField':
                values.append( CheckboxField.is_checked( field_value )) 
            else:
                values.append( util.restore_text( field_value ) )
        form_values = trans.model.FormValues( request_type.request_form, values )
        trans.sa_session.add( form_values )
        trans.sa_session.flush()
        if request is None:
            # We're creating a new request
            request = trans.model.Request( name, desc, request_type, user, form_values, notification )
            trans.sa_session.add( request )
            trans.sa_session.flush()
            trans.sa_session.refresh( request )
            # Create an event with state 'New' for this new request
            if request.user != trans.user:
                sample_event_comment = "Request created by user %s for user %s." % ( trans.user.email, request.user.email )
            else:
                sample_event_comment = "Request created."
            event = trans.model.RequestEvent( request, request.states.NEW, sample_event_comment )
            trans.sa_session.add( event )
            trans.sa_session.flush()
        else:
            # We're saving changes to an existing request
            request.name = name
            request.desc = desc
            request.type = request_type
            request.user = user
            request.notification = notification
            request.values = form_values
            trans.sa_session.add( request )
            trans.sa_session.flush()
        return request
    @web.expose
    @web.require_login( "submit sequencing requests" )
    def submit_request( self, trans, cntrller, **kwd ):
        params = util.Params( kwd )
        request_id = params.get( 'id', None )
        message = util.restore_text( params.get( 'message', '' ) )
        status = util.restore_text( params.get( 'status', 'done' ) )
        try:
            request = trans.sa_session.query( trans.model.Request ).get( trans.security.decode_id( request_id ) )
        except:
            return invalid_id_redirect( trans, cntrller, request_id )
        ok = True
        if not request.samples:
            message = 'Add at least 1 sample to this request before submitting.'
            ok = False
        if ok:
            message = self.__validate_request( trans, cntrller, request )
        if message or not ok:
            return trans.response.send_redirect( web.url_for( controller='requests_common',
                                                              action='edit_basic_request_info',
                                                              cntrller=cntrller,
                                                              id = request_id,
                                                              status='error',
                                                              message=message ) )
        # Change the request state to 'Submitted'
        if request.user.email is not trans.user:
            sample_event_comment = "Request submitted by %s on behalf of %s." % ( trans.user.email, request.user.email )
        else:
            sample_event_comment = ""
        event = trans.model.RequestEvent( request, request.states.SUBMITTED, sample_event_comment )
        trans.sa_session.add( event )
        # change the state of each of the samples of thus request
        new_state = request.type.states[0]
        for sample in request.samples:
            event = trans.model.SampleEvent( sample, new_state, 'Samples created.' )
            trans.sa_session.add( event )
        trans.sa_session.add( request )
        trans.sa_session.flush()
        request.send_email_notification( trans, new_state )
        message = 'The request has been submitted.'
        return trans.response.send_redirect( web.url_for( controller=cntrller,
                                                          action='browse_requests',
                                                          cntrller=cntrller,
                                                          id=request_id,
                                                          status=status,
                                                          message=message ) )
    @web.expose
    @web.require_login( "sequencing request page" )
    def manage_request( self, trans, cntrller, **kwd ):
        params = util.Params( kwd )
        is_admin = cntrller == 'requests_admin' and trans.user_is_admin()
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        request_id = params.get( 'id', None )
        try:
            request = trans.sa_session.query( trans.model.Request ).get( trans.security.decode_id( request_id ) )
        except:
            return invalid_id_redirect( trans, cntrller, request_id )
        sample_state_id = params.get( 'sample_state_id', None )
        # Get the user entered sample information
        current_samples, managing_samples, libraries = self.__get_sample_info( trans, request, **kwd )
        selected_samples = self.__get_selected_samples( trans, request, **kwd )
        selected_value = params.get( 'sample_operation', 'none' )
        if selected_value != 'none' and not selected_samples:
            message = 'Select at least one sample before selecting an operation.'
            status = 'error'
            return trans.response.send_redirect( web.url_for( controller='requests_common',
                                                              action='manage_request',
                                                              cntrller=cntrller,
                                                              id=request_id,
                                                              status=status,
                                                              message=message ) )
        sample_operation_select_field = self.__build_sample_operation_select_field( trans, is_admin, request, selected_value )
        sample_operation_selected_value = sample_operation_select_field.get_selected( return_value=True )
        if params.get( 'import_samples_button', False ):
            # Import sample field values from a csv file
            return self.__import_samples( trans, cntrller, request, current_samples, libraries, **kwd )
        elif params.get( 'add_sample_button', False ):
            return self.__add_sample( trans, cntrller, request, **kwd )
        elif params.get( 'save_samples_button', False ):
            return self.__save_sample( trans, cntrller, request, current_samples, **kwd )
        elif params.get( 'edit_samples_button', False ):
            managing_samples = True
        elif params.get( 'cancel_changes_button', False ):
            return trans.response.send_redirect( web.url_for( controller='requests_common',
                                                              action='manage_request',
                                                              cntrller=cntrller,
                                                              id=request_id ) )
            pass
        elif params.get( 'change_state_button', False ):
            sample_event_comment = util.restore_text( params.get( 'sample_event_comment', '' ) )
            new_state = trans.sa_session.query( trans.model.SampleState ).get( trans.security.decode_id( sample_state_id ) )
            for sample_id in selected_samples:
                sample = trans.sa_session.query( trans.model.Sample ).get( trans.security.decode_id( sample_id ) )
                event = trans.model.SampleEvent( sample, new_state, sample_event_comment )
                trans.sa_session.add( event )
                trans.sa_session.flush()
            return trans.response.send_redirect( web.url_for( controller='requests_common',
                                                              cntrller=cntrller, 
                                                              action='update_request_state',
                                                              request_id=request_id ) )
        elif params.get( 'cancel_change_state_button', False ):
            return trans.response.send_redirect( web.url_for( controller='requests_common',
                                                              action='manage_request',
                                                              cntrller=cntrller,
                                                              id=request_id ) )
        elif params.get( 'change_lib_button', False ):
            library_id = params.get( 'sample_0_library_id', None )
            try:
                library = trans.sa_session.query( trans.model.Library ).get( trans.security.decode_id( library_id ) )
            except:
                invalid_id_redirect( trans, cntrller, library_id )
            folder_id = params.get( 'sample_0_folder_id', None )
            try:
                folder = trans.sa_session.query( trans.model.LibraryFolder ).get( trans.security.decode_id( folder_id ) )
            except:
                invalid_id_redirect( trans, cntrller, folder_id )
            for sample_id in selected_samples:
                sample = trans.sa_session.query( trans.model.Sample ).get( sample_id )
                sample.library = library
                sample.folder = folder
                trans.sa_session.add( sample )
                trans.sa_session.flush()
            trans.sa_session.refresh( request )
            message = 'Changes made to the selected samples have been saved. '
        elif params.get( 'cancel_change_lib_button', False ):
            return trans.response.send_redirect( web.url_for( controller='requests_common',
                                                              action='manage_request',
                                                              cntrller=cntrller,
                                                              id=trans.security.encode_id( request.id ) ) )
        request_widgets = self.__get_request_widgets( trans, request.id )
        sample_copy = self.__build_copy_sample_select_field( trans, current_samples )
        libraries_select_field, folders_select_field = self.__build_library_and_folder_select_fields( trans,
                                                                                                      request.user,
                                                                                                      0,
                                                                                                      libraries,
                                                                                                      None,
                                                                                                      **kwd )
        # Build the sample_state_id_select_field SelectField
        sample_state_id_select_field = self.__build_sample_state_id_select_field( trans, request, sample_state_id )
        return trans.fill_template( '/requests/common/manage_request.mako',
                                    cntrller=cntrller, 
                                    request=request,
                                    selected_samples=selected_samples,
                                    request_widgets=request_widgets,
                                    current_samples=current_samples,
                                    sample_copy=sample_copy, 
                                    libraries=libraries,
                                    sample_operation_select_field=sample_operation_select_field,
                                    libraries_select_field=libraries_select_field,
                                    folders_select_field=folders_select_field,
                                    sample_state_id_select_field=sample_state_id_select_field,
                                    managing_samples=managing_samples,
                                    status=status,
                                    message=message )
    @web.expose
    @web.require_login( "delete sequencing requests" )
    def delete_request( self, trans, cntrller, **kwd ):
        params = util.Params( kwd )
        id_list = util.listify( kwd.get( 'id', '' ) )
        message = util.restore_text( params.get( 'message', '' ) )
        status = util.restore_text( params.get( 'status', 'done' ) )
        num_deleted = 0
        for id in id_list:
            ok_for_now = True
            try:
                request = trans.sa_session.query( trans.model.Request ).get( trans.security.decode_id( id ) )
            except:
                message += "Invalid request ID (%s).  " % str( id )
                status = 'error'
                ok_for_now = False
            if ok_for_now:
                request.deleted = True
                trans.sa_session.add( request )
                # delete all the samples belonging to this request
                for s in request.samples:
                    s.deleted = True
                    trans.sa_session.add( s )
                trans.sa_session.flush()
                num_deleted += 1
        message += '%i requests have been deleted.' % num_deleted
        return trans.response.send_redirect( web.url_for( controller=cntrller,
                                                          action='browse_requests',
                                                          status=status,
                                                          message=message ) )
    @web.expose
    @web.require_login( "undelete sequencing requests" )
    def undelete_request( self, trans, cntrller, **kwd ):
        params = util.Params( kwd )
        id_list = util.listify( kwd.get( 'id', '' ) )
        message = util.restore_text( params.get( 'message', '' ) )
        status = util.restore_text( params.get( 'status', 'done' ) )
        num_undeleted = 0
        for id in id_list:
            ok_for_now = True
            try:
                request = trans.sa_session.query( trans.model.Request ).get( trans.security.decode_id( id ) )
            except:
                message += "Invalid request ID (%s).  " % str( id )
                status = 'error'
                ok_for_now = False
            if ok_for_now:
                request.deleted = False
                trans.sa_session.add( request )
                # undelete all the samples belonging to this request
                for s in request.samples:
                    s.deleted = False
                    trans.sa_session.add( s )
                trans.sa_session.flush()
                num_undeleted += 1
        message += '%i requests have been undeleted.' % num_undeleted
        return trans.response.send_redirect( web.url_for( controller=cntrller,
                                                          action='browse_requests',
                                                          status=status,
                                                          message=message ) )
    @web.expose
    @web.require_login( "sequencing request events" )
    def request_events( self, trans, cntrller, **kwd ):
        params = util.Params( kwd )
        request_id = params.get( 'id', None )
        try:
            request = trans.sa_session.query( trans.model.Request ).get( trans.security.decode_id( request_id ) )
        except:
            return invalid_id_redirect( trans, cntrller, request_id )
        events_list = []
        for event in request.events:         
            events_list.append( ( event.state, time_ago( event.update_time ), event.comment ) )
        return trans.fill_template( '/requests/common/events.mako', 
                                    cntrller=cntrller,
                                    events_list=events_list,
                                    request=request )
    @web.expose
    @web.require_login( "edit email notification settings" )
    def edit_email_settings( self, trans, cntrller, **kwd ):
        """
        Allow for changing the email notification settings where email is sent to a list of users
        whenever the request state changes to one selected for notification.
        """
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        request_id = params.get( 'id', None )
        try:
            request = trans.sa_session.query( trans.model.Request ).get( trans.security.decode_id( request_id ) )
        except:
            return invalid_id_redirect( trans, cntrller, request_id )
        email_address = CheckboxField.is_checked( params.get( 'email_address', '' ) )
        additional_email_addresses = params.get( 'additional_email_addresses', '' )
        # Get the list of checked sample state CheckBoxFields
        checked_sample_states = []
        for index, sample_state in enumerate( request.type.states ):
            if CheckboxField.is_checked( params.get( 'sample_state_%i' % sample_state.id, '' ) ):
                checked_sample_states.append( sample_state.id )
        if additional_email_addresses:
            additional_email_addresses = additional_email_addresses.split( '\r\n' )
        if email_address or additional_email_addresses:
            # The user added 1 or more email addresses
            email_addresses = []
            if email_address:
                email_addresses.append( request.user.email )
            for email_address in additional_email_addresses:
                email_addresses.append( util.restore_text( email_address ) )
            # Make sure email addresses are valid
            err_msg = ''
            for email_address in email_addresses:
                err_msg += self.__validate_email( email_address )
            if err_msg:
                status = 'error'
                message += err_msg
            else:
                request.notification = dict( email=email_addresses,
                                             sample_states=checked_sample_states, 
                                             body='',
                                             subject='' )
        else:
            # The user may have eliminated email addresses that were previously set
            request.notification = None
            if checked_sample_states:
                message = 'All sample states have been unchecked since no email addresses have been selected or entered.  '
        trans.sa_session.add( request )
        trans.sa_session.flush()
        trans.sa_session.refresh( request )
        message += 'The changes made to the email notification settings have been saved.'
        return trans.response.send_redirect( web.url_for( controller='requests_common',
                                                          action='edit_basic_request_info',
                                                          cntrller=cntrller,
                                                          id=request_id,
                                                          message=message ,
                                                          status=status ) )
    @web.expose
    @web.require_login( "update sequencing request state" )
    def update_request_state( self, trans, cntrller, **kwd ):
        params = util.Params( kwd )
        message = params.get( 'message', '' )
        status = params.get( 'status', 'done' )
        request_id = params.get( 'request_id', None )
        try:
            request = trans.sa_session.query( trans.model.Request ).get( trans.security.decode_id( request_id ) )
        except:
            return invalid_id_redirect( trans, cntrller, request_id )
        # Make sure all the samples of the current request have the same state
        common_state = request.samples_have_common_state
        if not common_state:
            # If the current request state is complete and one of its samples moved from
            # the final sample state, then move the request state to In-progress
            if request.is_complete:
                message = "At least 1 sample state moved from the final sample state, so now the request is in the '%s' state" % request.states.SUBMITTED
                event = trans.model.RequestEvent( request, request.states.SUBMITTED, message )
                trans.sa_session.add( event )
                trans.sa_session.flush()
            return trans.response.send_redirect( web.url_for( controller='requests_common',
                                                              action='manage_request',
                                                              cntrller=cntrller,
                                                              id=request_id,
                                                              status=status,
                                                              message=message ) )
        final_state = False
        request_type_state = request.type.state
        if common_state.id == request_type_state.id:
            # since all the samples are in the final state, change the request state to 'Complete'
            comments = "All samples of this request are in the last sample state (%s). " % request_type_state.name
            state = request.states.COMPLETE
            final_state = True
        else:
            comments = "All samples are in %s state. " % common_state.name
            state = request.states.SUBMITTED
        event = trans.model.RequestEvent(request, state, comments)
        trans.sa_session.add( event )
        trans.sa_session.flush()
        # check if an email notification is configured to be sent when the samples 
        # are in this state
        retval = request.send_email_notification( trans, common_state, final_state )
        if retval:
            message = comments + retval
        else:
            message = comments
        return trans.response.send_redirect( web.url_for( controller='requests_common',
                                                          action='manage_request',
                                                          cntrller=cntrller,
                                                          id=trans.security.encode_id(request.id),
                                                          status='done',
                                                          message=message ) )
    def __save_sample( self, trans, cntrller, request, current_samples, **kwd ):
        # Save all the new/unsaved samples entered by the user
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        managing_samples = util.string_as_bool( params.get( 'managing_samples', False ) )
        is_admin = cntrller == 'requests_admin' and trans.user_is_admin()
        selected_value = params.get( 'sample_operation', 'none' )
        # Check for duplicate sample names
        message = ''
        for index in range( len( current_samples ) - len( request.samples ) ):
            sample_index = index + len( request.samples )
            current_sample = current_samples[ sample_index ]
            sample_name = current_sample[ 'name' ]
            if not sample_name.strip():
                message = 'Enter the name of sample number %i' % sample_index
                break
            count = 0
            for i in range( len( current_samples ) ):
                if sample_name == current_samples[ i ][ 'name' ]:
                    count += 1
            if count > 1: 
                message = "This request has %i samples with the name (%s).  Samples belonging to a request must have unique names." % ( count, sample_name )
                break
        if message:
            selected_samples = self.__get_selected_samples( trans, request, **kwd )
            request_widgets = self.__get_request_widgets( trans, request.id )
            sample_copy = self.__build_copy_sample_select_field( trans, current_samples )
            sample_operation_select_field = self.__build_sample_operation_select_field( trans, is_admin, request, selected_value )
            status = 'error'
            return trans.fill_template( '/requests/common/manage_request.mako',
                                        cntrller=cntrller,
                                        request=request,
                                        selected_samples=selected_samples,
                                        request_widgets=request_widgets,
                                        current_samples=current_samples,
                                        sample_copy=sample_copy, 
                                        managing_samples=managing_samples,
                                        sample_operation_select_field=sample_operation_select_field,
                                        status=status,
                                        message=message )
        if not managing_samples:
            for index in range( len( current_samples ) - len( request.samples ) ):
                sample_index = len( request.samples )
                current_sample = current_samples[ sample_index ]
                form_values = trans.model.FormValues( request.type.sample_form, current_sample[ 'field_values' ] )
                trans.sa_session.add( form_values )
                trans.sa_session.flush()                    
                s = trans.model.Sample( current_sample[ 'name' ],
                                        '', 
                                        request,
                                        form_values, 
                                        current_sample[ 'barcode' ],
                                        current_sample[ 'library' ],
                                        current_sample[ 'folder' ] )
                trans.sa_session.add( s )
                trans.sa_session.flush()
        else:
            message = 'Changes made to the samples are saved. '
            for sample_index in range( len( current_samples ) ):
                sample = request.samples[ sample_index ]
                current_sample = current_samples[ sample_index ]
                sample.name = current_sample[ 'name' ] 
                sample.library = current_sample[ 'library' ]
                sample.folder = current_sample[ 'folder' ]
                if request.is_submitted:
                    bc_message = self.__validate_barcode( trans, sample, current_sample[ 'barcode' ] )
                    if bc_message:
                        status = 'error'
                        message += bc_message
                    else:
                        if not sample.bar_code:
                            # If this is a 'new' (still in its first state) sample
                            # change the state to the next
                            if sample.state.id == request.type.states[0].id:
                                event = trans.model.SampleEvent( sample, 
                                                                 request.type.states[1], 
                                                                 'Sample added to the system' )
                                trans.sa_session.add( event )
                                trans.sa_session.flush()
                                # Now check if all the samples' barcode has been entered.
                                # If yes then send notification email if configured
                                common_state = request.samples_have_common_state
                                if common_state:
                                    if common_state.id == request.type.states[1].id:
                                        event = trans.model.RequestEvent( request, 
                                                                          request.states.SUBMITTED,
                                                                          "All samples are in %s state." % common_state.name )
                                        trans.sa_session.add( event )
                                        trans.sa_session.flush()
                                        request.send_email_notification( trans, request.type.states[1] )
                        sample.bar_code = current_samples[sample_index]['barcode']
                trans.sa_session.add( sample )
                trans.sa_session.flush()
                form_values = trans.sa_session.query( trans.model.FormValues ).get( sample.values.id )
                form_values.content = current_sample[ 'field_values' ]
                trans.sa_session.add( form_values )
                trans.sa_session.flush()
        return trans.response.send_redirect( web.url_for( controller='requests_common',
                                                          action='manage_request',
                                                          cntrller=cntrller,
                                                          id=trans.security.encode_id( request.id ),
                                                          status=status,
                                                          message=message ) )
    @web.expose
    @web.require_login( "find samples" )
    def find_samples( self, trans, cntrller, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        is_admin = cntrller == 'requests_admin' and trans.user_is_admin()
        samples_list = []
        results = ''
        if params.get( 'find_samples_button', False ):
            search_string = kwd.get( 'search_box', ''  )
            search_type = params.get( 'search_type', ''  )
            request_states = util.listify( params.get( 'request_states', '' ) )
            samples = []
            if search_type == 'barcode':
                samples = trans.sa_session.query( trans.model.Sample ) \
                                          .filter( and_( trans.model.Sample.table.c.deleted==False,
                                                         func.lower( trans.model.Sample.table.c.bar_code ).like( "%" + search_string.lower() + "%" ) ) ) \
                                          .order_by( trans.model.Sample.table.c.create_time.desc() )
            elif search_type == 'sample name':
                samples = trans.sa_session.query( trans.model.Sample ) \
                                          .filter( and_( trans.model.Sample.table.c.deleted==False,
                                                         func.lower( trans.model.Sample.table.c.name ).like( "%" + search_string.lower() + "%" ) ) ) \
                                          .order_by( trans.model.Sample.table.c.create_time.desc() )
            elif search_type == 'dataset':
                samples = trans.sa_session.query( trans.model.Sample ) \
                                          .filter( and_( trans.model.Sample.table.c.deleted==False,
                                                         trans.model.SampleDataset.table.c.sample_id==trans.model.Sample.table.c.id,
                                                         func.lower( trans.model.SampleDataset.table.c.name ).like( "%" + search_string.lower() + "%" ) ) ) \
                                          .order_by( trans.model.Sample.table.c.create_time.desc() )
            if is_admin:
                for s in samples:
                    if not s.request.deleted and s.request.state in request_states:
                        samples_list.append( s )
            else:
                for s in samples:
                    if s.request.user.id == trans.user.id and s.request.state in request_states and not s.request.deleted:
                        samples_list.append( s )
            results = 'There are %i samples matching the search parameters.' % len( samples_list )
        # Build the request_states SelectField
        selected_value = kwd.get( 'request_states', trans.model.Request.states.SUBMITTED )
        states = [ v for k, v in trans.model.Request.states.items() ]
        request_states = build_select_field( trans,
                                             states,
                                             'self',
                                             'request_states',
                                             selected_value=selected_value,
                                             refresh_on_change=False,
                                             multiple=True,
                                             display='checkboxes' )
        # Build the search_type SelectField
        selected_value = kwd.get( 'search_type', 'sample name' )
        types = [ 'sample name', 'barcode', 'dataset' ]
        search_type = build_select_field( trans, types, 'self', 'search_type', selected_value=selected_value, refresh_on_change=False )
        # Build the search_box TextField
        search_box = TextField( 'search_box', 50, kwd.get('search_box', '' ) )
        return trans.fill_template( '/requests/common/find_samples.mako', 
                                    cntrller=cntrller,
                                    request_states=request_states,
                                    samples=samples_list,
                                    search_type=search_type,
                                    results=results,
                                    search_box=search_box )
    @web.expose
    @web.require_login( "sample events" )
    def sample_events( self, trans, cntrller, **kwd ):
        params = util.Params( kwd )
        status = params.get( 'status', 'done' )
        message = util.restore_text( params.get( 'message', '' ) )
        sample_id = params.get( 'sample_id', None )
        try:
            sample = trans.sa_session.query( trans.model.Sample ).get( trans.security.decode_id( sample_id ) )
        except:
            return invalid_id_redirect( trans, cntrller, sample_id )
        events_list = []
        for event in sample.events:         
            events_list.append( ( event.state.name,
                                  event.state.desc, 
                                  time_ago( event.update_time ), 
                                  event.comment ) )
        return trans.fill_template( '/requests/common/sample_events.mako', 
                                    cntrller=cntrller,
                                    events_list=events_list,
                                    sample=sample )
    def __add_sample( self, trans, cntrller, request, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        managing_samples = util.string_as_bool( params.get( 'managing_samples', False ) )
        is_admin = cntrller == 'requests_admin' and trans.user_is_admin()
        # Get the widgets for rendering the request form
        request_widgets = self.__get_request_widgets( trans, request.id )
        current_samples, managing_samples, libraries = self.__get_sample_info( trans, request, **kwd )
        if not current_samples:
            # Form field names are zero-based.
            sample_index = 0
        else:
            sample_index = len( current_samples )
        if params.get( 'add_sample_button', False ):
            num_samples_to_add = int( params.get( 'num_sample_to_copy', 1 ) )
            # See if the user has selected a sample to copy.
            copy_sample_index = int( params.get( 'copy_sample_index', -1 ) )
            for index in range( num_samples_to_add ):
                if copy_sample_index != -1:
                    # The user has selected a sample to copy.
                    library_id = current_samples[ copy_sample_index][ 'library_select_field' ].get_selected( return_value=True )
                    folder_id = current_samples[ copy_sample_index ][ 'folder_select_field' ].get_selected( return_value=True )
                    name = current_samples[ copy_sample_index ][ 'name' ] + '_%i' % ( index+1 )
                    library_id = 'none'
                    folder_id = 'none'
                    field_values = [ val for val in current_samples[ copy_sample_index ][ 'field_values' ] ]
                else:
                    # The user has not selected a sample to copy (may just be adding a sample).
                    library_id = None
                    folder_id = None
                    name = 'Sample_%i' % ( sample_index+1 )
                    field_values = [ '' for field in request.type.sample_form.fields ]
                # Build the library_select_field and folder_select_field for the new sample being added.
                library_select_field, folder_select_field = self.__build_library_and_folder_select_fields( trans,
                                                                                                           user=request.user, 
                                                                                                           sample_index=sample_index, 
                                                                                                           libraries=libraries,
                                                                                                           sample=None, 
                                                                                                           library_id=library_id,
                                                                                                           folder_id=folder_id,
                                                                                                           **kwd )
                # Append the new sample to the current list of samples for the request
                current_samples.append( dict( name=name,
                                              barcode='',
                                              library=None,
                                              library_id=library_id,
                                              folder=None,
                                              folder_id=folder_id,
                                              field_values=field_values,
                                              library_select_field=library_select_field,
                                              folder_select_field=folder_select_field ) )
        selected_samples = self.__get_selected_samples( trans, request, **kwd )
        selected_value = params.get( 'sample_operation', 'none' )
        sample_operation_select_field = self.__build_sample_operation_select_field( trans, is_admin, request, selected_value )
        sample_copy = self.__build_copy_sample_select_field( trans, current_samples )
        return trans.fill_template( '/requests/common/manage_request.mako',
                                    cntrller=cntrller,
                                    request=request,
                                    selected_samples=selected_samples,
                                    request_widgets=request_widgets,
                                    current_samples=current_samples,
                                    sample_operation_select_field=sample_operation_select_field,
                                    sample_copy=sample_copy, 
                                    managing_samples=managing_samples,
                                    message=message,
                                    status=status )
    def __get_sample_info( self, trans, request, **kwd ):
        """
        Retrieves all user entered sample information and returns a
        list of all the samples and their field values.
        """
        params = util.Params( kwd )
        managing_samples = util.string_as_bool( params.get( 'managing_samples', False ) )
        # Bet all data libraries accessible to this user
        libraries = request.user.accessible_libraries( trans, [ trans.app.security_agent.permitted_actions.LIBRARY_ADD ] )
        # Build the list of widgets which will be used to render each sample row on the request page
        current_samples = []
        for index, sample in enumerate( request.samples ):
            library_select_field, folder_select_field = self.__build_library_and_folder_select_fields( trans,
                                                                                                       request.user,
                                                                                                       index,
                                                                                                       libraries,
                                                                                                       sample,
                                                                                                       **kwd )
            current_samples.append( dict( name=sample.name,
                                          barcode=sample.bar_code,
                                          library=sample.library,
                                          folder=sample.folder,
                                          field_values=sample.values.content,
                                          library_select_field=library_select_field,
                                          folder_select_field=folder_select_field ) )
        if not managing_samples:
            sample_index = len( request.samples ) 
        else:
            sample_index = 0
        while True:
            library_id = params.get( 'sample_%i_library_id' % sample_index, None )
            folder_id = params.get( 'sample_%i_folder_id' % sample_index, None )
            if params.get( 'sample_%i_name' % sample_index, False  ):
                # Data library
                try:
                    library = trans.sa_session.query( trans.model.Library ).get( trans.security.decode_id( library_id ) )
                    #library_id = library.id
                except:
                    library = None
                if library is not None:
                    # Folder
                    try:
                        folder = trans.sa_session.query( trans.model.LibraryFolder ).get( trans.security.decode_id( folder_id ) )
                        #folder_id = folder.id
                    except:
                        if library:
                            folder = library.root_folder
                        else:
                            folder = None
                else:
                    folder = None
                sample_info = dict( name=util.restore_text( params.get( 'sample_%i_name' % sample_index, ''  ) ),
                                    barcode=util.restore_text( params.get( 'sample_%i_barcode' % sample_index, ''  ) ),
                                    library=library,
                                    folder=folder)
                sample_info[ 'field_values' ] = []
                for field_index in range( len( request.type.sample_form.fields ) ):
                    sample_info[ 'field_values' ].append( util.restore_text( params.get( 'sample_%i_field_%i' % ( sample_index, field_index ), ''  ) ) )
                if not managing_samples:
                    sample_info[ 'library_select_field' ], sample_info[ 'folder_select_field' ] = self.__build_library_and_folder_select_fields( trans,
                                                                                                                                                 request.user, 
                                                                                                                                                 sample_index,
                                                                                                                                                 libraries, 
                                                                                                                                                 None,
                                                                                                                                                 library_id,
                                                                                                                                                 folder_id,
                                                                                                                                                 **kwd )
                    current_samples.append( sample_info )
                else:
                    sample_info[ 'library_select_field' ], sample_info[ 'folder_select_field' ] = self.__build_library_and_folder_select_fields( trans, 
                                                                                                                                                 request.user, 
                                                                                                                                                 sample_index, 
                                                                                                                                                 libraries, 
                                                                                                                                                 request.samples[ sample_index ], 
                                                                                                                                                 **kwd )
                    current_samples[ sample_index ] =  sample_info
                sample_index += 1
            else:
                break
        return current_samples, managing_samples, libraries
    @web.expose
    @web.require_login( "delete sample from sequencing request" )
    def delete_sample( self, trans, cntrller, **kwd ):
        params = util.Params( kwd )
        status = params.get( 'status', 'done' )
        message = util.restore_text( params.get( 'message', '' ) )
        request_id = params.get( 'request_id', None )
        try:
            request = trans.sa_session.query( trans.model.Request ).get( trans.security.decode_id( request_id ) )
        except:
            return invalid_id_redirect( trans, cntrller, request_id )
        current_samples, managing_samples, libraries = self.__get_sample_info( trans, request, **kwd )
        sample_index = int( params.get( 'sample_id', 0 ) )
        sample_name = current_samples[sample_index]['name']
        sample = request.has_sample( sample_name )
        if sample:
            trans.sa_session.delete( sample.values )
            trans.sa_session.delete( sample )
            trans.sa_session.flush()
        message = 'Sample (%s) has been deleted.' % sample_name
        return trans.response.send_redirect( web.url_for( controller='requests_common',
                                                          action='manage_request',
                                                          cntrller=cntrller,
                                                          id=trans.security.encode_id( request.id ),
                                                          status=status,
                                                          message=message ) )
    @web.expose
    @web.require_login( "view data transfer page" )
    def view_dataset_transfer( self, trans, cntrller, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        is_admin = cntrller == 'requests_admin' and trans.user_is_admin()
        sample_id = params.get( 'sample_id', None )
        try:
            sample = trans.sa_session.query( trans.model.Sample ).get( trans.security.decode_id( sample_id ) )
        except:
            return invalid_id_redirect( trans, cntrller, sample_id )
        # check if a library and folder has been set for this sample yet.
        if not sample.library or not sample.folder:
            status = 'error'
            message = "Set a data library and folder for sequencing request (%s) to transfer datasets." % sample.name
            return trans.response.send_redirect( web.url_for( controller='requests_common',
                                                              action='manage_request',
                                                              cntrller=cntrller,
                                                              id=trans.security.encode_id( sample.request.id ),
                                                              status=status,
                                                              message=message ) )
        if is_admin:
            return trans.response.send_redirect( web.url_for( controller='requests_admin',
                                                              action='manage_datasets',
                                                              sample_id=sample_id ) )
            
        folder_path = util.restore_text( params.get( 'folder_path', ''  ) )
        if not folder_path:
            if len( sample.datasets ):
                folder_path = os.path.dirname( sample.datasets[-1].file_path[:-1] )
            else:
                folder_path = util.restore_text( sample.request.type.datatx_info.get( 'data_dir', '' ) )
        if folder_path and folder_path[-1] != os.sep:
            folder_path += os.sep
        if not sample.request.type.datatx_info['host'] \
            or not sample.request.type.datatx_info['username'] \
            or not sample.request.type.datatx_info['password']:
            status = 'error'
            message = 'The sequencer login information is incomplete. Click on sequencer information to add login details.'
        return trans.fill_template( '/requests/common/dataset_transfer.mako', 
                                    cntrller=cntrller,
                                    sample=sample, 
                                    dataset_files=sample.datasets,
                                    message=message,
                                    status=status,
                                    files=[],
                                    folder_path=folder_path )
    def __import_samples( self, trans, cntrller, request, current_samples, libraries, **kwd ):
        """
        Reads the samples csv file and imports all the samples.  The format of the csv file is:
        SampleName,DataLibrary,DataLibraryFolder,Field1,Field2....
        """
        params = util.Params( kwd )
        managing_samples = util.string_as_bool( params.get( 'managing_samples', False ) )
        file_obj = params.get( 'file_data', '' )
        try:
            reader = csv.reader( file_obj.file )
            for row in reader:
                library_id = None
                folder_id = None
                # FIXME: this is bad - what happens when multiple libraries have the same name??
                lib = trans.sa_session.query( trans.model.Library ) \
                                      .filter( and_( trans.model.Library.table.c.name==row[1],
                                                     trans.model.Library.table.c.deleted==False ) ) \
                                      .first()
                if lib:
                    folder = trans.sa_session.query( trans.model.LibraryFolder ) \
                                             .filter( and_( trans.model.LibraryFolder.table.c.name==row[2],
                                                            trans.model.LibraryFolder.table.c.deleted==False ) ) \
                                             .first()
                    if folder:
                        library_id = lib.id
                        folder_id = folder.id
                library_select_field, folder_select_field = self.__build_library_and_folder_select_fields( trans,
                                                                                                           request.user,
                                                                                                           len( current_samples ), 
                                                                                                           libraries,
                                                                                                           None,
                                                                                                           library_id,
                                                                                                           folder_id,
                                                                                                           **kwd )
                current_samples.append( dict( name=row[0], 
                                              barcode='',
                                              library=None,
                                              folder=None,
                                              library_select_field=library_select_field,
                                              folder_select_field=folder_select_field,
                                              field_values=row[3:] ) )
        except Exception, e:
            status = 'error'
            message = 'Error thrown when importing samples file: %s' % str( e )
            return trans.response.send_redirect( web.url_for( controller='requests_common',
                                                              action='manage_request',
                                                              cntrller=cntrller,
                                                              id=trans.security.encode_id( request.id ),
                                                              status=status,
                                                              message=message ) )
        request_widgets = self.__get_request_widgets( trans, request.id )
        sample_copy = self.__build_copy_sample_select_field( trans, current_samples )
        return trans.fill_template( '/requests/common/manage_request.mako',
                                    cntrller=cntrller,
                                    request=request,
                                    request_widgets=request_widgets,
                                    current_samples=current_samples,
                                    sample_copy=sample_copy,
                                    managing_samples=managing_samples )
    # ===== Methods for handling form definition widgets =====
    def __get_request_widgets( self, trans, id ):
        """Get the widgets for the request"""
        request = trans.sa_session.query( trans.model.Request ).get( id )
        # The request_widgets list is a list of dictionaries
        request_widgets = []
        for index, field in enumerate( request.type.request_form.fields ):
            if field[ 'required' ]:
                required_label = 'Required'
            else:
                required_label = 'Optional'
            if field[ 'type' ] == 'AddressField':
                if request.values.content[ index ]:
                    request_widgets.append( dict( label=field[ 'label' ],
                                                  value=trans.sa_session.query( trans.model.UserAddress ).get( int( request.values.content[ index ] ) ).get_html(),
                                                  helptext=field[ 'helptext' ] + ' (' + required_label + ')' ) )
                else:
                    request_widgets.append( dict( label=field[ 'label' ],
                                                  value=None,
                                                  helptext=field[ 'helptext' ] + ' (' + required_label + ')' ) )
            else: 
                request_widgets.append( dict( label=field[ 'label' ],
                                              value=request.values.content[ index ],
                                              helptext=field[ 'helptext' ] + ' (' + required_label + ')' ) )
        return request_widgets
    def __get_samples_widgets( self, trans, request, libraries, **kwd ):
        """Get the widgets for all of the samples currently associated with the request"""
        # The current_samples_widgets list is a list of dictionaries
        current_samples_widgets = []
        for index, sample in enumerate( request.samples ):
            # Build the library_select_field and folder_select_field for each existing sample
            library_select_field, folder_select_field = self.__build_library_and_folder_select_fields( trans,
                                                                                                       user=request.user,
                                                                                                       sample_index=index,
                                                                                                       libraries=libraries,
                                                                                                       sample=sample,
                                                                                                       **kwd )
            # Append the dictionary for the current sample to the current_samples_widgets list
            current_samples_widgets.append( dict( name=sample.name,
                                                  barcode=sample.bar_code,
                                                  library=sample.library,
                                                  folder=sample.folder,
                                                  field_values=sample.values.content,
                                                  library_select_field=library_select_field,
                                                  folder_select_field=folder_select_field ) )
        return current_samples_widgets
    # ===== Methods for building SelectFields used on various request forms =====
    def __build_copy_sample_select_field( self, trans, current_samples ):
        copy_sample_index_select_field = SelectField( 'copy_sample_index' )
        copy_sample_index_select_field.add_option( 'None', -1, selected=True )  
        for index, sample_dict in enumerate( current_samples ):
            copy_sample_index_select_field.add_option( sample_dict[ 'name' ], index )
        return copy_sample_index_select_field  
    def __build_request_type_id_select_field( self, trans, selected_value='none' ):
        accessible_request_types = trans.user.accessible_request_types( trans )
        return build_select_field( trans, accessible_request_types, 'name', 'request_type_id', selected_value=selected_value, refresh_on_change=True )
    def __build_user_id_select_field( self, trans, selected_value='none' ):
        active_users = trans.sa_session.query( trans.model.User ) \
                                       .filter( trans.model.User.table.c.deleted == False ) \
                                       .order_by( trans.model.User.email.asc() )
        # A refresh_on_change is required so the user's set of addresses can be displayed.
        return build_select_field( trans, active_users, 'email', 'user_id', selected_value=selected_value, refresh_on_change=True )
    def __build_sample_operation_select_field( self, trans, is_admin, request, selected_value ):
        # The sample_operation SelectField is displayed only after the request has been submitted.
        # It's label is "For selected samples"
        if is_admin:
            if request.is_complete:
                bulk_operations = [ trans.model.Sample.bulk_operations.CHANGE_STATE ]
            if request.is_rejected:
                bulk_operations = [ trans.model.Sample.bulk_operations.SELECT_LIBRARY ]
            else:
                bulk_operations = [ s for i, s in trans.model.Sample.bulk_operations.items() ]
        else:
            if request.is_complete:
                bulk_operations = []
            else:
                bulk_operations = [ trans.model.Sample.bulk_operations.SELECT_LIBRARY ]
        return build_select_field( trans, bulk_operations, 'self', 'sample_operation', selected_value=selected_value, refresh_on_change=True )
    def __build_library_and_folder_select_fields( self, trans, user, sample_index, libraries, sample=None, library_id=None, folder_id=None, **kwd ):
        # Create the library_id SelectField for a specific sample. The received libraries param is a list of all the libraries
        # accessible to the current user, and we add them as options to the library_select_field.  If the user has selected an
        # existing library then display all the accessible folders of the selected library in the folder_select_field.
        #
        # The libraries dictionary looks like: { library : '1,2' }, library : '3' }.  Its keys are the libraries that
        # should be displayed for the current user and its values are strings of comma-separated folder ids that should
        # NOT be displayed.
        #
        # TODO: all object ids received in the params must be encoded.
        params = util.Params( kwd )
        library_select_field_name= "sample_%i_library_id" % sample_index
        folder_select_field_name = "sample_%i_folder_id" % sample_index
        if not library_id:
            library_id = params.get( library_select_field_name, 'none'  )
        selected_library = None
        selected_hidden_folder_ids = []
        showable_folders = []
        if sample and sample.library and library_id == 'none':
            library_id = str( sample.library.id )
            selected_library = sample.library
        # If we have a selected library, get the list of it's folders that are not accessible to the current user
        for library, hidden_folder_ids in libraries.items():
            encoded_id = trans.security.encode_id( library.id )
            if encoded_id == str( library_id ):
                selected_library = library
                selected_hidden_folder_ids = hidden_folder_ids.split( ',' )
                break
        # sample_%i_library_id SelectField with refresh on change enabled
        library_select_field = build_select_field( trans,
                                                   libraries.keys(),
                                                   'name', 
                                                   library_select_field_name,
                                                   initial_value='none',
                                                   selected_value=str( library_id ).lower(),
                                                   refresh_on_change=True )
        # Get all accessible folders for the selected library, if one is indeed selected
        if selected_library:
            showable_folders = trans.app.security_agent.get_showable_folders( user,
                                                                              user.all_roles(), 
                                                                              selected_library, 
                                                                              [ trans.app.security_agent.permitted_actions.LIBRARY_ADD ], 
                                                                              selected_hidden_folder_ids )
        if sample:
            # The user is editing the request, and may have previously selected a folder
            if sample.folder:
                selected_folder_id = sample.folder.id
            else:
                # If a library is selected but not a folder, use the library's root folder
                if sample.library:
                    selected_folder_id = sample.library.root_folder.id
                else:
                    # The user just selected a folder
                    selected_folder_id = params.get( folder_select_field_name, 'none' )
        elif folder_id:
            # TODO: not sure when this would be passed
                selected_folder_id = folder_id
        else:
            selected_folder_id = 'none'
        # TODO: Change the name of the library root folder to "Library root" to clarify to the
        # user that it is the root folder.  We probably should just change this in the Library code,
        # and update the data in the db.
        folder_select_field = build_select_field( trans,
                                                  showable_folders,
                                                  'name', 
                                                  folder_select_field_name,
                                                  initial_value='none',
                                                  selected_value=selected_folder_id )
        return library_select_field, folder_select_field
    def __build_sample_state_id_select_field( self, trans, request, selected_value ):
        if selected_value == 'none':
            if request.samples:
                selected_value = trans.security.encode_id( request.samples[0].state.id )
            else:
                selected_value = trans.security.encode_id( request.type.states[0].id )
        return build_select_field( trans,
                                   objs=request.type.states,
                                   label_attr='name',
                                   select_field_name='sample_state_id',
                                   selected_value=selected_value,
                                   refresh_on_change=False )
    # ===== Methods for validation forms and fields =====
    def __validate_request( self, trans, cntrller, request ):
        """Validates the request entered by the user"""
        # TODO: Add checks for required sample fields here.
        empty_fields = []
        # Make sure required form fields are filled in.
        for index, field in enumerate( request.type.request_form.fields ):
            if field[ 'required' ] == 'required' and request.values.content[ index ] in [ '', None ]:
                empty_fields.append( field[ 'label' ] )
        if empty_fields:
            message = 'Complete the following fields of the request before submitting: '
            for ef in empty_fields:
                message += '<b>' + ef + '</b> '
            return message
        return None
    def __validate_barcode( self, trans, sample, barcode ):
        """
        Makes sure that the barcode about to be assigned to a sample is gobally unique.
        That is, barcodes must be unique across requests in Galaxy sample tracking. 
        """
        message = ''
        unique = True
        for index in range( len( sample.request.samples ) ):
            # Check for empty bar code
            if not barcode.strip():
                message = 'Fill in the barcode for sample (%s).' % sample.name
                break
            # TODO: Add a unique constraint to sample.bar_code table column
            # Make sure bar code is unique
            for sample_has_bar_code in trans.sa_session.query( trans.model.Sample ) \
                                                        .filter( trans.model.Sample.table.c.bar_code == barcode ):
                if sample_has_bar_code and sample_has_bar_code.id != sample.id:
                    message = '''The bar code (%s) associated with the sample (%s) belongs to another sample.  
                                 Bar codes must be unique across all samples, so use a different bar code 
                                 for this sample.''' % ( barcode, sample.name )
                    unique = False
                    break
            if not unique:
                break
        return message
    def __validate_email( self, email ):
        error = ''
        if len( email ) == 0 or "@" not in email or "." not in email:
            error = "(%s) is not a valid email address.  " % str( email )
        elif len( email ) > 255:
            error = "(%s) exceeds maximum allowable length.  " % str( email )
        return error
    # ===== Other miscellaneoud utility methods =====
    def __get_selected_samples( self, trans, request, **kwd ):
        selected_samples = []
        for sample in request.samples:
            if CheckboxField.is_checked( kwd.get( 'select_sample_%i' % sample.id, '' ) ):
                selected_samples.append( trans.security.encode_id( sample.id ) )
        return selected_samples

# ===== Miscellaneoud utility methods outside of the RequestsCommon class =====
def invalid_id_redirect( trans, cntrller, obj_id, action='browse_requests' ):
    status = 'error'
    message = "Invalid request id (%s)" % str( obj_id )
    return trans.response.send_redirect( web.url_for( controller=cntrller,
                                                      action=action,
                                                      status=status,
                                                      message=message ) )
