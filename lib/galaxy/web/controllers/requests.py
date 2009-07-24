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
    title = "Sequencing Requests"
    model_class = model.Request
    default_sort_key = "-create_time"
    columns = [
        grids.GridColumn( "Name", key="name",
                          link=( lambda item: iff( item.deleted, None, dict( operation="show_request", id=item.id ) ) ),
                          attach_popup=True ),
        grids.GridColumn( "Description", key='desc'),
        grids.GridColumn( "Sample(s)", method='number_of_samples', 
                          link=( lambda item: iff( item.deleted, None, dict( operation="show_request", id=item.id ) ) ), ),
        grids.GridColumn( "Type", key="request_type_id", method='get_request_type'),
        grids.GridColumn( "Last update", key="update_time", format=time_ago ),
        grids.GridColumn( "Submitted", method='submitted'),
    ]
    operations = [
#        grids.GridOperation( "Edit", allow_multiple=False, condition=( lambda item: not item.deleted )  ),
        grids.GridOperation( "Submit", allow_multiple=False, condition=( lambda item: not item.submitted )  )
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
        return str(len(request.samples))
    def submitted(self, trans, request):
        if request.submitted:
            return 'Yes'
        return 'No'
    


class Requests( BaseController ):
    request_grid = RequestsListGrid()

    @web.expose
    def index( self, trans ):
        return trans.fill_template( "requests/index.mako" )
    
    def get_authorized_libs(self, trans):
        all_libraries = trans.app.model.Library.filter(trans.app.model.Library.table.c.deleted == False).order_by(trans.app.model.Library.name).all()
        authorized_libraries = []
        for library in all_libraries:
            if trans.app.security_agent.allow_action(trans.user, trans.app.security_agent.permitted_actions.LIBRARY_ADD, library_item=library) \
                or trans.app.security_agent.allow_action(trans.user, trans.app.security_agent.permitted_actions.LIBRARY_MODIFY, library_item=library):
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
                return self.__show_request(trans, id, kwargs.get('add_sample', False))
            elif operation == "submit":
                id = trans.security.decode_id(kwargs['id'])
                return self.__submit(trans, id)
        # Render the list view
        return self.request_grid( trans, template='/requests/grid.mako', **kwargs )
    
    def __show_request(self, trans, id, add_sample=False):
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
        if add_sample:
            self.current_samples.append(['Sample_%i' % (len(self.current_samples)+1),['' for field in request.type.sample_form.fields]])
        # selectfield of all samples
        copy_list = SelectField('copy_sample')
        copy_list.add_option('None', -1, selected=True)
        for i, s in enumerate(self.current_samples):
            copy_list.add_option(i+1, i)
        self.details_state = 'Show request details'
        return trans.fill_template( '/requests/show_request.mako',
                                    request=request,
                                    request_details=self.request_details(trans, id),
                                    current_samples = self.current_samples,
                                    sample_copy=copy_list, details_state=self.details_state)
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
        return request_details   
    
    def __update_samples(self, request, **kwd):
        params = util.Params( kwd )
        num_samples = len(self.current_samples)
        self.current_samples = []
        for s in request.samples:
            self.current_samples.append([s.name, s.values.content])
        for index in range(num_samples-len(request.samples)):
            sample_index = index + len(request.samples)
            sample_name = util.restore_text( params.get( 'sample_%i_name' % sample_index, ''  ) )
            sample_values = []
            for field_index in range(len(request.type.sample_form.fields)):
                sample_values.append(util.restore_text( params.get( 'sample_%i_field_%i' % (sample_index, field_index), ''  ) ))
            self.current_samples.append([sample_name, sample_values])
    @web.expose
    def show_request(self, trans, **kwd):
        params = util.Params( kwd )
        msg = util.restore_text( params.get( 'msg', ''  ) )
        messagetype = params.get( 'messagetype', 'done' )
        try:
            request = trans.app.model.Request.get(int(params.get('request_id', None)))
        except:
            return trans.response.send_redirect( web.url_for( controller='requests',
                                                              action='list',
                                                              status='error',
                                                              message="Invalid request ID",
                                                              **kwd) )
        if params.get('add_sample_button', False) == 'Add New':
            # save the all (saved+unsaved) sample info in 'current_samples'
            self.__update_samples(request, **kwd)
            # add an empty or filled sample
            # if the user has selected a sample no. to copy then copy the contents 
            # of the src sample to the new sample else an empty sample
            src_sample_index = int(params.get( 'copy_sample', -1  ))
            if src_sample_index == -1:
                # empty sample
                self.current_samples.append(['Sample_%i' % (len(self.current_samples)+1),['' for field in request.type.sample_form.fields]])
            else:
                self.current_samples.append([self.current_samples[src_sample_index][0]+'_%i' % (len(self.current_samples)+1),
                                                                  [val for val in self.current_samples[src_sample_index][1]]])
            # selectfield of all samples
            copy_list = SelectField('copy_sample')
            copy_list.add_option('None', -1, selected=True)  
            for i, s in enumerate(self.current_samples):
                copy_list.add_option(i+1, i)    
            return trans.fill_template( '/requests/show_request.mako',
                                        request=request,
                                        request_details=self.request_details(trans, request.id),
                                        current_samples = self.current_samples,
                                        sample_copy=copy_list, details_state=self.details_state)
        if params.get('save_samples_button', False) == 'Save':
            # update current_samples
            self.__update_samples(request, **kwd)
            # check for duplicate sample names
            msg = ''
            for index in range(len(self.current_samples)-len(request.samples)):
                sample_index = index + len(request.samples)
                sample_name = self.current_samples[sample_index][0]
                if not sample_name.strip():
                    msg = 'Please enter the name of sample number %i' % sample_index
                    break
                count = 0
                for i in range(len(self.current_samples)):
                    if sample_name == self.current_samples[i][0]:
                        count = count + 1
                if count > 1: 
                    msg = "This request has <b>%i</b> samples with the name <b>%s</b>.\nSamples belonging to a request must have unique names." % (count, sample_name)
                    break
            if msg:
                copy_list = SelectField('copy_sample')
                copy_list.add_option('None', -1, selected=True)  
                for i, s in enumerate(self.current_samples):
                    copy_list.add_option(i+1, i)    
                return trans.fill_template( '/requests/show_request.mako',
                                            request=request,
                                            request_details=self.request_details(trans, request.id),
                                            current_samples = self.current_samples,
                                            sample_copy=copy_list, details_state=self.details_state,
                                            messagetype='error', msg=msg)
            # save all the new/unsaved samples entered by the user
            for index in range(len(self.current_samples)-len(request.samples)):
                sample_index = index + len(request.samples)
                sample_name = util.restore_text( params.get( 'sample_%i_name' % sample_index, ''  ) )
                sample_values = []
                for field_index in range(len(request.type.sample_form.fields)):
                    sample_values.append(util.restore_text( params.get( 'sample_%i_field_%i' % (sample_index, field_index), ''  ) ))
                form_values = trans.app.model.FormValues(request.type.sample_form, sample_values)
                form_values.flush()                    
                s = trans.app.model.Sample(sample_name, '', request, form_values)
                s.flush()
                # set the initial state            
                state = s.request.type.states[0]
                event = trans.app.model.SampleEvent(s, state)
                event.flush()
            return trans.response.send_redirect( web.url_for( controller='requests',
                                                          action='list',
                                                          operation='show_request',
                                                          id=trans.security.encode_id(request.id)) )
    @web.expose
    def delete_sample(self, trans, **kwd):
        params = util.Params( kwd )
        msg = util.restore_text( params.get( 'msg', ''  ) )
        messagetype = params.get( 'messagetype', 'done' )
        request = trans.app.model.Request.get(int(params.get('request_id', 0)))
        sample_index = int(params.get('sample_id', 0))
        sample_name = self.current_samples[sample_index][0]
        s = request.has_sample(sample_name)
        if s:
            s.delete()
            s.flush()
            request.flush()
        del self.current_samples[sample_index]
        copy_list = SelectField('copy_sample')
        copy_list.add_option('None', -1, selected=True)  
        for i, s in enumerate(self.current_samples):
            copy_list.add_option(i+1, i)    
        return trans.fill_template( '/requests/show_request.mako',
                                    request=request,
                                    request_details=self.request_details(trans, request.id),
                                    current_samples = self.current_samples,
                                    sample_copy=copy_list, details_state=self.details_state)
    @web.expose
    def toggle_request_details(self, trans, **kwd):
        params = util.Params( kwd )
        msg = util.restore_text( params.get( 'msg', ''  ) )
        messagetype = params.get( 'messagetype', 'done' )
        request = trans.app.model.Request.get(int(params.get('request_id', 0)))
        if self.details_state == 'Show request details':
             self.details_state = 'Hide request details'
        elif self.details_state == 'Hide request details':
             self.details_state = 'Show request details'
        copy_list = SelectField('copy_sample')
        copy_list.add_option('None', -1, selected=True)  
        for i, s in enumerate(self.current_samples):
            copy_list.add_option(i+1, i)    
        return trans.fill_template( '/requests/show_request.mako',
                                    request=request,
                                    request_details=self.request_details(trans, request.id),
                                    current_samples = self.current_samples,
                                    sample_copy=copy_list, details_state=self.details_state)
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
                                  [('name','Name')], 
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
            if params.get('create_request_button', False) == 'Save':
                return trans.response.send_redirect( web.url_for( controller='requests',
                                                                  action='list',
                                                                  msg=msg ,
                                                                  messagetype='done') )
            elif params.get('create_request_samples_button', False) == 'Add samples':
                new_kwd = {}
                new_kwd['id'] = trans.security.encode_id(request.id)
                new_kwd['operation'] = 'show_request'
                new_kwd['add_sample'] = True
                return trans.response.send_redirect( web.url_for( controller='requests',
                                                                  action='list',
                                                                  msg=msg ,
                                                                  messagetype='done',
                                                                  **new_kwd) )
                
    def __validate(self, trans, main_fields=[], form_fields=[], **kwd):
        '''
        Validates the request entered by the user 
        '''
        params = util.Params( kwd )
        for field, field_name in main_fields:
            if not util.restore_text(params.get(field, '')):
                return 'Please enter the <b>%s</b> of the request' % field_name
        # check rest of the fields of the form
        for index, field in enumerate(form_fields):
            if not util.restore_text(params.get('field_%i' % index, None)) \
               and field['required'] == 'required':
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
        try:
            library_id = int(util.restore_text(params.get('library_id', None)))
        except:
            msg = "Sequencing request could not be saved. Invalid library"
            return trans.response.send_redirect( web.url_for( controller='requests',
                                                              action='list',
                                                              status='error',
                                                              message=msg,
                                                              **kwd) )
        values = []
        for index, field in enumerate(request_type.request_form.fields):
            values.append(util.restore_text(params.get('field_%i' % index, '')))
        if not request_id:
            form_values = trans.app.model.FormValues(request_type.request_form, values)
            form_values.flush()
            request = trans.app.model.Request(name, desc, request_type, 
                                              trans.user, form_values,
                                              trans.app.model.Library.get(library_id),
                                              submitted=False)
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
        libraries = self.get_authorized_libs(trans)
        if libraries:
            libui = self.__library_ui(libraries, **kwd)
            widgets.append(libui)
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
        
    def __library_ui(self, libraries, **kwd):
        params = util.Params( kwd )
        create_lib_str = 'Create a new library'
        value = int(params.get( 'library_id', 0  ))
        if not value: # if no library previously selected
            # show the selectbox with 'create a new library' option selected        
            lib_list = SelectField('library_id', refresh_on_change=True, 
                                   refresh_on_change_values=[create_lib_str])
            #lib_list.add_option(create_lib_str, 0, selected=True)
            for lib in libraries:
                lib_list.add_option(lib.name, lib.id)
            widget = dict(label='Library', 
                          widget=lib_list, 
                          helptext='Associated library where the resultant \
                                    dataset will be stored.')
        else: # if some library previously selected
            # show the selectbox with some library selected        
            lib_list = SelectField('library_id', refresh_on_change=True, 
                                   refresh_on_change_values=[create_lib_str])
            #lib_list.add_option(create_lib_str, 0)
            for lib in libraries:
                if value == lib.id:
                    lib_list.add_option(lib.name, lib.id, selected=True)
                else:
                    lib_list.add_option(lib.name, lib.id)
            widget = dict(label='Library', 
                          widget=lib_list, 
                          helptext='Associated library where the resultant \
                                    dataset will be stored.')
        return widget
    
    def __submit(self, trans, id):
        try:
            request = trans.app.model.Request.get(id)
        except:
            msg = "Invalid request ID"
            log.warn( msg )
            return trans.response.send_redirect( web.url_for( controller='requests',
                                                              action='list',
                                                              status='error',
                                                              message=msg,
                                                              **kwd) )
        # get the new state
        new_state = request.type.states[1]
        for s in request.samples:
            event = trans.app.model.SampleEvent(s, new_state, 'Samples submitted to the system')
            event.flush()
        # change request's submitted field
        request.submitted = True
        request.flush()
        kwd = {}
        kwd['id'] = trans.security.encode_id(request.id)
        return trans.response.send_redirect( web.url_for( controller='requests',
                                                          action='list',
                                                          **kwd) )
    @web.expose
    def submit_request(self, trans, **kwd):
        params = util.Params( kwd )
        try:
            id = int(params.get('id', False))
            request = trans.app.model.Request.get(id)
        except:
            msg = "Invalid request ID"
            log.warn( msg )
            return trans.response.send_redirect( web.url_for( controller='requests',
                                                              action='list',
                                                              status='error',
                                                              message=msg,
                                                              **kwd) )
        # get the new state
        new_state = request.type.states[1]
        for s in request.samples:
            event = trans.app.model.SampleEvent(s, new_state, 'Samples submitted to the system')
            event.flush()
        # change request's submitted field
        request.submitted = True
        request.flush()
        ## TODO
        kwd['id'] = trans.security.encode_id(request.id)
        return trans.response.send_redirect( web.url_for( controller='requests',
                                                          action='list',
                                                          **kwd) )
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
            if field['required'] == 'required':
                req = 'Required'
            else:
                req = 'Optional'
            widgets.append(dict(label=field['label'],
                                widget=fw,
                                helptext=field['helptext']+' ('+req+')'))
        return widgets
    @web.expose
    def show_events(self, trans, **kwd):
        params = util.Params( kwd )
        try:
            sample_id = int(params.get('sample_id', False))
            sample = trans.app.model.Sample.get(sample_id)
        except:
            msg = "Invalid sample ID"
            return trans.response.send_redirect( web.url_for( controller='requests',
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
        return trans.fill_template( '/sample/sample_events.mako', 
                                    events_list=events_list,
                                    sample_name=sample.name,
                                    request=sample.request)

            
    
    
