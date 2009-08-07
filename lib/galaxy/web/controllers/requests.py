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
    show_filter = model.Request.states.UNSUBMITTED
    columns = [
        grids.GridColumn( "Name", key="name",
                          link=( lambda item: iff( item.deleted, None, dict( operation="show_request", id=item.id ) ) ),
                          attach_popup=True ),
        grids.GridColumn( "Description", key='desc'),
        grids.GridColumn( "Sample(s)", method='number_of_samples', 
                          link=( lambda item: iff( item.deleted, None, dict( operation="show_request", id=item.id ) ) ), ),
        grids.GridColumn( "Type", key="request_type_id", method='get_request_type'),
        grids.GridColumn( "Last update", key="update_time", format=time_ago ),
        grids.GridColumn( "State", key='state'),
    ]
    operations = [
        grids.GridOperation( "Submit", allow_multiple=False, condition=( lambda item: not item.deleted and item.unsubmitted() and item.samples )  ),
        grids.GridOperation( "Edit", allow_multiple=False, condition=( lambda item: not item.deleted and item.unsubmitted() )  ),
        grids.GridOperation( "Delete", allow_multiple=False, condition=( lambda item: not item.deleted and item.unsubmitted() )  ),
        grids.GridOperation( "Undelete", allow_multiple=False, condition=( lambda item: item.deleted )  )

    ]
    standard_filters = [
        grids.GridColumnFilter( model.Request.states.UNSUBMITTED, 
                                args=dict( state=model.Request.states.UNSUBMITTED, deleted=False ) ),
        grids.GridColumnFilter( model.Request.states.SUBMITTED, 
                                args=dict( state=model.Request.states.SUBMITTED, deleted=False ) ),
        grids.GridColumnFilter( model.Request.states.COMPLETE, args=dict( state=model.Request.states.COMPLETE, deleted=False ) ),
        grids.GridColumnFilter( "Deleted", args=dict( deleted=True ) ),
        grids.GridColumnFilter( "All", args={} )
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
    def get_state(self, trans, request):
            return request.state
    


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
        self.request_grid.default_filter = dict(state=trans.app.model.Request.states.UNSUBMITTED, 
                                                deleted=False)
        if 'operation' in kwargs:
            operation = kwargs['operation'].lower()
            if operation == "show_request":
                id = trans.security.decode_id(kwargs['id'])
                return self.__show_request(trans, id, kwargs.get('add_sample', False))
            elif operation == "submit":
                id = trans.security.decode_id(kwargs['id'])
                return self.__submit(trans, id)
            elif operation == "delete":
                id = trans.security.decode_id(kwargs['id'])
                return self.__delete_request(trans, id)
            elif operation == "undelete":
                id = trans.security.decode_id(kwargs['id'])
                return self.__undelete_request(trans, id)
            elif operation == "edit":
                id = trans.security.decode_id(kwargs['id'])
                return self.__edit_request(trans, id)
        if 'show_filter' in kwargs.keys():
            if kwargs['show_filter'] == 'All':
                self.request_grid.default_filter = {}
            elif kwargs['show_filter'] == 'Deleted':
                self.request_grid.default_filter = dict(deleted=True)
            else:
                self.request_grid.default_filter = dict(state=kwargs['show_filter'], deleted=False)
        self.request_grid.show_filter = kwargs.get('show_filter', trans.app.model.Request.states.UNSUBMITTED)
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
        self.edit_mode = False
        for s in request.samples:
            self.current_samples.append([s.name, s.values.content])
        if add_sample:
            self.current_samples.append(['Sample_%i' % (len(self.current_samples)+1),['' for field in request.type.sample_form.fields]])
        self.details_state = 'Show request details'
        return trans.fill_template( '/requests/show_request.mako',
                                    request=request,
                                    request_details=self.request_details(trans, id),
                                    current_samples = self.current_samples,
                                    sample_copy=self.__copy_sample(), 
                                    details_state=self.details_state,
                                    edit_mode=self.edit_mode)
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
        if request.library:
            request_details.append(dict(label='Library', 
                                        value=request.library.name, 
                                        helptext='Associated library where the resultant \
                                                  dataset will be stored'))
        else:
            request_details.append(dict(label='Library', 
                                        value=None, 
                                        helptext='Associated library where the resultant \
                                                  dataset will be stored'))

        # form fields
        for index, field in enumerate(request.type.request_form.fields):
            if field['required']:
                req = 'Required'
            else:
                req = 'Optional'
            if field['type'] == 'AddressField':
                if request.values.content[index]:
                    request_details.append(dict(label=field['label'],
                                                value=trans.app.model.UserAddress.get(int(request.values.content[index])).get_html(),
                                                helptext=field['helptext']+' ('+req+')'))
                else:
                    request_details.append(dict(label=field['label'],
                                                value=None,
                                                helptext=field['helptext']+' ('+req+')'))

            else: 
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
            
    def __copy_sample(self):
        copy_list = SelectField('copy_sample')
        copy_list.add_option('None', -1, selected=True)  
        for i, s in enumerate(self.current_samples):
            copy_list.add_option(s[0], i)
        return copy_list   
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
        if params.get('import_samples_button', False) == 'Import samples':
            import traceback
            try:
                fname = params.get('import_samples', '')
                import csv
                reader = csv.reader(open(fname))
                for row in reader:
                    self.current_samples.append([row[0], row[1:]])  
                return trans.fill_template( '/requests/show_request.mako',
                                            request=request,
                                            request_details=self.request_details(trans, request.id),
                                            current_samples=self.current_samples,
                                            sample_copy=self.__copy_sample(), 
                                            details_state=self.details_state,
                                            edit_mode=self.edit_mode)
            except:
                return trans.response.send_redirect( web.url_for( controller='requests',
                                                                  action='list',
                                                                  status='error',
                                                                  message='Error in importing <b>%s</b> samples file' % fname,
                                                                  **kwd))
        elif params.get('add_sample_button', False) == 'Add New':
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
            return trans.fill_template( '/requests/show_request.mako',
                                        request=request,
                                        request_details=self.request_details(trans, request.id),
                                        current_samples=self.current_samples,
                                        sample_copy=self.__copy_sample(), 
                                        details_state=self.details_state,
                                        edit_mode=self.edit_mode)
        elif params.get('save_samples_button', False) == 'Save':
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
                return trans.fill_template( '/requests/show_request.mako',
                                            request=request,
                                            request_details=self.request_details(trans, request.id),
                                            current_samples = self.current_samples,
                                            sample_copy=self.__copy_sample(), details_state=self.details_state,
                                            messagetype='error', msg=msg)
            # save all the new/unsaved samples entered by the user
            if not self.edit_mode:
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
            else:
                for index in range(len(self.current_samples)):
                    sample_index = index
                    sample_name = self.current_samples[sample_index][0]
                    new_sample_name = util.restore_text( params.get( 'sample_%i_name' % sample_index, ''  ) )
                    sample_values = []
                    for field_index in range(len(request.type.sample_form.fields)):
                        sample_values.append(util.restore_text( params.get( 'sample_%i_field_%i' % (sample_index, field_index), ''  ) ))
                    sample = request.has_sample(sample_name)
                    if sample:
                        form_values = trans.app.model.FormValues.get(sample.values.id)
                        form_values.content = sample_values
                        form_values.flush()
                        sample.name = new_sample_name
                        sample.flush()
            return trans.response.send_redirect( web.url_for( controller='requests',
                                                          action='list',
                                                          operation='show_request',
                                                          id=trans.security.encode_id(request.id)) )
        elif params.get('edit_samples_button', False) == 'Edit samples':
            self.edit_mode = True
            return trans.fill_template( '/requests/show_request.mako',
                                        request=request,
                                        request_details=self.request_details(trans, request.id),
                                        current_samples=self.current_samples,
                                        sample_copy=self.__copy_sample(), 
                                        details_state=self.details_state,
                                        edit_mode=self.edit_mode)
        elif params.get('cancel_changes_button', False) == 'Cancel':
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
        return trans.fill_template( '/requests/show_request.mako',
                                    request=request,
                                    request_details=self.request_details(trans, request.id),
                                    current_samples = self.current_samples,
                                    sample_copy=self.__copy_sample(), 
                                    details_state=self.details_state,
                                    edit_mode=self.edit_mode)
        
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
        return trans.fill_template( '/requests/show_request.mako',
                                    request=request,
                                    request_details=self.request_details(trans, request.id),
                                    current_samples = self.current_samples,
                                    sample_copy=self.__copy_sample(), 
                                    details_state=self.details_state,
                                    edit_mode=self.edit_mode)
    def __select_request_type(self, trans, rtid):
        rt_ids = ['none']
        for rt in trans.app.model.RequestType.query().all():
            if not rt.deleted:
                rt_ids.append(str(rt.id))
        select_reqtype = SelectField('select_request_type', 
                                     refresh_on_change=True, 
                                     refresh_on_change_values=rt_ids[1:])
        if rtid == 'none':
            select_reqtype.add_option('Select one', 'none', selected=True)
        else:
            select_reqtype.add_option('Select one', 'none')
        for rt in trans.app.model.RequestType.query().all():
            if not rt.deleted:
                if rtid == rt.id:
                    select_reqtype.add_option(rt.name, rt.id, selected=True)
                else:
                    select_reqtype.add_option(rt.name, rt.id)
        return select_reqtype
    @web.expose
    def new(self, trans, **kwd):
        params = util.Params( kwd )
        msg = util.restore_text( params.get( 'msg', ''  ) )
        messagetype = params.get( 'messagetype', 'done' )
        if params.get('select_request_type', False) == 'True':
            return trans.fill_template( '/requests/new_request.mako',
                                        select_request_type=self.__select_request_type(trans, 'none'),                                 
                                        widgets=[],                                   
                                        msg=msg,
                                        messagetype=messagetype)
        elif params.get('create', False) == 'True':
            if params.get('create_request_button', False) == 'Save' \
               or params.get('create_request_samples_button', False) == 'Add samples':
                request_type = trans.app.model.RequestType.get(int(params.select_request_type))
                if not util.restore_text(params.get('name', '')):
                    msg = 'Please enter the <b>Name</b> of the request'
                    kwd['create'] = 'True'
                    kwd['messagetype'] = 'error'
                    kwd['msg'] = msg
                    kwd['create_request_button'] = None
                    kwd['create_request_samples_button'] = None
                    return trans.response.send_redirect( web.url_for( controller='requests',
                                                                      action='new',
                                                                      **kwd) )
                request = self.__save_request(trans, None, **kwd)
                msg = 'The new request named %s has been created' % request.name
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
            else:
                return self.__show_request_form(trans, **kwd)
        elif params.get('refresh', False) == 'true':
            return self.__show_request_form(trans, **kwd)
                

    def __show_request_form(self, trans, **kwd):
        params = util.Params( kwd )
        msg = util.restore_text( params.get( 'msg', ''  ) )
        messagetype = params.get( 'messagetype', 'done' )
        try:
            request_type = trans.app.model.RequestType.get(int(params.select_request_type))
        except:
            return trans.fill_template( '/requests/new_request.mako',
                                        select_request_type=self.__select_request_type(trans, 'none'),                                 
                                        widgets=[],                                   
                                        msg=msg,
                                        messagetype=messagetype)
        form_values = None
        select_request_type = self.__select_request_type(trans, request_type.id)
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
        libui = self.__library_ui(libraries, **kwd)
        widgets = widgets + libui
        widgets = self.__create_form(trans, request_type.request_form_id, widgets, 
                                     form_values, **kwd)
        title = 'Add a new request of type: %s' % request_type.name
        return trans.fill_template( '/requests/new_request.mako',
                                    select_request_type=select_request_type,
                                    request_type=request_type,                                    
                                    widgets=widgets,
                                    msg=msg,
                                    messagetype=messagetype)
        
    def __library_ui(self, libraries, request=None, **kwd):
        params = util.Params( kwd )
        lib_id = params.get( 'library_id', 'none'  )
        lib_list = SelectField('library_id', refresh_on_change=True, 
                               refresh_on_change_values=['new'])
        if request and lib_id == 'none':
            if request.library:
                lib_id = str(request.library.id)
        if lib_id == 'none':
            lib_list.add_option('Select one', 'none', selected=True)
        else:
            lib_list.add_option('Select one', 'none')
        for lib in libraries:
            if str(lib.id) == lib_id:
                lib_list.add_option(lib.name, lib.id, selected=True)
            else:
                lib_list.add_option(lib.name, lib.id)
        if lib_id == 'new':
            lib_list.add_option('Create a new library', 'new', selected=True)
        else:
            lib_list.add_option('Create a new library', 'new')
        widget = dict(label='Library', 
                      widget=lib_list, 
                      helptext='Associated library where the resultant \
                                dataset will be stored.')
        if lib_id == 'new':
            new_lib = dict(label='Create a new Library', 
                           widget=TextField('new_library_name', 40,
                                     util.restore_text( params.get( 'new_library_name', ''  ) )), 
                           helptext='Enter a library name here to request a new library')
            return [widget, new_lib]
        else:
            return [widget]
        
    def __create_form(self, trans, form_id, widgets=[], form_values=None, **kwd):
        # TODO: RC - replace this method by importing as follows:
        # from galaxy.web.controllers.forms import get_form_widgets
        params = util.Params( kwd )
        form = trans.app.model.FormDefinition.get(form_id)
        # form fields
        for index, field in enumerate(form.fields):
            # value of the field 
            if field['type'] == 'CheckboxField':
                value = util.restore_text( params.get( 'field_%i' % index, False  ) )
            else:
                value = util.restore_text( params.get( 'field_%i' % index, ''  ) )
            if not value:
                if form_values:
                    value = str(form_values.content[index])
            # create the field
            fw = eval(field['type'])('field_%i' % index)
            if field['type'] == 'TextField':
                fw.set_size(40)
                fw.value = value
            elif field['type'] == 'TextArea':
                fw.set_size(3, 40)
                fw.value = value
            elif field['type'] == 'AddressField':
                fw.user = trans.user
                fw.value = value
                fw.params = params
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
    def __validate(self, trans, request):
        '''
        Validates the request entered by the user 
        '''
        empty_fields = []
        if not request.library:
            empty_fields.append('Library')
        # check rest of the fields of the form
        for index, field in enumerate(request.type.request_form.fields):
            if field['required'] == 'required' and request.values.content[index] in ['', None]:
                empty_fields.append(field['label'])
        if empty_fields:
            msg = 'Fill the following fields of the request <b>%s</b> before submitting<br/>' % request.name
            for ef in empty_fields:
                msg = msg + '<b>' +ef + '</b><br/>'
            return msg
        return None
    def __save_request(self, trans, request=None, **kwd):
        '''
        This method saves a new request if request_id is None. 
        '''
        params = util.Params( kwd )
        request_type = trans.app.model.RequestType.get(int(params.select_request_type))
        name = util.restore_text(params.get('name', ''))
        desc = util.restore_text(params.get('desc', ''))
        # library
        try:
            library = trans.app.model.Library.get(int(params.get('library_id', None)))
        except:
            library = None
        # fields
        values = []
        for index, field in enumerate(request_type.request_form.fields):
            if field['type'] == 'AddressField':
                value = util.restore_text(params.get('field_%i' % index, ''))
                if value == 'new':
                    # save this new address in the list of this user's addresses
                    user_address = trans.app.model.UserAddress( user=trans.user )
                    user_address.desc = util.restore_text(params.get('field_%i_short_desc' % index, ''))
                    user_address.name = util.restore_text(params.get('field_%i_name' % index, ''))
                    user_address.institution = util.restore_text(params.get('field_%i_institution' % index, ''))
                    user_address.address = util.restore_text(params.get('field_%i_address1' % index, ''))+' '+util.restore_text(params.get('field_%i_address2' % index, ''))
                    user_address.city = util.restore_text(params.get('field_%i_city' % index, ''))
                    user_address.state = util.restore_text(params.get('field_%i_state' % index, ''))
                    user_address.postal_code = util.restore_text(params.get('field_%i_postal_code' % index, ''))
                    user_address.country = util.restore_text(params.get('field_%i_country' % index, ''))
                    user_address.phone = util.restore_text(params.get('field_%i_phone' % index, ''))
                    user_address.flush()
                    trans.user.refresh()
                    values.append(int(user_address.id))
                elif value == unicode('none'):
                    values.append('')
                else:
                    values.append(int(value))
            else:
                values.append(util.restore_text(params.get('field_%i' % index, '')))
        form_values = trans.app.model.FormValues(request_type.request_form, values)
        form_values.flush()
        if not request:
            request = trans.app.model.Request(name, desc, request_type, 
                                              trans.user, form_values,
                                              library=library, 
                                              state=trans.app.model.Request.states.UNSUBMITTED)
            request.flush()
        else:
            request.name = name
            request.desc = desc
            request.type = request_type
            request.user = trans.user
            request.values = form_values
            request.library = library
            request.state = trans.app.model.Request.states.UNSUBMITTED
            request.flush()
        return request
    @web.expose
    def edit(self, trans, **kwd):
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
        if params.get('show', False) == 'True':
            return self.__edit_request(trans, request.id, **kwd)
        elif params.get('save_changes_request_button', False) == 'Save changes' \
             or params.get('edit_samples_button', False) == 'Edit samples':
                request_type = trans.app.model.RequestType.get(int(params.select_request_type))
                if not util.restore_text(params.get('name', '')):
                    msg = 'Please enter the <b>Name</b> of the request'
                    kwd['messagetype'] = 'error'
                    kwd['msg'] = msg
                    kwd['show'] = 'True'
                    return trans.response.send_redirect( web.url_for( controller='requests',
                                                                      action='edit',
                                                                      **kwd) )
                request = self.__save_request(trans, request, **kwd)
                msg = 'The changes made to the request named %s has been saved' % request.name
                if params.get('save_changes_request_button', False) == 'Save changes':
                    return trans.response.send_redirect( web.url_for( controller='requests',
                                                                      action='list',
                                                                      message=msg ,
                                                                      status='done') )
                elif params.get('edit_samples_button', False) == 'Edit samples':
                    new_kwd = {}
                    new_kwd['request_id'] = request.id
                    new_kwd['edit_samples_button'] = 'Edit samples'
                    return trans.response.send_redirect( web.url_for( controller='requests',
                                                                      action='show_request',
                                                                      msg=msg ,
                                                                      messagetype='done',
                                                                      **new_kwd) )
        elif params.get('refresh', False) == 'true':
            return self.__edit_request(trans, request.id, **kwd)
            
    def __edit_request(self, trans, id, **kwd):
        try:
            request = trans.app.model.Request.get(id)
        except:
            msg = "Invalid request ID"
            log.warn( msg )
            return trans.response.send_redirect( web.url_for( controller='requests',
                                                              action='list',
                                                              status='error',
                                                              message=msg) )
        params = util.Params( kwd )
        msg = util.restore_text( params.get( 'msg', ''  ) )
        messagetype = params.get( 'messagetype', 'done' )
        select_request_type = self.__select_request_type(trans, request.type.id)
        # list of widgets to be rendered on the request form
        widgets = []
        if util.restore_text( params.get( 'name', ''  ) ):
            name = util.restore_text( params.get( 'name', ''  ) )
        else:
            name = request.name
        widgets.append(dict(label='Name', 
                            widget=TextField('name', 40, name), 
                            helptext='(Required)'))
        if util.restore_text( params.get( 'desc', ''  ) ):
            desc = util.restore_text( params.get( 'desc', ''  ) )
        else:
            desc = request.desc
        widgets.append(dict(label='Description', 
                            widget=TextField('desc', 40, desc), 
                            helptext='(Optional)'))
       
        # libraries selectbox
        libraries = self.get_authorized_libs(trans)
        libui = self.__library_ui(libraries, request, **kwd)
        widgets = widgets + libui
        widgets = self.__create_form(trans, request.type.request_form_id, widgets, 
                                     request.values, **kwd)
        return trans.fill_template( '/requests/edit_request.mako',
                                    select_request_type=select_request_type,
                                    request_type=request.type,
                                    request=request,
                                    widgets=widgets,
                                    msg=msg,
                                    messagetype=messagetype)
        return self.__show_request_form(trans)
    def __delete_request(self, trans, id):
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
        # change request's submitted field
        if not request.unsubmitted():
            return trans.response.send_redirect( web.url_for( controller='requests',
                                                              action='list',
                                                              status='error',
                                                              message='This request cannot be deleted as it is already been submitted',
                                                              **kwd) )
        request.deleted = True
        request.flush()
        kwd = {}
        kwd['id'] = trans.security.encode_id(request.id)
        return trans.response.send_redirect( web.url_for( controller='requests',
                                                          action='list',
                                                          **kwd) )
    def __undelete_request(self, trans, id):
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
        # change request's submitted field
        request.deleted = False
        request.flush()
        kwd = {}
        kwd['id'] = trans.security.encode_id(request.id)
        return trans.response.send_redirect( web.url_for( controller='requests',
                                                          action='list',
                                                          **kwd) )
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
        msg = self.__validate(trans, request)
        if msg:
            return trans.response.send_redirect( web.url_for( controller='requests',
                                                              action='edit',
                                                              messagetype = 'error',
                                                              msg=msg,
                                                              request_id=request.id,
                                                              show='True') )
        # get the new state
        new_state = request.type.states[0]
        for s in request.samples:
            event = trans.app.model.SampleEvent(s, new_state, 'Samples submitted to the system')
            event.flush()
        # change request's submitted field
        request.state = request.states.SUBMITTED
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
        msg = self.__validate(trans, request)
        if msg:
            return trans.response.send_redirect( web.url_for( controller='requests',
                                                              action='edit',
                                                              messagetype = 'error',
                                                              msg=msg,
                                                              request_id=request.id,
                                                              show='True') )
        # get the new state
        new_state = request.type.states[0]
        for s in request.samples:
            event = trans.app.model.SampleEvent(s, new_state, 'Samples submitted to the system')
            event.flush()
        # change request's submitted field
        request.state = request.states.SUBMITTED
        request.flush()
        ## TODO
        kwd['id'] = trans.security.encode_id(request.id)
        return trans.response.send_redirect( web.url_for( controller='requests',
                                                          action='list',
                                                          **kwd) )

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

            
    
    
