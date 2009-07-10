from galaxy.web.base.controller import *
from galaxy.web.framework.helpers import time_ago, iff, grids
from galaxy.model.orm import *
from galaxy.datatypes import sniff
from galaxy import util
from galaxy.util.streamball import StreamBall
import logging, tempfile, zipfile, tarfile, os, sys
from galaxy.web.form_builder import * 

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
        grids.GridColumn( "Description", key='desc'),
        grids.GridColumn( "Sample(s)", method='number_of_samples', 
                          link=( lambda item: iff( item.deleted, None, dict( operation="samples", id=item.id ) ) ), ),
        grids.GridColumn( "Type", key="request_type_id", method='get_request_type'),
        grids.GridColumn( "Last update", key="update_time", format=time_ago )
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
    #default_filter = dict( deleted=False )
    def get_current_item( self, trans ):
        return None
    def get_request_type(self, trans, request):
        request_type = trans.app.model.RequestType.get(request.request_type_id)
        return request_type.name
    def apply_default_filter( self, trans, query ):
        return query.filter_by( user=trans.user )
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
#        grids.GridOperation( "Delete", condition=( lambda item: not item.deleted ) ),
#        grids.GridOperation( "Undelete", condition=( lambda item: item.deleted ) ),
        
    ]
    standard_filters = [
        grids.GridColumnFilter( "Active", args=dict( deleted=False ) ),
        grids.GridColumnFilter( "Deleted", args=dict( deleted=True ) ),
        grids.GridColumnFilter( "All", args=dict( deleted='All' ) )
    ]
    def __init__(self, request):
        self.request  = request
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
    def index( self, trans ):
        return trans.fill_template( "requests/index.mako" )
    def get_authorized_libs(self, trans):
        all_libraries = trans.app.model.Library.filter(trans.app.model.Library.table.c.deleted == False).order_by(trans.app.model.Library.name).all()
        authorized_libraries = []
        for library in all_libraries:
            if trans.app.security_agent.allow_action(trans.user, trans.app.security_agent.permitted_actions.LIBRARY_ADD, library_item=library) or trans.app.security_agent.allow_action(trans.user, trans.app.security_agent.permitted_actions.LIBRARY_MODIFY, library_item=library) or trans.app.security_agent.allow_action(trans.user, trans.app.security_agent.permitted_actions.LIBRARY_MANAGE, library_item=library) or trans.app.security_agent.check_folder_contents(trans.user, library) or trans.app.security_agent.show_library_item(trans.user, library):
                authorized_libraries.append(library)
        return authorized_libraries
    @web.expose
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
            elif operation == "events":
                id = trans.security.decode_id(kwargs['id'])
                return self.show_events(trans, id)
        # Render the list view
        return self.request_grid( trans, status=status, message=message, template='/requests/grid.mako', **kwargs )
    def show_samples(self, trans, id, kwargs):
        '''
        Shows all the samples associated with this request
        '''
        status = message = None
        request = trans.app.model.Request.get(id)
        self.samples_grid = SamplesListGrid(request)
        return self.samples_grid( trans, status=status, message=message, template='/sample/grid.mako', **kwargs )        
    def show_read_only(self, trans, id):
        '''
        Shows the request details
        '''
        request = trans.app.model.Request.get(id)
        request_type = trans.app.model.RequestType.get(request.request_type_id)
        request_form = trans.app.model.FormDefinition.get(request_type.request_form_id)
        request_values = trans.app.model.FormValues.get(request.form_values_id)
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
                                    value=request_type.name, 
                                    helptext=''))
        request_details.append(dict(label='Date created', 
                                    value=request.create_time, 
                                    helptext=''))
        request_details.append(dict(label='Date updated', 
                                    value=request.create_time, 
                                    helptext=''))
        request_details.append(dict(label='User', 
                                    value=str(trans.user.email), 
                                    helptext=''))
        # library associated
        request_details.append(dict(label='Library', 
                                    value=trans.app.model.Library.get(request.library_id).name, 
                                    helptext='Associated library where the resultant \
                                              dataset will be stored'))
        # form fields
        for field in request_form.fields:
            if field['required']:
                req = 'Required'
            else:
                req = 'Optional'
            request_details.append(dict(label=field['label'],
                                        value=request_values.content[field['label']],
                                        helptext=field['helptext']+' ('+req+')'))
        return trans.fill_template( '/requests/view_request.mako',
                                    request_form_id=request_form.id, 
                                    request_details=request_details,
                                    request_type=request_type)    
    @web.expose
    def new(self, trans, **kwd):
        params = util.Params( kwd )
        msg = util.restore_text( params.get( 'msg', ''  ) )
        messagetype = params.get( 'messagetype', 'done' )
        if params.get('select_request_type', False) == 'True':
            return trans.fill_template( '/requests/select_request_type.mako', 
                                        request_types=trans.app.model.RequestType.query().all(),
                                        libraries=self.get_authorized_libs(trans),
                                        msg=msg,
                                        messagetype=messagetype )
        elif params.get('create', False) == 'True':
            request_type_id = int(util.restore_text( params.request_type_id ))
            return self.__show_request_form(trans, params, request_type_id)
        elif params.get('save', False) == 'True':
            request = self.__save(trans, params)
            msg = 'The new request named %s has been created' % request.name
            request_type_id = int(util.restore_text( params.request_type_id ))
            return trans.response.send_redirect( web.url_for( controller='requests',
                                                              action='list',
                                                              msg=msg ,
                                                              messagetype='done') )
            return self.__show_request_form(trans, params, request_type_id, request=request)
    def __save(self, trans, params, request_id=None):
        '''
        This method save a new request if request_id is None. 
        '''
        if not request_id:
            request_type_id = int(util.restore_text( params.request_type_id ))
            request_form_id = trans.app.model.RequestType.get(request_type_id).request_form_id
            request_form = trans.app.model.FormDefinition.get(request_form_id)
        else:
            request = trans.app.model.Request.get(request_id)
            form_values = trans.app.model.FormValues.get(request.form_values_id)
            request_form = trans.app.model.FormDefinition.get(form_values.request_form_id)
        name = params.get('name', '')
        desc = params.get('desc', '')
        library_id = params.get('library', '')
        values = {}
        for field in request_form.fields:
            values[field['label']] = params.get(field['label'], '')
        if not request_id:
            form_values = trans.app.model.FormValues(request_form_id, values)
            form_values.flush()
            request = trans.app.model.Request(name, desc, request_type_id, 
                                              trans.user.id, form_values.id,
                                              library_id)
            request.flush()
        else:
            form_values.content = values
            form_values.flush()
        return request
    def __show_request_form(self, trans, params, request_type_id, request=None):
        request_type = trans.app.model.RequestType.get(request_type_id)
        request_form_id = request_type.request_form_id
        if request:
            form_values = trans.app.model.FormValues.get(request.form_values_id)
        else:
            form_values = None
        # list of widgets to be rendered on the request form
        widgets = []
        widgets.append(dict(label='Name', 
                            widget=TextField('name'), 
                            helptext='(Required)'))
        widgets.append(dict(label='Description', 
                            widget=TextField('desc'), 
                            helptext='(Optional)'))
        widgets[0]['widget'].set_size(40)
        widgets[1]['widget'].set_size(40)
        # libraries selectbox
        libraries = self.get_authorized_libs(trans)
        lib_list = SelectField('library')
        for lib in libraries:
            lib_list.add_option(lib.name, lib.id)
        widgets.append(dict(label='Library', 
                            widget=lib_list, 
                            helptext='Associated library where the resultant \
                                        dataset will be stored'))
        widgets = self.__create_form(trans, params, request_form_id, widgets, form_values)
        title = 'Add a new request of type: %s' % request_type.name
        return trans.fill_template( '/requests/new_request.mako',
                        request_form_id=request_form_id,
                        request_type=request_type,                                     
                        widgets=widgets,
                        title=title)
        
    def __create_form(self, trans, params, form_id, widgets=[], form_values=None):
        form = trans.app.model.FormDefinition.get(form_id)
        if not form_values:
            values = {}
            for field in form.fields:
                if field['type'] in ['SelectField' or 'CheckBoxField']:
                    values[field['label']] = False
                else:
                    values[field['label']] = ''
        else:
            values = form_values.content
        # form fields
        for field in form.fields:
            fw = eval(field['type'])(field['label'])
            if field['type'] == 'TextField':
                fw.set_size(40)
                fw.value = values[field['label']]
            elif field['type'] == 'TextArea':
                fw.set_size(3, 40)
                fw.value = values[field['label']]
            elif field['type'] == 'SelectField':
                for option in field['selectlist']:
                    fw.add_option(option, option, values[field['label']])
            elif field['type'] == 'CheckBoxField':
                fw.checked = values[field['label']]
            
            if field['required']:
                req = 'Required'
            else:
                req = 'Optional'
            widgets.append(dict(label=field['label'],
                                widget=fw,
                                helptext=field['helptext']+' ('+req+')'))
        return widgets
    @web.expose
    def add_sample(self, trans, **kwd):
        params = util.Params( kwd )
        msg = util.restore_text( params.get( 'msg', ''  ) )
        messagetype = params.get( 'messagetype', 'done' )
        request_id = int(util.restore_text( params.get( 'id', ''  ) ))
        return self.__show_sample_form(trans, params, request_id)
        
    def __show_sample_form(self, trans, params, request_id, sample=None):
        request = trans.app.model.Request.get(request_id)
        request_type = trans.app.model.RequestType.get(request.request_type_id)
        sample_form_id = request_type.sample_form_id
        if sample:
            form_values = trans.app.model.FormValues.get(sample.form_values_id)
        else:
            form_values = None
        # list of widgets to be rendered on the request form
        widgets = []
        widgets.append(dict(label='Name', 
                            widget=TextField('name'), 
                            helptext='(Required)'))
        widgets.append(dict(label='Description', 
                            widget=TextField('desc'), 
                            helptext='(Optional)'))
        widgets[0]['widget'].set_size(40)
        widgets[1]['widget'].set_size(40)
        widgets = self.__create_form(trans, params, sample_form_id, widgets, form_values)
        title = 'Add a new sample to request: %s of type: %s' % (request.name, request_type.name) 
        return trans.fill_template( '/sample/new_sample.mako',
                        sample_form_id=sample_form_id,
                        request_id=request.id,                                     
                        widgets=widgets,
                        title=title)
    @web.expose
    def samples(self, trans, **kwd):
        params = util.Params( kwd )
        if params.get('save', False) == 'True':
            sample = self.__save_sample(trans, params)
            return trans.response.send_redirect( web.url_for( controller='requests',
                                                              action='list',
                                                              operation='samples',
                                                              id=trans.security.encode_id(sample.request_id)) )
    def __save_sample(self, trans, params, sample_id=None):
        if not sample_id:
            request = trans.app.model.Request.get(int(util.restore_text( params.request_id )))
            request_type = trans.app.model.RequestType.get(request.request_type_id)
            sample_form = trans.app.model.FormDefinition.get(request_type.sample_form_id)
        else:
            sample = trans.app.model.Sample.get(sample_id)
            form_data = trans.app.model.FormData.get(sample.form_data_id)
            form = trans.app.model.FormDefinition.get(form_data.form_definition_id)
        name = params.get('name', '')
        desc = params.get('desc', '')
        values = {}
        for field in sample_form.fields:
            values[field['label']] = params.get(field['label'], '')
        if not sample_id:
            form_values = trans.app.model.FormValues(sample_form.id, values)
            form_values.flush()
            sample = trans.app.model.Sample(name, desc, request.id, form_values.id)
            sample.flush()
            # set the initial state            
            state = trans.app.model.SampleState.filter(trans.app.model.SampleState.table.c.request_type_id == request_type.id).first()
            event = trans.app.model.SampleEvent(sample.id, state.id)
            event.flush()
        else:
            form_data.content = values
            form_data.flush()
        return sample
    def show_sample_read_only(self, trans, sample_id):
        '''
        Shows the sample details
        '''
        sample = trans.app.model.Sample.get(sample_id)
        request = trans.app.model.Request.get(sample.request_id)
        request_type = trans.app.model.RequestType.get(request.request_type_id)
        sample_form = trans.app.model.FormDefinition.get(request_type.sample_form_id)
        sample_values = trans.app.model.FormValues.get(sample.form_values_id)
        # list of widgets to be rendered on the request form
        sample_details = []
        # main details
        sample_details.append(dict(label='Name', 
                                    value=sample.name, 
                                    helptext=''))
        sample_details.append(dict(label='Description', 
                                    value=sample.desc, 
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
        curr_state = trans.app.model.SampleState.get(all_states[len(all_states)-1].sample_state_id)
        sample_details.append(dict(label='State', 
                                    value=curr_state.name, 
                                    helptext=curr_state.desc))
        # form fields
        for field in sample_form.fields:
            if field['required']:
                req = 'Required'
            else:
                req = 'Optional'
            sample_details.append(dict(label=field['label'],
                                        value=sample_values.content[field['label']],
                                        helptext=field['helptext']+' ('+req+')'))
        return trans.fill_template( '/sample/view_sample.mako', 
                                    sample_details=sample_details)
    def show_events(self, trans, sample_id):
        sample = trans.app.model.Sample.get(sample_id)
        events_list = []
        for event in trans.app.model.SampleEvent.filter(trans.app.model.SampleEvent.table.c.sample_id == sample_id).all():
            state = trans.app.model.SampleState.get(event.sample_state_id)
            events_list.append((state.name, event.update_time, state.desc, event.comment))
        return trans.fill_template( '/sample/sample_events.mako', 
                                    events_list=events_list,
                                    sample_name=sample.name,
                                    request=trans.app.model.Request.get(sample.request_id).name)

            
    
    
