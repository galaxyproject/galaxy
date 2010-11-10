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
        
    # Grid definition
    title = "Sequencing Requests"
    template = "requests/grid.mako"
    model_class = model.Request
    default_sort_key = "-update_time"
    num_rows_per_page = 50
    use_paging = True
    default_filter = dict( state="All", deleted="False" )
    columns = [
        NameColumn( "Name", 
                    key="name", 
                    link=( lambda item: dict( operation="view_request", id=item.id ) ),
                    attach_popup=True, 
                    filterable="advanced" ),
        DescriptionColumn( "Description",
                           key='desc',
                           filterable="advanced" ),
        SamplesColumn( "Samples", 
                       link=( lambda item: iff( item.deleted, None, dict( operation="edit_samples", id=item.id ) ) ) ),
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
                     link=( lambda item: iff( item.deleted, None, dict( operation="request_events", id=item.id ) ) )
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
    def sample_state_updates( self, trans, ids=None, states=None ):
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
                                                                               sample=sample),
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
        user_id_encoded = True
        user_id = params.get( 'user_id', 'none' )
        if user_id != 'none':
            try: 
                user = trans.sa_session.query( trans.model.User ).get( trans.security.decode_id( user_id ) )
            except TypeError, e:
                # We must have an email address rather than an encoded user id
                # This is because the galaxy.base.js creates a search+select box 
                # when there are more than 20 items in a SelectField.
                user = trans.sa_session.query( trans.model.User ) \
                                       .filter( trans.model.User.table.c.email==util.restore_text( user_id ) ) \
                                       .first()
                user_id_encoded = False
                
        elif not is_admin:
            user = trans.user
        else:
            user = None
        if params.get( 'create_request_button', False ) or params.get( 'add_sample_button', False ):
            name = util.restore_text( params.get( 'name', '' ) )
            if is_admin and user_id == 'none':
                message = 'Select the user on behalf of whom you are submitting this request.'
                status = 'error'
            elif user is None:
                message = 'Invalid user ID (%s)' % str(user_id)
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
                    request_id = trans.security.encode_id( request.id )
                    return self.add_sample( trans, cntrller, request_id, **kwd )
        request_type_select_field = self.__build_request_type_id_select_field( trans, selected_value=request_type_id )
        # Widgets to be rendered on the request form
        widgets = []
        if request_type is not None or status == 'error':
            # Either the user selected a request_type or an error exists on the form.
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
        widgets = self.populate_widgets_from_kwd( trans, widgets, **kwd )
        if request_type is not None or status == 'error':
            # Either the user selected a request_type or an error exists on the form.
            if is_admin:
                if not user_id_encoded:
                    selected_user_id = trans.security.encode_id( user.id )
                else:
                    selected_user_id = user_id
                user_widget = dict( label='Select user',
                                    widget=self.__build_user_id_select_field( trans, selected_value=selected_user_id ),
                                    helptext='Submit the request on behalf of the selected user (Required)')
                widgets = [ user_widget ] + widgets
        return trans.fill_template( '/requests/common/create_request.mako',
                                    cntrller=cntrller,
                                    request_type_select_field=request_type_select_field,
                                    request_type_select_field_selected=request_type_id,                               
                                    widgets=widgets,
                                    message=message,
                                    status=status )
    @web.expose
    @web.require_login( "view request" )
    def view_request( self, trans, cntrller, **kwd ):
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
        current_samples = self.__get_sample_widgets( trans, request, request.samples, **kwd )
        request_widgets = self.__get_request_widgets( trans, request.id )
        return trans.fill_template( '/requests/common/view_request.mako',
                                    cntrller=cntrller, 
                                    request=request,
                                    request_widgets=request_widgets,
                                    current_samples=current_samples,
                                    status=status,
                                    message=message )
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
        if params.get( 'edit_basic_request_info_button', False ):
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
        widgets = self.populate_widgets_from_kwd( trans, widgets, **kwd )
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
        notification = dict( email=[ user.email ], sample_states=[ request_type.final_sample_state.id ], body='', subject='' )
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
            comment = "Request created by %s" % trans.user.email
            if request.user != trans.user:
                comment += " on behalf of %s." % request.user.email
            event = trans.model.RequestEvent( request, request.states.NEW, comment )
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
        comment = "Request submitted by %s" % trans.user.email
        if request.user != trans.user:
            comment += " on behalf of %s." % request.user.email
        event = trans.model.RequestEvent( request, request.states.SUBMITTED, comment )
        trans.sa_session.add( event )
        # Change the state of each of the samples of this request
        # request.type.states is the list of SampleState objects configured
        # by the admin for this RequestType.
        trans.sa_session.add( event )
        trans.sa_session.flush()
        # Samples will not have an associated SampleState until the request is submitted, at which
        # time all samples of the request will be set to the first SampleState configured for the
        # request's RequestType configured by the admin.
        initial_sample_state_after_request_submitted = request.type.states[0]
        for sample in request.samples:
            event_comment = 'Request submitted and sample state set to %s.' % request.type.states[0].name
            event = trans.model.SampleEvent( sample,
                                             initial_sample_state_after_request_submitted,
                                             event_comment )
            trans.sa_session.add( event )
        trans.sa_session.add( request )
        trans.sa_session.flush()
        request.send_email_notification( trans, initial_sample_state_after_request_submitted )
        message = 'The request has been submitted.'
        return trans.response.send_redirect( web.url_for( controller=cntrller,
                                                          action='browse_requests',
                                                          cntrller=cntrller,
                                                          id=request_id,
                                                          status=status,
                                                          message=message ) )
    @web.expose
    @web.require_login( "manage samples" )
    def edit_samples( self, trans, cntrller, **kwd ):
        params = util.Params( kwd )
        is_admin = cntrller == 'requests_admin' and trans.user_is_admin()
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        request_id = params.get( 'id', None )
        try:
            request = trans.sa_session.query( trans.model.Request ).get( trans.security.decode_id( request_id ) )
        except:
            return invalid_id_redirect( trans, cntrller, request_id )
        # This method is called when the user is adding new samples as well as
        # editing existing samples, so we use the editing_samples flag to keep
        # track of what's occurring.
        # TODO: CRITICAL: We need another round of code fixes to abstract out 
        # adding samples vs editing samples.  We need to eliminate the need for
        # this editing_samples flag since it is not maintainable.  Greg will do
        # this work as soon as possible.
        editing_samples = util.string_as_bool( params.get( 'editing_samples', False ) )
        if params.get( 'cancel_changes_button', False ):
            return trans.response.send_redirect( web.url_for( controller='requests_common',
                                                                          action='edit_samples',
                                                                          cntrller=cntrller,
                                                                          id=request_id,
                                                                          editing_samples=editing_samples ) )
        # Get all libraries for which the current user has permission to add items.
        libraries = request.user.accessible_libraries( trans, [ trans.app.security_agent.permitted_actions.LIBRARY_ADD ] )
        # Get the user entered sample information
        current_samples = self.__get_sample_widgets( trans, request, request.samples, **kwd )
        encoded_selected_sample_ids = self.__get_encoded_selected_sample_ids( trans, request, **kwd )
        sample_operation = params.get( 'sample_operation', 'none' )
        def handle_error( **kwd ):
            kwd[ 'status' ] = 'error'
            return trans.response.send_redirect( web.url_for( controller='requests_common',
                                                              action='edit_samples',
                                                              cntrller=cntrller,
                                                              **kwd ) )
        if not encoded_selected_sample_ids and sample_operation != 'none':
            # Probably occurred due to refresh_on_change...is there a better approach?
            kwd[ 'sample_operation' ] = 'none'
            message = 'Select at least one sample before selecting an operation.'
            kwd[ 'message' ] = message
            handle_error( **kwd )
        if params.get( 'import_samples_button', False ):
            # Import sample field values from a csv file
            return self.__import_samples( trans, cntrller, request, current_samples, libraries, **kwd )
        elif params.get( 'add_sample_button', False ):
            return self.add_sample( trans, cntrller, request_id, **kwd )
        elif params.get( 'save_samples_button', False ):
            if encoded_selected_sample_ids:
                # This gets tricky because we need the list of samples to include the same number
                # of objects that that current_samples ( i.e., request.samples ) has.  We'll first
                # get the set of samples corresponding to the checked sample ids.
                samples = []
                selected_samples = []
                for encoded_sample_id in encoded_selected_sample_ids:
                    sample = trans.sa_session.query( trans.model.Sample ).get( trans.security.decode_id( encoded_sample_id ) )
                    selected_samples.append( sample )
                # Now build the list of samples, inserting None for samples that have not been checked.
                for sample in request.samples:
                    if sample in selected_samples:
                        samples.append( sample )
                    else:
                        samples.append( None )
                # The __save_samples method requires sample_widgets, not sample objects
                samples = self.__get_sample_widgets( trans, request, samples, **kwd )
            else:
                samples = current_samples
            return self.__save_samples( trans, cntrller, request, samples, **kwd )
        request_widgets = self.__get_request_widgets( trans, request.id )
        sample_copy = self.__build_copy_sample_select_field( trans, current_samples )
        libraries_select_field, folders_select_field = self.__build_library_and_folder_select_fields( trans,
                                                                                                      request.user,
                                                                                                      0,
                                                                                                      libraries,
                                                                                                      None,
                                                                                                      **kwd )
        sample_operation_select_field = self.__build_sample_operation_select_field( trans, is_admin, request, sample_operation )
        sample_state_id = params.get( 'sample_state_id', None )
        sample_state_id_select_field = self.__build_sample_state_id_select_field( trans, request, sample_state_id )
        return trans.fill_template( '/requests/common/edit_samples.mako',
                                    cntrller=cntrller, 
                                    request=request,
                                    encoded_selected_sample_ids=encoded_selected_sample_ids,
                                    request_widgets=request_widgets,
                                    current_samples=current_samples,
                                    sample_copy=sample_copy, 
                                    libraries=libraries,
                                    sample_operation_select_field=sample_operation_select_field,
                                    libraries_select_field=libraries_select_field,
                                    folders_select_field=folders_select_field,
                                    sample_state_id_select_field=sample_state_id_select_field,
                                    editing_samples=editing_samples,
                                    status=status,
                                    message=message )
    @web.expose
    def update_sample_state(self, trans, cntrller, sample_ids, new_state, comment=None ):
        for sample_id in sample_ids:
            try:
                sample = trans.sa_session.query( trans.model.Sample ).get( trans.security.decode_id( sample_id ) )
            except:
                if cntrller == 'api':
                    trans.response.status = 400
                    return "Invalid sample id ( %s ) specified, unable to decode." % str( sample_id )
                else:
                    return invalid_id_redirect( trans, cntrller, sample_id )
            event = trans.model.SampleEvent( sample, new_state, comment )
            trans.sa_session.add( event )
            trans.sa_session.flush()
        if cntrller == 'api':
            return 200, 'Done'        
    @web.expose
    @web.require_login( "delete sequencing requests" )
    def delete_request( self, trans, cntrller, **kwd ):
        params = util.Params( kwd )
        id_list = util.listify( kwd.get( 'id', '' ) )
        message = util.restore_text( params.get( 'message', '' ) )
        status = util.restore_text( params.get( 'status', 'done' ) )
        is_admin = cntrller == 'requests_admin' and trans.user_is_admin()
        num_deleted = 0
        not_deleted = []
        for id in id_list:
            ok_for_now = True
            try:
                # This block will handle bots that do not send valid request ids.
                request = trans.sa_session.query( trans.model.Request ).get( trans.security.decode_id( id ) )
            except:
                ok_for_now = False
            if ok_for_now:
                # We will only allow the request to be deleted by a non-admin user if not request.submitted
                if is_admin or not request.is_submitted:
                    request.deleted = True
                    trans.sa_session.add( request )
                    # Delete all the samples belonging to this request
                    for s in request.samples:
                        s.deleted = True
                        trans.sa_session.add( s )
                    comment = "Request marked deleted by %s." % trans.user.email
                    # There is no DELETED state for a request, so keep the current request state
                    event = trans.model.RequestEvent( request, request.state, comment )
                    trans.sa_session.add( event )
                    trans.sa_session.flush()
                    num_deleted += 1
                else:
                    not_deleted.append( request )
        message += '%i requests have been deleted.' % num_deleted
        if not_deleted:
            message += '  Contact the administrator to delete the following submitted requests: '
            for request in not_deleted:
                message += '%s, ' % request.name
            message = message.rstrip( ', ' )
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
                # This block will handle bots that do not send valid request ids.
                request = trans.sa_session.query( trans.model.Request ).get( trans.security.decode_id( id ) )
            except:
                ok_for_now = False
            if ok_for_now:
                request.deleted = False
                trans.sa_session.add( request )
                # Undelete all the samples belonging to this request
                for s in request.samples:
                    s.deleted = False
                    trans.sa_session.add( s )
                comment = "Request marked undeleted by %s." % trans.user.email
                event = trans.model.RequestEvent( request, request.state, comment )
                trans.sa_session.add( event )
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
                message = "At least 1 sample state moved from the final sample state, so now the request's state is (%s)" % request.states.SUBMITTED
                event = trans.model.RequestEvent( request, request.states.SUBMITTED, message )
                trans.sa_session.add( event )
                trans.sa_session.flush()
            if cntrller == 'api':
                return 200, message
            return trans.response.send_redirect( web.url_for( controller='requests_common',
                                                              action='edit_samples',
                                                              cntrller=cntrller,
                                                              id=request_id,
                                                              editing_samples=True,
                                                              status=status,
                                                              message=message ) )
        final_state = False
        request_type_state = request.type.final_sample_state
        if common_state.id == request_type_state.id:
            # since all the samples are in the final state, change the request state to 'Complete'
            comment = "All samples of this request are in the final sample state (%s). " % request_type_state.name
            state = request.states.COMPLETE
            final_state = True
        else:
            comment = "All samples of this request are in the (%s) sample state. " % common_state.name
            state = request.states.SUBMITTED
        event = trans.model.RequestEvent( request, state, comment )
        trans.sa_session.add( event )
        trans.sa_session.flush()
        # See if an email notification is configured to be sent when the samples 
        # are in this state.
        retval = request.send_email_notification( trans, common_state, final_state )
        if retval:
            message = comment + retval
        else:
            message = comment
        if cntrller == 'api':
            return 200, message
        return trans.response.send_redirect( web.url_for( controller='requests_common',
                                                          action='edit_samples',
                                                          cntrller=cntrller,
                                                          id=request_id,
                                                          editing_samples=True,
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
    @web.expose
    @web.require_login( "add sample" )
    def add_sample( self, trans, cntrller, request_id, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        try:
            request = trans.sa_session.query( trans.model.Request ).get( trans.security.decode_id( request_id ) )
        except:
            return invalid_id_redirect( trans, cntrller, request_id )
        is_admin = cntrller == 'requests_admin' and trans.user_is_admin()
        # Get the widgets for rendering the request form
        request_widgets = self.__get_request_widgets( trans, request.id )
        current_samples = self.__get_sample_widgets( trans, request, request.samples, **kwd )
        if not current_samples:
            # Form field names are zero-based.
            sample_index = 0
        else:
            sample_index = len( current_samples )
        if params.get( 'add_sample_button', False ):
            # Get all libraries for which the current user has permission to add items
            libraries = request.user.accessible_libraries( trans, [ trans.app.security_agent.permitted_actions.LIBRARY_ADD ] )
            num_samples_to_add = int( params.get( 'num_sample_to_copy', 1 ) )
            # See if the user has selected a sample to copy.
            copy_sample_index = int( params.get( 'copy_sample_index', -1 ) )
            for index in range( num_samples_to_add ):
                id_index = len( current_samples ) + 1
                if copy_sample_index != -1:
                    # The user has selected a sample to copy.
                    library_id = current_samples[ copy_sample_index][ 'library_select_field' ].get_selected( return_value=True )
                    folder_id = current_samples[ copy_sample_index ][ 'folder_select_field' ].get_selected( return_value=True )
                    name = current_samples[ copy_sample_index ][ 'name' ] + '_%i' % ( len( current_samples ) + 1 )
                    field_values = [ val for val in current_samples[ copy_sample_index ][ 'field_values' ] ]
                else:
                    # The user has not selected a sample to copy, just adding a new generic sample.
                    library_id = None
                    folder_id = None
                    name = 'Sample_%i' % ( len( current_samples ) + 1 )
                    field_values = [ '' for field in request.type.sample_form.fields ]
                # Build the library_select_field and folder_select_field for the new sample being added.
                library_select_field, folder_select_field = self.__build_library_and_folder_select_fields( trans,
                                                                                                           user=request.user, 
                                                                                                           sample_index=id_index, 
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
        encoded_selected_sample_ids = self.__get_encoded_selected_sample_ids( trans, request, **kwd )
        sample_operation = params.get( 'sample_operation', 'none' )
        sample_operation_select_field = self.__build_sample_operation_select_field( trans, is_admin, request, sample_operation )
        sample_copy = self.__build_copy_sample_select_field( trans, current_samples )
        return trans.fill_template( '/requests/common/edit_samples.mako',
                                    cntrller=cntrller,
                                    request=request,
                                    encoded_selected_sample_ids=encoded_selected_sample_ids,
                                    request_widgets=request_widgets,
                                    current_samples=current_samples,
                                    sample_operation_select_field=sample_operation_select_field,
                                    sample_copy=sample_copy, 
                                    editing_samples=False,
                                    message=message,
                                    status=status )
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
        current_samples = self.__get_sample_widgets( trans, request, request.samples, **kwd )
        sample_index = int( params.get( 'sample_id', 0 ) )
        sample_name = current_samples[sample_index]['name']
        sample = request.has_sample( sample_name )
        if sample:
            trans.sa_session.delete( sample.values )
            trans.sa_session.delete( sample )
            trans.sa_session.flush()
        message = 'Sample (%s) has been deleted.' % sample_name
        return trans.response.send_redirect( web.url_for( controller='requests_common',
                                                          action='edit_samples',
                                                          cntrller=cntrller,
                                                          id=trans.security.encode_id( request.id ),
                                                          editing_samples=True,
                                                          status=status,
                                                          message=message ) )
    @web.expose
    @web.require_login( "view data transfer page" )
    def view_sample_datasets( self, trans, cntrller, **kwd ):
        # The link on the number of selected datasets will only appear if there is at least 1 selected dataset.
        # If there are 0 selected datasets, there is no link, so this method will only be reached from the requests
        # controller if there are selected datasets.
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        is_admin = cntrller == 'requests_admin' and trans.user_is_admin()
        sample_id = params.get( 'sample_id', None )
        try:
            sample = trans.sa_session.query( trans.model.Sample ).get( trans.security.decode_id( sample_id ) )
        except:
            return invalid_id_redirect( trans, cntrller, sample_id )
        # See if a library and folder have been set for this sample.
        if is_admin and not sample.library or not sample.folder:
            status = 'error'
            message = "Select a target data library and folder for the sample before selecting the datasets."
            return trans.response.send_redirect( web.url_for( controller='requests_common',
                                                              action='edit_samples',
                                                              cntrller=cntrller,
                                                              id=trans.security.encode_id( sample.request.id ),
                                                              editing_samples=True,
                                                              status=status,
                                                              message=message ) )
        folder_path = util.restore_text( params.get( 'folder_path', ''  ) )
        if not folder_path:
            if len( sample.datasets ):
                folder_path = os.path.dirname( sample.datasets[-1].file_path[:-1] )
            else:
                folder_path = util.restore_text( sample.request.type.datatx_info.get( 'data_dir', '' ) )
        if folder_path and folder_path[-1] != os.sep:
            folder_path += os.sep
        if not sample.request.type.datatx_info['host'] \
            or not sample.request.type.datatx_info[ 'username' ] \
            or not sample.request.type.datatx_info[ 'password' ]:
            status = 'error'
            message = 'The sequencer login information is incomplete. Click sequencer information to add login details.'
        transfer_status = params.get( 'transfer_status', None )
        if transfer_status in [ None, 'None' ]:
            title = 'All selected datasets for "%s"' % sample.name
            sample_datasets = sample.datasets
        elif transfer_status == trans.model.SampleDataset.transfer_status.IN_QUEUE:
            title = 'Datasets of "%s" that are in the transfer queue' % sample.name
            sample_datasets = sample.queued_dataset_files
        elif transfer_status == trans.model.SampleDataset.transfer_status.TRANSFERRING:
            title = 'Datasets of "%s" that are being transferred' % sample.name
            sample_datasets = sample.transferring_dataset_files
        elif transfer_status == trans.model.SampleDataset.transfer_status.ADD_TO_LIBRARY:
            title = 'Datasets of "%s" that are being added to the target data library' % sample.name
            sample_datasets = sample.adding_to_library_dataset_files
        elif transfer_status == trans.model.SampleDataset.transfer_status.COMPLETE:
            title = 'Datasets of "%s" that are available in the target data library' % sample.name
            sample_datasets = sample.transferred_dataset_files
        elif transfer_status == trans.model.SampleDataset.transfer_status.ERROR:
            title = 'Datasets of "%s" that resulted in a transfer error' % sample.name
            sample_datasets = sample.transfer_error_dataset_files
        return trans.fill_template( '/requests/common/view_sample_datasets.mako', 
                                    cntrller=cntrller,
                                    sample=sample,
                                    sample_datasets=sample_datasets,
                                    transfer_status=transferr_status,
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
            if str( e ) == "'unicode' object has no attribute 'file'":
                message = "Select a file"
            else:
                message = 'Error attempting to create samples from selected file: %s.' % str( e )
                message += '  Make sure the selected csv file uses the format: SampleName,DataLibrary,DataLibraryFolder,FieldValue1,FieldValue2...'
            return trans.response.send_redirect( web.url_for( controller='requests_common',
                                                              action='add_sample',
                                                              cntrller=cntrller,
                                                              request_id=trans.security.encode_id( request.id ),
                                                              add_sample_button='Add sample',
                                                              status='error',
                                                              message=message ) )
        request_widgets = self.__get_request_widgets( trans, request.id )
        sample_copy = self.__build_copy_sample_select_field( trans, current_samples )
        return trans.fill_template( '/requests/common/edit_samples.mako',
                                    cntrller=cntrller,
                                    request=request,
                                    request_widgets=request_widgets,
                                    current_samples=current_samples,
                                    sample_copy=sample_copy,
                                    editing_samples=False )
    def __save_samples( self, trans, cntrller, request, samples, **kwd ):
        # Here we handle saving all new samples added by the user as well as saving
        # changes to any subset of the request's samples.
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        editing_samples = util.string_as_bool( params.get( 'editing_samples', False ) )
        is_admin = cntrller == 'requests_admin' and trans.user_is_admin()
        sample_operation = params.get( 'sample_operation', 'none' )
        # Check for duplicate sample names within the request
        self.__validate_sample_names( trans, cntrller, request, samples, **kwd )
        if editing_samples:
            library = None
            folder = None
            def handle_error( **kwd ):
                kwd[ 'status' ] = 'error'
                return trans.response.send_redirect( web.url_for( controller='requests_common',
                                                                  action='edit_samples',
                                                                  cntrller=cntrller,
                                                                  **kwd ) )
            # Here we handle saving changes to single samples as well as saving changes to
            # selected sets of samples.  If samples are selected, the sample_operation param
            # will have a value other than 'none', and the samples param will be a list of
            # encoded sample ids.  There are currently only 2 multi-select operations;
            # 'Change state' and 'Select data library and folder'.  If sample_operation is
            # 'none, then the samples param will be a list of sample objects.
            if sample_operation == 'Change state':
                sample_state_id = params.get( 'sample_state_id', None )
                if sample_state_id in [ None, 'none' ]:
                    message = "Select a new state from the <b>Change current state</b> list before clicking the <b>Save</b> button."
                    kwd[ 'message' ] = message
                    del kwd[ 'save_samples_button' ]
                    handle_error( **kwd )
                sample_event_comment = util.restore_text( params.get( 'sample_event_comment', '' ) )
                new_state = trans.sa_session.query( trans.model.SampleState ).get( trans.security.decode_id( sample_state_id ) )
                # Send the encoded sample_ids to update_sample_state.
                # TODO: make changes necessary to just send the samples...
                encoded_selected_sample_ids = self.__get_encoded_selected_sample_ids( trans, request, **kwd )
                # Make sure all samples have a unique barcode if the state is changing
                for sample_index in range( len( samples ) ):
                    current_sample = samples[ sample_index ]
                    if current_sample is None:
                        # We have a None value because the user did not select this sample 
                        # on which to perform the action.
                        continue
                    request_sample = request.samples[ sample_index ]
                    bc_message = self.__validate_barcode( trans, request_sample, current_sample[ 'barcode' ] )
                    if bc_message:
                        #status = 'error'
                        message += bc_message
                        kwd[ 'message' ] = message
                        del kwd[ 'save_samples_button' ]
                        handle_error( **kwd )
                self.update_sample_state( trans, cntrller, encoded_selected_sample_ids, new_state, comment=sample_event_comment )
                return trans.response.send_redirect( web.url_for( controller='requests_common',
                                                                  cntrller=cntrller, 
                                                                  action='update_request_state',
                                                                  request_id=trans.security.encode_id( request.id ) ) )
            elif sample_operation == 'Select data library and folder':
                # TODO: fix the code so that the sample_operation_select_field does not use
                # sample_0_library_id as it's name.  it should use something like sample_operation_library_id
                # and sample_operation-folder_id because the name sample_0_library_id should belong to the
                # first sample since all other form field values are named like this.  The library and folder
                # are skewed to be named +1 resulting in the forced use of id_index everywhere...
                library_id = params.get( 'sample_0_library_id', 'none' )
                folder_id = params.get( 'sample_0_folder_id', 'none' )
                library, folder = self.__get_library_and_folder( trans, library_id, folder_id )
            self.__update_samples( trans, cntrller, request, samples, **kwd )
            # Samples will not have an associated SampleState until the request is submitted, at which
            # time all samples of the request will be set to the first SampleState configured for the
            # request's RequestType defined by the admin.
            if request.is_submitted:
                # See if all the samples' barcodes are in the same state, and if so send email if configured to.
                common_state = request.samples_have_common_state
                if common_state and common_state.id == request.type.states[1].id:
                    comment = "All samples of this request are in the (%s) sample state. " % common_state.name
                    event = trans.model.RequestEvent( request, request.states.SUBMITTED, comment )
                    trans.sa_session.add( event )
                    trans.sa_session.flush()
                    request.send_email_notification( trans, request.type.states[1] )
            message = 'Changes made to the samples have been saved. '
        else:
            # Saving a newly created sample.  The sample will not have an associated SampleState
            # until the request is submitted, at which time all samples of the request will be 
            # set to the first SampleState configured for the request's RequestType configured
            # by the admin ( i.e., the sample's SampleState would be set to request.type.states[0] ).
            for index in range( len( samples ) - len( request.samples ) ):
                sample_index = len( request.samples )
                current_sample = samples[ sample_index ]
                form_values = trans.model.FormValues( request.type.sample_form, current_sample[ 'field_values' ] )
                trans.sa_session.add( form_values )
                trans.sa_session.flush()                    
                s = trans.model.Sample( name=current_sample[ 'name' ],
                                        desc='', 
                                        request=request,
                                        form_values=form_values, 
                                        bar_code='',
                                        library=current_sample[ 'library' ],
                                        folder=current_sample[ 'folder' ] )
                trans.sa_session.add( s )
                trans.sa_session.flush()
        return trans.response.send_redirect( web.url_for( controller='requests_common',
                                                          action='edit_samples',
                                                          cntrller=cntrller,
                                                          id=trans.security.encode_id( request.id ),
                                                          editing_samples=editing_samples,
                                                          status=status,
                                                          message=message ) )
    def __update_samples( self, trans, cntrller, request, sample_widgets, **kwd ):
        # Determine if the values in kwd require updating the request's samples.  The list of
        # sample_widgets must have the same number of objects as request.samples, but some of
        # the objects can be None.  Those that are not None correspond to samples selected by
        # the user for performing an action on multiple samples simultaneously.
        def handle_error( **kwd ):
            kwd[ 'status' ] = 'error'
            return trans.response.send_redirect( web.url_for( controller='requests_common',
                                                              action='edit_samples',
                                                              cntrller=cntrller,
                                                              **kwd ) )
        params = util.Params( kwd )
        sample_operation = params.get( 'sample_operation', 'none' )
        if sample_operation != 'none':
            # These values will be in kwd if the user checked 1 or more checkboxes for performing this action
            # on a set of samples.
            library_id = params.get( 'sample_0_library_id', 'none' )
            folder_id = params.get( 'sample_0_folder_id', 'none' )
        for index, sample_widget in enumerate( sample_widgets ):
            if sample_widget is not None:
                # sample_widget will be None if the user checked sample check boxes and selected an action
                # to perform on multiple samples, but did not select certain samples.
                sample = request.samples[ index ]
                # Get the sample's form values to see if they have changed.
                form_values = trans.sa_session.query( trans.model.FormValues ).get( sample.values.id )
                if sample.name != sample_widget[ 'name' ] or \
                    sample.bar_code != sample_widget[ 'barcode' ] or \
                    sample.library != sample_widget[ 'library' ] or \
                    sample.folder != sample_widget[ 'folder' ] or \
                    form_values.content != sample_widget[ 'field_values' ]:
                    # Information about this sample has been changed.
                    sample.name = sample_widget[ 'name' ]
                    barcode = sample_widget[ 'barcode' ]
                    # The bar_code field requires special handling because after a request is submitted, the
                    # state of a sample cannot be changed without a bar_code associated with the sample.  Bar
                    # codes can only be added to a sample after the request is submitted.  Also, a samples will
                    # not have an associated SampleState until the request is submitted, at which time the sample
                    # is automatically associated with the first SamplesState configured by the admin for the
                    # request's RequestType.
                    if barcode:
                        bc_message = self.__validate_barcode( trans, sample, bar_code )
                        if bc_message:
                            kwd[ 'message' ] = bc_message
                            del kwd[ 'save_samples_button' ]
                            handle_error( **kwd )
                        if not sample.bar_code:
                            # If the sample's associated SampleState is still the initial state
                            # configured by the admin for the request's RequestType, this must be
                            # the first time a bar code was added to the sample, so change it's state
                            # to the next associated SampleState.
                            if sample.state.id == request.type.states[0].id:
                                event = trans.app.model.SampleEvent(sample, 
                                                                    request.type.states[1], 
                                                                    'Bar code associated with the sample' )
                                trans.sa_session.add( event )
                                trans.sa_session.flush()
                    sample.bar_code = barcode
                    sample.library = sample_widget[ 'library' ]
                    sample.folder = sample_widget[ 'folder' ]
                    form_values.content = sample_widget[ 'field_values' ]
                    trans.sa_session.add_all( ( sample, form_values ) )
                    trans.sa_session.flush()           
    def __get_library_and_folder( self, trans, library_id, folder_id ):
        try:
            library = trans.sa_session.query( trans.model.Library ).get( trans.security.decode_id( library_id ) )
        except:
            library = None
        if library and folder_id == 'none':
            folder = library.root_folder
        elif library and folder_id != 'none':
            try:
                folder = trans.sa_session.query( trans.model.LibraryFolder ).get( trans.security.decode_id( folder_id ) )
            except:
                if library:
                    folder = library.root_folder
                else:
                    folder = None
        else:
            folder = None
        return library, folder
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
    def __get_sample_widgets( self, trans, request, samples, **kwd ):
        """
        Returns a list of dictionaries, each representing the widgets that define a sample on a form.
        The widgets are populated from kwd based on the set of samples received.  The set of samples
        corresponds to a request.samples list, but if the user checked specific check boxes on the form,
        those samples that were not checked will have None objects in the list of samples.  In this case,
        the corresponding sample_widget is populated from the db rather than kwd.
        """
        params = util.Params( kwd )
        sample_operation = params.get( 'sample_operation', 'none' )
        # This method is called when the user is adding new samples as well as
        # editing existing samples, so we use the editing_samples flag to keep
        # track of what's occurring.
        editing_samples = util.string_as_bool( params.get( 'editing_samples', False ) )
        sample_widgets = []
        if sample_operation != 'none':
            # The sample_operatin param has a value other than 'none', and a specified
            # set of samples was received.
            library_id = util.restore_text( params.get( 'sample_0_library_id', 'none' ) )
            folder_id = util.restore_text( params.get( 'sample_0_folder_id', 'none' ) )
        # Build the list of widgets which will be used to render each sample row on the request page
        if not request:
            return sample_widgets
        # Get the list of libraries for which the current user has permission to add items.
        libraries = request.user.accessible_libraries( trans, [ trans.app.security_agent.permitted_actions.LIBRARY_ADD ] )
        # Build the list if sample widgets, populating the values from kwd.
        for index, sample in enumerate( samples ):
            id_index = index + 1
            if sample is None:
                # Id sample is None, then we'll use the sample from the request object since it will
                # not have updated =values from kwd.
                sample = request.samples[ index ]
                name = sample.name
                bar_code = sample.bar_code
                library = sample.library
                folder = sample.folder
                field_values = sample.values.content
            else:
                # Update the sample attributes from kwd
                name = util.restore_text( params.get( 'sample_%i_name' % index, sample.name ) )
                bar_code = util.restore_text( params.get( 'sample_%i_barcode' % index, sample.bar_code ) )
                library_id = util.restore_text( params.get( 'sample_%i_library_id' % id_index, '' ) )
                if not library_id and sample.library:
                    library_id = trans.security.encode_id( sample.library.id )
                folder_id = util.restore_text( params.get( 'sample_%i_folder_id' % id_index, '' ) )
                if not folder_id and sample.folder:
                    folder_id = trans.security.encode_id( sample.folder.id )
                library, folder = self.__get_library_and_folder( trans, library_id, folder_id )
                field_values = []
                for field_index in range( len( request.type.sample_form.fields ) ):
                    field_value = util.restore_text( params.get( 'sample_%i_field_%i' % ( index, field_index ), sample.values.content[ field_index ] ) )
                    field_values.append( field_value )
            library_select_field, folder_select_field = self.__build_library_and_folder_select_fields( trans=trans,
                                                                                                       user=request.user,
                                                                                                       sample_index=id_index,
                                                                                                       libraries=libraries,
                                                                                                       sample=sample,
                                                                                                       library_id=library_id,
                                                                                                       folder_id=folder_id,
                                                                                                       **kwd )
            sample_widgets.append( dict( name=name,
                                         barcode=bar_code,
                                         library=library,
                                         folder=folder,
                                         field_values=field_values,
                                         library_select_field=library_select_field,
                                         folder_select_field=folder_select_field ) )
        # There may be additional new samples on the form that have not yet been associated with the request.
        # TODO: factor this code so it is not duplicating what's above.
        index = len( samples )
        while True:
            name = util.restore_text( params.get( 'sample_%i_name' % index, '' ) )
            if not name:
                break
            id_index = index + 1
            bar_code = util.restore_text( params.get( 'sample_%i_barcode' % index, '' ) )
            library_id = util.restore_text( params.get( 'sample_%i_library_id' % id_index, '' ) )
            folder_id = util.restore_text( params.get( 'sample_%i_folder_id' % id_index, '' ) )
            library, folder = self.__get_library_and_folder( trans, library_id, folder_id )
            field_values = []
            for field_index in range( len( request.type.sample_form.fields ) ):
                field_values.append( util.restore_text( params.get( 'sample_%i_field_%i' % ( index, field_index ), '' ) ) )
            library_select_field, folder_select_field = self.__build_library_and_folder_select_fields( trans=trans,
                                                                                                       user=request.user,
                                                                                                       sample_index=id_index,
                                                                                                       libraries=libraries,
                                                                                                       sample=None,
                                                                                                       library_id=library_id,
                                                                                                       folder_id=folder_id,
                                                                                                       **kwd )
            sample_widgets.append( dict( name=name,
                                         barcode=bar_code,
                                         library=library,
                                         folder=folder,
                                         field_values=field_values,
                                         library_select_field=library_select_field,
                                         folder_select_field=folder_select_field ) )
            index += 1
        return sample_widgets   
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
        params = util.Params( kwd )
        library_select_field_name= "sample_%i_library_id" % sample_index
        folder_select_field_name = "sample_%i_folder_id" % sample_index
        if not library_id:
            library_id = params.get( library_select_field_name, None )
        if not folder_id:
            folder_id = params.get( folder_select_field_name, None )
        selected_library = None
        selected_hidden_folder_ids = []
        showable_folders = []
        if library_id not in [ None, 'none' ]:
            # If we have a selected library, get the list of it's folders that are not accessible to the current user
            for library, hidden_folder_ids in libraries.items():
                encoded_id = trans.security.encode_id( library.id )
                if encoded_id == str( library_id ):
                    selected_library = library
                    selected_hidden_folder_ids = hidden_folder_ids.split( ',' )
                    break
        elif sample and sample.library and library_id == 'none':
            # The user previously selected a library but is now resetting the selection to 'none'
            selected_library = None
        elif sample and sample.library:
            library_id = trans.security.encode_id( sample.library.id )
            selected_library = sample.library
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
            if folder_id:
                selected_folder_id = folder_id
            elif sample and sample.folder:
                selected_folder_id = trans.security.encode_id( sample.folder.id )
            else:
                selected_folder_id = trans.security.encode_id( selected_library.root_folder.id )
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
    def __validate_sample_names( self, trans, cntrller, request, current_samples, **kwd ):
        # Check for duplicate sample names for all samples of the request.
        editing_samples = util.string_as_bool( kwd.get( 'editing_samples', False ) )
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
                message = "You tried to add %i samples with the name (%s).  Samples belonging to a request must have unique names." % ( count, sample_name )
                break
        if message:
            del kwd[ 'save_samples_button' ]
            kwd[ 'message' ] = message
            kwd[ 'status' ] = 'error'
            return trans.response.send_redirect( web.url_for( controller='requests_common',
                                                              action='edit_samples',
                                                              cntrller=cntrller,
                                                              **kwd ) )
    def __validate_barcode( self, trans, sample, barcode ):
        """
        Makes sure that the barcode about to be assigned to a sample is globally unique.
        That is, barcodes must be unique across requests in Galaxy sample tracking. 
        """
        message = ''
        unique = True
        for index in range( len( sample.request.samples ) ):
            # Check for empty bar code
            if not barcode.strip():
                if sample.state.id == sample.request.type.states[0].id:
                    # The user has not yet filled in the barcode value, but the sample is
                    # 'new', so all is well.
                    break
                else:
                    message = "Fill in the barcode for sample (%s) before changing it's state." % sample.name
                    break
            # TODO: Add a unique constraint to sample.bar_code table column
            # Make sure bar code is unique
            for sample_with_barcode in trans.sa_session.query( trans.model.Sample ) \
                                                       .filter( trans.model.Sample.table.c.bar_code == barcode ):
                if sample_with_barcode and sample_with_barcode.id != sample.id:
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
    # ===== Other miscellaneous utility methods =====
    def __get_encoded_selected_sample_ids( self, trans, request, **kwd ):
        encoded_selected_sample_ids = []
        for sample in request.samples:
            if CheckboxField.is_checked( kwd.get( 'select_sample_%i' % sample.id, '' ) ):
                encoded_selected_sample_ids.append( trans.security.encode_id( sample.id ) )
        return encoded_selected_sample_ids

# ===== Miscellaneous utility methods outside of the RequestsCommon class =====
def invalid_id_redirect( trans, cntrller, obj_id, action='browse_requests' ):
    status = 'error'
    message = "Invalid request id (%s)" % str( obj_id )
    return trans.response.send_redirect( web.url_for( controller=cntrller,
                                                      action=action,
                                                      status=status,
                                                      message=message ) )
