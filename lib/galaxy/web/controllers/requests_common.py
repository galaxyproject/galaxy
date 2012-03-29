from galaxy.web.base.controller import *
from galaxy.web.framework.helpers import time_ago, iff, grids
from galaxy.model.orm import *
from galaxy import model, util
from galaxy.util.odict import odict
from galaxy.web.form_builder import *
from galaxy.security.validate_user_input import validate_email
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
        TypeColumn( "Type",
                    link=( lambda item: iff( item.deleted, None, dict( operation="view_type", id=item.type.id ) ) ) ),
        grids.GridColumn( "Last Updated", key="update_time", format=time_ago ),
        grids.DeletedColumn( "Deleted", 
                             key="deleted", 
                             visible=False, 
                             filterable="advanced" ),
        StateColumn( "State", 
                     key='state',
                     filterable="advanced",
                     link=( lambda item: iff( item.deleted, None, dict( operation="view_request_history", id=item.id ) ) )
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

class RequestsCommon( BaseUIController, UsesFormDefinitions ):
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
                                   "html_state": unicode( trans.fill_template( "requests/common/sample_state.mako",
                                                                               sample=sample),
                                                                               'utf-8' ) }
        return rval
    @web.json
    def sample_datasets_updates( self, trans, ids=None, datasets=None ):
        # Avoid caching
        trans.response.headers['Pragma'] = 'no-cache'
        trans.response.headers['Expires'] = '0'
        # Create new HTML for any that have changed
        rval = {}
        if ids is not None and datasets is not None:
            ids = map( int, ids.split( "," ) )
            number_of_datasets_list = map(int, datasets.split( "," ) )
            for id, number_of_datasets in zip( ids, number_of_datasets_list ):
                sample = trans.sa_session.query( self.app.model.Sample ).get( id )
                if len(sample.datasets) != number_of_datasets:
                    rval[ id ] = { "datasets": len( sample.datasets ),
                                   "html_datasets": unicode( trans.fill_template( "requests/common/sample_datasets.mako",
                                                                                  sample=sample),
                                                                                  'utf-8' ) }
        return rval
    @web.json
    def dataset_transfer_status_updates( self, trans, ids=None, transfer_status_list=None ):
        # Avoid caching
        trans.response.headers['Pragma'] = 'no-cache'
        trans.response.headers['Expires'] = '0'
        # Create new HTML for any that have changed
        rval = {}
        if ids is not None and transfer_status_list is not None:
            ids = ids.split( "," )
            transfer_status_list = transfer_status_list.split( "," )
            for id, transfer_status in zip( ids, transfer_status_list ):
                sample_dataset = trans.sa_session.query( self.app.model.SampleDataset ).get( trans.security.decode_id( id ) )
                if sample_dataset.status != transfer_status:
                    rval[ id ] = { "status": sample_dataset.status,
                                   "html_status": unicode( trans.fill_template( "requests/common/sample_dataset_transfer_status.mako",
                                                                                sample_dataset=sample_dataset),
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
            # when creating a request from the user perspective, check if the 
            # user has access permission to this request_type 
            elif cntrller == 'requests' and not trans.app.security_agent.can_access_request_type( user.all_roles(), request_type ):
                message = '%s does not have access permission to the "%s" request type.' % ( user.email, request_type.name )
                status = 'error'
            elif not name:
                message = 'Enter the name of the request.'
                status = 'error'
            else:
                request = self.__save_request( trans, cntrller, **kwd )
                message = 'The sequencing request has been created.'
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
                if not user_id_encoded and user:
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
        # Build a list of sample widgets (based on the attributes of each sample) for display.
        displayable_sample_widgets = self.__get_sample_widgets( trans, request, request.samples, **kwd )
        request_widgets = self.__get_request_widgets( trans, request.id )
        return trans.fill_template( '/requests/common/view_request.mako',
                                    cntrller=cntrller, 
                                    request=request,
                                    request_widgets=request_widgets,
                                    displayable_sample_widgets=displayable_sample_widgets,
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
        values = self.get_form_values( trans, user, request_type.request_form, **kwd )
        if request is None:
            form_values = trans.model.FormValues( request_type.request_form, values )
            trans.sa_session.add( form_values )
            # We're creating a new request
            request = trans.model.Request( name, desc, request_type, user, form_values, notification )
            trans.sa_session.add( request )
            trans.sa_session.flush()
            trans.sa_session.refresh( request )
            # Create an event with state 'New' for this new request
            comment = "Sequencing request created by %s" % trans.user.email
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
            request.values.content = values
            trans.sa_session.add( request )
            trans.sa_session.add( request.values )
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
        comment = "Sequencing request submitted by %s" % trans.user.email
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
            event_comment = 'Sequencing request submitted and sample state set to %s.' % request.type.states[0].name
            event = trans.model.SampleEvent( sample,
                                             initial_sample_state_after_request_submitted,
                                             event_comment )
            trans.sa_session.add( event )
        trans.sa_session.add( request )
        trans.sa_session.flush()
        request.send_email_notification( trans, initial_sample_state_after_request_submitted )
        message = 'The sequencing request has been submitted.'
        # show the request page after submitting the request 
        return trans.response.send_redirect( web.url_for( controller='requests_common',
                                                          action='view_request',
                                                          cntrller=cntrller,
                                                          id=request_id,
                                                          status=status,
                                                          message=message ) )
    @web.expose
    @web.require_login( "edit samples" )
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
        if params.get( 'cancel_changes_button', False ):
            return trans.response.send_redirect( web.url_for( controller='requests_common',
                                                                          action='edit_samples',
                                                                          cntrller=cntrller,
                                                                          id=request_id ) )
        libraries = trans.app.security_agent.get_accessible_libraries( trans, request.user )
        # Build a list of sample widgets (based on the attributes of each sample) for display.
        displayable_sample_widgets = self.__get_sample_widgets( trans, request, request.samples, **kwd )
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
        if params.get( 'save_samples_button', False ):
            if encoded_selected_sample_ids:
                # We need the list of displayable_sample_widgets to include the same number
                # of objects that that request.samples has so that we can enumerate over each
                # list without problems.  We have to be careful here since the user may have
                # used the multi-select check boxes when editing sample widgets, but didn't
                # select all of them.  We'll first get the set of samples corresponding to the
                # checked sample ids.
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
                # The __save_samples method requires sample_widgets, not sample objects, so we'll get what we
                # need by calling __get_sample_widgets().  However, we need to take care here because __get_sample_widgets()
                # is used to populate the sample widget dicts from kwd, and the method assumes that a None object in the 
                # received list of samples should be populated from the db.  Since we're just re-using the method here to
                # change our list of samples into a list of sample widgets, we'll need to make sure to keep track of our
                # None objects.
                sample_widgets = [ obj for obj in samples ]
                sample_widgets = self.__get_sample_widgets( trans, request, sample_widgets, **kwd )
                # Replace each sample widget dict with a None object if necessary
                for index, obj in enumerate( samples ):
                    if obj is None:
                        sample_widgets[ index ] = None
            else:
                sample_widgets = displayable_sample_widgets
            return self.__save_samples( trans, cntrller, request, sample_widgets, saving_new_samples=False, **kwd )
        request_widgets = self.__get_request_widgets( trans, request.id )
        sample_copy_select_field = self.__build_copy_sample_select_field( trans, displayable_sample_widgets )
        libraries_select_field, folders_select_field = self.__build_library_and_folder_select_fields( trans,
                                                                                                      request.user,
                                                                                                      'sample_operation',
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
                                    displayable_sample_widgets=displayable_sample_widgets,
                                    sample_copy_select_field=sample_copy_select_field, 
                                    libraries=libraries,
                                    sample_operation_select_field=sample_operation_select_field,
                                    libraries_select_field=libraries_select_field,
                                    folders_select_field=folders_select_field,
                                    sample_state_id_select_field=sample_state_id_select_field,
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
                    return invalid_id_redirect( trans, cntrller, sample_id, 'sample' )
            if comment is None:
                comment = 'Sample state set to %s' % str( new_state )
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
                    comment = "Sequencing request marked deleted by %s." % trans.user.email
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
                comment = "Sequencing request marked undeleted by %s." % trans.user.email
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
    @web.require_login( "sequencing request history" )
    def view_request_history( self, trans, cntrller, **kwd ):
        params = util.Params( kwd )
        request_id = params.get( 'id', None )
        try:
            request = trans.sa_session.query( trans.model.Request ).get( trans.security.decode_id( request_id ) )
        except:
            return invalid_id_redirect( trans, cntrller, request_id )
        return trans.fill_template( '/requests/common/view_request_history.mako', 
                                    cntrller=cntrller,
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
                err_msg += validate_email( trans, email_address, check_dup=False )
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
        else:
            final_state = False
            request_type_state = request.type.final_sample_state
            if common_state.id == request_type_state.id:
                # since all the samples are in the final state, change the request state to 'Complete'
                comment = "All samples of this sequencing request are in the final sample state (%s). " % request_type_state.name
                state = request.states.COMPLETE
                final_state = True
            else:
                comment = "All samples of this sequencing request are in the (%s) sample state. " % common_state.name
                state = request.states.SUBMITTED
            event = trans.model.RequestEvent( request, state, comment )
            trans.sa_session.add( event )
            trans.sa_session.flush()
            # See if an email notification is configured to be sent when the samples are in this state.
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
            if search_type == 'bar_code':
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
            elif search_type == 'form value':
                samples = []
                if search_string.find('=') != -1:
                    field_label, field_value = search_string.split('=')
                    all_samples = trans.sa_session.query( trans.model.Sample ) \
                                              .filter( trans.model.Sample.table.c.deleted==False ) \
                                              .order_by( trans.model.Sample.table.c.create_time.desc() )
                    for sample in all_samples:
                        # find the field in the sample form with the given label
                        for field in sample.request.type.sample_form.fields:
                            if field_label == field['label']:
                                # check if the value is equal to the value in the search string
                                if sample.values.content[ field['name'] ] == field_value:
                                    samples.append( sample )
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
        types = [ 'sample name', 'bar_code', 'dataset', 'form value' ]
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
    def view_sample_history( self, trans, cntrller, **kwd ):
        params = util.Params( kwd )
        status = params.get( 'status', 'done' )
        message = util.restore_text( params.get( 'message', '' ) )
        sample_id = params.get( 'sample_id', None )
        try:
            sample = trans.sa_session.query( trans.model.Sample ).get( trans.security.decode_id( sample_id ) )
        except:
            return invalid_id_redirect( trans, cntrller, sample_id, 'sample' )
        return trans.fill_template( '/requests/common/view_sample_history.mako', 
                                    cntrller=cntrller,
                                    sample=sample )
    @web.expose
    @web.require_login( "add samples" )
    def add_samples( self, trans, cntrller, **kwd ):
        params = util.Params( kwd )
        is_admin = cntrller == 'requests_admin' and trans.user_is_admin()
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        request_id = params.get( 'id', None )
        try:
            request = trans.sa_session.query( trans.model.Request ).get( trans.security.decode_id( request_id ) )
        except:
            return invalid_id_redirect( trans, cntrller, request_id )
        libraries = trans.app.security_agent.get_accessible_libraries( trans, request.user )
        # Build a list of sample widgets (based on the attributes of each sample) for display.
        displayable_sample_widgets = self.__get_sample_widgets( trans, request, request.samples, **kwd )
        if params.get( 'import_samples_button', False ):
            # Import sample field values from a csv file
            # TODO: should this be a mapper?
            workflows = [ w.latest_workflow for w in trans.user.stored_workflows if not w.deleted ]
            return self.__import_samples( trans, cntrller, request, displayable_sample_widgets, libraries, workflows, **kwd )
        elif params.get( 'add_sample_button', False ):
            return self.add_sample( trans, cntrller, request_id, **kwd )
        elif params.get( 'save_samples_button', False ):
            return self.__save_samples( trans, cntrller, request, displayable_sample_widgets, saving_new_samples=True, **kwd )
        request_widgets = self.__get_request_widgets( trans, request.id )
        sample_copy_select_field = self.__build_copy_sample_select_field( trans, displayable_sample_widgets )
        libraries_select_field, folders_select_field = self.__build_library_and_folder_select_fields( trans,
                                                                                                      request.user,
                                                                                                      'sample_operation',
                                                                                                      libraries,
                                                                                                      None,
                                                                                                      **kwd )
        return trans.fill_template( '/requests/common/add_samples.mako',
                                    cntrller=cntrller, 
                                    request=request,
                                    request_widgets=request_widgets,
                                    displayable_sample_widgets=displayable_sample_widgets,
                                    sample_copy_select_field=sample_copy_select_field, 
                                    libraries=libraries,
                                    libraries_select_field=libraries_select_field,
                                    folders_select_field=folders_select_field,
                                    status=status,
                                    message=message )
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
        displayable_sample_widgets = self.__get_sample_widgets( trans, request, request.samples, **kwd )
        if not displayable_sample_widgets:
            # Form field names are zero-based.
            sample_index = 0
        else:
            sample_index = len( displayable_sample_widgets )
        if params.get( 'add_sample_button', False ):
            libraries = trans.app.security_agent.get_accessible_libraries( trans, request.user )
            num_samples_to_add = int( params.get( 'num_sample_to_copy', 1 ) )
            # See if the user has selected a sample to copy.
            copy_sample_index = int( params.get( 'copy_sample_index', -1 ) )
            for index in range( num_samples_to_add ):
                field_values = {}
                if copy_sample_index != -1:
                    # The user has selected a sample to copy.
                    library_id = displayable_sample_widgets[ copy_sample_index][ 'library_select_field' ].get_selected( return_value=True )
                    folder_id = displayable_sample_widgets[ copy_sample_index ][ 'folder_select_field' ].get_selected( return_value=True )
                    name = displayable_sample_widgets[ copy_sample_index ][ 'name' ] + '_%i' % ( len( displayable_sample_widgets ) + 1 )
                    history_id = displayable_sample_widgets[ copy_sample_index ][ 'history_select_field' ].get_selected( return_value=True )
                    workflow_id = displayable_sample_widgets[ copy_sample_index ][ 'workflow_select_field' ][0].get_selected( return_value=True )
                    # DBTODO Do something nicer with the workflow fieldset.  Remove [0] indexing and copy mappings as well.
                    for field_name in displayable_sample_widgets[ copy_sample_index ][ 'field_values' ]:
                        field_values[ field_name ] = ''
                else:
                    # The user has not selected a sample to copy, just adding a new generic sample.
                    library_id = None
                    folder_id = None
                    history_id = None
                    workflow_id = None
                    name = 'Sample_%i' % ( len( displayable_sample_widgets ) + 1 )
                    for field in request.type.sample_form.fields:
                        field_values[ field[ 'name' ] ] = ''
                # Build the library_select_field and folder_select_field for the new sample being added.
                library_select_field, folder_select_field = self.__build_library_and_folder_select_fields( trans,
                                                                                                           user=request.user, 
                                                                                                           sample_index=len( displayable_sample_widgets ), 
                                                                                                           libraries=libraries,
                                                                                                           sample=None, 
                                                                                                           library_id=library_id,
                                                                                                           folder_id=folder_id,
                                                                                                           **kwd )
                history_select_field = self.__build_history_select_field( trans=trans,
                                                                          user=request.user,
                                                                          sample_index=len( displayable_sample_widgets ),
                                                                          history_id=history_id,
                                                                          **kwd )
                workflow_select_field = self.__build_workflow_select_field( trans=trans,
                                                                            user=request.user,
                                                                            request=request,
                                                                            sample_index=len( displayable_sample_widgets ),
                                                                            workflow_id=workflow_id,
                                                                            history_id=history_id,
                                                                            **kwd )
                # Append the new sample to the current list of samples for the request
                displayable_sample_widgets.append( dict( id=None,
                                                         name=name,
                                                         bar_code='',
                                                         library=None,
                                                         library_id=library_id,
                                                         history=None,
                                                         workflow=None,
                                                         history_select_field=history_select_field,
                                                         workflow_select_field=workflow_select_field,
                                                         folder=None,
                                                         folder_id=folder_id,
                                                         field_values=field_values,
                                                         library_select_field=library_select_field,
                                                         folder_select_field=folder_select_field ) )
        sample_copy_select_field = self.__build_copy_sample_select_field( trans, displayable_sample_widgets )
        return trans.fill_template( '/requests/common/add_samples.mako',
                                    cntrller=cntrller,
                                    request=request,
                                    request_widgets=request_widgets,
                                    displayable_sample_widgets=displayable_sample_widgets,
                                    sample_copy_select_field=sample_copy_select_field, 
                                    message=message,
                                    status=status )
    @web.expose
    @web.require_login( "view request" )
    def view_sample( self, trans, cntrller, **kwd ):
        params = util.Params( kwd )
        is_admin = cntrller == 'requests_admin' and trans.user_is_admin()
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        sample_id = params.get( 'id', None )
        try:
            sample = trans.sa_session.query( trans.model.Sample ).get( trans.security.decode_id( sample_id ) )
        except:
            return invalid_id_redirect( trans, cntrller, sample_id, 'sample' )
        # See if we have any associated templates
        widgets = sample.get_template_widgets( trans )
        widget_fields_have_contents = self.widget_fields_have_contents( widgets )
        if is_admin:
            external_services = sample.populate_external_services( trans = trans )
        else:
            external_services = None
        return trans.fill_template( '/requests/common/view_sample.mako',
                                    cntrller=cntrller, 
                                    sample=sample,
                                    widgets=widgets,
                                    widget_fields_have_contents=widget_fields_have_contents,
                                    status=status,
                                    message=message,
                                    external_services=external_services )
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
        displayable_sample_widgets = self.__get_sample_widgets( trans, request, request.samples, **kwd )
        sample_index = int( params.get( 'sample_id', 0 ) )
        sample_name = displayable_sample_widgets[sample_index]['name']
        sample = request.get_sample( sample_name )
        if sample:
            trans.sa_session.delete( sample.values )
            trans.sa_session.delete( sample )
            trans.sa_session.flush()
        message = 'Sample (%s) has been deleted.' % sample_name
        return trans.response.send_redirect( web.url_for( controller='requests_common',
                                                          action='edit_samples',
                                                          cntrller=cntrller,
                                                          id=trans.security.encode_id( request.id ),
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
            return invalid_id_redirect( trans, cntrller, sample_id, 'sample' )
        external_service_id = params.get( 'external_service_id', None )
        external_service = trans.sa_session.query( trans.model.ExternalService ).get( trans.security.decode_id( external_service_id ) )
        # See if a library and folder have been set for this sample.
        if is_admin and not sample.library or not sample.folder:
            status = 'error'
            message = "Select a target data library and folder for the sample before selecting the datasets."
            return trans.response.send_redirect( web.url_for( controller='requests_common',
                                                              action='edit_samples',
                                                              cntrller=cntrller,
                                                              id=trans.security.encode_id( sample.request.id ),
                                                              status=status,
                                                              message=message ) )
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
                                    title=title,
                                    external_service=external_service,
                                    sample=sample,
                                    sample_datasets=sample_datasets,
                                    transfer_status=transfer_status,
                                    message=message,
                                    status=status )
    def __import_samples( self, trans, cntrller, request, displayable_sample_widgets, libraries, workflows, **kwd ):
        """
        Reads the samples csv file and imports all the samples.  The csv file must be in the following format.  The [:FieldValue]
        is optional, the form field will contain the value after the ':' if included.
                        SampleName,DataLibraryName,DataLibraryFolderName,HistoryName,WorkflowName,Field1Name:Field1Value,Field2Name:Field2Value...
        """
        params = util.Params( kwd )
        current_user_roles = trans.get_current_user_roles()
        is_admin = trans.user_is_admin() and cntrller == 'requests_admin'
        file_obj = params.get( 'file_data', '' )
        try:
            reader = csv.reader( file_obj.file )
            for row in reader:
                library_id = None
                library = None
                folder_id = None
                folder = None
                history_id = None
                history = None
                workflow_id = None
                workflow = None
                # Get the library
                library = trans.sa_session.query( trans.model.Library ) \
                                          .filter( and_( trans.model.Library.table.c.name==row[1],
                                                         trans.model.Library.table.c.deleted==False ) ) \
                                          .first()
                if library:
                    # Get the folder
                    for folder in trans.sa_session.query( trans.model.LibraryFolder ) \
                                                  .filter( and_( trans.model.LibraryFolder.table.c.name==row[2],
                                                                 trans.model.LibraryFolder.table.c.deleted==False ) ):
                        if folder.parent_library == library:
                            break
                    if folder:
                        library_id = trans.security.encode_id( library.id )
                        folder_id = trans.security.encode_id( folder.id )
                library_select_field, folder_select_field = self.__build_library_and_folder_select_fields( trans,
                                                                                                           request.user,
                                                                                                           len( displayable_sample_widgets ),
                                                                                                           libraries,
                                                                                                           None,
                                                                                                           library_id,
                                                                                                           folder_id,
                                                                                                           **kwd )
                # Get the history
                history = trans.sa_session.query( trans.model.History ) \
                                          .filter( and_( trans.model.History.table.c.name==row[3],
                                                         trans.model.History.table.c.deleted==False,
                                                         trans.model.History.user_id == trans.user.id ) ) \
                                          .first()
                if history:
                    history_id = trans.security.encode_id( history.id )
                else:
                    history_id = 'none'
                history_select_field = self.__build_history_select_field( trans=trans,
                                                                          user=request.user,
                                                                          sample_index=len( displayable_sample_widgets ),
                                                                          history_id=history_id )
                # Get the workflow
                workflow = trans.sa_session.query( trans.model.StoredWorkflow ) \
                                           .filter( and_( trans.model.StoredWorkflow.table.c.name==row[4],
                                                          trans.model.StoredWorkflow.table.c.deleted==False,
                                                          trans.model.StoredWorkflow.user_id == trans.user.id ) ) \
                                           .first()
                if workflow:
                    workflow_id = trans.security.encode_id( workflow.id )
                else:
                    workflow_id = 'none'
                workflow_select_field = self.__build_workflow_select_field( trans=trans,
                                                                            user=request.user,
                                                                            request=request,
                                                                            sample_index=len( displayable_sample_widgets ),
                                                                            workflow_id=workflow_id,
                                                                            history_id=history_id )
                field_values = {}
                field_names = row[5:]
                for field_name in field_names:
                    if field_name.find( ':' ) >= 0:
                        field_list = field_name.split( ':' )
                        field_name = field_list[0]
                        field_value = field_list[1]
                    else:
                        field_value = ''
                    field_values[ field_name ] = field_value
                displayable_sample_widgets.append( dict( id=None,
                                                         name=row[0],
                                                         bar_code='',
                                                         library=library,
                                                         library_id=library_id,
                                                         library_select_field=library_select_field,
                                                         folder=folder,
                                                         folder_id=folder_id,
                                                         folder_select_field=folder_select_field,
                                                         history=history,
                                                         history_id=history_id,
                                                         history_select_field=history_select_field,
                                                         workflow=workflow,
                                                         workflow_id=workflow_id,
                                                         workflow_select_field=workflow_select_field,
                                                         field_values=field_values ) )
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
        sample_copy_select_field = self.__build_copy_sample_select_field( trans, displayable_sample_widgets )
        return trans.fill_template( '/requests/common/add_samples.mako',
                                    cntrller=cntrller,
                                    request=request,
                                    request_widgets=request_widgets,
                                    displayable_sample_widgets=displayable_sample_widgets,
                                    sample_copy_select_field=sample_copy_select_field )
    def __save_samples( self, trans, cntrller, request, sample_widgets, saving_new_samples=False, **kwd ):
        # Here we handle saving all new samples added by the user as well as saving
        # changes to any subset of the request's samples.  A sample will not have an
        # associated SampleState until the request is submitted, at which time the
        # sample is automatically associated with the first SampleState configured by
        # the admin for the request's RequestType.
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        is_admin = cntrller == 'requests_admin' and trans.user_is_admin()
        sample_operation = params.get( 'sample_operation', 'none' )
        if saving_new_samples:
            redirect_action = 'add_samples'
        else:
            redirect_action = 'edit_samples'
        # Check for duplicate sample names within the request
        self.__validate_sample_names( trans, cntrller, request, sample_widgets, **kwd )
        print "SAVING SAMPLES!"
        print "saving_new_samples is %s" % saving_new_samples
        if not saving_new_samples:
            library = None
            folder = None
            def handle_error( **kwd ):
                kwd[ 'status' ] = 'error'
                return trans.response.send_redirect( web.url_for( controller='requests_common',
                                                                  action=redirect_action,
                                                                  cntrller=cntrller,
                                                                  **kwd ) )
            # Here we handle saving changes to single samples as well as saving changes to
            # selected sets of samples.  If samples are selected, the sample_operation param
            # will have a value other than 'none', and the samples param will be a list of
            # encoded sample ids.  There are currently only 2 multi-select operations;
            # model.Sample.bulk_operations.CHANGE_STATE and model.sample.bulk_operations.SELECT_LIBRARY.
            # If sample_operation is 'none, then the samples param will be a list of sample objects.
            if sample_operation == trans.model.Sample.bulk_operations.CHANGE_STATE:
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
                # Make sure all samples have a unique bar_code if the state is changing
                for sample_index in range( len( sample_widgets ) ):
                    current_sample = sample_widgets[ sample_index ]
                    if current_sample is None:
                        # We have a None value because the user did not select this sample 
                        # on which to perform the action.
                        continue
                    request_sample = request.samples[ sample_index ]
                    bar_code = current_sample[ 'bar_code' ]
                    if bar_code:
                        # If the sample has a new bar_code, make sure it is unique.
                        bc_message = self.__validate_bar_code( trans, request_sample, bar_code )
                        if bc_message:
                            message += bc_message
                            kwd[ 'message' ] = message
                            del kwd[ 'save_samples_button' ]
                            handle_error( **kwd )
                self.update_sample_state( trans, cntrller, encoded_selected_sample_ids, new_state, comment=sample_event_comment )
                return trans.response.send_redirect( web.url_for( controller='requests_common',
                                                                  cntrller=cntrller,
                                                                  action='update_request_state',
                                                                  request_id=trans.security.encode_id( request.id ) ) )
            elif sample_operation == trans.model.Sample.bulk_operations.SELECT_LIBRARY:
                library_id = params.get( 'sample_operation_library_id', 'none' )
                folder_id = params.get( 'sample_operation_folder_id', 'none' )
                library, folder = self.__get_library_and_folder( trans, library_id, folder_id )
                for sample_index in range( len( sample_widgets ) ):
                    current_sample = sample_widgets[ sample_index ]
                    if current_sample is None:
                        # We have a None value because the user did not select this sample
                        # on which to perform the action.
                        continue
                    current_sample[ 'library' ] = library
                    current_sample[ 'folder' ] = folder
            self.__update_samples( trans, cntrller, request, sample_widgets, **kwd )
            message = 'Changes made to the samples have been saved. '
        else:
            # Saving a newly created sample.  The sample will not have an associated SampleState
            # until the request is submitted, at which time all samples of the request will be
            # set to the first SampleState configured for the request's RequestType configured
            # by the admin ( i.e., the sample's SampleState would be set to request.type.states[0] ).
            new_samples = []
            for index in range( len( sample_widgets ) - len( request.samples ) ):
                sample_index = len( request.samples )
                sample_widget = sample_widgets[ sample_index ]
                form_values = trans.model.FormValues( request.type.sample_form, sample_widget[ 'field_values' ] )
                trans.sa_session.add( form_values )
                trans.sa_session.flush()
                if request.is_submitted:
                    bar_code = sample_widget[ 'bar_code' ]
                else:
                    bar_code = ''
                sample = trans.model.Sample( name=sample_widget[ 'name' ],
                                             desc='',
                                             request=request,
                                             form_values=form_values,
                                             bar_code=bar_code,
                                             library=sample_widget[ 'library' ],
                                             folder=sample_widget[ 'folder' ],
                                             history=sample_widget['history'],
                                             workflow=sample_widget['workflow_dict'] )
                trans.sa_session.add( sample )
                trans.sa_session.flush()
                new_samples.append( sample )
            # If this sample is added when the request is already submitted then these new samples 
            # should be in the first sample state when saved
            if request.is_submitted:
                initial_sample_state_after_request_submitted = request.type.states[0]
                for sample in new_samples:
                    event_comment = 'Sample added and sample state set to %s.' % request.type.states[0].name
                    event = trans.model.SampleEvent( sample,
                                                     initial_sample_state_after_request_submitted,
                                                     event_comment )
                    trans.sa_session.add( event )
                trans.sa_session.flush()
        return trans.response.send_redirect( web.url_for( controller='requests_common',
                                                          action=redirect_action,
                                                          cntrller=cntrller,
                                                          id=trans.security.encode_id( request.id ),
                                                          status=status,
                                                          message=message ) )
    def __update_samples( self, trans, cntrller, request, sample_widgets, **kwd ):
        # The list of sample_widgets must have the same number of objects as request.samples,
        # but some of the objects can be None.  Those that are not None correspond to samples
        # selected by the user for performing an action on multiple samples simultaneously.
        # The items in the sample_widgets list have already been populated with any changed
        # param values (changed implies the value in kwd is different from the attribute value
        # in the database) in kwd before this method is reached.
        def handle_error( **kwd ):
            kwd[ 'status' ] = 'error'
            return trans.response.send_redirect( web.url_for( controller='requests_common',
                                                              action='edit_samples',
                                                              cntrller=cntrller,
                                                              **kwd ) )
        params = util.Params( kwd )
        for index, sample_widget in enumerate( sample_widgets ):
            if sample_widget is not None:
                # sample_widget will be None if the user checked sample check boxes and selected an action
                # to perform on multiple samples, but did not select certain samples.
                sample = request.samples[ index ]
                # Get the sample's form values to see if they have changed.
                form_values = trans.sa_session.query( trans.model.FormValues ).get( sample.values.id )
                if sample.name != sample_widget[ 'name' ] or \
                    sample.bar_code != sample_widget[ 'bar_code' ] or \
                    sample.library != sample_widget[ 'library' ] or \
                    sample.folder != sample_widget[ 'folder' ] or \
                    sample.history != sample_widget[ 'history' ] or \
                    sample.workflow != sample_widget[ 'workflow_dict' ] or \
                    form_values.content != sample_widget[ 'field_values' ]:
                    # Information about this sample has been changed.
                    sample.name = sample_widget[ 'name' ]
                    bar_code = sample_widget[ 'bar_code' ]
                    # If the sample has a new bar_code, make sure it is unique.
                    if bar_code:
                        bc_message = self.__validate_bar_code( trans, sample, bar_code )
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
                                # Change the sample state only if its request_type 
                                # has at least 2 states
                                if len( request.type.states ) >= 2:
                                    next_sample_state = request.type.states[1]
                                else:
                                    next_sample_state = request.type.states[0]
                                event = trans.model.SampleEvent( sample, 
                                                                 next_sample_state, 
                                                                 'Bar code associated with the sample' )
                                trans.sa_session.add( event )
                                trans.sa_session.flush()
                                # Next step is to update the request event history if bar codes 
                                # have been assigned to all the samples of this request
                                common_state = request.samples_have_common_state
                                if request.is_submitted and common_state and len( request.type.states ) >= 2:
                                    comment = "All samples of this request are in the (%s) sample state. " % common_state.name
                                    event = trans.model.RequestEvent( request, request.states.SUBMITTED, comment )
                                    trans.sa_session.add( event )
                                    trans.sa_session.flush()
                                    request.send_email_notification( trans, next_sample_state )

                    sample.bar_code = bar_code
                    sample.library = sample_widget[ 'library' ]
                    sample.folder = sample_widget[ 'folder' ]
                    sample.history = sample_widget[ 'history' ]
                    sample.workflow = sample_widget[ 'workflow_dict' ]
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
    def __get_history( self, trans, history_id):
        try:
            history = trans.sa_session.query( trans.model.History).get(trans.security.decode_id( history_id))
            return history
        except:
            return None
    def __get_workflow( self, trans, workflow_id):
        try:
            workflow = trans.sa_session.query( trans.model.Workflow).get(trans.security.decode_id( workflow_id))
            return workflow
        except:
            return None
    def __get_active_folders( self, folder, active_folders_list ):
        """Return all of the active folders for the received library"""
        active_folders_list.extend( folder.active_folders )
        for sub_folder in folder.active_folders:
            self.__get_active_folders( sub_folder, active_folders_list ) 
        return active_folders_list
    # ===== Methods for handling form definition widgets =====
    def __get_request_widgets( self, trans, id ):
        """Get the widgets for the request"""
        request = trans.sa_session.query( trans.model.Request ).get( id )
        # The request_widgets list is a list of dictionaries
        request_widgets = []
        for index, field in enumerate( request.type.request_form.fields ):
            field_value = request.values.content[ field['name'] ]
            if field[ 'required' ]:
                required_label = 'Required'
            else:
                required_label = 'Optional'
            if field[ 'type' ] == 'AddressField':
                if field_value:
                    request_widgets.append( dict( label=field[ 'label' ],
                                                  value=trans.sa_session.query( trans.model.UserAddress ).get( int( field_value ) ).get_html(),
                                                  helptext=field[ 'helptext' ] + ' (' + required_label + ')' ) )
                else:
                    request_widgets.append( dict( label=field[ 'label' ],
                                                  value=None,
                                                  helptext=field[ 'helptext' ] + ' (' + required_label + ')' ) )
            else: 
                request_widgets.append( dict( label=field[ 'label' ],
                                              value=field_value,
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
        sample_widgets = []
        if sample_operation != 'none':
            # The sample_operatin param has a value other than 'none', and a specified
            # set of samples was received.
            library_id = util.restore_text( params.get( 'sample_operation_library_id', 'none' ) )
            folder_id = util.restore_text( params.get( 'sample_operation_folder_id', 'none' ) )
        # Build the list of widgets which will be used to render each sample row on the request page
        if not request:
            return sample_widgets
        libraries = trans.app.security_agent.get_accessible_libraries( trans, request.user )
        # Build the list if sample widgets, populating the values from kwd.
        for index, sample in enumerate( samples ):
            if sample is None:
                # Use the sample from the request object since it will not have updated values from kwd.
                sample = request.samples[ index ]
                sample_id = sample.id
                name = sample.name
                bar_code = sample.bar_code
                library = sample.library
                folder = sample.folder
                history = sample.history
                workflow = sample.workflow
                field_values = sample.values.content
                if not history:
                    history_id = 'none'
                else:
                    history_id = history.id
                if not workflow:
                    workflow_id = 'none'
                else:
                    workflow_id = workflow.id
                workflow_dict = sample.workflow
            else:
                # Update the sample attributes from kwd
                sample_id = None
                name = util.restore_text( params.get( 'sample_%i_name' % index, sample.name ) )
                bar_code = util.restore_text( params.get( 'sample_%i_bar_code' % index, sample.bar_code ) )
                library_id = util.restore_text( params.get( 'sample_%i_library_id' % index, '' ) )
                if not library_id and sample.library:
                    library_id = trans.security.encode_id( sample.library.id )
                folder_id = util.restore_text( params.get( 'sample_%i_folder_id' % index, '' ) )
                if not folder_id and sample.folder:
                    folder_id = trans.security.encode_id( sample.folder.id )
                library, folder = self.__get_library_and_folder( trans, library_id, folder_id )
                history_id = util.restore_text( params.get( 'sample_%i_history_id' % index, '' ))
                if not history_id and sample.history:
                    history_id = trans.security.encode_id( sample.history.id )
                history = self.__get_history(trans, history_id)
                wf_tag = 'sample_%i_workflow_id' % index
                workflow_id = util.restore_text( params.get( wf_tag , '' ) )
                if not workflow_id and sample.workflow:
                    workflow_id = trans.security.encode_id( sample.workflow['id'] )
                    workflow_dict = sample.workflow
                    workflow = self.__get_workflow(trans, workflow_id)
                else:
                    workflow_dict = None
                    workflow = self.__get_workflow(trans, workflow_id)
                    if workflow:
                        workflow_dict = {'id': workflow.id,
                                         'name' : workflow.name,
                                         'mappings': {}}
                        for k, v in kwd.iteritems():
                            kwd_tag = "%s_" % wf_tag
                            if k.startswith(kwd_tag):
                                # DBTODO Don't need to store the whole mapping word in the dict, only the step.
                                workflow_dict['mappings'][int(k[len(kwd_tag):])] = {'ds_tag':v}
                field_values = {}
                for field_index, field in enumerate( request.type.sample_form.fields ):
                    field_name = field['name']
                    input_value = params.get( 'sample_%i_field_%i' % ( index, field_index ), sample.values.content[ field_name ] )
                    if field['type'] == CheckboxField.__name__:
                        field_value = CheckboxField.is_checked( input_value )
                    else: 
                        field_value = util.restore_text( input_value )
                    field_values[ field_name ] = field_value
            library_select_field, folder_select_field = self.__build_library_and_folder_select_fields( trans=trans,
                                                                                                       user=request.user,
                                                                                                       sample_index=index,
                                                                                                       libraries=libraries,
                                                                                                       sample=sample,
                                                                                                       library_id=library_id,
                                                                                                       folder_id=folder_id,
                                                                                                       **kwd )
            history_select_field = self.__build_history_select_field( trans=trans,
                                                        user=request.user,
                                                        sample_index=index,
                                                        sample=sample,
                                                        history_id=history_id,
                                                        **kwd)
            workflow_select_field = self.__build_workflow_select_field( trans=trans,
                                                          user=request.user,
                                                          request=request,
                                                          sample_index=index,
                                                          sample=sample,
                                                          workflow_dict=workflow_dict,
                                                          history_id=history_id,
                                                          **kwd)
            sample_widgets.append( dict( id=sample_id,
                                         name=name,
                                         bar_code=bar_code,
                                         library=library,
                                         folder=folder,
                                         history=history,
                                         workflow=workflow,
                                         workflow_dict=workflow_dict,
                                         field_values=field_values,
                                         library_select_field=library_select_field,
                                         folder_select_field=folder_select_field,
                                         history_select_field=history_select_field,
                                         workflow_select_field=workflow_select_field ) )
        # There may be additional new samples on the form that have not yet been associated with the request.
        # TODO: factor this code so it is not duplicating what's above.
        index = len( samples )
        while True:
            name = util.restore_text( params.get( 'sample_%i_name' % index, '' ) )
            if not name:
                break
            bar_code = util.restore_text( params.get( 'sample_%i_bar_code' % index, '' ) )
            library_id = util.restore_text( params.get( 'sample_%i_library_id' % index, '' ) )
            folder_id = util.restore_text( params.get( 'sample_%i_folder_id' % index, '' ) )
            library, folder = self.__get_library_and_folder( trans, library_id, folder_id )
            history_id = util.restore_text( params.get( 'sample_%i_history_id' % index, '' ))
            if not history_id and sample.history:
                history_id = trans.security.encode_id( sample.history.id )
            history = self.__get_history(trans, history_id)
            wf_tag = 'sample_%i_workflow_id' % index
            workflow_id = util.restore_text( params.get( wf_tag , '' ) )
            if not workflow_id and sample.workflow:
                workflow_id = trans.security.encode_id( sample.workflow['id'] )
                workflow_dict = sample.workflow
                workflow = self.__get_workflow(trans, workflow_id)
            else:
                workflow_dict = None
                workflow = self.__get_workflow(trans, workflow_id)
                if workflow:
                    workflow_dict = {'id': workflow.id,
                                     'name' : workflow.name,
                                     'mappings': {}}
                    for k, v in kwd.iteritems():
                        kwd_tag = "%s_" % wf_tag
                        if k.startswith(kwd_tag):
                            # DBTODO Change the key to include the dataset tag, not just the names.
                            workflow_dict['mappings'][int(k[len(kwd_tag):])] = {'ds_tag':v}
            field_values = {}
            for field_index, field in enumerate( request.type.sample_form.fields ):
                    field_name = field['name']
                    input_value = params.get( 'sample_%i_field_%i' % ( index, field_index ), '' )
                    if field['type'] == CheckboxField.__name__:
                        field_value = CheckboxField.is_checked( input_value )
                    else: 
                        field_value = util.restore_text( input_value )
                    field_values[ field_name ] = field_value
            library_select_field, folder_select_field = self.__build_library_and_folder_select_fields( trans=trans,
                                                                                                       user=request.user,
                                                                                                       sample_index=index,
                                                                                                       libraries=libraries,
                                                                                                       sample=None,
                                                                                                       library_id=library_id,
                                                                                                       folder_id=folder_id,
                                                                                                       **kwd )
            history_select_field = self.__build_history_select_field( trans=trans,
                                                       user=request.user,
                                                       sample_index=index,
                                                       sample=None,
                                                       history_id=history_id,
                                                       **kwd)

            workflow_select_field = self.__build_workflow_select_field( trans=trans,
                                                         user=request.user,
                                                         request=request,
                                                         sample_index=index,
                                                         sample=None,
                                                         workflow_dict=workflow_dict,
                                                         history_id=history_id,
                                                         **kwd)
            sample_widgets.append( dict( id=None,
                                         name=name,
                                         bar_code=bar_code,
                                         library=library,
                                         folder=folder,
                                         field_values=field_values,
                                         history=history,
                                         workflow=workflow,
                                         workflow_dict=workflow_dict,
                                         history_select_field=history_select_field,
                                         workflow_select_field=workflow_select_field,
                                         library_select_field=library_select_field,
                                         folder_select_field=folder_select_field ) )
            index += 1
        return sample_widgets   
    # ===== Methods for building SelectFields used on various request forms =====
    def __build_copy_sample_select_field( self, trans, displayable_sample_widgets ):
        copy_sample_index_select_field = SelectField( 'copy_sample_index' )
        copy_sample_index_select_field.add_option( 'None', -1, selected=True )  
        for index, sample_dict in enumerate( displayable_sample_widgets ):
            copy_sample_index_select_field.add_option( sample_dict[ 'name' ], index )
        return copy_sample_index_select_field  
    def __build_request_type_id_select_field( self, trans, selected_value='none' ):
        accessible_request_types = trans.app.security_agent.get_accessible_request_types( trans, trans.user )
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
        # existing library then display all the folders of the selected library in the folder_select_field.  Library folders do
        # not have ACCESS permissions associated with them (only LIBRARY_ADD, LIBRARY_MODIFY, LIBRARY_MANAGE), so all folders will
        # be present in the folder_select_field for each library selected.
        params = util.Params( kwd )
        if sample_index == 'sample_operation':
            # build the library selection widget for the bulk sample operation
            library_select_field_name= "sample_operation_library_id"
            folder_select_field_name = "sample_operation_folder_id"
        else:
            library_select_field_name= "sample_%i_library_id" % sample_index
            folder_select_field_name = "sample_%i_folder_id" % sample_index
        if not library_id:
            library_id = params.get( library_select_field_name, None )
        if not folder_id:
            folder_id = params.get( folder_select_field_name, None )
        selected_library = None
        if library_id not in [ None, 'none' ]:
            for library in libraries:
                encoded_id = trans.security.encode_id( library.id )
                if encoded_id == str( library_id ):
                    selected_library = library
                    break
        elif sample and sample.library and library_id == 'none':
            # The user previously selected a library but is now resetting the selection to 'none'
            selected_library = None
        elif sample and sample.library:
            library_id = trans.security.encode_id( sample.library.id )
            selected_library = sample.library
        # Build the sample_%i_library_id SelectField with refresh on change enabled
        library_select_field = build_select_field( trans,
                                                   libraries,
                                                   'name', 
                                                   library_select_field_name,
                                                   initial_value='none',
                                                   selected_value=str( library_id ).lower(),
                                                   refresh_on_change=True )
        # Get all folders for the selected library, if one is indeed selected
        if selected_library:
            folders = self.__get_active_folders( selected_library.root_folder, active_folders_list=[ selected_library.root_folder ] )
            if folder_id:
                selected_folder_id = folder_id
            elif sample and sample.folder:
                selected_folder_id = trans.security.encode_id( sample.folder.id )
            else:
                selected_folder_id = trans.security.encode_id( selected_library.root_folder.id )
        else:
            selected_folder_id = 'none'
            folders = []
        # Change the name of the library root folder to clarify that it is the root
        for folder in folders:
            if not folder.parent:
                folder.name = 'Data library root'
                break
        folder_select_field = build_select_field( trans,
                                                  folders,
                                                  'name', 
                                                  folder_select_field_name,
                                                  initial_value='none',
                                                  selected_value=selected_folder_id )
        return library_select_field, folder_select_field
    
    def __build_history_select_field(self, trans, user, sample_index, sample = None, history_id=None, **kwd):
        params = util.Params( kwd )
        history_select_field_name= "sample_%i_history_id" % sample_index
        if not history_id:
            history_id = params.get( history_select_field_name, None )
        selected_history = None
        if history_id not in [ None, 'none', 'new']:
            for history in user.histories:
                if not history.deleted:
                    encoded_id = trans.security.encode_id(history.id)
                    if encoded_id == str(history_id):
                        selected_history = history
                        break
        elif sample and sample.history and history_id == 'none' or history_id == 'new':
            # The user previously selected a history but is now resetting the selection to 'none'
            selected_history = None
        elif sample and sample.history:
            history_id = trans.security.encode_id( sample.history.id )
            selected_history = sample.history
        # Build the sample_%i_history_id SelectField with refresh on change disabled
        hsf = build_select_field( trans,
                                   [h for h in user.histories if not h.deleted],
                                   'name',
                                   history_select_field_name,
                                   initial_value='none',
                                   selected_value=str( history_id ).lower(),
                                   refresh_on_change=True )
        # This is ugly, but allows for an explicit "New History", while still using build_select_field.
        # hsf.options = hsf.options[:1] + [( "Create a New History", 'new', 'new'==str( history_id ).lower() )] + hsf.options[1:]
        hsf.options = [( "Select one", 'none', 'none'==str( history_id ).lower() )] + hsf.options[1:]
        return hsf

    def __build_workflow_select_field(self, trans, user, request, sample_index, sample=None, workflow_id=None, workflow_dict=None, history_id=None, **kwd ):
        params = util.Params( kwd )
        workflow_select_field_name= "sample_%i_workflow_id" % sample_index
        selected_workflow = None
        if not workflow_id:
            workflow_id = params.get( workflow_select_field_name, None )
        if workflow_id not in [ None, 'none' ]:
            selected_workflow = trans.sa_session.query( trans.model.Workflow ).get(trans.security.decode_id(workflow_id))
        elif sample and sample.workflow and workflow_id == 'none':
            selected_workflow = None
        elif sample and sample.workflow:
            workflow_id = sample.workflow['id']
            selected_workflow = trans.sa_session.query( trans.model.Workflow ).get(sample.workflow['id'])
        s_list = [w.latest_workflow for w in user.stored_workflows if not w.deleted]
        if selected_workflow and selected_workflow not in s_list:
            s_list.append(selected_workflow)
        workflow_select_field = build_select_field(trans,
                                                   s_list,
                                                   'name',
                                                   workflow_select_field_name,
                                                   initial_value='none',
                                                   selected_value=str( workflow_id ).lower(),
                                                   refresh_on_change=True )
        workflow_select_field.options = [( "Select one", 'none', 'none'==str( workflow_id ).lower() )] + workflow_select_field.options[1:]
        wf_fieldset = [workflow_select_field]
        if selected_workflow and request.type.external_services:
            # DBTODO This will work for now, but should be handled more rigorously.
            ds_list = []
            external_service = request.type.external_services[0]
            dataset_name_re = re.compile( '(dataset\d+)_(name)' )
            for k, v in external_service.form_values.content.items():
                match = dataset_name_re.match( k )
                if match:
                    ds_list.append(("ds|%s" % k[:-5], v))
            if history_id not in [None, 'none', 'new', '']:
                hist = trans.sa_session.query( trans.model.History ).get(trans.security.decode_id(history_id))
                h_inputs = [("hi|%s" % trans.security.encode_id(ds.id), ds.name) for ds in hist.datasets if not ds.deleted]
                ds_list += h_inputs
            for step in selected_workflow.steps:
                if step.type == 'data_input':
                    if step.tool_inputs and "name" in step.tool_inputs:
                        sf_name = '%s_%s' % (workflow_select_field_name, step.id)
                        select_field = SelectField( name=sf_name )
                        sf = params.get( sf_name, None )
                        if not sf and sample and sample.workflow:
                            if sample.workflow['mappings'].has_key(str(step.id)):
                                sf = sample.workflow['mappings'][str(step.id)]['ds_tag']
                        for value, label in ds_list:
                            if value == sf:
                                select_field.add_option( label, value, selected=True)
                            else:
                                select_field.add_option( label, value )
                        wf_fieldset.append((step.tool_inputs['name'], select_field))
        return wf_fieldset

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
            if field[ 'required' ] == 'required' and request.values.content[ field[ 'name' ] ] in [ '', None ]:
                empty_fields.append( field[ 'label' ] )
        empty_sample_fields = []
        for s in request.samples:
            for field in request.type.sample_form.fields:
                print "field:", field
                print "svc:", s.values.content
                if field['required'] == 'required' and s.values.content[field['name']] in ['', None]:
                    empty_sample_fields.append((s.name, field['label']))
        if empty_fields or empty_sample_fields:
            message = 'Complete the following fields of the request before submitting: <br/>'
            if empty_fields:
                for ef in empty_fields:
                    message += '<b>%s</b><br/>' % ef
            if empty_sample_fields:
                for sname, ef in empty_sample_fields:
                    message = message + '<b>%s</b> field of sample <b>%s</b><br/>' % (ef, sname)
            return message
        return None
    def __validate_sample_names( self, trans, cntrller, request, displayable_sample_widgets, **kwd ):
        # Check for duplicate sample names for all samples of the request.
        message = ''
        for index in range( len( displayable_sample_widgets ) - len( request.samples ) ):
            sample_index = index + len( request.samples )
            sample_widget = displayable_sample_widgets[ sample_index ]
            sample_name = sample_widget[ 'name' ]
            if not sample_name.strip():
                message = 'Enter the name of sample number %i' % sample_index
                break
            count = 0
            for i in range( len( displayable_sample_widgets ) ):
                if sample_name == displayable_sample_widgets[ i ][ 'name' ]:
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
    def __validate_bar_code( self, trans, sample, bar_code ):
        """
        Make sure that the bar_code about to be assigned to a sample is globally unique.
        That is, bar_codes must be unique across requests in Galaxy sample tracking.
        Bar codes are not required, but if used, they can only be added to a sample after
        the request is submitted.
        """
        message = ''
        unique = True
        for index in range( len( sample.request.samples ) ):
            # TODO: Add a unique constraint to sample.bar_code table column
            # Make sure bar code is unique
            for sample_with_bar_code in trans.sa_session.query( trans.model.Sample ) \
                                                       .filter( trans.model.Sample.table.c.bar_code == bar_code ):
                if sample_with_bar_code and sample_with_bar_code.id != sample.id:
                    message = '''The bar code (%s) associated with the sample (%s) belongs to another sample.  
                                 Bar codes must be unique across all samples, so use a different bar code 
                                 for this sample.''' % ( bar_code, sample.name )
                    unique = False
                    break
            if not unique:
                break
        return message
    # ===== Other miscellaneous utility methods =====
    def __get_encoded_selected_sample_ids( self, trans, request, **kwd ):
        encoded_selected_sample_ids = []
        for sample in request.samples:
            if CheckboxField.is_checked( kwd.get( 'select_sample_%i' % sample.id, '' ) ):
                encoded_selected_sample_ids.append( trans.security.encode_id( sample.id ) )
        return encoded_selected_sample_ids

# ===== Miscellaneous utility methods outside of the RequestsCommon class =====
def invalid_id_redirect( trans, cntrller, obj_id, item='sequencing request', action='browse_requests' ):
    status = 'error'
    message = "Invalid %s id (%s)" % ( item, str( obj_id ) )
    return trans.response.send_redirect( web.url_for( controller=cntrller,
                                                      action=action,
                                                      status=status,
                                                      message=message ) )
