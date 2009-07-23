from galaxy.web.base.controller import *
from galaxy.web.framework.helpers import time_ago, iff, grids
from galaxy.model.orm import *
from galaxy.datatypes import sniff
from galaxy import util
from galaxy.util.streamball import StreamBall
import logging, tempfile, zipfile, tarfile, os, sys
from galaxy.web.form_builder import * 
from datetime import datetime, timedelta

log = logging.getLogger( __name__ )


# States for passing messages
SUCCESS, INFO, WARNING, ERROR = "done", "info", "warning", "error"

class RequestsListGrid( grids.Grid ):
    title = "Sequencing Requests"
    model_class = model.Request
    default_sort_key = "-create_time"
    columns = [
        grids.GridColumn( "Name", key="name",
                          link=( lambda item: iff( item.deleted, None, dict( operation="show_request", id=item.id ) ) )),
        grids.GridColumn( "Description", key="desc"),
        grids.GridColumn( "Sample(s)", method='number_of_samples',
                          link=( lambda item: iff( item.deleted, None, dict( operation="show_request", id=item.id ) ) ), ),
        grids.GridColumn( "Type", key="request_type_id", method='get_request_type'),
        grids.GridColumn( "Last update", key="update_time", format=time_ago ),
        grids.GridColumn( "User", key="user_id", method='get_user')
        
    ]
    operations = [
#        grids.GridOperation( "Edit", allow_multiple=False, condition=( lambda item: not item.deleted )  ),
#        grids.GridOperation( "Samples", allow_multiple=False, condition=( lambda item: not item.deleted )  ),
#        grids.GridOperation( "Delete", condition=( lambda item: not item.deleted ) ),
#        grids.GridOperation( "Undelete", condition=( lambda item: item.deleted ) ),    
    ]
    standard_filters = [
        grids.GridColumnFilter( "Active", args=dict( deleted=False ) ),
        grids.GridColumnFilter( "Deleted", args=dict( deleted=True ) ),
        grids.GridColumnFilter( "All", args=dict( deleted='All' ) )
    ]
    def get_user(self, trans, request):
        return trans.app.model.User.get(request.user_id).email
    def get_current_item( self, trans ):
        return None
    def get_request_type(self, trans, request):
        request_type = trans.app.model.RequestType.get(request.request_type_id)
        return request_type.name
    def apply_default_filter( self, trans, query ):
        return query.filter_by(submitted=True)
    def number_of_samples(self, trans, request):
        return str(len(request.samples))
    
class Requests( BaseController ):
    request_grid = RequestsListGrid()
    
    @web.expose
    @web.require_admin
    def index( self, trans ):
        return trans.fill_template( "/admin/requests/index.mako" )
    def get_authorized_libs(self, trans):
        all_libraries = trans.app.model.Library.filter(trans.app.model.Library.table.c.deleted == False).order_by(trans.app.model.Library.name).all()
        authorized_libraries = []
        for library in all_libraries:
            if trans.app.security_agent.allow_action(trans.user, trans.app.security_agent.permitted_actions.LIBRARY_ADD, library_item=library) or trans.app.security_agent.allow_action(trans.user, trans.app.security_agent.permitted_actions.LIBRARY_MODIFY, library_item=library) or trans.app.security_agent.allow_action(trans.user, trans.app.security_agent.permitted_actions.LIBRARY_MANAGE, library_item=library) or trans.app.security_agent.check_folder_contents(trans.user, library) or trans.app.security_agent.show_library_item(trans.user, library):
                authorized_libraries.append(library)
        return authorized_libraries
    @web.expose
    @web.require_admin
    def list( self, trans, **kwargs ):
        '''
        List all request made by the current user
        '''
        status = message = None
        if 'operation' in kwargs:
            operation = kwargs['operation'].lower()
            if operation == "show_request":
                id = trans.security.decode_id(kwargs['id'])
                return self.__show_request(trans, id)
        # Render the list view
        return self.request_grid( trans, template='/admin/requests/grid.mako', **kwargs )
    def __show_request(self, trans, id):
        try:
            request = trans.app.model.Request.get(id)
        except:
            return trans.response.send_redirect( web.url_for( controller='requests',
                                                              action='list',
                                                              status='error',
                                                              message="Invalid request ID",
                                                              **kwd) )
        self.current_samples = []
        for s in request.samples:
            self.current_samples.append([s.name, s.values.content])
        return trans.fill_template( '/admin/requests/show_request.mako',
                                    request=request,
                                    request_details=self.request_details(trans, id),
                                    current_samples = self.current_samples)
    def request_details(self, trans, id):
        '''
        Shows the request details
        '''
        request = trans.app.model.Request.get(id)
        libraries = self.get_authorized_libs(trans)
        # list of widgets to be rendered on the request form
        request_details = []
        # main details
        request_details.append(dict(label='Description', 
                                    value=request.desc, 
                                    helptext=''))
        request_details.append(dict(label='Type', 
                                    value=request.type.name, 
                                    helptext=''))
        request_details.append(dict(label='Date created', 
                                    value=request.create_time, 
                                    helptext=''))
        request_details.append(dict(label='Date updated', 
                                    value=request.create_time, 
                                    helptext=''))
        request_details.append(dict(label='User', 
                                    value=str(request.user.email), 
                                    helptext=''))
        # library associated
        request_details.append(dict(label='Library', 
                            value=trans.app.model.Library.get(request.library_id).name, 
                            helptext='Associated library where the resultant \
                                        dataset will be stored'))
        # form fields
        for index, field in enumerate(request.type.request_form.fields):
            if field['required']:
                req = 'Required'
            else:
                req = 'Optional'
            request_details.append(dict(label=field['label'],
                                        value=request.values.content[index],
                                        helptext=field['helptext']+' ('+req+')'))
        return request_details
    @web.expose
    @web.require_admin
    def bar_codes(self, trans, **kwd):
        params = util.Params( kwd )
        request_id = params.get('request_id', None)
        if request_id:
            request_id = int(request_id)
            request = trans.app.model.Request.get(request_id)
            return trans.fill_template( '/admin/samples/bar_codes.mako', 
                                        samples_list=[s for s in request.samples],
                                        user=request.user,
                                        request=request)

    @web.expose
    @web.require_admin
    def save_bar_codes(self, trans, **kwd):
        params = util.Params( kwd )
        request_id = params.get('request_id', None)
        if request_id:
            request_id = int(request_id)
            request = trans.app.model.Request.get(request_id)
            # validate 
            # bar codes need to be globally unique
            unique = True
            for index in range(len(request.samples)):
                bar_code = util.restore_text(params.get('sample_%i_bar_code' % index, ''))
                all_samples = trans.app.model.Sample.query.all()
                for sample in all_samples:
                    if bar_code == sample.bar_code:
                        unique = False
            if not unique:
                return trans.fill_template( '/admin/samples/bar_codes.mako', 
                                            samples_list=[s for s in request.samples],
                                            user=request.user,
                                            request=request,
                                            messagetype='error',
                                            msg='Samples cannot have same bar code.')
            for index, sample in enumerate(request.samples):
                bar_code = util.restore_text(params.get('sample_%i_bar_code' % index, ''))
                sample.bar_code = bar_code
                sample.flush()
        return trans.response.send_redirect( web.url_for( controller='requests_admin',
                                                          action='list',
                                                          operation='show_request',
                                                          id=trans.security.encode_id(request.id)) )
    def change_state(self, trans, sample):
        possible_states = sample.request.type.states 
        curr_state = sample.current_state() 
        states_input = SelectField('select_state')
        for state in possible_states:
            if curr_state.name == state.name:
                states_input.add_option(state.name+' (Current)', state.id, selected=True)
            else:
                states_input.add_option(state.name, state.id)
        widgets = []
        widgets.append(('Select the new state of the sample from the list of possible state(s)',
                      states_input))
        widgets.append(('Comments', TextArea('comment')))
        title = 'Change current state'
        return widgets, title
    @web.expose
    @web.require_admin
    def save_state(self, trans, **kwd):
        params = util.Params( kwd )
        try:
            sample_id = int(params.get('sample_id', False))
            sample = trans.app.model.Sample.get(sample_id)
        except:
            msg = "Invalid sample ID"
            return trans.response.send_redirect( web.url_for( controller='requests_admin',
                                                              action='list',
                                                              status='error',
                                                              message=msg,
                                                              **kwd) )
        comments = util.restore_text( params.comment )
        selected_state = int( params.select_state )
        new_state = trans.app.model.SampleState.filter(trans.app.model.SampleState.table.c.request_type_id == sample.request.type.id 
                                                        and trans.app.model.SampleState.table.c.id == selected_state)[0]
        event = trans.app.model.SampleEvent(sample, new_state, comments)
        event.flush()
        return trans.response.send_redirect( web.url_for( controller='requests_admin',
                                                          action='show_events',
                                                          sample_id=sample.id))
    @web.expose
    @web.require_admin
    def show_events(self, trans, **kwd):
        params = util.Params( kwd )
        try:
            sample_id = int(params.get('sample_id', False))
            sample = trans.app.model.Sample.get(sample_id)
        except:
            msg = "Invalid sample ID"
            return trans.response.send_redirect( web.url_for( controller='requests_admin',
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
        widgets, title = self.change_state(trans, sample)
        return trans.fill_template( '/admin/samples/events.mako', 
                                    events_list=events_list,
                                    sample=sample, widgets=widgets, title=title)
    