from galaxy.web.base.controller import *
from galaxy.web.framework.helpers import time_ago, iff, grids
from galaxy.model.orm import *
from galaxy.datatypes import sniff
from galaxy import util
from galaxy.util.streamball import StreamBall
import logging, tempfile, zipfile, tarfile, os, sys
from galaxy.web.form_builder import * 
from datetime import datetime, timedelta
from galaxy.web.controllers.forms import get_all_forms

log = logging.getLogger( __name__ )

class RequestsListGrid( grids.Grid ):
    title = "Sequencing Requests"
    template = "admin/requests/grid.mako"
    model_class = model.Request
    default_sort_key = "-create_time"
    show_filter = model.Request.states.SUBMITTED
    columns = [
        grids.GridColumn( "Name", key="name",
                          link=( lambda item: iff( item.deleted, None, dict( operation="show_request", id=item.id ) ) ),
                          attach_popup=True ),
        grids.GridColumn( "Description", key="desc"),
        grids.GridColumn( "Sample(s)", method='number_of_samples',
                          link=( lambda item: iff( item.deleted, None, dict( operation="show_request", id=item.id ) ) ), ),
        grids.GridColumn( "Type", key="request_type_id", method='get_request_type'),
        grids.GridColumn( "Last update", key="update_time", format=time_ago ),
        grids.GridColumn( "State", key='state'),
        grids.GridColumn( "User", key="user_id", method='get_user')
        
    ]
    operations = [
        grids.GridOperation( "Submit", allow_multiple=False, condition=( lambda item: not item.deleted and item.unsubmitted() and item.samples )  ),
        grids.GridOperation( "Edit", allow_multiple=False, condition=( lambda item: not item.deleted )  ),
        grids.GridOperation( "Delete", allow_multiple=False, condition=( lambda item: not item.deleted and item.unsubmitted() )  ),
        grids.GridOperation( "Undelete", condition=( lambda item: item.deleted ) ),    
    ]
    standard_filters = [
        grids.GridColumnFilter( model.Request.states.UNSUBMITTED, 
                                args=dict( state=model.Request.states.UNSUBMITTED, deleted=False ) ),
        grids.GridColumnFilter( model.Request.states.SUBMITTED, 
                                args=dict( state=model.Request.states.SUBMITTED, deleted=False ) ),
        grids.GridColumnFilter( model.Request.states.COMPLETE, args=dict( state=model.Request.states.COMPLETE, deleted=False ) ),
        grids.GridColumnFilter( "Deleted", args=dict( deleted=True ) ),
        grids.GridColumnFilter( "All", args=dict( deleted=False ) )
    ]
    def get_user(self, trans, request):
        return trans.app.model.User.get(request.user_id).email
    def get_current_item( self, trans ):
        return None
    def get_request_type(self, trans, request):
        request_type = trans.app.model.RequestType.get(request.request_type_id)
        return request_type.name
    def number_of_samples(self, trans, request):
        return str(len(request.samples))
    
class Requests( BaseController ):
    request_grid = RequestsListGrid()
    
    @web.expose
    @web.require_admin
    def index( self, trans ):
        return trans.fill_template( "/admin/requests/index.mako" )
    @web.expose
    @web.require_admin
    def list( self, trans, **kwargs ):
        '''
        List all request made by the current user
        '''
        message = util.restore_text( kwargs.get( 'message', ''  ) )
        status = kwargs.get( 'status', 'done' )
        self.request_grid.default_filter = dict(state=trans.app.model.Request.states.SUBMITTED, 
                                                deleted=False)
        if 'operation' in kwargs:
            operation = kwargs['operation'].lower()
            if operation == "show_request":
                id = trans.security.decode_id(kwargs['id'])
                return self.__show_request(trans, id, status, message)
            elif operation == "submit":
                id = trans.security.decode_id(kwargs['id'])
                return self.__submit(trans, id)
            elif operation == "edit":
                id = trans.security.decode_id(kwargs['id'])
                return self.__edit_request(trans, id)
            elif operation == "delete":
                id = trans.security.decode_id(kwargs['id'])
                return self.__delete_request(trans, id)
            elif operation == "undelete":
                id = trans.security.decode_id(kwargs['id'])
                return self.__undelete_request(trans, id)
        if 'show_filter' in kwargs.keys():
            if kwargs['show_filter'] == 'All':
                self.request_grid.default_filter = {}
            elif kwargs['show_filter'] == 'Deleted':
                self.request_grid.default_filter = dict(deleted=True)
            else:
                self.request_grid.default_filter = dict(state=kwargs['show_filter'], deleted=False)   
        self.request_grid.show_filter = kwargs.get('show_filter', trans.app.model.Request.states.SUBMITTED)
        # Render the list view
        return self.request_grid( trans, **kwargs )
    @web.expose
    @web.require_admin
    def edit(self, trans, **kwd):
        params = util.Params( kwd )
        msg = util.restore_text( params.get( 'msg', ''  ) )
        messagetype = params.get( 'messagetype', 'done' )
        try:
            request = trans.app.model.Request.get(int(params.get('request_id', None)))
        except:
            return trans.response.send_redirect( web.url_for( controller='requests_admin',
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
                    return trans.response.send_redirect( web.url_for( controller='requests_admin',
                                                                      action='edit',
                                                                      **kwd) )
                request = self.__save_request(trans, request, **kwd)
                msg = 'The changes made to the request named %s has been saved' % request.name
                if params.get('save_changes_request_button', False) == 'Save changes':
                    return trans.response.send_redirect( web.url_for( controller='requests_admin',
                                                                      action='list',
                                                                      message=msg ,
                                                                      status='done') )
                elif params.get('edit_samples_button', False) == 'Edit samples':
                    new_kwd = {}
                    new_kwd['request_id'] = request.id
                    new_kwd['edit_samples_button'] = 'Edit samples'
                    return trans.response.send_redirect( web.url_for( controller='requests_admin',
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
            return trans.response.send_redirect( web.url_for( controller='requests_admin',
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
        libui = self.__library_ui(trans, request.user, request, **kwd)
        widgets = widgets + libui
        widgets = widgets + request.type.request_form.get_widgets( request.user, request.values.content, **kwd )
        return trans.fill_template( '/admin/requests/edit_request.mako',
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
            return trans.response.send_redirect( web.url_for( controller='requests_admin',
                                                              action='list',
                                                              status='error',
                                                              message=msg,
                                                              **kwd) )
        # change request's submitted field
        if not request.unsubmitted():
            return trans.response.send_redirect( web.url_for( controller='requests_admin',
                                                              action='list',
                                                              status='error',
                                                              message='This request cannot be deleted as it is already been submitted',
                                                              **kwd) )
        request.deleted = True
        request.flush()
        kwd = {}
        kwd['id'] = trans.security.encode_id(request.id)
        return trans.response.send_redirect( web.url_for( controller='requests_admin',
                                                          action='list',
                                                          show_filter=trans.app.model.Request.states.UNSUBMITTED,
                                                          status='done',
                                                          message='The request <b>%s</b> has been deleted.' % request.name,
                                                          **kwd) )
    def __undelete_request(self, trans, id):
        try:
            request = trans.app.model.Request.get(id)
        except:
            msg = "Invalid request ID"
            log.warn( msg )
            return trans.response.send_redirect( web.url_for( controller='requests_admin',
                                                              action='list',
                                                              status='error',
                                                              message=msg,
                                                              **kwd) )
        # change request's submitted field
        request.deleted = False
        request.flush()
        kwd = {}
        kwd['id'] = trans.security.encode_id(request.id)
        return trans.response.send_redirect( web.url_for( controller='requests_admin',
                                                          action='list',
                                                          show_filter=trans.app.model.Request.states.UNSUBMITTED,
                                                          status='done',
                                                          message='The request <b>%s</b> has been undeleted.' % request.name,                                                          
                                                          **kwd) )
    def __submit(self, trans, id):
        try:
            request = trans.app.model.Request.get(id)
        except:
            msg = "Invalid request ID"
            log.warn( msg )
            return trans.response.send_redirect( web.url_for( controller='requests_admin',
                                                              action='list',
                                                              status='error',
                                                              message=msg,
                                                              **kwd) )
        msg = self.__validate(trans, request)
        if msg:
            return trans.response.send_redirect( web.url_for( controller='requests_admin',
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
        kwd['status'] = 'done'
        kwd['message'] = 'The request <b>%s</b> has been submitted.' % request.name
        return trans.response.send_redirect( web.url_for( controller='requests_admin',
                                                          action='list',
                                                          show_filter=trans.app.model.Request.states.SUBMITTED,
                                                          **kwd) )
    @web.expose
    @web.require_admin
    def submit_request(self, trans, **kwd):
        params = util.Params( kwd )
        try:
            id = int(params.get('id', False))
            request = trans.app.model.Request.get(id)
        except:
            msg = "Invalid request ID"
            log.warn( msg )
            return trans.response.send_redirect( web.url_for( controller='requests_admin',
                                                              action='list',
                                                              status='error',
                                                              message=msg,
                                                              **kwd) )
        msg = self.__validate(trans, request)
        if msg:
            return trans.response.send_redirect( web.url_for( controller='requests_admin',
                                                              action='edit',
                                                              messagetype='error',
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
        kwd['id'] = trans.security.encode_id(request.id)
        kwd['status'] = 'done'
        kwd['message'] = 'The request <b>%s</b> has been submitted.' % request.name
        return trans.response.send_redirect( web.url_for( controller='requests_admin',
                                                          action='list',
                                                          show_filter=trans.app.model.Request.states.SUBMITTED,
                                                          **kwd) )
    def __copy_sample(self):
        copy_list = SelectField('copy_sample')
        copy_list.add_option('None', -1, selected=True)  
        for i, s in enumerate(self.current_samples):
            copy_list.add_option(s[0], i)
        return copy_list   
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
    def __show_request(self, trans, id, messagetype, msg):
        try:
            request = trans.app.model.Request.get(id)
        except:
            return trans.response.send_redirect( web.url_for( controller='requests_admin',
                                                              action='list',
                                                              status='error',
                                                              message="Invalid request ID",
                                                              **kwd) )
        self.current_samples = []
        self.edit_mode = False
        for s in request.samples:
            self.current_samples.append([s.name, s.values.content])
        self.details_state = 'Show request details'
        return trans.fill_template( '/admin/requests/show_request.mako',
                                    request=request,
                                    request_details=self.request_details(trans, id),
                                    current_samples = self.current_samples, 
                                    sample_copy=self.__copy_sample(), 
                                    details_state=self.details_state,
                                    edit_mode=self.edit_mode,
                                    msg=msg, messagetype=messagetype)
    @web.expose
    @web.require_admin
    def show_request(self, trans, **kwd):
        params = util.Params( kwd )
        msg = util.restore_text( params.get( 'msg', ''  ) )
        messagetype = params.get( 'messagetype', 'done' )
        try:
            request = trans.app.model.Request.get(int(params.get('request_id', None)))
        except:
            return trans.response.send_redirect( web.url_for( controller='requests_admin',
                                                              action='list',
                                                              status='error',
                                                              message="Invalid request ID",
                                                              **kwd) )
        if params.get('import_samples_button', False) == 'Import samples':
            try:
                file_obj = params.get('file_data', '')
                import csv
                reader = csv.reader(file_obj.file)
                for row in reader:
                    self.current_samples.append([row[0], row[1:]])  
                return trans.fill_template( '/admin/requests/show_request.mako',
                                            request=request,
                                            request_details=self.request_details(trans, request.id),
                                            current_samples=self.current_samples,
                                            sample_copy=self.__copy_sample(), 
                                            details_state=self.details_state,
                                            edit_mode=self.edit_mode)
            except:
                return trans.response.send_redirect( web.url_for( controller='requests_admin',
                                                                  action='list',
                                                                  status='error',
                                                                  operation='show_request',
                                                                  id=trans.security.encode_id(request.id),
                                                                  message='Error in importing samples from the given file.',
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
            return trans.fill_template( '/admin/requests/show_request.mako',
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
                return trans.fill_template( '/admin/requests/show_request.mako',
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
            return trans.response.send_redirect( web.url_for( controller='requests_admin',
                                                          action='list',
                                                          operation='show_request',
                                                          id=trans.security.encode_id(request.id)) )
        elif params.get('edit_samples_button', False) == 'Edit samples':
            self.edit_mode = True
            return trans.fill_template( '/admin/requests/show_request.mako',
                                        request=request,
                                        request_details=self.request_details(trans, request.id),
                                        current_samples=self.current_samples,
                                        sample_copy=self.__copy_sample(), 
                                        details_state=self.details_state,
                                        edit_mode=self.edit_mode)
        elif params.get('cancel_changes_button', False) == 'Cancel':
            return trans.response.send_redirect( web.url_for( controller='requests_admin',
                                                          action='list',
                                                          operation='show_request',
                                                          id=trans.security.encode_id(request.id)) )

            
    @web.expose
    @web.require_admin
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
        return trans.fill_template( '/admin/requests/show_request.mako',
                                    request=request,
                                    request_details=self.request_details(trans, request.id),
                                    current_samples = self.current_samples,
                                    sample_copy=self.__copy_sample(), 
                                    details_state=self.details_state,
                                    edit_mode=self.edit_mode)

    @web.expose
    @web.require_admin
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
        return trans.fill_template( '/admin/requests/show_request.mako',
                                    request=request,
                                    request_details=self.request_details(trans, request.id),
                                    current_samples = self.current_samples,
                                    sample_copy=copy_list, details_state=self.details_state)
    def request_details(self, trans, id):
        '''
        Shows the request details
        '''
        request = trans.app.model.Request.get(id)
        # list of widgets to be rendered on the request form
        request_details = []
        # main details
        request_details.append(dict(label='User', 
                                    value=str(request.user.email), 
                                    helptext=''))
        request_details.append(dict(label='Description', 
                                    value=request.desc, 
                                    helptext=''))
        request_details.append(dict(label='Type', 
                                    value=request.type.name, 
                                    helptext=''))
        request_details.append(dict(label='State', 
                                    value=request.state, 
                                    helptext=''))
        request_details.append(dict(label='Date created', 
                                    value=request.create_time, 
                                    helptext=''))
        # library associated
        if request.library:
			value=request.library.name
        else:
			value = None
        request_details.append(dict(label='Data library', 
                                    value=value, 
                                    helptext='Data library where the resultant dataset will be stored'))
        # folder associated
        if request.folder:
            value = request.folder.name
        else:
            value = None
        request_details.append( dict( label='Data library folder', 
                                      value=value, 
                                      helptext='Data library folder where the resultant dataset will be stored' ) )

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
    @web.require_admin
    def new(self, trans, **kwd):
        params = util.Params( kwd )
        msg = util.restore_text( params.get( 'msg', ''  ) )
        messagetype = params.get( 'messagetype', 'done' )
        if params.get('select_request_type', False) == 'True':
            return trans.fill_template( '/admin/requests/new_request.mako',
                                        select_request_type=self.__select_request_type(trans, 'none'),                                 
                                        widgets=[],                                   
                                        msg=msg,
                                        messagetype=messagetype)
        elif params.get('create', False) == 'True':
            if params.get('create_request_button', False) == 'Save' \
               or params.get('create_request_samples_button', False) == 'Add samples':
                request_type = trans.app.model.RequestType.get(int(params.select_request_type))
                if not util.restore_text(params.get('name', '')) \
                    or util.restore_text(params.get('select_user', '')) == unicode('none'):
                    msg = 'Please enter the <b>Name</b> of the request and the <b>user</b> on behalf of whom this request will be submitted before saving this request'
                    kwd['create'] = 'True'
                    kwd['messagetype'] = 'error'
                    kwd['msg'] = msg
                    kwd['create_request_button'] = None
                    kwd['create_request_samples_button'] = None
                    return trans.response.send_redirect( web.url_for( controller='requests_admin',
                                                                      action='new',
                                                                      **kwd) )
                request = self.__save_request(trans, None, **kwd)
                msg = 'The new request named %s has been created' % request.name
                if params.get('create_request_button', False) == 'Save':
                    return trans.response.send_redirect( web.url_for( controller='requests_admin',
                                                                      action='list',
                                                                      show_filter=trans.app.model.Request.states.UNSUBMITTED,
                                                                      message=msg ,
                                                                      status='done') )
                elif params.get('create_request_samples_button', False) == 'Add samples':
                    new_kwd = {}
                    new_kwd['id'] = trans.security.encode_id(request.id)
                    new_kwd['operation'] = 'show_request'
                    new_kwd['add_sample'] = True
                    return trans.response.send_redirect( web.url_for( controller='requests_admin',
                                                                      action='list',
                                                                      message=msg ,
                                                                      status='done',
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
            return trans.fill_template( '/admin/requests/new_request.mako',
                                        select_request_type=self.__select_request_type(trans, 'none'),                                 
                                        widgets=[],                                   
                                        msg=msg,
                                        messagetype=messagetype)
        form_values = None
        select_request_type = self.__select_request_type(trans, request_type.id)
        # user
        user_id = params.get( 'select_user', 'none' )
        try:
            user = trans.app.model.User.get(int(user_id))
        except:
            user = None
        # list of widgets to be rendered on the request form
        widgets = []
        widgets.append(dict(label='Select user',
                            widget=self.__select_user(trans, user_id),
                            helptext='The request would be submitted on behalf of this user (Required)'))
        widgets.append(dict(label='Name', 
                            widget=TextField('name', 40, 
                                             util.restore_text( params.get( 'name', ''  ) )), 
                            helptext='(Required)'))
        widgets.append(dict(label='Description', 
                            widget=TextField('desc', 40,
                                             util.restore_text( params.get( 'desc', ''  ) )), 
                            helptext='(Optional)'))
        # libraries selectbox
        libui = self.__library_ui(trans, user, **kwd)
        widgets = widgets + libui
        widgets = widgets + request_type.request_form.get_widgets( user, **kwd )
        return trans.fill_template( '/admin/requests/new_request.mako',
                                    select_request_type=select_request_type,
                                    request_type=request_type,                                    
                                    widgets=widgets,
                                    msg=msg,
                                    messagetype=messagetype)
    def __select_user(self, trans, userid):
        user_ids = ['none']
        for user in trans.app.model.User.query().all():
            if not user.deleted:
                user_ids.append(str(user.id))
        select_user = SelectField('select_user', 
                                  refresh_on_change=True, 
                                  refresh_on_change_values=user_ids[1:])
        if userid == 'none':
            select_user.add_option('Select one', 'none', selected=True)
        else:
            select_user.add_option('Select one', 'none')
        for user in trans.app.model.User.query().all():
            if not user.deleted:
                if userid == str(user.id):
                    select_user.add_option(user.email, user.id, selected=True)
                else:
                    select_user.add_option(user.email, user.id)
        return select_user
        
    def __library_ui(self, trans, user, request=None, **kwd):
        """
        Return a list of libraries for which user has the permission
        to perform the LIBRARY_ADD action on any of it's folders
        """
        params = util.Params( kwd )
        lib_id = params.get( 'library_id', 'none'  )
        if not user:
            libraries = {}
        else:
            all_libraries = trans.app.model.Library.filter( trans.app.model.Library.table.c.deleted == False ) \
                                                   .order_by( trans.app.model.Library.name ).all()
            roles = user.all_roles()
            actions_to_check = [ trans.app.security_agent.permitted_actions.LIBRARY_ADD ]
            # The libraries dictionary looks like: { library : '1,2' }, library : '3' }
            # Its keys are the libraries that should be displayed for the current user and whose values are a
            # string of comma-separated folder ids, of the associated folders the should NOT be displayed.
            # The folders that should not be displayed may not be a complete list, but it is ultimately passed
            # to the calling method to keep from re-checking the same folders when the library / folder
            # select lists are rendered.
            #
            # TODO: RC, when you add the folders select list to your request form, take advantage of the hidden_folder_ids
            # so that you do not need to check those same folders yet again when populating the select list.
            #
            libraries = {}
            for library in all_libraries:
                can_show, hidden_folder_ids = trans.app.security_agent.show_library_item( user, roles, library, actions_to_check )
                if can_show:
                    libraries[ library ] = hidden_folder_ids
        lib_id_list = ['new'] + [str(lib.id) for lib in libraries.keys()]
        lib_list = SelectField( 'library_id', refresh_on_change=True, refresh_on_change_values=lib_id_list )
        folders = []
        if request and lib_id == 'none':
            if request.library:
                lib_id = str(request.library.id)
        if lib_id == 'none':
            lib_list.add_option('Select one', 'none', selected=True)
        else:
            lib_list.add_option('Select one', 'none')
        for lib, hidden_folder_ids in libraries.items():
            if str(lib.id) == lib_id:
                lib_list.add_option(lib.name, lib.id, selected=True)
                folders.append( lib.root_folder )
                for f in lib.root_folder.folders:
                    if str(f.id) not in hidden_folder_ids.split(','):
                        folders.append( f )
            else:
                lib_list.add_option(lib.name, lib.id)
            lib_list.refresh_on_change_values.append(lib.id)
        if lib_id == 'new':
            lib_list.add_option('Create a new data library', 'new', selected=True)
        else:
            lib_list.add_option('Create a new data library', 'new')
        lib_widget = dict(label='Data library', 
                          widget=lib_list, 
                          helptext='Data library where the resultant dataset will be stored.')
        if folders:
            if request:
                if request.folder:
                    current_fid = request.folder.id
                else:
                    current_fid = request.library.root_folder.id
            else:
                current_fid = params.get( 'folder_id', 'none'  )
            folder_list = SelectField( 'folder_id')
            for f in folders:
                if str(f.id) == current_fid:
                    folder_list.add_option(f.name, f.id, selected=True)
                else:
                    folder_list.add_option(f.name, f.id)
            folder_widget = dict(label='Folder', 
                                 widget=folder_list, 
                                 helptext='Folder of the selected data library where the resultant dataset will be stored.')
        if lib_id == 'new':
            new_lib = dict(label='Create a new data library', 
                           widget=TextField('new_library_name', 40,
                                     util.restore_text( params.get( 'new_library_name', ''  ) )), 
                           helptext='Enter a name here to request a new data library')
            return [lib_widget, new_lib]
        else:
            if folders:
                return [lib_widget, folder_widget]
            else:
                return [lib_widget]
    def __validate(self, trans, request):
        '''
        Validates the request entered by the user 
        '''
        empty_fields = []
#        if not request.library:
#            empty_fields.append('Library')
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
        if request:
            user = request.user
        else:
            user = trans.app.model.User.get(int(params.get('select_user', '')))
        name = util.restore_text(params.get('name', ''))
        desc = util.restore_text(params.get('desc', ''))
        # library
        try:
            library = trans.app.model.Library.get(int(params.get('library_id', None)))
        except:
            library = None
        try:
            folder = trans.app.model.LibraryFolder.get(int(params.get('folder_id', None)))
        except:
            if library:
                folder = library.root_folder
            else:
                folder = None
        # fields
        values = []
        for index, field in enumerate(request_type.request_form.fields):
            if field['type'] == 'AddressField':
                value = util.restore_text(params.get('field_%i' % index, ''))
                if value == 'new':
                    # save this new address in the list of this user's addresses
                    user_address = trans.app.model.UserAddress( user=user )
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
                                              user, form_values,
                                              library=library, folder=folder, 
                                              state=trans.app.model.Request.states.UNSUBMITTED)
            request.flush()
        else:
            request.name = name
            request.desc = desc
            request.type = request_type
            request.user = user
            request.values = form_values
            request.library = library
            request.folder = folder
            request.flush()
        return request
    @web.expose
    @web.require_admin
    def bar_codes(self, trans, **kwd):
        params = util.Params( kwd )
        msg = util.restore_text( params.get( 'msg', ''  ) )
        messagetype = params.get( 'messagetype', 'done' )
        request_id = params.get( 'request_id', None )
        if request_id:
            request = trans.app.model.Request.get( int( request_id ))
        if not request:
            return trans.response.send_redirect( web.url_for( controller='requests_admin',
                                                              action='list',
                                                              status='error',
                                                              message="Invalid request ID",
                                                              **kwd) )
        widgets = []
        for index, sample in enumerate(request.samples):
            if sample.bar_code:
                bc = sample.bar_code
            else:
                bc = util.restore_text(params.get('sample_%i_bar_code' % index, ''))
            widgets.append(TextField('sample_%i_bar_code' % index, 
                                     40, 
                                     bc))
        return trans.fill_template( '/admin/samples/bar_codes.mako', 
                                    samples_list=[s for s in request.samples],
                                    user=request.user, request=request, widgets=widgets, 
                                    messagetype=messagetype,
                                    msg=msg)
    @web.expose
    @web.require_admin
    def save_bar_codes(self, trans, **kwd):
        params = util.Params( kwd )
        try:
            request = trans.app.model.Request.get(int(params.get('request_id', None)))
        except:
            return trans.response.send_redirect( web.url_for( controller='requests_admin',
                                                              action='list',
                                                              status='error',
                                                              message="Invalid request ID",
                                                              **kwd) )
        # validate 
        # bar codes need to be globally unique
        msg = ''
        for index in range(len(request.samples)):
            bar_code = util.restore_text(params.get('sample_%i_bar_code' % index, ''))
            # check for empty bar code
            if not bar_code.strip():
                msg = 'Please fill the bar code for sample <b>%s</b>.' % request.samples[index].name
                break
            # check all the unsaved bar codes
            count = 0
            for i in range(len(request.samples)):
                if bar_code == util.restore_text(params.get('sample_%i_bar_code' % i, '')):
                    count = count + 1
            if count > 1:
                msg = '''The bar code <b>%s</b> of sample <b>%s</b> already belongs
                         another sample in this request. The sample bar codes must
                         be unique throughout the system''' % \
                         (bar_code, request.samples[index].name)
                break
            # check all the saved bar codes
            all_samples = trans.app.model.Sample.query.all()
            for sample in all_samples:
                if bar_code == sample.bar_code:
                    msg = '''The bar code <b>%s</b> of sample <b>%s</b> already 
                             belongs another sample. The sample bar codes must be 
                             unique throughout the system''' % \
                             (bar_code, request.samples[index].name)
                    break
            if msg:
                break
        if msg:
            widgets = []
            for index, sample in enumerate(request.samples):
                if sample.bar_code:
                    bc = sample.bar_code
                else:
                    bc = util.restore_text(params.get('sample_%i_bar_code' % index, ''))
                widgets.append(TextField('sample_%i_bar_code' % index, 
                                         40, 
                                         util.restore_text(params.get('sample_%i_bar_code' % index, ''))))
            return trans.fill_template( '/admin/samples/bar_codes.mako', 
                                        samples_list=[s for s in request.samples],
                                        user=request.user, request=request, widgets=widgets, messagetype='error',
                                        msg=msg)
        # now save the bar codes
        for index, sample in enumerate(request.samples):
            bar_code = util.restore_text(params.get('sample_%i_bar_code' % index, ''))
            sample.bar_code = bar_code
            sample.flush()
        return trans.response.send_redirect( web.url_for( controller='requests_admin',
                                                          action='bar_codes',
                                                          request_id=request.id,
                                                          msg='Bar codes has been saved for this request',
                                                          messagetype='done'))
                    
    def __set_request_state(self, request):
        # check if all the samples of the current request are in the final state
        complete = True 
        for s in request.samples:
            if s.current_state().id != request.type.states[-1].id:
                complete = False
        if complete:
            request.state = request.states.COMPLETE
        else:
            request.state = request.states.SUBMITTED
        request.flush()
                
        
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
        self.__set_request_state(sample.request)
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
    
    # Request Type Stuff
    @web.expose
    @web.require_admin
    def manage_request_types( self, trans, **kwd ):       
        params = util.Params( kwd )
        msg = util.restore_text( params.get( 'msg', ''  ) )
        messagetype = params.get( 'messagetype', 'done' )
        show_filter = util.restore_text( params.get( 'show_filter', 'Active'  ) )
        forms = get_all_forms(trans, all_versions=True)
        request_types_list = trans.app.model.RequestType.query().all()
        if show_filter == 'All':
            request_types = request_types_list
        elif show_filter == 'Deleted':
            request_types = [rt for rt in request_types_list if rt.deleted]
        else:
            request_types = [rt for rt in request_types_list if not rt.deleted]
        return trans.fill_template( '/admin/requests/manage_request_types.mako', 
                                    request_types=request_types,
                                    forms=forms,
                                    show_filter=show_filter,
                                    msg=msg,
                                    messagetype=messagetype )
    @web.expose
    @web.require_admin
    def request_type( self, trans, **kwd ):
        params = util.Params( kwd )
        msg = util.restore_text( params.get( 'msg', ''  ) )
        messagetype = params.get( 'messagetype', 'done' )   
        if params.get( 'create', False ):
            return trans.fill_template( '/admin/requests/create_request_type.mako', 
                                        request_forms=get_all_forms( trans, 
                                                             filter=dict(deleted=False),
                                                             form_type=trans.app.model.FormDefinition.types.REQUEST ),
                                        sample_forms=get_all_forms( trans, 
                                                             filter=dict(deleted=False),
                                                             form_type=trans.app.model.FormDefinition.types.SAMPLE ),
                                        msg=msg,
                                        messagetype=messagetype)
        elif params.get( 'define_states_button', False ):
            return trans.fill_template( '/admin/requests/add_states.mako',
                                        request_type_name=util.restore_text( params.name ),
                                        desc=util.restore_text( params.description ),
                                        num_states=int(util.restore_text( params.num_states )),
                                        request_form_id=int(util.restore_text( params.request_form_id )),
                                        sample_form_id=int(util.restore_text( params.sample_form_id )),
                                        msg=msg,
                                        messagetype=messagetype)            
        elif params.get( 'save_request_type', False ):
            st, msg = self.__save_request_type(trans, **kwd)
            if not st:
                return trans.fill_template( '/admin/requests/create_request_type.mako', 
                                            forms=get_all_forms( trans ),
                                            msg=msg,
                                            messagetype='error')
            return trans.response.send_redirect( web.url_for( controller='requests_admin',
                                                              action='manage_request_types',
                                                              msg='Request type <b>%s</b> has been created' % st.name,
                                                              messagetype='done') )
        elif params.get('view', False):
            rt = trans.app.model.RequestType.get(int(util.restore_text( params.id )))
            ss_list = trans.app.model.SampleState.filter(trans.app.model.SampleState.table.c.request_type_id == rt.id).all()
            return trans.fill_template( '/admin/requests/view_request_type.mako', 
                                        request_type=rt,
                                        forms=get_all_forms( trans ),
                                        states_list=ss_list,
                                        deleted=False,
                                        show_deleted=False,
                                        msg=msg,
                                        messagetype=messagetype )
    def __save_request_type(self, trans, **kwd):
        params = util.Params( kwd )
        num_states = int( util.restore_text( params.get( 'num_states', 0 ) ))
        proceed = True
        for i in range( num_states ):
            if not util.restore_text( params.get( 'state_name_%i' % i, None ) ):
                proceed = False
                break
        if not proceed:
            msg = "All the state name(s) must be completed."
            return None, msg
        rt = trans.app.model.RequestType() 
        rt.name = util.restore_text( params.name ) 
        rt.desc = util.restore_text( params.description ) or ""
        rt.request_form = trans.app.model.FormDefinition.get(int( params.request_form_id ))
        rt.sample_form = trans.app.model.FormDefinition.get(int( params.sample_form_id ))
        rt.flush()
        # set sample states
        ss_list = trans.app.model.SampleState.filter(trans.app.model.SampleState.table.c.request_type_id == rt.id).all()
        for ss in ss_list:
            ss.delete()
            ss.flush()
        for i in range( num_states ):
            name = util.restore_text( params.get( 'state_name_%i' % i, None ))
            desc = util.restore_text( params.get( 'state_desc_%i' % i, None ))
            ss = trans.app.model.SampleState(name, desc, rt) 
            ss.flush()
        msg = "The new request type named '%s' with %s state(s) has been created" % (rt.name, num_states)
        return rt, msg
    @web.expose
    @web.require_admin
    def delete_request_type( self, trans, **kwd ):
        params = util.Params( kwd )
        msg = util.restore_text( params.get( 'msg', ''  ) )
        messagetype = params.get( 'messagetype', 'done' )
        rt = trans.app.model.RequestType.get(int(util.restore_text( params.request_type_id )))
        rt.deleted = True
        rt.flush()
        return trans.response.send_redirect( web.url_for( controller='requests_admin',
                                                          action='manage_request_types',
                                                          msg='Request type <b>%s</b> has been deleted' % rt.name,
                                                          messagetype='done') )
    @web.expose
    @web.require_admin
    def undelete_request_type( self, trans, **kwd ):
        params = util.Params( kwd )
        msg = util.restore_text( params.get( 'msg', ''  ) )
        messagetype = params.get( 'messagetype', 'done' )
        rt = trans.app.model.RequestType.get(int(util.restore_text( params.request_type_id )))
        rt.deleted = False
        rt.flush()
        return trans.response.send_redirect( web.url_for( controller='requests_admin',
                                                          action='manage_request_types',
                                                          msg='Request type <b>%s</b> has been undeleted' % rt.name,
                                                          messagetype='done') )
