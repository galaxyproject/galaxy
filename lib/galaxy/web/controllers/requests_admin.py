from galaxy.web.base.controller import *
from galaxy.web.framework.helpers import time_ago, iff, grids
from galaxy.model.orm import *
from galaxy.datatypes import sniff
from galaxy import model, util
from galaxy.util.streamball import StreamBall
import logging, tempfile, zipfile, tarfile, os, sys, subprocess, smtplib, socket
from galaxy.web.form_builder import * 
from datetime import datetime, timedelta
from email.MIMEText import MIMEText
from galaxy.web.controllers.forms import get_all_forms
from sqlalchemy.sql.expression import func, and_
from sqlalchemy.sql import select
import pexpect
import ConfigParser, threading, time
from amqplib import client_0_8 as amqp
import csv
log = logging.getLogger( __name__ )

#
# ---- Request Grid ------------------------------------------------------------ 
#

class RequestsGrid( grids.Grid ):
    # Custom column types
    class NameColumn( grids.TextColumn ):
        def get_value(self, trans, grid, request):
            return request.name
    class DescriptionColumn( grids.TextColumn ):
        def get_value(self, trans, grid, request):
            return request.desc
    class SamplesColumn( grids.GridColumn ):
        def get_value(self, trans, grid, request):
            return str(len(request.samples))
    class TypeColumn( grids.TextColumn ):
        def get_value(self, trans, grid, request):
            return request.type.name
    class StateColumn( grids.GridColumn ):
        def __init__( self, col_name, key, model_class, event_class, filterable, link ):
            grids.GridColumn.__init__(self, col_name, key=key, model_class=model_class, filterable=filterable, link=link)
            self.event_class = event_class
        def get_value(self, trans, grid, request):
            if request.state() == request.states.REJECTED:
                return '<div class="count-box state-color-error">%s</div>' % request.state()
            elif request.state() == request.states.NEW:
                return '<div class="count-box state-color-queued">%s</div>' % request.state()
            elif request.state() == request.states.SUBMITTED:
                return '<div class="count-box state-color-running">%s</div>' % request.state()
            elif request.state() == request.states.COMPLETE:
                return '<div class="count-box state-color-ok">%s</div>' % request.state()
            return request.state()
        def filter( self, trans, user, query, column_filter ):
            """ Modify query to filter request by state. """
            if column_filter == "All":
                return query
            if column_filter:
                # select r.id, r.name, re.id, re.state 
                # from request as r, request_event as re
                # where re.request_id=r.id and re.state='Complete' and re.create_time in
                #                        (select MAX( create_time)
                #                         from request_event
                #                         group by request_id)
                q = query.join(self.event_class.table)\
                         .filter( self.model_class.table.c.id==self.event_class.table.c.request_id )\
                         .filter( self.event_class.table.c.state==column_filter )\
                         .filter( self.event_class.table.c.id.in_(select(columns=[func.max(self.event_class.table.c.id)],
                                                                                  from_obj=self.event_class.table,
                                                                                  group_by=self.event_class.table.c.request_id)))
            return q
        def get_accepted_filters( self ):
            """ Returns a list of accepted filters for this column. """
            accepted_filter_labels_and_vals = [ model.Request.states.NEW,
                                                model.Request.states.REJECTED,
                                                model.Request.states.SUBMITTED,
                                                model.Request.states.COMPLETE,
                                                "All"]
            accepted_filters = []
            for val in accepted_filter_labels_and_vals:
                label = val.lower()
                args = { self.key: val }
                accepted_filters.append( grids.GridColumnFilter( label, args) )
            return accepted_filters
    class UserColumn( grids.TextColumn ):
        def get_value(self, trans, grid, request):
            return request.user.email
    # Grid definition
    title = "Sequencing Requests"
    template = "admin/requests/grid.mako"
    model_class = model.Request
    default_sort_key = "-update_time"
    num_rows_per_page = 50
    preserve_state = True
    use_paging = True
    default_filter = dict( deleted="False")
    columns = [
        NameColumn( "Name", 
                    key="name", 
                    model_class=model.Request,
                    link=( lambda item: iff( item.deleted, None, dict( operation="show", id=item.id ) ) ),
                    attach_popup=True, 
                    filterable="advanced" ),
        DescriptionColumn( "Description",
                           key='desc',
                           model_class=model.Request,
                           filterable="advanced" ),
        SamplesColumn( "Sample(s)", 
                       link=( lambda item: iff( item.deleted, None, dict( operation="show", id=item.id ) ) ), ),
        TypeColumn( "Type",
                    link=( lambda item: iff( item.deleted, None, dict( operation="view_type", id=item.type.id ) ) ), ),
        grids.GridColumn( "Last Updated", key="update_time", format=time_ago ),
        grids.DeletedColumn( "Deleted", 
                       key="deleted", 
                       visible=False, 
                       filterable="advanced" ),
        StateColumn( "State", 
                     key='state',
                     model_class=model.Request,
                     event_class=model.RequestEvent,
                     filterable="advanced",
                     link=( lambda item: iff( item.deleted, None, dict( operation="events", id=item.id ) ) ),
                     ),
        UserColumn( "User",
                    #key='user.email',
                    model_class=model.Request)

    ]
    columns.append( grids.MulticolFilterColumn( "Search", 
                                                cols_to_filter=[ columns[0], columns[1] ], 
                                                key="free-text-search",
                                                visible=False,
                                                filterable="standard" ) )
    operations = [
        grids.GridOperation( "Submit", allow_multiple=False, condition=( lambda item: not item.deleted and item.unsubmitted() and item.samples ),
                             confirm="More samples cannot be added to this request once it is submitted. Click OK to submit."  ),
        grids.GridOperation( "Edit", allow_multiple=False, condition=( lambda item: not item.deleted )  ),
        grids.GridOperation( "Reject", allow_multiple=False, condition=( lambda item: not item.deleted and item.submitted() )  ),
        grids.GridOperation( "Delete", allow_multiple=True, condition=( lambda item: not item.deleted )  ),
        grids.GridOperation( "Undelete", condition=( lambda item: item.deleted ) ),    
        grids.GridOperation( "Purge", allow_multiple=False, confirm="This will permanently delete the sequencing request. Click OK to proceed.", condition=( lambda item: item.deleted ) ),
    ]
    global_actions = [
        grids.GridAction( "Create new request", dict( controller='requests_common',
                                                      cntrller='requests_admin',
                                                      action='new', 
                                                      select_request_type='True' ) )
    ]


#
# ---- Request Type Grid ------------------------------------------------------ 
#
class RequestTypeGrid( grids.Grid ):
    # Custom column types
    class NameColumn( grids.TextColumn ):
        def get_value(self, trans, grid, request_type):
            return request_type.name
    class DescriptionColumn( grids.TextColumn ):
        def get_value(self, trans, grid, request_type):
            return request_type.desc
    class RequestFormColumn( grids.TextColumn ):
        def get_value(self, trans, grid, request_type):
            return request_type.request_form.name
    class SampleFormColumn( grids.TextColumn ):
        def get_value(self, trans, grid, request_type):
            return request_type.sample_form.name
    # Grid definition
    title = "Requests Types"
    template = "admin/requests/manage_request_types.mako"
    model_class = model.RequestType
    default_sort_key = "-create_time"
    num_rows_per_page = 50
    preserve_state = True
    use_paging = True
    default_filter = dict( deleted="False" )
    columns = [
        NameColumn( "Name", 
                    key="name", 
                    model_class=model.RequestType,
                    link=( lambda item: iff( item.deleted, None, dict( operation="view", id=item.id ) ) ),
                    attach_popup=True,
                    filterable="advanced" ),
        DescriptionColumn( "Description",
                           key='desc',
                           model_class=model.Request,
                           filterable="advanced" ),
        RequestFormColumn( "Request Form", 
                           link=( lambda item: iff( item.deleted, None, dict( operation="view_form", id=item.request_form.id ) ) ), ),
        SampleFormColumn( "Sample Form", 
                           link=( lambda item: iff( item.deleted, None, dict( operation="view_form", id=item.sample_form.id ) ) ), ),
        grids.DeletedColumn( "Deleted", 
                       key="deleted", 
                       visible=False, 
                       filterable="advanced" )
    ]
    columns.append( grids.MulticolFilterColumn( "Search", 
                                                cols_to_filter=[ columns[0], columns[1] ], 
                                                key="free-text-search",
                                                visible=False,
                                                filterable="standard" ) )
    operations = [
        grids.GridOperation( "Permissions", allow_multiple=False, condition=( lambda item: not item.deleted  )  ),
        #grids.GridOperation( "Clone", allow_multiple=False, condition=( lambda item: not item.deleted  )  ),
        grids.GridOperation( "Delete", allow_multiple=True, condition=( lambda item: not item.deleted  )  ),
        grids.GridOperation( "Undelete", condition=( lambda item: item.deleted ) ),    
    ]
    global_actions = [
        grids.GridAction( "Create new request type", dict( controller='requests_admin', 
                                                           action='create_request_type' ) )
    ]


# ---- Data Transfer Grid ------------------------------------------------------ 
#
class DataTransferGrid( grids.Grid ):
    # Custom column types
    class NameColumn( grids.TextColumn ):
        def get_value(self, trans, grid, sample_dataset):
            return sample_dataset.name
    class SizeColumn( grids.TextColumn ):
        def get_value(self, trans, grid, sample_dataset):
            return sample_dataset.size
    class StatusColumn( grids.TextColumn ):
        def get_value(self, trans, grid, sample_dataset):
            return sample_dataset.status
    # Grid definition
    title = "Sample Datasets"
    template = "admin/requests/datasets_grid.mako"
    model_class = model.SampleDataset
    default_sort_key = "-create_time"
    num_rows_per_page = 50
    preserve_state = True
    use_paging = True
    #default_filter = dict( deleted="False" )
    columns = [
        NameColumn( "Name", 
                    #key="name", 
                    model_class=model.SampleDataset,
                    link=( lambda item: dict( operation="view", id=item.id ) ),
                    attach_popup=True,
                    filterable="advanced" ),
        SizeColumn( "Size",
                    #key='size',
                    model_class=model.SampleDataset,
                    filterable="advanced" ),
        grids.GridColumn( "Last Updated", key="update_time", format=time_ago ),
        StatusColumn( "Status",
                      #key='status',
                      model_class=model.SampleDataset,
                      filterable="advanced" ),
    ]
    columns.append( grids.MulticolFilterColumn( "Search", 
                                                cols_to_filter=[ columns[0] ], 
                                                key="free-text-search",
                                                visible=False,
                                                filterable="standard" ) )
    operations = [
        grids.GridOperation( "Start Transfer", allow_multiple=True, condition=( lambda item: item.status in [model.Sample.transfer_status.NOT_STARTED] ) ),
        grids.GridOperation( "Rename", allow_multiple=True, allow_popup=False, condition=( lambda item: item.status in [model.Sample.transfer_status.NOT_STARTED] ) ),
        grids.GridOperation( "Delete", allow_multiple=True, condition=( lambda item: item.status in [model.Sample.transfer_status.NOT_STARTED] )  ),
    ]
    def apply_query_filter( self, trans, query, **kwd ):
        return query.filter_by( sample_id=kwd['sample_id'] )
#
# ---- Request Controller ------------------------------------------------------ 
#

class RequestsAdmin( BaseController ):
    request_grid = RequestsGrid()
    requesttype_grid = RequestTypeGrid()
    datatx_grid = DataTransferGrid()

    
    @web.expose
    @web.require_admin
    def index( self, trans ):
        return trans.fill_template( "/admin/requests/index.mako" )
    
    @web.expose
    @web.require_admin
    def list( self, trans, **kwd ):
        '''
        List all request made by the current user
        '''
        if 'operation' in kwd:
            operation = kwd['operation'].lower()
            if not kwd.get( 'id', None ):
                return trans.response.send_redirect( web.url_for( controller='requests_admin',
                                                                  action='list',
                                                                  status='error',
                                                                  message="Invalid request ID") )
            if operation == "show":
                return trans.response.send_redirect( web.url_for( controller='requests_common',
                                                                  cntrller='requests_admin',
                                                                  action='show',
                                                                  **kwd ) )
            elif operation == "submit":
                return trans.response.send_redirect( web.url_for( controller='requests_common',
                                                                  cntrller='requests_admin',
                                                                  action='submit',
                                                                  **kwd ) )
            elif operation == "delete":
                return trans.response.send_redirect( web.url_for( controller='requests_common',
                                                                  cntrller='requests_admin',
                                                                  action='delete',
                                                                  **kwd ) )
            elif operation == "undelete":
                return trans.response.send_redirect( web.url_for( controller='requests_common',
                                                                  cntrller='requests_admin',
                                                                  action='undelete',
                                                                  **kwd ) )
            elif operation == "edit":
                return trans.response.send_redirect( web.url_for( controller='requests_common',
                                                                  cntrller='requests_admin',
                                                                  action='edit',
                                                                  show=True, **kwd ) )
            elif operation == "events":
                return trans.response.send_redirect( web.url_for( controller='requests_common',
                                                                  cntrller='requests_admin',
                                                                  action='events',
                                                                  **kwd ) )
            elif operation == "reject":
                return self.__reject_request( trans, **kwd )
            elif operation == "view_type":
                return self.__view_request_type( trans, **kwd )
            elif operation == "upload_datasets":
                return self.__upload_datasets( trans, **kwd )
        # Render the grid view
        return self.request_grid( trans, **kwd )

    @web.json
    def get_file_details( self, trans, id=None, folder_path=None ):
        def print_ticks(d):
            pass
        # Avoid caching
        trans.response.headers['Pragma'] = 'no-cache'
        trans.response.headers['Expires'] = '0'
        request = trans.sa_session.query( self.app.model.Request ).get( int(id) )
        datatx_info = request.type.datatx_info
        cmd  = 'ssh %s@%s "ls -oghp \'%s\'"' % ( datatx_info['username'],
                                                 datatx_info['host'],
                                                 folder_path  )
        output = pexpect.run(cmd, events={'.ssword:*': datatx_info['password']+'\r\n', 
                                          pexpect.TIMEOUT:print_ticks}, 
                                          timeout=10)
        return unicode(output.replace('\n', '<br/>'))

    @web.json
    def open_folder( self, trans, id=None, folder_path=None ):
        def print_ticks(d):
            pass
        # Avoid caching
        trans.response.headers['Pragma'] = 'no-cache'
        trans.response.headers['Expires'] = '0'
        request = trans.sa_session.query( self.app.model.Request ).get( int(id) )
        return self.__get_files(trans, request.type, folder_path)

    def __reject_request(self, trans, **kwd):
        try:
            request = trans.sa_session.query( trans.app.model.Request ).get( trans.security.decode_id(kwd['id']) )
        except:
            message = "Invalid request ID"
            log.warn( message )
            return trans.response.send_redirect( web.url_for( controller='requests_admin',
                                                              action='list',
                                                              status='error',
                                                              message=message,
                                                              **kwd) )
        return trans.fill_template( '/admin/requests/reject.mako', 
                                    request=request)
    @web.expose
    @web.require_admin
    def reject(self, trans, **kwd):
        params = util.Params( kwd )
        if params.get('cancel_reject_button', False):
            return trans.response.send_redirect( web.url_for( controller='requests_admin',
                                                              action='list',
                                                              operation='show_request',
                                                              id=kwd['id']))
        try:
            request = trans.sa_session.query( trans.app.model.Request ).get( trans.security.decode_id(kwd['id']) )
        except:
            message = "Invalid request ID"
            log.warn( message )
            return trans.response.send_redirect( web.url_for( controller='requests_admin',
                                                              action='list',
                                                              status='error',
                                                              message=message,
                                                              **kwd) )
        # validate
        if not params.get('comment', ''):
            return trans.fill_template( '/admin/requests/reject.mako', 
                                        request=request, status='error',
                                        message='A comment is required for rejecting a request.')
        # create an event with state 'Rejected' for this request
        comments = util.restore_text( params.comment )
        event = trans.app.model.RequestEvent(request, request.states.REJECTED, comments)
        trans.sa_session.add( event )
        trans.sa_session.flush()
        return trans.response.send_redirect( web.url_for( controller='requests_admin',
                                                          action='list',
                                                          status='done',
                                                          message='Request <b>%s</b> has been rejected.' % request.name) )
    
    def __upload_datasets(self, trans, **kwd):
        return trans.fill_template( '/admin/requests/upload_datasets.mako' )
            

    @web.expose
    @web.require_admin
    def bar_codes(self, trans, **kwd):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        request_id = params.get( 'request_id', None )
        if request_id:
            request = trans.sa_session.query( trans.app.model.Request ).get( int( request_id ))
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
                                    status=status,
                                    message=message)
    @web.expose
    @web.require_admin
    def save_bar_codes(self, trans, **kwd):
        params = util.Params( kwd )
        try:
            request = trans.sa_session.query( trans.app.model.Request ).get( int( params.get( 'request_id', None ) ) )
        except:
            return trans.response.send_redirect( web.url_for( controller='requests_admin',
                                                              action='list',
                                                              status='error',
                                                              message="Invalid request ID",
                                                              **kwd) )
        # validate 
        # bar codes need to be globally unique
        message = ''
        for index in range(len(request.samples)):
            bar_code = util.restore_text(params.get('sample_%i_bar_code' % index, ''))
            # check for empty bar code
            if not bar_code.strip():
                message = 'Please fill the barcode for sample <b>%s</b>.' % request.samples[index].name
                break
            # check all the unsaved bar codes
            count = 0
            for i in range(len(request.samples)):
                if bar_code == util.restore_text(params.get('sample_%i_bar_code' % i, '')):
                    count = count + 1
            if count > 1:
                message = '''The barcode <b>%s</b> of sample <b>%s</b> belongs
                         another sample in this request. The sample barcodes must
                         be unique throughout the system''' % \
                         (bar_code, request.samples[index].name)
                break
            # check all the saved bar codes
            all_samples = trans.sa_session.query( trans.app.model.Sample )
            for sample in all_samples:
                if bar_code == sample.bar_code:
                    message = '''The bar code <b>%s</b> of sample <b>%s</b>  
                             belongs another sample. The sample bar codes must be 
                             unique throughout the system''' % \
                             (bar_code, request.samples[index].name)
                    break
            if message:
                break
        if message:
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
                                        user=request.user, request=request, widgets=widgets, status='error',
                                        message=message)
        # now save the bar codes
        for index, sample in enumerate(request.samples):
            bar_code = util.restore_text(params.get('sample_%i_bar_code' % index, ''))
            sample.bar_code = bar_code
            trans.sa_session.add( sample )
            trans.sa_session.flush()
        # change the state of all the samples to the next state
        # get the new state
        new_state = request.type.states[1]
        for s in request.samples:
            event = trans.app.model.SampleEvent(s, new_state, 'Bar code added to this sample')
            trans.sa_session.add( event )
            trans.sa_session.flush()
        return trans.response.send_redirect( web.url_for( controller='requests_admin',
                                                          action='list',
                                                          operation='show_request',
                                                          id=trans.security.encode_id(request.id),
                                                          message='Bar codes have been saved for this request',
                                                          status='done'))
    @web.expose
    @web.require_admin
    def update_request_state( self, trans, **kwd ):
        params = util.Params( kwd )
        try:
            request = trans.sa_session.query( trans.app.model.Request ).get( int( params.get( 'request_id', None ) ) )
            sample_id = int(params.get('sample_id', False))
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
                event = trans.app.model.RequestEvent(request, request.states.SUBMITTED, "One or more samples' state moved from the final sample state.")
                trans.sa_session.add( event )
                trans.sa_session.flush()
            return trans.response.send_redirect( web.url_for( controller='requests_common',
                                                              cntrller='requests_admin', 
                                                              action='sample_events',
                                                              sample_id=sample_id))
        final_state = False
        if common_state.id == request.type.last_state().id:
            # since all the samples are in the final state, change the request state to 'Complete'
            comments = "All samples of this request are in the last sample state (%s)." % request.type.last_state().name
            state = request.states.COMPLETE
            final_state = True
        else:
            comments = "All samples are in %s state." % common_state.name
            state = request.states.SUBMITTED
        event = trans.app.model.RequestEvent(request, state, comments)
        trans.sa_session.add( event )
        trans.sa_session.flush()
        # check if an email notification is configured to be sent when the samples 
        # are in this state
#        if common_state.id in request.notification['sample_states']:
        request.send_email_notification(trans, common_state, final_state)
        return trans.response.send_redirect( web.url_for( controller='requests_common',
                                                          cntrller='requests_admin', 
                                                          action='sample_events',
                                                          sample_id=sample_id))

    @web.expose
    @web.require_admin
    def save_state(self, trans, **kwd):
        params = util.Params( kwd )
        try:
            sample_id = int(params.get('sample_id', False))
            sample = trans.sa_session.query( trans.app.model.Sample ).get( sample_id )
        except:
            message = "Invalid sample ID"
            return trans.response.send_redirect( web.url_for( controller='requests_admin',
                                                              action='list',
                                                              status='error',
                                                              message=message,
                                                              **kwd) )
        comments = util.restore_text( params.comment )
        selected_state = int( params.select_state )
        new_state = trans.sa_session.query( trans.app.model.SampleState ) \
                                    .filter( and_( trans.app.model.SampleState.table.c.request_type_id == sample.request.type.id,
                                                   trans.app.model.SampleState.table.c.id == selected_state ) ) \
                                    .first()
        event = trans.app.model.SampleEvent(sample, new_state, comments)
        trans.sa_session.add( event )
        trans.sa_session.flush()
        return trans.response.send_redirect( web.url_for( controller='requests_admin',
                                                          cntrller='requests_admin', 
                                                          action='update_request_state',
                                                          request_id=sample.request.id,
                                                          sample_id=sample.id))
    #
    # Data transfer from sequencer
    #
    
    @web.expose
    @web.require_admin
    def manage_datasets( self, trans, **kwd ):
        if 'operation' in kwd:
            operation = kwd['operation'].lower()
            if not kwd.get( 'id', None ):
                return trans.response.send_redirect( web.url_for( controller='requests_admin',
                                                                  action='list',
                                                                  status='error',
                                                                  message="Invalid sample dataset ID") )
            if operation == "view":
                sample_dataset = trans.sa_session.query( trans.app.model.SampleDataset ).get( trans.security.decode_id(kwd['id']) )
                return trans.fill_template( '/admin/requests/dataset.mako', 
                                            sample=sample_dataset.sample,
                                            sample_dataset=sample_dataset)

            elif operation == "delete":
                id_list = util.listify( kwd['id'] )
                not_deleted = []
                for id in id_list:
                    sample_dataset = trans.sa_session.query( trans.app.model.SampleDataset ).get( trans.security.decode_id(id) )
                    sample_id = sample_dataset.sample_id
                    if sample_dataset.status == sample_dataset.sample.transfer_status.NOT_STARTED:
                        trans.sa_session.delete( sample_dataset )
                        trans.sa_session.flush()
                    else:
                        not_deleted.append(sample_dataset.name)
                message = '%i dataset(s) have been successfully deleted. ' % (len(id_list) - len(not_deleted))
                status = 'done'
                if not_deleted:
                    status = 'warning'
                    message = message + '%s could not be deleted. Only datasets with transfer status "Not Started" can be deleted. ' % str(not_deleted)
                return trans.response.send_redirect( web.url_for( controller='requests_admin',
                                                                  action='manage_datasets',
                                                                  sample_id=sample_id,
                                                                  status=status,
                                                                  message=message) )

            elif operation == "rename":
                id_list = util.listify( kwd['id'] )
                sample_dataset = trans.sa_session.query( trans.app.model.SampleDataset ).get( trans.security.decode_id(id_list[0]) )
                return trans.fill_template( '/admin/requests/rename_datasets.mako', 
                                            sample=sample_dataset.sample,
                                            id_list=id_list )
            elif operation == "start transfer":
                id_list = util.listify( kwd['id'] )
                sample_dataset = trans.sa_session.query( trans.app.model.SampleDataset ).get( trans.security.decode_id(id_list[0]) )
                self.__start_datatx(trans, sample_dataset.sample, id_list)
                

        # Render the grid view
        try:
            sample = trans.sa_session.query( trans.app.model.Sample ).get( kwd['sample_id']  )
        except:
            return trans.response.send_redirect( web.url_for( controller='requests_admin',
                                                              action='list',
                                                              status='error',
                                                              message="Invalid sample ID" ) )
        self.datatx_grid.title = 'Datasets of Sample "%s"' % sample.name
        self.datatx_grid.global_actions = [
                                           grids.GridAction( "Refresh", 
                                                             dict( controller='requests_admin', 
                                                                   action='manage_datasets',
                                                                   sample_id=sample.id) ),
                                           grids.GridAction( "Select Datasets", 
                                                             dict(controller='requests_admin', 
                                                                  action='get_data',
                                                                  request_id=sample.request.id,
                                                                  folder_path=sample.request.type.datatx_info['data_dir'],
                                                                  sample_id=sample.id,
                                                                  show_page=True)),
                                           grids.GridAction( 'Data Library "%s"' % sample.library.name, 
                                                             dict(controller='library_common', 
                                                                  action='browse_library', 
                                                                  cntrller='library_admin', 
                                                                  id=trans.security.encode_id( sample.library.id))),
                                           grids.GridAction( "Browse this request", 
                                                             dict( controller='requests_admin', 
                                                                   action='list',
                                                                   operation='show',
                                                                   id=trans.security.encode_id(sample.request.id)))]
        return self.datatx_grid( trans, **kwd )

    @web.expose
    @web.require_admin
    def rename_datasets( self, trans, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' ) 
        try:
            sample = trans.sa_session.query( trans.app.model.Sample ).get( trans.security.decode_id(kwd['sample_id']))
        except:
            return trans.response.send_redirect( web.url_for( controller='requests_admin',
                                                              action='list',
                                                              status='error',
                                                              message="Invalid sample ID" ) )
        if params.get( 'save_button', False ):
            id_list = util.listify( kwd['id_list'] )
            for id in id_list:
                sample_dataset = trans.sa_session.query( trans.app.model.SampleDataset ).get( trans.security.decode_id(id) )
                prepend = util.restore_text( params.get( 'prepend_%i' % sample_dataset.id, ''  ) )
                name = util.restore_text( params.get( 'name_%i' % sample_dataset.id, sample_dataset.name  ) )
                if prepend == 'None':
                    sample_dataset.name = name
                else: 
                    sample_dataset.name = prepend+'_'+name
                trans.sa_session.add( sample_dataset )
                trans.sa_session.flush()
            return trans.fill_template( '/admin/requests/rename_datasets.mako', 
                                        sample=sample, id_list=id_list,
                                        message='Changes saved successfully.',
                                        status='done' )
        return trans.response.send_redirect( web.url_for( controller='requests_admin',
                                                          action='manage_datasets',
                                                          sample_id=sample.id) )


    def __get_files(self, trans, request_type, folder_path):
        '''
        This method retrieves the filenames to be transfer from the remote host.
        '''
        datatx_info = request_type.datatx_info
        if not datatx_info['host'] or not datatx_info['username'] or not datatx_info['password']:
            message = "Error in sequencer login information." 
            return trans.response.send_redirect( web.url_for( controller='requests_common',
                                                              cntrller='requests_admin' ,
                                                              action='show_datatx_page', 
                                                              sample_id=trans.security.encode_id(sample.id),
                                                              status='error',
                                                              message=message))
        def print_ticks(d):
            pass
        cmd  = 'ssh %s@%s "ls -p \'%s\'"' % ( datatx_info['username'],
                                             datatx_info['host'],
                                             folder_path)
        output = pexpect.run(cmd, events={'.ssword:*': datatx_info['password']+'\r\n', 
                                          pexpect.TIMEOUT:print_ticks}, 
                                          timeout=10)
        if 'No such file or directory' in output:
            message = "No such folder (%s) exists on the sequencer." % folder_path
            return trans.response.send_redirect( web.url_for( controller='requests_common',
                                                              cntrller='requests_admin' ,
                                                              action='show_datatx_page',
                                                              sample_id=trans.security.encode_id(sample.id),
                                                              message=message, status='error',
                                                              folder_path=folder_path )) 
        
        return output.splitlines()
    
#    def __get_files_in_dir(self, trans, sample, folder_path):
#        tmpfiles = self.__get_files(trans, sample, folder_path)
#        for tf in tmpfiles:
#            if tf[-1] == os.sep:
#                self.__get_files_in_dir(trans, sample, os.path.join(folder_path, tf))
#            else:
#                sample.dataset_files.append([os.path.join(folder_path, tf),
#                                             sample.transfer_status.NOT_STARTED])
#                trans.sa_session.add( sample )
#                trans.sa_session.flush()
#        return
    

    def __samples_selectbox(self, trans, request, sample_id=None):
        samples_selectbox = SelectField('sample_id')
        for i, s in enumerate(request.samples):
            if str(s.id) == sample_id:
                samples_selectbox.add_option(s.name, s.id, selected=True)
            else:
                samples_selectbox.add_option(s.name, s.id)
        return samples_selectbox
        
    @web.expose
    @web.require_admin
    def get_data(self, trans, **kwd):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' ) 
        try:
            request = trans.sa_session.query( trans.app.model.Request ).get( kwd['request_id']  )
        except:
            return trans.response.send_redirect( web.url_for( controller='requests_admin',
                                                              action='list',
                                                              status='error',
                                                              message="Invalid request ID" ) )
        files_list = util.listify( params.get( 'files_list', ''  ) ) 
        folder_path = util.restore_text( params.get( 'folder_path', 
                                                     request.type.datatx_info['data_dir']  ) )
        sbox = self.__samples_selectbox(trans, request, kwd.get('sample_id', None))
        if not folder_path:
            return trans.fill_template( '/admin/requests/get_data.mako',
                                        cntrller='requests_admin', request=request,
                                        samples_selectbox=sbox, files=[], 
                                        folder_path=folder_path )
        if folder_path[-1] != os.sep:
            folder_path = folder_path+os.sep
        if params.get( 'show_page', False ):
            if kwd.get('sample_id', None):
                sample = trans.sa_session.query( trans.app.model.Sample ).get( kwd['sample_id']  )
                if sample.datasets:
                    folder_path = os.path.dirname(sample.datasets[-1].file_path)
            return trans.fill_template( '/admin/requests/get_data.mako',
                                        cntrller='requests_admin', request=request,
                                        samples_selectbox=sbox, files=[], 
                                        folder_path=folder_path,
                                        status=status, message=message )
        elif params.get( 'browse_button', False ):
            # get the filenames from the remote host
            files = self.__get_files(trans, request.type, folder_path)
            if folder_path[-1] != os.sep:
                folder_path += os.sep
            return trans.fill_template( '/admin/requests/get_data.mako',
                                        cntrller='requests_admin', request=request,
                                        samples_selectbox=sbox, files=files, 
                                        folder_path=folder_path,
                                        status=status, message=message )
        elif params.get( 'folder_up', False ):
            if folder_path[-1] == os.sep:
                folder_path = os.path.dirname(folder_path[:-1])
            # get the filenames from the remote host
            files = self.__get_files(trans, request.type, folder_path)
            if folder_path[-1] != os.sep:
                folder_path += os.sep
            return trans.fill_template( '/admin/requests/get_data.mako',
                                        cntrller='requests_admin',request=request,
                                        samples_selectbox=sbox, files=files, 
                                        folder_path=folder_path,
                                        status=status, message=message )
        elif params.get( 'open_folder', False ):
            if len(files_list) == 1:
                folder_path = os.path.join(folder_path, files_list[0])
            # get the filenames from the remote host
            files = self.__get_files(trans, request.type, folder_path)
            if folder_path[-1] != os.sep:
                folder_path += os.sep
            return trans.fill_template( '/admin/requests/get_data.mako',
                                        cntrller='requests_admin', request=request,
                                        samples_selectbox=sbox, files=files, 
                                        folder_path=folder_path,
                                        status=status, message=message )
        elif params.get( 'select_show_datasets_button', False ):
            sample = trans.sa_session.query( trans.app.model.Sample ).get( kwd['sample_id']  )
            retval = self.__save_sample_datasets(trans, sample, files_list, folder_path)
            if retval: message='The dataset(s) %s have been selected for sample <b>%s</b>' %(str(retval)[1:-1].replace("'", ""), sample.name)
            else: message = None
            return trans.response.send_redirect( web.url_for( controller='requests_admin',
                                                              action='manage_datasets',
                                                              sample_id=sample.id,
                                                              status='done',
                                                              message=message) )
        elif params.get( 'select_more_button', False ):
            sample = trans.sa_session.query( trans.app.model.Sample ).get( kwd['sample_id']  )
            retval = self.__save_sample_datasets(trans, sample, files_list, folder_path)
            if retval: message='The dataset(s) %s have been selected for sample <b>%s</b>' %(str(retval)[1:-1].replace("'", ""), sample.name)
            else: message = None
            return trans.response.send_redirect( web.url_for( controller='requests_admin',
                                                              action='get_data', 
                                                              request_id=sample.request.id,
                                                              folder_path=folder_path,
                                                              sample_id=sample.id,
                                                              open_folder=True,
                                                              status='done',
                                                              message=message))
        return trans.response.send_redirect( web.url_for( controller='requests_admin',
                                                          action='get_data', 
                                                          request_id=sample.request.id,
                                                          folder_path=folder_path,
                                                          show_page=True))
        
    def __save_sample_datasets(self, trans, sample, files_list, folder_path):
        files = []
        if len(files_list):
            for f in files_list:
                filepath = os.path.join(folder_path, f)
                if f[-1] == os.sep:
                    # the selected item is a folder so transfer all the 
                    # folder contents
                    # FIXME 
                    #self.__get_files_in_dir(trans, sample, filepath)
                    return trans.response.send_redirect( web.url_for( controller='requests_admin',
                                                                      action='get_data', 
                                                                      request=sample.request,
                                                                      folder_path=folder_path,
                                                                      open_folder=True))
                else:
                    sample_dataset = trans.app.model.SampleDataset(  sample=sample,
                                                                     file_path=filepath,
                                                                     status=sample.transfer_status.NOT_STARTED,
                                                                     name=self.__dataset_name(sample, filepath.split('/')[-1]),
                                                                     error_msg='',
                                                                     size=sample.dataset_size(filepath))
                    trans.sa_session.add( sample_dataset )
                    trans.sa_session.flush()
                    files.append(str(sample_dataset.name))
        return files
        
    
    def __dataset_name(self, sample, filepath):
        name = filepath.split('/')[-1]
        opt = sample.request.type.datatx_info.get('rename_dataset', sample.request.type.rename_dataset_options.NO) 
        if opt == sample.request.type.rename_dataset_options.NO:
            return name
        elif opt == sample.request.type.rename_dataset_options.SAMPLE_NAME:
            return sample.name+'_'+name
        elif opt == sample.request.type.rename_dataset_options.EXPERIMENT_AND_SAMPLE_NAME:
            return sample.request.name+'_'+sample.name+'_'+name
        elif opt == sample.request.type.rename_dataset_options.EXPERIMENT_NAME:
            return sample.request.name+'_'+name
    def __setup_datatx_user(self, trans, library, folder):
        '''
        This method sets up the datatx user:
        - Checks if the user exists already, if not creates the user
        - Checks if the user had ADD_LIBRARY permission on the target library
          and the target folder, if not sets up the permissions.
        '''
        # Retrieve the upload user login information from the config file
        config = ConfigParser.ConfigParser()
        config.read('transfer_datasets.ini')
        email = config.get("data_transfer_user_login_info", "email")
        password = config.get("data_transfer_user_login_info", "password")
        # check if the user already exists
        datatx_user = trans.sa_session.query( trans.app.model.User ) \
                                      .filter( trans.app.model.User.table.c.email==email ) \
                                      .first()
        if not datatx_user:
            # if not create the user
            datatx_user = trans.app.model.User( email=email )
            datatx_user.set_password_cleartext( password )
            if trans.app.config.use_remote_user:
                datatx_user.external = True
            trans.sa_session.add( datatx_user )
            trans.sa_session.flush()
            trans.app.security_agent.create_private_user_role( datatx_user )
            trans.app.security_agent.user_set_default_permissions( datatx_user, history=False, dataset=False )
        for role in datatx_user.all_roles():
            if role.name == datatx_user.email and role.description == 'Private Role for %s' % datatx_user.email:
                datatx_user_private_role = role
                break
        def check_permission(item_actions, role):
            for item_permission in item_actions:
                if item_permission.action == trans.app.security_agent.permitted_actions.LIBRARY_ADD.action \
                    and item_permission.role.id == role.id:
                    return True
            return False
        # check if this user has 'add' permissions on the target library & folder
        # if not, set 'ADD' permission
        if not check_permission(library.actions, datatx_user_private_role):
            lp = trans.app.model.LibraryPermissions( trans.app.security_agent.permitted_actions.LIBRARY_ADD.action,
                                                     library, 
                                                     datatx_user_private_role )
            trans.sa_session.add( lp )
        if not check_permission(folder.actions, datatx_user_private_role):
            dp = trans.app.model.LibraryFolderPermissions( trans.app.security_agent.permitted_actions.LIBRARY_ADD.action,
                                                           folder, 
                                                           datatx_user_private_role )
            trans.sa_session.add( dp )
            trans.sa_session.flush()
        return datatx_user

    def __send_message(self, trans, datatx_info, sample, id_list):
        '''
        This method creates the xml message and sends it to the rabbitmq server
        '''
        # first create the xml message based on the following template
        xml = \
            ''' <data_transfer>
                    <data_host>%(DATA_HOST)s</data_host>
                    <data_user>%(DATA_USER)s</data_user>
                    <data_password>%(DATA_PASSWORD)s</data_password>
                    <sample_id>%(SAMPLE_ID)s</sample_id>
                    <library_id>%(LIBRARY_ID)s</library_id>
                    <folder_id>%(FOLDER_ID)s</folder_id>
                    %(DATASETS)s
                </data_transfer>'''
        dataset_xml = \
            '''<dataset>
                   <dataset_id>%(ID)s</dataset_id>
                   <name>%(NAME)s</name>
                   <file>%(FILE)s</file>
               </dataset>'''
        datasets = ''
        for id in id_list:
            sample_dataset = trans.sa_session.query( trans.app.model.SampleDataset ).get( trans.security.decode_id(id) )
            if sample_dataset.status == sample.transfer_status.NOT_STARTED:
                datasets = datasets + dataset_xml % dict(ID=str(sample_dataset.id),
                                                         NAME=sample_dataset.name,
                                                         FILE=sample_dataset.file_path)
                sample_dataset.status = sample.transfer_status.IN_QUEUE
                trans.sa_session.add( sample_dataset )
                trans.sa_session.flush()
        data = xml % dict(DATA_HOST=datatx_info['host'],
                          DATA_USER=datatx_info['username'],
                          DATA_PASSWORD=datatx_info['password'],
                          SAMPLE_ID=str(sample.id),
                          LIBRARY_ID=str(sample.library.id),
                          FOLDER_ID=str(sample.folder.id),
                          DATASETS=datasets)
        # now send this message 
        conn = amqp.Connection(host=trans.app.config.amqp['host']+":"+trans.app.config.amqp['port'], 
                               userid=trans.app.config.amqp['userid'], 
                               password=trans.app.config.amqp['password'], 
                               virtual_host=trans.app.config.amqp['virtual_host'], 
                               insist=False)    
        chan = conn.channel()
        msg = amqp.Message(data.replace('\n', '').replace('\r', ''), 
                           content_type='text/plain', 
                           application_headers={'msg_type': 'data_transfer'})
        msg.properties["delivery_mode"] = 2
        chan.basic_publish(msg,
                           exchange=trans.app.config.amqp['exchange'],
                           routing_key=trans.app.config.amqp['routing_key'])
        chan.close()
        conn.close()

    def __start_datatx(self, trans, sample, id_list):
        # data transfer user
        datatx_user = self.__setup_datatx_user(trans, sample.library, sample.folder)
        # validate sequecer information
        datatx_info = sample.request.type.datatx_info
        if not datatx_info['host'] or \
           not datatx_info['username'] or \
           not datatx_info['password']:
            message = "Error in sequencer login information." 
            return trans.response.send_redirect( web.url_for( controller='requests_admin',
                                                              action='manage_datasets',
                                                              sample_id=sample.id,
                                                              status='error',
                                                              message=message) )
        self.__send_message(trans, datatx_info, sample, id_list)
        message="%i dataset(s) have been queued for transfer from the sequencer. Click on <b>Refresh</b> button above to get the latest transfer status." % len(id_list)
        return trans.response.send_redirect( web.url_for( controller='requests_admin',
                                                          action='manage_datasets',
                                                          sample_id=sample.id,
                                                          status='done',
                                                          message=message) )

##
#### Request Type Stuff ###################################################
##
    @web.expose
    @web.require_admin
    def manage_request_types( self, trans, **kwd ):
        if 'operation' in kwd:
            operation = kwd['operation'].lower()
            if not kwd.get( 'id', None ):
                return trans.response.send_redirect( web.url_for( controller='requests_admin',
                                                                  action='manage_request_types',
                                                                  status='error',
                                                                  message="Invalid requesttype ID") )
            if operation == "view":
                return self.__view_request_type( trans, **kwd )
            elif operation == "view_form":
                return self.__view_form( trans, **kwd )
            elif operation == "delete":
                return self.__delete_request_type( trans, **kwd )
            elif operation == "undelete":
                return self.__undelete_request_type( trans, **kwd )
            elif operation == "clone":
                return self.__clone_request_type( trans, **kwd )
            elif operation == "permissions":
                return self.__show_request_type_permissions( trans, **kwd )
        # Render the grid view
        return self.requesttype_grid( trans, **kwd )
    def __view_request_type(self, trans, **kwd):
        try:
            rt = trans.sa_session.query( trans.app.model.RequestType ).get( trans.security.decode_id(kwd['id']) )
        except:
            return trans.response.send_redirect( web.url_for( controller='requests_admin',
                                                              action='manage_request_types',
                                                              status='error',
                                                              message="Invalid requesttype ID") )
        return trans.fill_template( '/admin/requests/view_request_type.mako', 
                                    request_type=rt,
                                    forms=get_all_forms( trans ),
                                    states_list=rt.states,
                                    rename_dataset_selectbox=self.__rename_dataset_selectbox(trans, rt) )
    def __view_form(self, trans, **kwd):
        try:
            fd = trans.sa_session.query( trans.app.model.FormDefinition ).get( trans.security.decode_id(kwd['id']) )
        except:
            return trans.response.send_redirect( web.url_for( controller='requests_admin',
                                                              action='manage_request_types',
                                                              status='error',
                                                              message="Invalid form ID") )
        return trans.fill_template( '/admin/forms/show_form_read_only.mako',
                                    form=fd )

    @web.expose
    @web.require_admin
    def create_request_type( self, trans, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )   
        if params.get( 'add_state_button', False ):
            rt_info, rt_states = self.__create_request_type_form(trans, **kwd)
            rt_states.append(("", ""))
            return trans.fill_template( '/admin/requests/create_request_type.mako', 
                                        rt_info_widgets=rt_info,
                                        rt_states_widgets=rt_states,
                                        message=message,
                                        status=status,
                                        rename_dataset_selectbox=self.__rename_dataset_selectbox(trans))
        elif params.get( 'remove_state_button', False ):
            rt_info, rt_states = self.__create_request_type_form(trans, **kwd)
            index = int(params.get( 'remove_state_button', '' ).split(" ")[2])
            del rt_states[index-1]
            return trans.fill_template( '/admin/requests/create_request_type.mako', 
                                        rt_info_widgets=rt_info,
                                        rt_states_widgets=rt_states,
                                        message=message,
                                        status=status,
                                        rename_dataset_selectbox=self.__rename_dataset_selectbox(trans))
        elif params.get( 'save_request_type', False ):
            rt, message = self.__save_request_type(trans, **kwd)
            if not rt:
                return trans.fill_template( '/admin/requests/create_request_type.mako', 
                                            forms=get_all_forms( trans ),
                                            message=message,
                                            status='error')
            return trans.response.send_redirect( web.url_for( controller='requests_admin',
                                                              action='manage_request_types',
                                                              message='Request type <b>%s</b> has been created' % rt.name,
                                                              status='done') )
        elif params.get( 'save_changes', False ):
            try:
                rt = trans.sa_session.query( trans.app.model.RequestType ).get( int(kwd['rt_id']) )
            except:
                return trans.response.send_redirect( web.url_for( controller='requests_admin',
                                                                  action='manage_request_types',
                                                                  message='Invalid request type ID',
                                                                  status='error') )
            # data transfer info
            rt.datatx_info = dict(host=util.restore_text( params.get( 'host', ''  ) ),
                                  username=util.restore_text( params.get( 'username', ''  ) ),
                                  password=params.get( 'password', '' ),
                                  data_dir=util.restore_text( params.get( 'data_dir', ''  ) ),
                                  rename_dataset=util.restore_text( params.get('rename_dataset', False) ))
            if rt.datatx_info.get('data_dir', '') and rt.datatx_info.get('data_dir', '')[-1] != os.sep:
                rt.datatx_info['data_dir'] = rt.datatx_info['data_dir']+os.sep
            trans.sa_session.add( rt )
            trans.sa_session.flush()
            return trans.response.send_redirect( web.url_for( controller='requests_admin',
                                                              action='manage_request_types',
                                                              operation='view',
                                                              id=trans.security.encode_id(rt.id),
                                                              message='Changes made to request type <b>%s</b> has been saved' % rt.name,
                                                              status='done') )
        else:
            rt_info, rt_states = self.__create_request_type_form(trans, **kwd)
            return trans.fill_template( '/admin/requests/create_request_type.mako',
                                        rt_info_widgets=rt_info,
                                        rt_states_widgets=rt_states,
                                        message=message,
                                        status=status,
                                        rename_dataset_selectbox=self.__rename_dataset_selectbox(trans))
    def __create_request_type_form(self, trans, **kwd):
        request_forms=get_all_forms( trans, 
                                     filter=dict(deleted=False),
                                     form_type=trans.app.model.FormDefinition.types.REQUEST )
        sample_forms=get_all_forms( trans, 
                                    filter=dict(deleted=False),
                                    form_type=trans.app.model.FormDefinition.types.SAMPLE )
        if not len(request_forms) or not len(sample_forms):
            return [],[]
        params = util.Params( kwd )
        rt_info = []
        rt_info.append(dict(label='Name', 
                            widget=TextField('name', 40, util.restore_text( params.get( 'name', ''  ) ) ) ))
        rt_info.append(dict(label='Description', 
                            widget=TextField('desc', 40, util.restore_text( params.get( 'desc', ''  ) ) ) ))

        rf_selectbox = SelectField('request_form_id')
        for fd in request_forms:
            if str(fd.id) == params.get( 'request_form_id', ''  ):
                rf_selectbox.add_option(fd.name, fd.id, selected=True)
            else:
                rf_selectbox.add_option(fd.name, fd.id)
        rt_info.append(dict(label='Request form', 
                            widget=rf_selectbox ))

        sf_selectbox = SelectField('sample_form_id')
        for fd in sample_forms:
            if str(fd.id) == params.get( 'sample_form_id', ''  ):
                sf_selectbox.add_option(fd.name, fd.id, selected=True)
            else:
                sf_selectbox.add_option(fd.name, fd.id)
        rt_info.append(dict(label='Sample form', 
                            widget=sf_selectbox ))
        # possible sample states
        rt_states = []
        i=0
        while True:
            if kwd.has_key( 'state_name_%i' % i ):
                rt_states.append((params.get( 'state_name_%i' % i, ''  ), 
                                  params.get( 'state_desc_%i' % i, ''  )))
                i=i+1
            else:
                break
        return rt_info, rt_states
    
    def __rename_dataset_selectbox(self, trans, rt=None):
        if rt:
            sel_opt = rt.datatx_info.get('rename_dataset', trans.app.model.RequestType.rename_dataset_options.NO)
        else:
            sel_opt = trans.app.model.RequestType.rename_dataset_options.NO
        rename_dataset_selectbox = SelectField('rename_dataset')
        for opt, opt_name in trans.app.model.RequestType.rename_dataset_options.items():
            if sel_opt == opt_name: 
                rename_dataset_selectbox.add_option(opt_name, opt_name, selected=True)
            else:
                rename_dataset_selectbox.add_option(opt_name, opt_name)
        return rename_dataset_selectbox  
    
    def __save_request_type(self, trans, **kwd):
        params = util.Params( kwd )
        rt = trans.app.model.RequestType() 
        rt.name = util.restore_text( params.get( 'name', ''  ) ) 
        rt.desc = util.restore_text( params.get( 'desc', '' ) )
        rt.request_form = trans.sa_session.query( trans.app.model.FormDefinition ).get( int( params.request_form_id ) )
        rt.sample_form = trans.sa_session.query( trans.app.model.FormDefinition ).get( int( params.sample_form_id ) )
        # data transfer info
        rt.datatx_info = dict(host=util.restore_text( params.get( 'host', ''  ) ),
                              username=util.restore_text( params.get( 'username', ''  ) ),
                              password=params.get( 'password', '' ),
                              data_dir=util.restore_text( params.get( 'data_dir', ''  ) ),
                              rename_dataset=util.restore_text( params.get('rename_dataset', '') ))
        if rt.datatx_info.get('data_dir', '') and rt.datatx_info.get('data_dir', '')[-1] != os.sep:
             rt.datatx_info['data_dir'] = rt.datatx_info['data_dir']+os.sep
        trans.sa_session.add( rt )
        trans.sa_session.flush()
        # set sample states
        ss_list = trans.sa_session.query( trans.app.model.SampleState ).filter( trans.app.model.SampleState.table.c.request_type_id == rt.id )
        for ss in ss_list:
            trans.sa_session.delete( ss )
            trans.sa_session.flush()
        i=0
        while True:
            if kwd.has_key( 'state_name_%i' % i ):
                name = util.restore_text( params.get( 'state_name_%i' % i, None ))
                desc = util.restore_text( params.get( 'state_desc_%i' % i, None ))
                ss = trans.app.model.SampleState(name, desc, rt) 
                trans.sa_session.add( ss )
                trans.sa_session.flush()
                i = i + 1
            else:
                break
        message = "The new request type named '%s' with %s state(s) has been created" % (rt.name, i)
        return rt, message
    def __delete_request_type( self, trans, **kwd ):
        id_list = util.listify( kwd['id'] )
        for id in id_list:
            try:
                rt = trans.sa_session.query( trans.app.model.RequestType ).get( trans.security.decode_id(id) )
            except:
                return trans.response.send_redirect( web.url_for( controller='requests_admin',
                                                                  action='manage_request_types',
                                                                  message='Invalid request type ID',
                                                                  status='error') )
            rt.deleted = True
            trans.sa_session.add( rt )
            trans.sa_session.flush()
        return trans.response.send_redirect( web.url_for( controller='requests_admin',
                                                          action='manage_request_types',
                                                          message='%i request type(s) has been deleted' % len(id_list),
                                                          status='done') )
    def __undelete_request_type( self, trans, **kwd ):
        id_list = util.listify( kwd['id'] )
        for id in id_list:
            try:
                rt = trans.sa_session.query( trans.app.model.RequestType ).get( trans.security.decode_id(id) )
            except:
                return trans.response.send_redirect( web.url_for( controller='requests_admin',
                                                                  action='manage_request_types',
                                                                  message='Invalid request type ID',
                                                                  status='error') )
            rt.deleted = False
            trans.sa_session.add( rt )
            trans.sa_session.flush()
        return trans.response.send_redirect( web.url_for( controller='requests_admin',
                                                          action='manage_request_types',
                                                          message='%i request type(s) has been undeleted' % len(id_list),
                                                          status='done') )
    def __show_request_type_permissions(self, trans, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        try:
            rt = trans.sa_session.query( trans.app.model.RequestType ).get( trans.security.decode_id(kwd['id']) )
        except:
            return trans.response.send_redirect( web.url_for( controller='requests_admin',
                                                              action='manage_request_types',
                                                              status='error',
                                                              message="Invalid requesttype ID") )
        roles = trans.sa_session.query( trans.app.model.Role ) \
                                .filter( trans.app.model.Role.table.c.deleted==False ) \
                                .order_by( trans.app.model.Role.table.c.name )
        if params.get( 'update_roles_button', False ):
            permissions = {}
            for k, v in trans.app.model.RequestType.permitted_actions.items():
                in_roles = [ trans.sa_session.query( trans.app.model.Role ).get( x ) for x in util.listify( params.get( k + '_in', [] ) ) ]
                permissions[ trans.app.security_agent.get_action( v.action ) ] = in_roles
            trans.app.security_agent.set_request_type_permissions( rt, permissions )
            trans.sa_session.refresh( rt )
            message = "Permissions updated for request type '%s'" % rt.name
        return trans.fill_template( '/admin/requests/request_type_permissions.mako',
                                    request_type=rt,
                                    roles=roles,
                                    status=status,
                                    message=message)



