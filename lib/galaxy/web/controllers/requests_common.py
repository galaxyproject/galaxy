from galaxy.web.base.controller import *
from galaxy.web.framework.helpers import time_ago, iff, grids
from galaxy.model.orm import *
from galaxy.datatypes import sniff
from galaxy import model, util
from galaxy.util.streamball import StreamBall
import logging, tempfile, zipfile, tarfile, os, sys, subprocess
from galaxy.web.form_builder import * 
from datetime import datetime, timedelta
from sqlalchemy.sql.expression import func, and_
from sqlalchemy.sql import select
import pexpect
import ConfigParser, threading, time
from amqplib import client_0_8 as amqp
import csv, smtplib, socket
log = logging.getLogger( __name__ )


class RequestsCommon( BaseController, UsesFormDefinitionWidgets ):
    
    @web.json
    def sample_state_updates( self, trans, ids=None, states=None, cntrller=None ):
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
                if sample.current_state().name != state:
                    rval[id] = {
                        "state": sample.current_state().name,
                        "datasets": len(sample.datasets),
                        "html_state": unicode( trans.fill_template( "requests/common/sample_state.mako", sample=sample, cntrller=cntrller ), 'utf-8' ),
                        "html_datasets": unicode( trans.fill_template( "requests/common/sample_datasets.mako", trans=trans, sample=sample, cntrller=cntrller ), 'utf-8' )
                    }
        return rval

    
    @web.expose
    @web.require_login( "create/submit sequencing requests" )
    def new(self, trans, **kwd):
        params = util.Params( kwd )
        cntrller = util.restore_text( params.get( 'cntrller', 'requests'  ) )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        if params.get('select_request_type', False) == 'True':
            return trans.fill_template( '/requests/common/new_request.mako',
                                        cntrller=cntrller,
                                        select_request_type=self.__select_request_type(trans, 'none'),                                 
                                        widgets=[],                                   
                                        message=message,
                                        status=status)
        elif params.get('create_request_button', False) == 'Save' \
           or params.get('create_request_samples_button', False) == 'Add samples':
            request_type = trans.sa_session.query( trans.app.model.RequestType ).get( int( params.select_request_type ) )
            if not util.restore_text(params.get('name', '')) \
                or util.restore_text(params.get('select_user', '')) == unicode('none'):
                message = 'Please enter the <b>Name</b> of the request and the <b>user</b> on behalf of whom this request will be submitted before saving this request'
                kwd['create'] = 'True'
                kwd['status'] = 'error'
                kwd['message'] = message
                kwd['create_request_button'] = None
                kwd['create_request_samples_button'] = None
                return trans.response.send_redirect( web.url_for( controller='requests_common',
                                                                  cntrller=cntrller,
                                                                  action='new',
                                                                  **kwd) )
            request = self.__save_request(trans, None, **kwd)
            message = 'The new request named <b>%s</b> has been created' % request.name
            if params.get('create_request_button', False) == 'Save':
                return trans.response.send_redirect( web.url_for( controller=cntrller,
                                                                  action='list',
                                                                  message=message ,
                                                                  status='done') )
            elif params.get('create_request_samples_button', False) == 'Add samples':
                new_kwd = {}
                new_kwd['id'] = trans.security.encode_id(request.id)
                new_kwd['operation'] = 'show'
                new_kwd['add_sample'] = True
                return trans.response.send_redirect( web.url_for( controller=cntrller,
                                                                  action='list',
                                                                  message=message ,
                                                                  status='done',
                                                                  **new_kwd) )
        elif params.get('refresh', False) == 'true':
            return self.__show_request_form(trans, **kwd)
        
    def __select_request_type(self, trans, rtid):
        requesttype_list = trans.user.accessible_request_types(trans)
        rt_ids = ['none']
        for rt in requesttype_list:
            if not rt.deleted:
                rt_ids.append(str(rt.id))
        select_reqtype = SelectField('select_request_type', 
                                     refresh_on_change=True, 
                                     refresh_on_change_values=rt_ids[1:])
        if rtid == 'none':
            select_reqtype.add_option('Select one', 'none', selected=True)
        else:
            select_reqtype.add_option('Select one', 'none')
        for rt in requesttype_list:
            if not rt.deleted:
                if rtid == rt.id:
                    select_reqtype.add_option(rt.name, rt.id, selected=True)
                else:
                    select_reqtype.add_option(rt.name, rt.id)
        return select_reqtype
    
    def __show_request_form(self, trans, **kwd):
        params = util.Params( kwd )
        cntrller = util.restore_text( params.get( 'cntrller', 'requests'  ) )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        try:
            request_type = trans.sa_session.query( trans.app.model.RequestType ).get( int( params.select_request_type ) )
        except:
            return trans.fill_template( '/requests/common/new_request.mako',
                                        cntrller=cntrller, 
                                        select_request_type=self.__select_request_type(trans, 'none'),                                 
                                        widgets=[],                                   
                                        message=message,
                                        status=status)
        form_values = None
        select_request_type = self.__select_request_type(trans, request_type.id)
        # user
        if cntrller == 'requests_admin' and trans.user_is_admin():
            user_id = params.get( 'select_user', 'none' )
            try:
                user = trans.sa_session.query( trans.app.model.User ).get( int( user_id ) )
            except:
                user = None
        elif cntrller == 'requests':
            user = trans.user
        # list of widgets to be rendered on the request form
        widgets = []
        if cntrller == 'requests_admin' and trans.user_is_admin():
            widgets.append(dict(label='Select user',
                                widget=self.__select_user(trans, user_id),
                                helptext='The request would be submitted on behalf of this user (Required)'))
        widgets.append(dict(label='Name of the Experiment', 
                            widget=TextField('name', 40, 
                                             util.restore_text( params.get( 'name', ''  ) )), 
                            helptext='(Required)'))
        widgets.append(dict(label='Description', 
                            widget=TextField('desc', 40,
                                             util.restore_text( params.get( 'desc', ''  ) )), 
                            helptext='(Optional)'))
        widgets = widgets + request_type.request_form.get_widgets( user, **kwd )
        return trans.fill_template( '/requests/common/new_request.mako',
                                    cntrller=cntrller,
                                    select_request_type=select_request_type,
                                    request_type=request_type,                                    
                                    widgets=widgets,
                                    message=message,
                                    status=status)
    def __select_user(self, trans, userid):
        user_list = trans.sa_session.query( trans.app.model.User )\
                                    .order_by( trans.app.model.User.email.asc() )
        user_ids = ['none']
        for user in user_list:
            if not user.deleted:
                user_ids.append(str(user.id))
        select_user = SelectField('select_user', 
                                  refresh_on_change=True, 
                                  refresh_on_change_values=user_ids[1:])
        if userid == 'none':
            select_user.add_option('Select one', 'none', selected=True)
        else:
            select_user.add_option('Select one', 'none')
        for user in user_list:
            if not user.deleted:
                if userid == str(user.id):
                    select_user.add_option(user.email, user.id, selected=True)
                else:
                    select_user.add_option(user.email, user.id)
        return select_user
    def __save_request(self, trans, request, **kwd):
        '''
        This method saves a new request if request_id is None. 
        '''
        params = util.Params( kwd )
        cntrller = util.restore_text( params.get( 'cntrller', 'requests'  ) )
        if request:
            user = request.user
            request_type = request.type
        else:
            request_type = trans.sa_session.query( trans.app.model.RequestType ).get( int( params.select_request_type ) )
            if cntrller == 'requests_admin' and trans.user_is_admin():
                user = trans.sa_session.query( trans.app.model.User ).get( int( params.get( 'select_user', '' ) ) )
            elif cntrller == 'requests':
                user = trans.user
        name = util.restore_text(params.get('name', ''))
        desc = util.restore_text(params.get('desc', ''))
        notification = dict(email=[user.email], sample_states=[request_type.last_state().id], body='', subject='')
        # fields
        values = []
        for index, field in enumerate(request_type.request_form.fields):
            if field['type'] == 'AddressField':
                value = util.restore_text(params.get('field_%i' % index, ''))
                if value == 'new':
                    # save this new address in the list of this user's addresses
                    user_address = trans.app.model.UserAddress( user=user )
                    self.save_widget_field( trans, user_address, index, **kwd )
                    trans.sa_session.refresh( user )
                    values.append(int(user_address.id))
                elif value == unicode('none'):
                    values.append('')
                else:
                    values.append(int(value))
            elif field['type'] == 'CheckboxField':
                values.append(CheckboxField.is_checked( params.get('field_%i' % index, '') )) 
            else:
                values.append(util.restore_text(params.get('field_%i' % index, '')))
        form_values = trans.app.model.FormValues(request_type.request_form, values)
        trans.sa_session.add( form_values )
        trans.sa_session.flush()
        if not request:
            request = trans.app.model.Request(name, desc, request_type, 
                                              user, form_values, notification)
            trans.sa_session.add( request )
            trans.sa_session.flush()
            trans.sa_session.refresh( request )
            # create an event with state 'New' for this new request
            if request.user.email is not trans.user:
                comments = "Request created by admin (%s) on behalf of %s." % (trans.user.email, request.user.email)
            else:
                comments = "Request created."
            event = trans.app.model.RequestEvent(request, request.states.NEW, comments)
            trans.sa_session.add( event )
            trans.sa_session.flush()
        else:
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
    @web.require_login( "create/submit sequencing requests" )
    def email_settings(self, trans, **kwd):
        params = util.Params( kwd )
        cntrller = util.restore_text( params.get( 'cntrller', 'requests'  ) )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        try:
            request = trans.sa_session.query( trans.app.model.Request ).get( trans.security.decode_id( params.get( 'id', None ) ) )
        except:
            return trans.response.send_redirect( web.url_for( controller=cntrller,
                                                              action='list',
                                                              status='error',
                                                              message="Invalid request ID") )
        email_user = CheckboxField.is_checked( params.get('email_user', '') )
        email_additional = params.get('email_additional', '').split('\r\n')
        if email_user or email_additional:
            emails = []
            if email_user:
                emails.append(request.user.email)
            for e in email_additional:
                emails.append(util.restore_text(e))
            # check if valid email addresses
            invalid = ''
            for e in emails:
                if len( e ) == 0 or "@" not in e or "." not in e:
                    invalid = e
                    break
            if invalid:
                message = "<b>%s</b> is not a valid email address." % invalid
                return trans.response.send_redirect( web.url_for( controller='requests_common',
                                                                  cntrller=cntrller,
                                                                  action='edit',
                                                                  show=True, 
                                                                  id=trans.security.encode_id(request.id),
                                                                  message=message ,
                                                                  status='error' ) )
            else:
                email_states = []
                for i, ss in enumerate(request.type.states):
                    if CheckboxField.is_checked( params.get('sample_state_%i' % ss.id, '') ):
                        email_states.append(ss.id)
                request.notification = dict(email=emails, sample_states=email_states, 
                                            body='', subject='')
                trans.sa_session.flush()
                trans.sa_session.refresh( request )
        message = 'The changes made to the sequencing request has been saved'
        return trans.response.send_redirect( web.url_for( controller='requests_common',
                                                          cntrller=cntrller,
                                                          action='show',
                                                          id=trans.security.encode_id(request.id),
                                                          message=message ,
                                                          status='done') )

        
    @web.expose
    @web.require_login( "create/submit sequencing requests" )
    def edit(self, trans, **kwd):
        params = util.Params( kwd )
        cntrller = util.restore_text( params.get( 'cntrller', 'requests'  ) )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        try:
            request = trans.sa_session.query( trans.app.model.Request ).get( trans.security.decode_id( params.get( 'id', None ) ) )
        except:
            return trans.response.send_redirect( web.url_for( controller=cntrller,
                                                              action='list',
                                                              status='error',
                                                              message="Invalid request ID") )
        if params.get('show', False) == 'True':
            return self.__edit_request(trans, **kwd)
        elif params.get('save_changes_request_button', False) == 'Save' \
             or params.get('edit_samples_button', False) == 'Edit samples':
                if not util.restore_text(params.get('name', '')):
                    message = 'Please enter the <b>Name</b> of the request'
                    kwd['status'] = 'error'
                    kwd['message'] = message
                    kwd['show'] = 'True'
                    return trans.response.send_redirect( web.url_for( controller='requests_common',
                                                                      cntrller=cntrller,
                                                                      action='edit',
                                                                      **kwd) )
                request = self.__save_request(trans, request, **kwd)
                message = 'The changes made to the request named %s has been saved' % request.name
                if params.get('save_changes_request_button', False) == 'Save':
                    return trans.response.send_redirect( web.url_for( controller=cntrller,
                                                                      cntrller=cntrller,
                                                                      action='list',
                                                                      message=message ,
                                                                      status='done') )
                elif params.get('edit_samples_button', False) == 'Edit samples':
                    new_kwd = {}
                    new_kwd['id'] = request.id
                    new_kwd['edit_samples_button'] = 'Edit samples'
                    return trans.response.send_redirect( web.url_for( controller=cntrller,
                                                                      cntrller=cntrller,
                                                                      action='show',
                                                                      message=message ,
                                                                      status='done',
                                                                      **new_kwd) )
        elif params.get('refresh', False) == 'true':
            return self.__edit_request(trans, **kwd)
        
    def __edit_request(self, trans, **kwd):
        try:
            request = trans.sa_session.query( trans.app.model.Request ).get( trans.security.decode_id(kwd['id']) )
        except:
            message = "Invalid request ID"
            log.warn( message )
            return trans.response.send_redirect( web.url_for( controller=cntrller,
                                                              cntrller=cntrller,
                                                              action='list',
                                                              status='error',
                                                              message=message) )
        params = util.Params( kwd )
        cntrller = util.restore_text( params.get( 'cntrller', 'requests'  ) )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        #select_request_type = self.__select_request_type(trans, request.type.id)
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
        widgets = widgets + request.type.request_form.get_widgets( request.user, request.values.content, **kwd )
        return trans.fill_template( 'requests/common/edit_request.mako',
                                    cntrller=cntrller,
                                    #select_request_type=select_request_type,
                                    request_type=request.type,
                                    request=request,
                                    widgets=widgets,
                                    message=message,
                                    status=status)
    def __validate(self, trans, cntrller, request):
        '''
        Validates the request entered by the user 
        '''
        if not request.samples:
            return trans.response.send_redirect( web.url_for( controller=cntrller,
                                                              action='list',
                                                              operation='show',
                                                              message='Please add one or more samples to this request before submitting.',
                                                              status='error',
                                                              id=trans.security.encode_id(request.id)) )
        empty_fields = []
        # check rest of the fields of the form
        for index, field in enumerate(request.type.request_form.fields):
            if field['required'] == 'required' and request.values.content[index] in ['', None]:
                empty_fields.append(field['label'])
        if empty_fields:
            message = 'Fill the following fields of the request <b>%s</b> before submitting<br/>' % request.name
            for ef in empty_fields:
                message = message + '<b>' +ef + '</b><br/>'
            return message
        return None
    @web.expose
    @web.require_login( "create/submit sequencing requests" )
    def submit(self, trans, **kwd):
        params = util.Params( kwd )
        cntrller = util.restore_text( params.get( 'cntrller', 'requests'  ) )
        try:
            request = trans.sa_session.query( trans.app.model.Request ).get( trans.security.decode_id(kwd['id']) )
        except:
            message = "Invalid request ID"
            log.warn( message )
            return trans.response.send_redirect( web.url_for( controller=cntrller,
                                                              action='list',
                                                              status='error',
                                                              message=message,
                                                              **kwd) )
        message = self.__validate(trans, cntrller, request)
        if message:
            return trans.response.send_redirect( web.url_for( controller=cntrller,
                                                              action='list',
                                                              operation='edit',
                                                              status = 'error',
                                                              message=message,
                                                              id=trans.security.encode_id(request.id) ) )
        # change the request state to 'Submitted'
        if request.user.email is not trans.user:
            comments = "Request submitted by admin (%s) on behalf of %s." % (trans.user.email, request.user.email)
        else:
            comments = ""
        event = trans.app.model.RequestEvent(request, request.states.SUBMITTED, comments)
        trans.sa_session.add( event )
        trans.sa_session.flush()
        # change the state of each of the samples of thus request
        new_state = request.type.states[0]
        for s in request.samples:
            event = trans.app.model.SampleEvent(s, new_state, 'Samples created.')
            trans.sa_session.add( event )
        trans.sa_session.add( request )
        trans.sa_session.flush()
        request.send_email_notification(trans, new_state)
        return trans.response.send_redirect( web.url_for( controller=cntrller,
                                                          action='list',
                                                          id=trans.security.encode_id(request.id),
                                                          status='done',
                                                          message='The request <b>%s</b> has been submitted.' % request.name
                                                          ) )
    @web.expose
    @web.require_login( "create/submit sequencing requests" )
    def delete(self, trans, **kwd):
        params = util.Params( kwd )
        cntrller = util.restore_text( params.get( 'cntrller', 'requests'  ) )
        id_list = util.listify( kwd['id'] )
        for id in id_list:
            try:
                request = trans.sa_session.query( trans.app.model.Request ).get( trans.security.decode_id(id) )
            except:
                message = "Invalid request ID"
                log.warn( message )
                return trans.response.send_redirect( web.url_for( controller=cntrller,
                                                                  action='list',
                                                                  status='error',
                                                                  message=message,
                                                                  **kwd) )
            request.deleted = True
            trans.sa_session.add( request )
            # delete all the samples belonging to this request
            for s in request.samples:
                s.deleted = True
                trans.sa_session.add( s )
            trans.sa_session.flush()
        message = '%i request(s) has been deleted.' % len(id_list)
        status = 'done'
        return trans.response.send_redirect( web.url_for( controller=cntrller,
                                                          action='list',
                                                          status=status,
                                                          message=message) )
    @web.expose
    @web.require_login( "create/submit sequencing requests" )
    def undelete(self, trans, **kwd):
        params = util.Params( kwd )
        cntrller = util.restore_text( params.get( 'cntrller', 'requests'  ) )
        id_list = util.listify( kwd['id'] )
        for id in id_list:
            try:
                request = trans.sa_session.query( trans.app.model.Request ).get( trans.security.decode_id(id) )
            except:
                message = "Invalid request ID"
                log.warn( message )
                return trans.response.send_redirect( web.url_for( controller=cntrller,
                                                                  action='list',
                                                                  status='error',
                                                                  message=message,
                                                                  **kwd) )
            request.deleted = False
            trans.sa_session.add( request )
            # undelete all the samples belonging to this request
            for s in request.samples:
                s.deleted = False
                trans.sa_session.add( s )
            trans.sa_session.flush()
        return trans.response.send_redirect( web.url_for( controller=cntrller,
                                                          action='list',
                                                          status='done',
                                                          message='%i request(s) has been undeleted.' % len(id_list) ) )
    @web.expose
    @web.require_login( "create/submit sequencing requests" )
    def events(self, trans, **kwd):
        params = util.Params( kwd )
        cntrller = params.get( 'cntrller', 'requests'  )
        try:
            request = trans.sa_session.query( trans.app.model.Request ).get( trans.security.decode_id(kwd['id']) )
        except:
            message = "Invalid request ID"
            log.warn( message )
            return trans.response.send_redirect( web.url_for( controller=cntrller,
                                                              action='list',
                                                              status='error',
                                                              message=message) )
        events_list = []
        all_events = request.events
        for event in all_events:         
            events_list.append((event.state, time_ago(event.update_time), event.comment))
        return trans.fill_template( '/requests/common/events.mako', 
                                    cntrller=cntrller,
                                    events_list=events_list, request=request)
    @web.expose
    @web.require_admin
    def update_request_state( self, trans, **kwd ):
        params = util.Params( kwd )
        cntrller = params.get( 'cntrller', 'requests'  )
        try:
            request = trans.sa_session.query( trans.app.model.Request ).get( int( params.get( 'request_id', None ) ) )
        except:
            return trans.response.send_redirect( web.url_for( controller='requests_admin',
                                                              action='list',
                                                              status='error',
                                                              message="Invalid request ID",
                                                              **kwd) )
        # check if all the samples of the current request are in the sample state
        common_state = request.common_state()
        if not common_state:
            # if the current request state is complete and one of its samples moved from
            # the final sample state, then move the request state to In-progress
            if request.complete():
                status='done'
                message = "One or more samples' state moved from the final sample state. Now request in '%s' state" % request.states.SUBMITTED
                event = trans.app.model.RequestEvent(request, request.states.SUBMITTED, message)
                trans.sa_session.add( event )
                trans.sa_session.flush()
            else:
                message = ''
                status = 'ok'
            return trans.response.send_redirect( web.url_for( controller=cntrller,
                                                              action='list',
                                                              operation='show',
                                                              id=trans.security.encode_id(request.id),
                                                              status=status,
                                                              message=message ) )
        final_state = False
        if common_state.id == request.type.last_state().id:
            # since all the samples are in the final state, change the request state to 'Complete'
            comments = "All samples of this request are in the last sample state (%s). " % request.type.last_state().name
            state = request.states.COMPLETE
            final_state = True
        else:
            comments = "All samples are in %s state. " % common_state.name
            state = request.states.SUBMITTED
        event = trans.app.model.RequestEvent(request, state, comments)
        trans.sa_session.add( event )
        trans.sa_session.flush()
        # check if an email notification is configured to be sent when the samples 
        # are in this state
        retval = request.send_email_notification(trans, common_state, final_state)
        if retval:
            message = comments + retval
        else:
            message = comments
        return trans.response.send_redirect( web.url_for( controller=cntrller,
                                                          action='list',
                                                          operation='show',
                                                          id=trans.security.encode_id(request.id),
                                                          status='done',
                                                          message=message ) )
    @web.expose
    @web.require_login( "create/submit sequencing requests" )
    def show(self, trans, **kwd):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        cntrller = util.restore_text( params.get( 'cntrller', 'requests'  ) )
        status = params.get( 'status', 'done' )
        add_sample = params.get('add_sample', False)
        try:
            request = trans.sa_session.query( trans.app.model.Request ).get( trans.security.decode_id(kwd['id']) )
        except:
            return trans.response.send_redirect( web.url_for( controller=cntrller,
                                                              action='list',
                                                              status='error',
                                                              message="Invalid request ID") )
        # get all data libraries accessible to this user
        libraries = request.user.accessible_libraries( trans, [ trans.app.security_agent.permitted_actions.LIBRARY_ADD ] )
        current_samples = []
        for i, s in enumerate(request.samples):
            lib_widget, folder_widget = self.__library_widgets(trans, request.user, i, libraries, s, **kwd)
            current_samples.append(dict(name=s.name,
                                        barcode=s.bar_code,
                                        library=s.library,
                                        folder=s.folder,
                                        field_values=s.values.content,
                                        lib_widget=lib_widget,
                                        folder_widget=folder_widget))
        if add_sample:
            lib_widget, folder_widget = self.__library_widgets(trans, request.user, 
                                                               len(current_samples)+1, 
                                                               libraries, None, **kwd)
            current_samples.append(dict(name='Sample_%i' % (len(current_samples)+1),
                                        barcode='',
                                        library=None,
                                        folder=None,
                                        field_values=['' for field in request.type.sample_form.fields],
                                        lib_widget=lib_widget,
                                        folder_widget=folder_widget))
        bulk_lib_ops = self.__library_widgets(trans, request.user, 0, libraries, None, **kwd)
        return trans.fill_template( '/requests/common/show_request.mako',
                                    cntrller=cntrller,
                                    request=request, selected_samples=[],
                                    request_details=self.request_details(trans, request.id),
                                    current_samples=current_samples,
                                    sample_ops=self.__sample_operation_selectbox(trans, request, **kwd),
                                    sample_copy=self.__copy_sample(current_samples), 
                                    details='hide', edit_mode=util.restore_text( params.get( 'edit_mode', 'False'  ) ),
                                    message=message, status=status, bulk_lib_ops=bulk_lib_ops )

    def __update_samples(self, trans, request, **kwd):
        '''
        This method retrieves all the user entered sample information and
        returns an list of all the samples and their field values
        '''
        params = util.Params( kwd )
        details = params.get( 'details', 'hide' )
        edit_mode = params.get( 'edit_mode', 'False' )
        # get all data libraries accessible to this user
        libraries = request.user.accessible_libraries( trans, [ trans.app.security_agent.permitted_actions.LIBRARY_ADD ] )
        
        current_samples = []
        for i, s in enumerate(request.samples):
            lib_widget, folder_widget = self.__library_widgets(trans, request.user, i, libraries, s, **kwd)
            current_samples.append(dict(name=s.name,
                                        barcode=s.bar_code,
                                        library=s.library,
                                        folder=s.folder,
                                        field_values=s.values.content,
                                        lib_widget=lib_widget,
                                        folder_widget=folder_widget))
        if edit_mode == 'False':
            sample_index = len(request.samples) 
        else:
            sample_index = 0
        while True:
            lib_id = None
            folder_id = None
            if params.get( 'sample_%i_name' % sample_index, ''  ):
                # data library
                try:
                    library = trans.sa_session.query( trans.app.model.Library ).get( int( params.get( 'sample_%i_library_id' % sample_index, None ) ) )
                    lib_id = library.id
                except:
                    library = None
                # folder
                try:
                    folder = trans.sa_session.query( trans.app.model.LibraryFolder ).get( int( params.get( 'sample_%i_folder_id' % sample_index, None ) ) )
                    folder_id = folder.id
                except:
                    if library:
                        folder = library.root_folder
                    else:
                        folder = None
                sample_info = dict( name=util.restore_text( params.get( 'sample_%i_name' % sample_index, ''  ) ),
                                    barcode=util.restore_text( params.get( 'sample_%i_barcode' % sample_index, ''  ) ),
                                    library=library,
                                    folder=folder)
                sample_info['field_values'] = []
                for field_index in range(len(request.type.sample_form.fields)):
                    sample_info['field_values'].append(util.restore_text( params.get( 'sample_%i_field_%i' % (sample_index, field_index), ''  ) ))
                if edit_mode == 'False':
                    sample_info['lib_widget'], sample_info['folder_widget'] = self.__library_widgets(trans, request.user, 
                                                                                                     sample_index, libraries, 
                                                                                                     None, lib_id, folder_id, **kwd)
                    current_samples.append(sample_info)
                else:
                    sample_info['lib_widget'], sample_info['folder_widget'] = self.__library_widgets(trans, 
                                                                                                     request.user, 
                                                                                                     sample_index, 
                                                                                                     libraries, 
                                                                                                     request.samples[sample_index], 
                                                                                                     **kwd)
                    current_samples[sample_index] =  sample_info
                sample_index = sample_index + 1
            else:
                break
        return current_samples, details, edit_mode, libraries
    
    def __library_widgets(self, trans, user, sample_index, libraries, sample=None, lib_id=None, folder_id=None, **kwd):
        '''
        This method creates the data library & folder selectbox for creating &
        editing samples. First we get a list of all the libraries accessible to
        the current user and display it in a selectbox. If the user has selected an
        existing library then display all the accessible sub folders of the selected 
        data library. 
        '''
        params = util.Params( kwd )
        # data library selectbox
        if not lib_id:
            lib_id = params.get( "sample_%i_library_id" % sample_index, 'none'  )
        selected_lib = None
        if sample and lib_id == 'none':
            if sample.library:
                lib_id = str(sample.library.id)
                selected_lib = sample.library
        # create data library selectbox with refresh on change enabled
        lib_id_list = ['new'] + [str(lib.id) for lib in libraries.keys()]
        lib_widget = SelectField( "sample_%i_library_id" % sample_index, 
                                refresh_on_change=True, 
                                refresh_on_change_values=lib_id_list )
        # fill up the options in the Library selectbox
        # first option 'none' is the value for "Select one" option
        if lib_id == 'none':
            lib_widget.add_option('Select one', 'none', selected=True)
        else:
            lib_widget.add_option('Select one', 'none')
        # all the libraries available to the selected user
        for lib, hidden_folder_ids in libraries.items():
            if str(lib.id) == str(lib_id):
                lib_widget.add_option(lib.name, lib.id, selected=True)
                selected_lib, selected_hidden_folder_ids = lib, hidden_folder_ids.split(',')
            else:
                lib_widget.add_option(lib.name, lib.id)
            lib_widget.refresh_on_change_values.append(lib.id)
        # create the folder selectbox
        folder_widget = SelectField( "sample_%i_folder_id" % sample_index )
        # when editing a request, either the user has already selected a subfolder or not
        if sample:
            if sample.folder:
                current_fid = sample.folder.id
            else: 
                # when a folder not yet associated with the request then the 
                # the current folder is set to the root_folder of the 
                # parent data library if present. 
                if sample.library:
                    current_fid = sample.library.root_folder.id
                else:
                    current_fid = params.get( "sample_%i_folder_id" % sample_index, 'none'  )
        else:
            if folder_id:
                current_fid = folder_id
            else:
                current_fid = 'none'
        # first option
        if lib_id == 'none':
            folder_widget.add_option('Select one', 'none', selected=True)
        else:
            folder_widget.add_option('Select one', 'none')
        if selected_lib:
            # get all show-able folders for the selected library
            showable_folders = trans.app.security_agent.get_showable_folders( user, user.all_roles(), 
                                                                              selected_lib, 
                                                                              [ trans.app.security_agent.permitted_actions.LIBRARY_ADD ], 
                                                                              selected_hidden_folder_ids )
            for f in showable_folders:
                if str(f.id) == str(current_fid):
                    folder_widget.add_option(f.name, f.id, selected=True)
                else:
                    folder_widget.add_option(f.name, f.id)
        return lib_widget, folder_widget
    def __copy_sample(self, current_samples):
        copy_list = SelectField('copy_sample')
        copy_list.add_option('None', -1, selected=True)  
        for i, s in enumerate(current_samples):
            copy_list.add_option(s['name'], i)
        return copy_list  
    
    def __sample_operation_selectbox(self, trans, request, **kwd):
        params = util.Params( kwd )
        cntrller = util.restore_text( params.get( 'cntrller', 'requests'  ) )
        if cntrller == 'requests_admin' and trans.user_is_admin():
            if request.complete():
                bulk_operations = [trans.app.model.Sample.bulk_operations.CHANGE_STATE]
            if request.rejected():
                bulk_operations = [trans.app.model.Sample.bulk_operations.SELECT_LIBRARY]
            else:
                bulk_operations = [s for i, s in trans.app.model.Sample.bulk_operations.items()]
        else:
            if request.complete():
                bulk_operations = []
            else:
                bulk_operations = [trans.app.model.Sample.bulk_operations.SELECT_LIBRARY]
        op_list = SelectField('select_sample_operation', 
                              refresh_on_change=True, 
                              refresh_on_change_values=bulk_operations)
        sel_op = kwd.get('select_sample_operation', 'none')
        if sel_op == 'none':
            op_list.add_option('Select operation', 'none', True)
        else:
            op_list.add_option('Select operation', 'none')
        for s in bulk_operations:
            if s == sel_op:
                op_list.add_option(s, s, True)
            else:
                op_list.add_option(s, s)
        return op_list
    
    def __selected_samples(self, trans, request, **kwd):
        params = util.Params( kwd )
        selected_samples = []
        for s in request.samples:
            if CheckboxField.is_checked(params.get('select_sample_%i' % s.id, '')):
                selected_samples.append(s.id)
        return selected_samples

    @web.expose
    @web.require_login( "create/submit sequencing requests" )
    def request_page(self, trans, **kwd):
        params = util.Params( kwd )
        cntrller = util.restore_text( params.get( 'cntrller', 'requests'  ) )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        try:
            request = trans.sa_session.query( trans.app.model.Request ).get( trans.security.decode_id( kwd['id']) )
        except:
            return trans.response.send_redirect( web.url_for( controller=cntrller,
                                                              action='list',
                                                              status='error',
                                                              message="Invalid request ID") )
        # get the user entered sample details
        current_samples, details, edit_mode, libraries = self.__update_samples( trans, request, **kwd )
        selected_samples = self.__selected_samples(trans, request, **kwd)
        sample_ops = self.__sample_operation_selectbox(trans, request,**kwd)
        if params.get('select_sample_operation', 'none') != 'none' and not len(selected_samples):
            return trans.response.send_redirect( web.url_for( controller=cntrller,
                                                              action='list',
                                                              operation='show',
                                                              id=trans.security.encode_id(request.id),
                                                              status='error',
                                                              message='Select at least one sample before selecting an operation.' ))
        if params.get('import_samples_button', False) == 'Import samples':
            return self.__import_samples(trans, cntrller, request, current_samples, details, libraries, **kwd)
        elif params.get('add_sample_button', False) == 'Add New':
            # add an empty or filled sample
            # if the user has selected a sample no. to copy then copy the contents 
            # of the src sample to the new sample else an empty sample
            src_sample_index = int(params.get( 'copy_sample', -1  ))
            # get the number of new copies of the src sample
            num_sample_to_copy = int(params.get( 'num_sample_to_copy', 1  ))
            if src_sample_index == -1:
                for ns in range(num_sample_to_copy):
                    # empty sample
                    lib_widget, folder_widget = self.__library_widgets(trans, request.user, 
                                                                       len(current_samples), 
                                                                       libraries, None, **kwd)
                    current_samples.append(dict(name='Sample_%i' % (len(current_samples)+1),
                                                barcode='',
                                                library=None,
                                                folder=None,
                                                field_values=['' for field in request.type.sample_form.fields],
                                                lib_widget=lib_widget,
                                                folder_widget=folder_widget))
            else:
                src_library_id = current_samples[src_sample_index]['lib_widget'].get_selected()[1]
                src_folder_id = current_samples[src_sample_index]['folder_widget'].get_selected()[1]
                for ns in range(num_sample_to_copy):
                    lib_widget, folder_widget = self.__library_widgets(trans, request.user, 
                                                                       len(current_samples), 
                                                                       libraries, sample=None, 
                                                                       lib_id=src_library_id,
                                                                       folder_id=src_folder_id,
                                                                       **kwd)
                    current_samples.append(dict(name=current_samples[src_sample_index]['name']+'_%i' % (len(current_samples)+1),
                                                barcode='',
                                                library_id='none',
                                                folder_id='none',
                                                field_values=[val for val in current_samples[src_sample_index]['field_values']],
                                                lib_widget=lib_widget,
                                                folder_widget=folder_widget))
            return trans.fill_template( '/requests/common/show_request.mako',
                                        cntrller=cntrller,
                                        request=request,
                                        request_details=self.request_details(trans, request.id),
                                        current_samples=current_samples,
                                        sample_copy=self.__copy_sample(current_samples), 
                                        details=details, selected_samples=selected_samples,
                                        sample_ops=sample_ops,
                                        edit_mode=edit_mode)
        elif params.get('save_samples_button', False) == 'Save':
            # check for duplicate sample names
            message = ''
            for index in range(len(current_samples)-len(request.samples)):
                sample_index = index + len(request.samples)
                sample_name = current_samples[sample_index]['name']
                if not sample_name.strip():
                    message = 'Please enter the name of sample number %i' % sample_index
                    break
                count = 0
                for i in range(len(current_samples)):
                    if sample_name == current_samples[i]['name']:
                        count = count + 1
                if count > 1: 
                    message = "This request has <b>%i</b> samples with the name <b>%s</b>.\nSamples belonging to a request must have unique names." % (count, sample_name)
                    break
            if message:
                return trans.fill_template( '/requests/common/show_request.mako',
                                            cntrller=cntrller,
                                            request=request, selected_samples=selected_samples,
                                            request_details=self.request_details(trans, request.id),
                                            current_samples = current_samples,
                                            sample_copy=self.__copy_sample(current_samples), 
                                            details=details, edit_mode=edit_mode,
                                            sample_ops=sample_ops,
                                            status='error', message=message)
            # save all the new/unsaved samples entered by the user
            if edit_mode == 'False':
                for index in range(len(current_samples)-len(request.samples)):
                    sample_index = len(request.samples)
                    form_values = trans.app.model.FormValues(request.type.sample_form, 
                                                             current_samples[sample_index]['field_values'])
                    trans.sa_session.add( form_values )
                    trans.sa_session.flush()                    
                    s = trans.app.model.Sample(current_samples[sample_index]['name'], '', 
                                               request, form_values, 
                                               current_samples[sample_index]['barcode'],
                                               current_samples[sample_index]['library'],
                                               current_samples[sample_index]['folder'])
                    trans.sa_session.add( s )
                    trans.sa_session.flush()

            else:
                status = 'done'
                message = 'Changes made to the sample(s) are saved. '
                for sample_index in range(len(current_samples)):
                    sample = request.samples[sample_index]
                    sample.name = current_samples[sample_index]['name'] 
                    sample.library = current_samples[sample_index]['library']
                    sample.folder = current_samples[sample_index]['folder']
                    if request.submitted():
                        bc_message = self.__validate_barcode(trans, sample, current_samples[sample_index]['barcode'])
                        if bc_message:
                            status = 'error'
                            message += bc_message
                        else:
                            if not sample.bar_code:
                                # if this is a 'new' (still in its first state) sample
                                # change the state to the next
                                if sample.current_state().id == request.type.states[0].id:
                                    event = trans.app.model.SampleEvent(sample, 
                                                                        request.type.states[1], 
                                                                        'Sample added to the system')
                                    trans.sa_session.add( event )
                                    trans.sa_session.flush()
                                    # now check if all the samples' barcode has been entered.
                                    # If yes then send notification email if configured
                                    common_state = request.common_state()
                                    if common_state:
                                        if common_state.id == request.type.states[1].id:
                                            event = trans.app.model.RequestEvent(request, 
                                                                                 request.states.SUBMITTED,
                                                                                 "All samples are in %s state." % common_state.name)
                                            trans.sa_session.add( event )
                                            trans.sa_session.flush()
                                            request.send_email_notification(trans, request.type.states[1])
                            sample.bar_code = current_samples[sample_index]['barcode']
                    trans.sa_session.add( sample )
                    trans.sa_session.flush()
                    form_values = trans.sa_session.query( trans.app.model.FormValues ).get( sample.values.id )
                    form_values.content = current_samples[sample_index]['field_values']
                    trans.sa_session.add( form_values )
                    trans.sa_session.flush()
            return trans.response.send_redirect( web.url_for( controller=cntrller,
                                                              action='list',
                                                              operation='show',
                                                              id=trans.security.encode_id(request.id),
                                                              status=status,
                                                              message=message ))
        elif params.get('edit_samples_button', False) == 'Edit samples':
            edit_mode = 'True'
            return trans.fill_template( '/requests/common/show_request.mako',
                                        cntrller=cntrller,
                                        request=request, selected_samples=selected_samples,
                                        request_details=self.request_details(trans, request.id),
                                        current_samples=current_samples,
                                        sample_copy=self.__copy_sample(current_samples), 
                                        sample_ops=sample_ops,
                                        details=details, libraries=libraries,
                                        edit_mode=edit_mode)
        elif params.get('cancel_changes_button', False) == 'Cancel':
            return trans.response.send_redirect( web.url_for( controller=cntrller,
                                                              action='list',
                                                              operation='show',
                                                              id=trans.security.encode_id(request.id)) )
        elif params.get('change_state_button', False) == 'Save':
            comments = util.restore_text( params.comment )
            selected_state = int( params.select_state )
            new_state = trans.sa_session.query( trans.app.model.SampleState ).get( selected_state )
            for sample_id in selected_samples:
                sample = trans.sa_session.query( trans.app.model.Sample ).get( sample_id )
                event = trans.app.model.SampleEvent(sample, new_state, comments)
                trans.sa_session.add( event )
                trans.sa_session.flush()
            return trans.response.send_redirect( web.url_for( controller='requests_common',
                                                              cntrller=cntrller, 
                                                              action='update_request_state',
                                                              request_id=request.id ))
        elif params.get('change_state_button', False) == 'Cancel':
            return trans.response.send_redirect( web.url_for( controller=cntrller,
                                                              action='list',
                                                              operation='show',
                                                              id=trans.security.encode_id(request.id)) )
        elif params.get('change_lib_button', False) == 'Save':
            library = trans.sa_session.query( trans.app.model.Library ).get( int( params.get( 'sample_0_library_id', None ) ) )
            folder = trans.sa_session.query( trans.app.model.LibraryFolder ).get( int( params.get( 'sample_0_folder_id', None ) ) )
            for sample_id in selected_samples:
                sample = trans.sa_session.query( trans.app.model.Sample ).get( sample_id )
                sample.library = library
                sample.folder = folder
                trans.sa_session.add( sample )
                trans.sa_session.flush()
            return trans.response.send_redirect( web.url_for( controller=cntrller,
                                                              action='list',
                                                              operation='show',
                                                              id=trans.security.encode_id(request.id),
                                                              status='done',
                                                              message='Changes made to the selected sample(s) are saved. ') )
        elif params.get('change_lib_button', False) == 'Cancel':
            return trans.response.send_redirect( web.url_for( controller=cntrller,
                                                              action='list',
                                                              operation='show',
                                                              id=trans.security.encode_id(request.id)) )
        else:
            return trans.fill_template( '/requests/common/show_request.mako',
                                        cntrller=cntrller, 
                                        request=request, selected_samples=selected_samples,
                                        request_details=self.request_details(trans, request.id),
                                        current_samples=current_samples,
                                        sample_copy=self.__copy_sample(current_samples), 
                                        details=details, libraries=libraries,
                                        sample_ops=sample_ops, 
                                        edit_mode=edit_mode, status=status, message=message,
                                        bulk_lib_ops=self.__library_widgets(trans, request.user, 0, libraries, None, **kwd))
            
    def __import_samples(self, trans, cntrller, request, current_samples, details, libraries, **kwd):
        '''
        This method reads the samples csv file and imports all the samples
        The format of the csv file is:
        SampleName,DataLibrary,DataLibraryFolder,Field1,Field2....
        ''' 
        try:
            params = util.Params( kwd )
            edit_mode = params.get( 'edit_mode', 'False' )
            file_obj = params.get('file_data', '')
            reader = csv.reader(file_obj.file)
            for row in reader:
                lib_id = None
                folder_id = None
                lib = trans.sa_session.query( trans.app.model.Library ) \
                                      .filter( and_( trans.app.model.Library.table.c.name==row[1], \
                                                     trans.app.model.Library.table.c.deleted==False ) )\
                                      .first()
                if lib:
                    folder = trans.sa_session.query( trans.app.model.LibraryFolder ) \
                                             .filter( and_( trans.app.model.LibraryFolder.table.c.name==row[2], \
                                                            trans.app.model.LibraryFolder.table.c.deleted==False ) )\
                                             .first()
                    if folder:
                        lib_id = lib.id
                        folder_id = folder.id
                lib_widget, folder_widget = self.__library_widgets(trans, request.user, len(current_samples), 
                                                                   libraries, None, lib_id, folder_id, **kwd)
                current_samples.append(dict(name=row[0], 
                                            barcode='',
                                            library=None,
                                            folder=None,
                                            lib_widget=lib_widget,
                                            folder_widget=folder_widget,
                                            field_values=row[3:]))  
            return trans.fill_template( '/requests/common/show_request.mako',
                                        cntrller=cntrller,
                                        request=request,
                                        request_details=self.request_details(trans, request.id),
                                        current_samples=current_samples,
                                        sample_copy=self.__copy_sample(current_samples), 
                                        details=details,
                                        edit_mode=edit_mode)
        except:
            return trans.response.send_redirect( web.url_for( controller=cntrller,
                                                              action='list',
                                                              operation='show',
                                                              id=trans.security.encode_id(request.id),
                                                              status='error',
                                                              message='Error in importing samples file' ))

    def __validate_barcode(self, trans, sample, barcode):
        '''
        This method makes sure that the given barcode about to be assigned to 
        the given sample is gobally unique. That is, barcodes must be unique 
        across requests in Galaxy LIMS 
        '''
        message = ''
        for index in range(len(sample.request.samples)):
            # check for empty bar code
            if not barcode.strip():
                message = 'Please fill the barcode for sample <b>%s</b>.' % sample.name
                break
            # check all the saved bar codes
            all_samples = trans.sa_session.query( trans.app.model.Sample )
            for s in all_samples:
                if barcode == s.bar_code:
                    if sample.id == s.id:
                        continue
                    else:
                        message = '''The bar code <b>%s</b> of sample <b>%s</b>  
                                 belongs another sample. The sample bar codes must be 
                                 unique throughout the system''' % \
                                 (barcode, sample.name)
                        break
            if message:
                break
        return message


    @web.expose
    @web.require_login( "create/submit sequencing requests" )
    def delete_sample(self, trans, **kwd):
        params = util.Params( kwd )
        cntrller = util.restore_text( params.get( 'cntrller', 'requests'  ) )
        request = trans.sa_session.query( trans.app.model.Request ).get( int( params.get( 'request_id', 0 ) ) )
        current_samples, details, edit_mode, libraries = self.__update_samples( trans, request, **kwd )
        sample_index = int(params.get('sample_id', 0))
        sample_name = current_samples[sample_index]['name']
        s = request.has_sample(sample_name)
        if s:
            trans.sa_session.delete( s.values )
            trans.sa_session.delete( s )
            trans.sa_session.flush()
        return trans.response.send_redirect( web.url_for( controller=cntrller,
                                                          action='list',
                                                          operation='show',
                                                          id=trans.security.encode_id(request.id),
                                                          status='done',
                                                          message='Sample <b>%s</b> has been deleted.' % sample_name ))
    def request_details(self, trans, id):
        '''
        Shows the request details
        '''
        request = trans.sa_session.query( trans.app.model.Request ).get( id )
        # list of widgets to be rendered on the request form
        request_details = []
        # form fields
        for index, field in enumerate(request.type.request_form.fields):
            if field['required']:
                req = 'Required'
            else:
                req = 'Optional'
            if field['type'] == 'AddressField':
                if request.values.content[index]:
                    request_details.append(dict(label=field['label'],
                                                value=trans.sa_session.query( trans.app.model.UserAddress ).get( int( request.values.content[index] ) ).get_html(),
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
    @web.expose
    @web.require_login( "create/submit sequencing requests" )
    def sample_events(self, trans, **kwd):
        params = util.Params( kwd )
        cntrller = util.restore_text( params.get( 'cntrller', 'requests'  ) )
        try:
            sample_id = int(params.get('sample_id', False))
            sample = trans.sa_session.query( trans.app.model.Sample ).get( sample_id )
        except:
            message = "Invalid sample ID"
            return trans.response.send_redirect( web.url_for( controller=cntrller,
                                                              action='list',
                                                              status='error',
                                                              message=message) )
        events_list = []
        all_events = sample.events
        for event in all_events:         
            events_list.append((event.state.name, event.state.desc, 
                                time_ago(event.update_time), 
                                event.comment))
        return trans.fill_template( '/requests/common/sample_events.mako', 
                                    cntrller=cntrller,
                                    events_list=events_list,
                                    sample=sample)
    @web.expose
    @web.require_admin
    def show_datatx_page( self, trans, **kwd ):
        params = util.Params( kwd )
        cntrller = util.restore_text( params.get( 'cntrller', 'requests'  ) )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' ) 
        try:
            sample = trans.sa_session.query( trans.app.model.Sample ).get( trans.security.decode_id( kwd['sample_id'] ) )
        except:
            return trans.response.send_redirect( web.url_for( controller=cntrller,
                                                              action='list',
                                                              status='error',
                                                              message="Invalid sample ID") )
        # check if a library and folder has been set for this sample yet.
        if not sample.library or not sample.folder:
            return trans.response.send_redirect( web.url_for( controller=cntrller,
                                                              action='list',
                                                              operation='show',
                                                              status='error',
                                                              message="Set a data library and folder for <b>%s</b> to transfer dataset(s)." % sample.name,
                                                              id=trans.security.encode_id(sample.request.id) ) )
        if cntrller == 'requests_admin':
            return trans.response.send_redirect( web.url_for( controller='requests_admin',
                                                              action='manage_datasets',
                                                              sample_id=sample.id) )
            
        if params.get( 'folder_path', ''  ):
            folder_path = util.restore_text( params.get( 'folder_path', ''  ) )
        else:
            if len(sample.datasets):
                folder_path = os.path.dirname(sample.datasets[-1].file_path[:-1])
            else:
                folder_path = util.restore_text( sample.request.type.datatx_info.get('data_dir', '') )
        if folder_path and folder_path[-1] != os.sep:
            folder_path += os.sep
        if not sample.request.type.datatx_info['host'] or not sample.request.type.datatx_info['username'] \
           or not sample.request.type.datatx_info['password']:
            status = 'error'
            message = 'The sequencer login information is incomplete. Click on the <b>Sequencer information</b> to add login details.'
        return trans.fill_template( '/requests/common/get_data.mako', 
                                    cntrller=cntrller, sample=sample, 
                                    dataset_files=sample.datasets,
                                    message=message, status=status, files=[],
                                    folder_path=folder_path )
    #
    # Find sequencing requests & samples
    #
    def __find_widgets(self, trans, **kwd):
        params = util.Params( kwd )
        request_states = SelectField('request_states', multiple=True, display="checkboxes")
        sel_op = kwd.get('request_states', trans.app.model.Request.states.SUBMITTED)
        for i, s in trans.app.model.Request.states.items():
            if s in sel_op:
                request_states.add_option(s, s, True)
            else:
                request_states.add_option(s, s)
        search_type = SelectField('search_type')
        sel_op = kwd.get('search_type', 'sample name')
        for s in ['sample name', 'barcode', 'dataset']:
            if s in sel_op:
                search_type.add_option(s, s, True)
            else:
                search_type.add_option(s, s)
        search_box = TextField('search_box', 50, kwd.get('search_box', ''))
        return request_states, search_type, search_box
        
    @web.expose
    @web.require_admin
    def find( self, trans, **kwd ):
        params = util.Params( kwd )
        cntrller = params.get( 'cntrller', 'requests'  )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        samples_list = []
        results = ''
        if params.get('go_button', '') == 'Find':
            search_string = kwd.get( 'search_box', ''  )
            search_type = params.get( 'search_type', ''  )
            request_states = util.listify( params.get( 'request_states', ''  ) )
            samples = []
            if search_type == 'barcode':
                samples = trans.sa_session.query( trans.app.model.Sample ) \
                                          .filter( and_( trans.app.model.Sample.table.c.deleted==False,
                                                         trans.app.model.Sample.table.c.bar_code.like(search_string) ) )\
                                          .order_by( trans.app.model.Sample.table.c.create_time.desc())\
                                          .all()
            elif search_type == 'sample name':
                samples = trans.sa_session.query( trans.app.model.Sample ) \
                                          .filter( and_( trans.app.model.Sample.table.c.deleted==False,
                                                         trans.app.model.Sample.table.c.name.ilike(search_string) ) )\
                                          .order_by( trans.app.model.Sample.table.c.create_time.desc())\
                                          .all()
            elif search_type == 'dataset':
                samples = trans.sa_session.query( trans.app.model.Sample ) \
                                          .filter( and_( trans.app.model.Sample.table.c.deleted==False,
                                                         trans.app.model.SampleDataset.table.c.sample_id==trans.app.model.Sample.table.c.id,
                                                         trans.app.model.SampleDataset.table.c.name.ilike(search_string) ) )\
                                          .order_by( trans.app.model.Sample.table.c.create_time.desc())\
                                          .all()
            if cntrller == 'requests':
                for s in samples:
                    if s.request.user.id == trans.user.id \
                        and s.request.state() in request_states\
                        and not s.request.deleted:
                        samples_list.append(s)
            elif cntrller == 'requests_admin':
                for s in samples:
                    if not s.request.deleted \
                        and s.request.state() in request_states:
                        samples_list.append(s)
            results = 'There are %i sample(s) matching the search parameters.' % len(samples_list)
        request_states, search_type, search_box = self.__find_widgets(trans, **kwd)
        return trans.fill_template( '/requests/common/find.mako', 
                                    cntrller=cntrller, request_states=request_states,
                                    samples=samples_list, search_type=search_type,
                                    results=results, search_box=search_box )
    
    
    
    
    
    
    
    
        

