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
        return request.type.name
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
        curr_state = all_states[len(all_states)-1].state
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
                                    value=request.library.name, 
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
        return trans.fill_template( '/requests/view_request.mako',
                                    request_form_id=request.type.request_form.id, 
                                    request_details=request_details,
                                    request_type=request.type)    
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
            return self.__show_request_form(trans=trans,
                                            request=None, **kwd)
        elif params.get('save', False) == 'True':
            request_type = trans.app.model.RequestType.get(int(params.request_type_id))
            msg = self.__validate(trans, 
                                  [('name','Name'), ('library_id','Library')], 
                                  request_type.request_form.fields, 
                                  **kwd)
            if msg:
                kwd['create'] = 'True'
                return trans.response.send_redirect( web.url_for( controller='requests',
                                                                  action='new',
                                                                  msg=msg,
                                                                  messagetype='error',
                                                                  **kwd) )
            request = self.__save_request(trans, None, **kwd)
            msg = 'The new request named %s has been created' % request.name
            request_type_id = int(util.restore_text( params.request_type_id ))
            return trans.response.send_redirect( web.url_for( controller='requests',
                                                              action='list',
                                                              msg=msg ,
                                                              messagetype='done') )
    def __validate(self, trans, main_fields=[], form_fields=[], **kwd):
        '''
        Validates the request entered by the user 
        '''
        params = util.Params( kwd )
        for field, field_name in main_fields:
            if not util.restore_text(params.get(field, None)):
                return 'Please enter the <b>%s</b> of the request' % field_name
        # check rest of the fields of the form
        for index, field in enumerate(form_fields):
            if not util.restore_text(params.get('field_%i' % index, None)) and field['required']:
                return 'Please enter the <b>%s</b> field of the request' % field['label']
        return None
    def __save_request(self, trans, request_id=None, **kwd):
        '''
        This method saves a new request if request_id is None. 
        '''
        params = util.Params( kwd )
        if not request_id:
            request_type = trans.app.model.RequestType.get(int(params.request_type_id ))
        else:
            # TODO editing
            pass
        name = util.restore_text(params.get('name', ''))
        desc = util.restore_text(params.get('desc', ''))
        library_id = int(util.restore_text(params.get('library_id', 0)))
        values = []
        for index, field in enumerate(request_type.request_form.fields):
            values.append(util.restore_text(params.get('field_%i' % index, '')))
        if not request_id:
            form_values = trans.app.model.FormValues(request_type.request_form, values)
            form_values.flush()
            request = trans.app.model.Request(name, desc, request_type, 
                                              trans.user, form_values,
                                              trans.app.model.Library.get(library_id))
            request.flush()
        else:
            # TODO editing
            pass
        return request
    def __show_request_form(self, trans, request=None, **kwd):
        params = util.Params( kwd )
        msg = util.restore_text( params.get( 'msg', ''  ) )
        messagetype = params.get( 'messagetype', 'done' )
        request_type = trans.app.model.RequestType.get(int(params.request_type_id))
        if request:
            form_values = request.values
        else:
            form_values = None
        # list of widgets to be rendered on the request form
        widgets = []
        widgets.append(dict(label='Name', 
                            widget=TextField('name', 40, 
                                             util.restore_text( params.get( 'name', ''  ) )), 
                            helptext='(Required)'))
        widgets.append(dict(label='Description', 
                            widget=TextField('desc', 40,
                                             util.restore_text( params.get( 'desc', ''  ) )), 
                            helptext='(Optional)'))
        # libraries selectbox
        value = int(params.get( 'library_id', 0  ))
        libraries = self.get_authorized_libs(trans)
        lib_list = SelectField('library_id')
        for lib in libraries:
            if lib.id == value:
                lib_list.add_option(lib.name, lib.id, selected=True)
            else:
                lib_list.add_option(lib.name, lib.id)
        widgets.append(dict(label='Library', 
                            widget=lib_list, 
                            helptext='Associated library where the resultant \
                                        dataset will be stored'))
        widgets = self.__create_form(trans, request_type.request_form_id, widgets, 
                                     form_values, **kwd)
        title = 'Add a new request of type: %s' % request_type.name
        return trans.fill_template( '/requests/new_request.mako',
                        request_form_id=request_type.request_form_id,
                        request_type=request_type,                                     
                        widgets=widgets,
                        title=title,
                        msg=msg,
                        messagetype=messagetype)
        
    def __create_form(self, trans, form_id, widgets=[], form_values=None, **kwd):
        params = util.Params( kwd )
        form = trans.app.model.FormDefinition.get(form_id)
        # form fields
        for index, field in enumerate(form.fields):
            # value of the field 
            if field['type'] == 'CheckboxField':
                value = util.restore_text( params.get( 'field_%i' % index, False  ) )
            else:
                value = util.restore_text( params.get( 'field_%i' % index, ''  ) )
            # create the field
            fw = eval(field['type'])('field_%i' % index)
            if field['type'] == 'TextField':
                fw.set_size(40)
                fw.value = value
            elif field['type'] == 'TextArea':
                fw.set_size(3, 40)
                fw.value = value
            elif field['type'] == 'SelectField':
                for option in field['selectlist']:
                    if option == value:
                        fw.add_option(option, option, selected=True)
                    else:
                        fw.add_option(option, option)
            elif field['type'] == 'CheckboxField':
                fw.checked = value
            # require/optional
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
        return self.__show_sample_form(trans, sample=None, **kwd)
        
    def __show_sample_form(self, trans, sample=None, **kwd):
        params = util.Params( kwd )
        msg = util.restore_text( params.get( 'msg', ''  ) )
        messagetype = params.get( 'messagetype', 'done' )
        request = trans.app.model.Request.get(int( params.request_id ))
        if sample:
            form_values = sample.values
        else:
            form_values = None
        # list of widgets to be rendered on the request form
        widgets = []
        widgets.append(dict(label='Name', 
                            widget=TextField('name', 40, 
                                             util.restore_text( params.get( 'name', ''  ) )), 
                            helptext='(Required)'))
        widgets.append(dict(label='Description', 
                            widget=TextField('desc', 40, 
                                             util.restore_text( params.get( 'desc', ''  ) )), 
                            helptext='(Optional)'))
        widgets = self.__create_form(trans, request.type.sample_form_id, widgets, 
                                     form_values, **kwd)
        title = 'Add a new sample to request: %s of type: %s' % (request.name, request.type.name) 
        return trans.fill_template( '/sample/new_sample.mako',
                        sample_form_id=request.type.sample_form_id,
                        request_id=request.id,                                     
                        widgets=widgets,
                        title=title,
                        msg=msg,
                        messagetype=messagetype)
    @web.expose
    def samples(self, trans, **kwd):
        params = util.Params( kwd )
        if params.get('save', False) == 'True':
            request = trans.app.model.Request.get(int(params.request_id ))
            msg = self.__validate(trans, 
                                  [('name','Name')],
                                  request.type.sample_form.fields, 
                                  **kwd)
            if msg:
                return trans.response.send_redirect( web.url_for( controller='requests',
                                                                  action='add_sample',
                                                                  msg=msg,
                                                                  messagetype='error',
                                                                  **kwd) )
            sample = self.__save_sample(trans, sample_id=None, **kwd)
            msg = 'The new sample named %s has been created' % sample.name
            return trans.response.send_redirect( web.url_for( controller='requests',
                                                              action='list',
                                                              operation='samples',
                                                              id=trans.security.encode_id(sample.request_id),
                                                              **kwd) )
    def __save_sample(self, trans, sample_id=None, **kwd):
        params = util.Params( kwd )
        if not sample_id:
            request = trans.app.model.Request.get(int(params.request_id))
        else:
            #TODO editing
            pass
        name = util.restore_text(params.get('name', ''))
        desc = util.restore_text(params.get('desc', ''))
        values = []
        for index, field in enumerate(request.type.sample_form.fields):
            values.append(util.restore_text(params.get('field_%i' % index, '')))
        if not sample_id:
            form_values = trans.app.model.FormValues(request.type.sample_form, values)
            form_values.flush()
            sample = trans.app.model.Sample(name, desc, request, form_values)
            sample.flush()
            # set the initial state            
            state = trans.app.model.SampleState.filter(trans.app.model.SampleState.table.c.request_type_id == request.type.id).first()
            event = trans.app.model.SampleEvent(sample, state)
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
        request = sample.request
        request_type = sample.request.type
        sample_form = sample.request.type.sample_form
        sample_values = sample.values
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
        return trans.fill_template( '/sample/view_sample.mako', 
                                    sample_details=sample_details)
    def show_events(self, trans, sample_id):
        sample = trans.app.model.Sample.get(sample_id)
        events_list = []
        all_events = trans.app.model.SampleEvent.filter(trans.app.model.SampleEvent.table.c.sample_id == sample_id).all()
        all_events.reverse()
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
                                    request=sample.request.name)

            
    
    
