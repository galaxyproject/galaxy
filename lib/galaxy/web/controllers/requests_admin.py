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
    title = "Requests"
    model_class = model.Request
    default_sort_key = "-create_time"
    columns = [
        grids.GridColumn( "Name", key="name",
                          link=( lambda item: iff( item.deleted, None, dict( operation="show_request", id=item.id ) ) ),
                          attach_popup=True ),
        grids.GridColumn( "Description", key="desc"),
        grids.GridColumn( "Sample(s)", method='number_of_samples',
                          link=( lambda item: iff( item.deleted, None, dict( operation="samples", id=item.id ) ) ), ),
        grids.GridColumn( "Type", key="request_type_id", method='get_request_type'),
        grids.GridColumn( "Last update", key="update_time", format=time_ago ),
        grids.GridColumn( "User", key="user_id", method='get_user')
        
    ]
    operations = [
#        grids.GridOperation( "Edit", allow_multiple=False, condition=( lambda item: not item.deleted )  ),
        grids.GridOperation( "Samples", allow_multiple=False, condition=( lambda item: not item.deleted )  ),
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
        return query
    def number_of_samples(self, trans, request):
        return str(len(trans.app.model.Sample.filter(trans.app.model.Sample.table.c.request_id==request.id).all()))
    
class SamplesListGrid( grids.Grid ):
    model_class = model.Sample
    default_sort_key = "-create_time"
    columns = [
        grids.GridColumn( "Name", key="name",
                          link=( lambda item: iff( item.deleted, None, dict( operation="show_sample", id=item.id ) ) ),
                          attach_popup=True ),
        grids.GridColumn( "Description", key='desc' ),
        grids.GridColumn( "Status", method="get_status",
                          link=( lambda item: iff( item.deleted, None, dict( operation="events", id=item.id ) ) )),

        grids.GridColumn( "Last update", key="update_time", format=time_ago )
        
        # Valid for filtering but invisible
        #grids.GridColumn( "Deleted", key="deleted", visible=False )
    ]
    operations = [
#        grids.GridOperation( "Edit", allow_multiple=False, condition=( lambda item: not item.deleted )  ),
        grids.GridOperation( "Change state", condition=( lambda item: not item.deleted )  ),
#        grids.GridOperation( "Delete", condition=( lambda item: not item.deleted ) ),
#        grids.GridOperation( "Undelete", condition=( lambda item: item.deleted ) ),
        
    ]
    standard_filters = [
        grids.GridColumnFilter( "Active", args=dict( deleted=False ) ),
        grids.GridColumnFilter( "Deleted", args=dict( deleted=True ) ),
        grids.GridColumnFilter( "All", args=dict( deleted='All' ) )
    ]
    def __init__(self, request, user):
        self.request  = request
        self.user = user
    def get_current_item( self, trans ):
        return None
    def apply_default_filter( self, trans, query ):
        return query.filter_by( request_id=self.request.id )
    def get_status(self, trans, sample):
        all_states = trans.app.model.SampleEvent.filter(trans.app.model.SampleEvent.table.c.sample_id == sample.id).all()
        curr_state = trans.app.model.SampleState.get(all_states[len(all_states)-1].sample_state_id)
        return curr_state.name

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
                return self.show_read_only(trans, id)
            elif operation == "samples":
                id = trans.security.decode_id(kwargs['id'])
                return self.show_samples(trans, id, kwargs)
            elif operation == "show_sample":
                id = trans.security.decode_id(kwargs['id'])
                return self.show_sample_read_only(trans, id)
            elif operation == "change state":
                id_list = [trans.security.decode_id(id) for id in util.listify(kwargs['id'])]
                return self.change_state(trans, id_list)
            elif operation == "events":
                id = trans.security.decode_id(kwargs['id'])
                return self.show_events(trans, id)
        # Render the list view
        return self.request_grid( trans, status=status, message=message, template='/admin/requests/grid.mako', **kwargs )
    def show_samples(self, trans, id, kwargs):
        '''
        Shows all the samples associated with this request
        '''
        status = message = None
        request = trans.app.model.Request.get(id)
        self.samples_grid = SamplesListGrid(request, trans.app.model.User.get(request.user_id))
        return self.samples_grid( trans, status=status, message=message, template='/admin/samples/grid.mako', **kwargs )        
    def show_read_only(self, trans, id):
        '''
        Shows the request details
        '''
        request = trans.app.model.Request.get(id)
        libraries = self.get_authorized_libs(trans)
        # list of widgets to be rendered on the request form
        request_details = []
        # main details
        request_details.append(dict(label='Name', 
                                    value=request.name, 
                                    helptext=''))
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
        return trans.fill_template( '/admin/requests/view_request.mako',
                                    request_form_id=request.type.request_form.id, 
                                    request_details=request_details,
                                    request_type=request.type)    

    @web.expose
    @web.require_admin
    def samples(self, trans, **kwd):
        params = util.Params( kwd )
        if params.get('save', False) == 'True':
            sample = self.__save_sample(trans, params)
            return self.show_samples(trans, sample.request_id, {})            
    def show_sample_read_only(self, trans, sample_id):
        '''
        Shows the sample details
        '''
        sample = trans.app.model.Sample.get(sample_id)
        request = sample.request
        request_type = sample.request.type
        sample_form = sample.request.type.sample_form
        sample_values = sample.values
        # list of widgets to be rendered on the request form
        sample_details = []
        # main details
        sample_details.append(dict(label='Name', 
                                    value=request.name, 
                                    helptext=''))
        sample_details.append(dict(label='Description', 
                                    value=request.desc, 
                                    helptext=''))
        sample_details.append(dict(label='Date created', 
                                    value=sample.create_time, 
                                    helptext=''))
        sample_details.append(dict(label='Date updated', 
                                    value=sample.create_time, 
                                    helptext=''))
        sample_details.append(dict(label='User', 
                                    value=str(trans.user.email), 
                                    helptext=''))
        sample_details.append(dict(label='Request', 
                                    value=request.name, 
                                    helptext='Name/ID of the request this sample belongs to.'))
        # get the current state of the sample
        all_states = trans.app.model.SampleEvent.filter(trans.app.model.SampleEvent.table.c.sample_id == sample_id).all()
        curr_state = all_states[len(all_states)-1].state
        sample_details.append(dict(label='State', 
                                    value=curr_state.name, 
                                    helptext=curr_state.desc))
        # form fields
        for index, field in enumerate(sample_form.fields):
            if field['required']:
                req = 'Required'
            else:
                req = 'Optional'
            sample_details.append(dict(label=field['label'],
                                        value=sample_values.content[index],
                                        helptext=field['helptext']+' ('+req+')'))
        return trans.fill_template( '/admin/samples/view_sample.mako', 
                                    sample_details=sample_details)
    def __get_all_states(self, trans, sample):
        request = trans.app.model.Request.get(sample.request_id)
        request_type = trans.app.model.RequestType.get(request.request_type_id)
        all_states = trans.app.model.SampleEvent.filter(trans.app.model.SampleEvent.table.c.sample_id == sample.id).all()
        curr_state = trans.app.model.SampleState.get(all_states[len(all_states)-1].sample_state_id)
        states_list = trans.app.model.SampleState.filter(trans.app.model.SampleState.table.c.request_type_id == request_type.id)
        return states_list
    def __get_curr_state(self, trans, sample):
        all_states = trans.app.model.SampleEvent.filter(trans.app.model.SampleEvent.table.c.sample_id == sample.id).all()
        curr_state = trans.app.model.SampleState.get(all_states[len(all_states)-1].sample_state_id)
        return curr_state
    def change_state(self, trans, sample_id_list):
        sample = trans.app.model.Sample.get(sample_id_list[0])
        states_list = self.__get_all_states(trans, sample)
        curr_state = self.__get_curr_state(trans, sample)
        states_input = SelectField('select_state')
        for state in states_list:
            if len(sample_id_list) == 1:
                if curr_state.name == state.name:
                    states_input.add_option(state.name+' (Current)', state.name, selected=True)
                else:
                    states_input.add_option(state.name, state.name)
            else:
                states_input.add_option(state.name, state.name)
        widgets = []
        widgets.append(('Select the new state of the sample(s) from the list of possible state(s)',
                      states_input))
        widgets.append(('Comments', TextArea('comment')))
        title = 'Change current state of sample: ' + sample.name
        return trans.fill_template( '/admin/samples/change_state.mako', 
                                    widgets=widgets, title=title, 
                                    sample_id_list=util.object_to_string(sample_id_list)) 
    @web.expose
    @web.require_admin
    def save_state(self, trans, **kwd):
        params = util.Params( kwd )
        sample_id_list = util.string_to_object(util.restore_text( params.sample_id_list ))
        comments = util.restore_text( params.comment )
        sample = trans.app.model.Sample.get(sample_id_list[0])
        request = trans.app.model.Request.get(sample.request_id)
        selected_state = util.restore_text( params.select_state )
        new_state = trans.app.model.SampleState.filter(trans.app.model.SampleState.table.c.request_type_id == request.request_type_id 
                                                        and trans.app.model.SampleState.table.c.name == selected_state)[0]
        for sample_id in sample_id_list:
            event = trans.app.model.SampleEvent(sample_id, new_state.id, comments)
            event.flush()
        return trans.response.send_redirect( web.url_for( controller='requests_admin',
                                                          action='list',
                                                          operation='samples',
                                                          id=trans.security.encode_id(request.id)) )
    @web.expose
    @web.require_admin
    def show_events(self, trans, sample_id):
        sample = trans.app.model.Sample.get(sample_id)
        request = trans.app.model.Request.get(sample.request_id)
        events_list = []
        all_events = trans.app.model.SampleEvent.filter(trans.app.model.SampleEvent.table.c.sample_id == sample_id).all()
        all_events.reverse()
        for event in all_events:         
            state = trans.app.model.SampleState.get(event.sample_state_id)
            delta = datetime.utcnow() - event.update_time
            if delta > timedelta( minutes=60 ):
                last_update = '%s hours' % int( delta.seconds / 60 / 60 )
            else:
                last_update = '%s minutes' % int( delta.seconds / 60 )
            events_list.append((state.name, state.desc, last_update, event.comment))
        return trans.fill_template( '/admin/samples/events.mako', 
                                    events_list=events_list,
                                    sample_name=sample.name, user=trans.app.model.User.get(request.user_id),
                                    request=request.name)
    