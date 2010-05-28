from galaxy.web.base.controller import *
from galaxy.web.framework.helpers import time_ago, iff, grids
from galaxy.model.orm import *
from galaxy.datatypes import sniff
from galaxy import model, util
from galaxy.util.streamball import StreamBall
from galaxy.util.odict import odict
import logging, tempfile, zipfile, tarfile, os, sys
from galaxy.web.form_builder import * 
from datetime import datetime, timedelta
from cgi import escape, FieldStorage

log = logging.getLogger( __name__ )

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
        def filter( self, db_session, user, query, column_filter ):
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
    # Grid definition
    title = "Sequencing Requests"
    template = 'requests/grid.mako'
    model_class = model.Request
    default_sort_key = "create_time"
    num_rows_per_page = 50
    preserve_state = True
    use_paging = True
    default_filter = dict( deleted="False")
    columns = [
        NameColumn( "Name", 
                    key="name", 
                    model_class=model.Request,
                    link=( lambda item: iff( item.deleted, None, dict( operation="show_request", id=item.id ) ) ),
                    attach_popup=True, 
                    filterable="advanced" ),
        DescriptionColumn( "Description",
                           key='desc',
                           model_class=model.Request,
                           filterable="advanced" ),
        SamplesColumn( "Sample(s)", 
                       link=( lambda item: iff( item.deleted, None, dict( operation="show_request", id=item.id ) ) ), ),
        TypeColumn( "Type" ),
        grids.GridColumn( "Last Updated", key="update_time", format=time_ago ),
        grids.DeletedColumn( "Deleted", 
                       key="deleted", 
                       visible=False, 
                       filterable="advanced" ),
        StateColumn( "State", 
                     model_class=model.Request,
                     event_class=model.RequestEvent,
                     key='state',
                     filterable="advanced",
                     link=( lambda item: iff( item.deleted, None, dict( operation="events", id=item.id ) ) ) )
    ]
    columns.append( grids.MulticolFilterColumn( "Search", 
                                                cols_to_filter=[ columns[0], columns[1] ], 
                                                key="free-text-search",
                                                visible=False,
                                                filterable="standard" ) )
    operations = [
        grids.GridOperation( "Submit", allow_multiple=False, condition=( lambda item: not item.deleted and item.unsubmitted() and item.samples ),
                             confirm="More samples cannot be added to this request once it is submitted. Click OK to submit."  ),
        grids.GridOperation( "Edit", allow_multiple=False, condition=( lambda item: not item.deleted and item.unsubmitted() )  ),
        grids.GridOperation( "Delete", allow_multiple=True, condition=( lambda item: not item.deleted and item.new() )  ),
        grids.GridOperation( "Undelete", allow_multiple=True, condition=( lambda item: item.deleted )  )

    ]
    global_actions = [
        grids.GridAction( "Create new request", dict( controller='requests', 
                                                      action='new', 
                                                      select_request_type='True' ) )
    ]
    def apply_query_filter( self, trans, query, **kwd ):
        return query.filter_by( user=trans.user )

class Requests( BaseController ):
    request_grid = RequestsGrid()

    @web.expose
    @web.require_login( "create/submit sequencing requests" )
    def index( self, trans ):
        return trans.fill_template( "requests/index.mako" )

    @web.expose
    @web.require_login( "create/submit sequencing requests" )
    def list( self, trans, **kwd ):
        '''
        List all request made by the current user
        '''
        
        if 'operation' in kwd:
            operation = kwd['operation'].lower()
            if not kwd.get( 'id', None ):
                return trans.response.send_redirect( web.url_for( controller='requests',
                                                                  action='list',
                                                                  status='error',
                                                                  message="Invalid request ID") )
            if operation == "show_request":
                return self.__show_request( trans, **kwd )
            elif operation == "submit":
                return self.__submit_request( trans, **kwd )
            elif operation == "delete":
                return self.__delete_request( trans, **kwd )
            elif operation == "undelete":
                return self.__undelete_request( trans, **kwd )
            elif operation == "edit":
                return self.__edit_request( trans, **kwd )
            elif operation == "events":
                return self.__request_events( trans, **kwd )
        # if there are one or more requests that has been rejected by the admin
        # recently, then show a message as a reminder to the user
        rlist = trans.sa_session.query( trans.app.model.Request ) \
                                .filter( trans.app.model.Request.table.c.deleted==False ) \
                                .filter( trans.app.model.Request.table.c.user_id==trans.user.id )
        rejected = 0
        for r in rlist:
            if r.rejected():
                rejected = rejected + 1
        if rejected:
            kwd['status'] = 'warning'
            kwd['message'] = "%d requests (highlighted in red) were rejected, click on the request name for details." \
                             % rejected 
        # Render the list view
        return self.request_grid( trans, **kwd )
    def __request_events(self, trans, **kwd):
        try:
            request = trans.sa_session.query( trans.app.model.Request ).get( trans.security.decode_id(kwd['id']) )
        except:
            message = "Invalid request ID"
            log.warn( message )
            return trans.response.send_redirect( web.url_for( controller='requests',
                                                              action='list',
                                                              status='error',
                                                              message=message,
                                                              **kwd) )
        events_list = []
        all_events = request.events
        for event in all_events:         
            events_list.append((event.state, time_ago(event.update_time), event.comment))
        return trans.fill_template( '/requests/events.mako', 
                                    events_list=events_list, request=request)
    def request_details(self, trans, id):
        '''
        Shows the request details
        '''
        request = trans.sa_session.query( trans.app.model.Request ).get( id )
        # list of widgets to be rendered on the request form
        request_details = []
        # main details
        request_details.append(dict(label='Description', 
                                    value=request.desc, 
                                    helptext=''))
        request_details.append(dict(label='Type', 
                                    value=request.type.name, 
                                    helptext=''))

        request_details.append(dict(label='State', 
                                    value=request.state(), 
                                    helptext=''))
        request_details.append(dict(label='Date created', 
                                    value=request.create_time, 
                                    helptext=''))
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
        if request.notify:
            notify = 'Yes'
        else:
            notify = 'No'
        request_details.append(dict(label='Send email notification once the sequencing request is complete', 
                                    value=notify, 
                                    helptext=''))
        return request_details   
    def __show_request(self, trans, **kwd):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        add_sample = params.get('add_sample', False)
        try:
            request = trans.sa_session.query( trans.app.model.Request ).get( trans.security.decode_id(kwd['id']) )
        except:
            return trans.response.send_redirect( web.url_for( controller='requests',
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
                                        dataset_files=s.dataset_files,
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
                                        dataset_files=[],
                                        field_values=['' for field in request.type.sample_form.fields],
                                        lib_widget=lib_widget,
                                        folder_widget=folder_widget))
        return trans.fill_template( '/requests/show_request.mako',
                                    request=request,
                                    request_details=self.request_details(trans, request.id),
                                    current_samples=current_samples,
                                    sample_copy=self.__copy_sample(current_samples), 
                                    details='hide', edit_mode=util.restore_text( params.get( 'edit_mode', 'False'  ) ),
                                    message=message, status=status )
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
                    sample_info['lib_widget'], sample_info['folder_widget'] = self.__library_widgets(trans, 
                                                                                                     request.user, 
                                                                                                     sample_index, 
                                                                                                     libraries, 
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
    def __copy_sample(self, current_samples):
        copy_list = SelectField('copy_sample')
        copy_list.add_option('None', -1, selected=True)  
        for i, s in enumerate(current_samples):
            copy_list.add_option(s['name'], i)
        return copy_list
    def __import_samples(self, trans, request, current_samples, details, libraries, **kwd):
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
            return trans.fill_template( '/admin/requests/show_request.mako',
                                        request=request,
                                        request_details=self.request_details(trans, request.id),
                                        current_samples=current_samples,
                                        sample_copy=self.__copy_sample(current_samples), 
                                        details=details,
                                        edit_mode=edit_mode)
        except:
            return trans.response.send_redirect( web.url_for( controller='requests',
                                                          action='list',
                                                          operation='show_request',
                                                          id=trans.security.encode_id(request.id),
                                                          status='error',
                                                          message='Error in importing samples file' ))

    @web.expose
    @web.require_login( "create/submit sequencing requests" )
    def show_request(self, trans, **kwd):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        try:
            request = trans.sa_session.query( trans.app.model.Request ).get( int( params.get( 'request_id', None ) ) )
        except:
            return trans.response.send_redirect( web.url_for( controller='requests',
                                                              action='list',
                                                              status='error',
                                                              message="Invalid request ID",
                                                              **kwd) )
        # get the user entered sample details
        current_samples, details, edit_mode, libraries = self.__update_samples( trans, request, **kwd )
        if params.get('import_samples_button', False) == 'Import samples':
            return self.__import_samples(trans, request, current_samples, details, libraries, **kwd)
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
            return trans.fill_template( '/requests/show_request.mako',
                                        request=request,
                                        request_details=self.request_details(trans, request.id),
                                        current_samples=current_samples,
                                        sample_copy=self.__copy_sample(current_samples), 
                                        details=details,
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
                return trans.fill_template( '/requests/show_request.mako',
                                            request=request,
                                            request_details=self.request_details(trans, request.id),
                                            current_samples = current_samples,
                                            sample_copy=self.__copy_sample(current_samples), 
                                            details=details, edit_mode=edit_mode,
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
                                               current_samples[sample_index]['folder'], 
                                               dataset_files=[])
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
                            sample.bar_code = current_samples[sample_index]['barcode']
                    trans.sa_session.add( sample )
                    trans.sa_session.flush()
                    form_values = trans.sa_session.query( trans.app.model.FormValues ).get( sample.values.id )
                    form_values.content = current_samples[sample_index]['field_values']
                    trans.sa_session.add( form_values )
                    trans.sa_session.flush()
            return trans.response.send_redirect( web.url_for( controller='requests',
                                                          action='list',
                                                          operation='show_request',
                                                          id=trans.security.encode_id(request.id),
                                                          status=status,
                                                          message=message ))
        elif params.get('edit_samples_button', False) == 'Edit samples':
            edit_mode = 'True'
            return trans.fill_template( '/requests/show_request.mako',
                                        request=request,
                                        request_details=self.request_details(trans, request.id),
                                        current_samples=current_samples,
                                        sample_copy=self.__copy_sample(current_samples), 
                                        details=details, libraries=libraries,
                                        edit_mode=edit_mode)
        elif params.get('cancel_changes_button', False) == 'Cancel':
            return trans.response.send_redirect( web.url_for( controller='requests',
                                                          action='list',
                                                          operation='show_request',
                                                          id=trans.security.encode_id(request.id)) )
        else:
            return trans.fill_template( '/requests/show_request.mako',
                                        request=request,
                                        request_details=self.request_details(trans, request.id),
                                        current_samples=current_samples,
                                        sample_copy=self.__copy_sample(current_samples), 
                                        details=details, libraries=libraries,
                                        edit_mode=edit_mode, status=status, message=message)

            
    @web.expose
    @web.require_login( "create/submit sequencing requests" )
    def delete_sample(self, trans, **kwd):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        request = trans.sa_session.query( trans.app.model.Request ).get( int( params.get( 'request_id', 0 ) ) )
        current_samples, details, edit_mode = self.__update_samples( request, **kwd )
        sample_index = int(params.get('sample_id', 0))
        sample_name = current_samples[sample_index]['name']
        s = request.has_sample(sample_name)
        if s:
            trans.sa_session.delete( s.values )
            trans.sa_session.delete( s )
            trans.sa_session.flush()
        del current_samples[sample_index]  
        return trans.fill_template( '/requests/show_request.mako',
                                    request=request,
                                    request_details=self.request_details(trans, request.id),
                                    current_samples = current_samples,
                                    sample_copy=self.__copy_sample(current_samples), 
                                    details=details,
                                    edit_mode=edit_mode)
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
    @web.expose
    @web.require_login( "create/submit sequencing requests" )
    def new(self, trans, **kwd):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        if params.get('select_request_type', False) == 'True':
            return trans.fill_template( '/requests/new_request.mako',
                                        select_request_type=self.__select_request_type(trans, 'none'),                                 
                                        widgets=[],                                   
                                        message=message,
                                        status=status)
        elif params.get('create', False) == 'True':
            if params.get('create_request_button', False) == 'Save' \
               or params.get('create_request_samples_button', False) == 'Add samples':
                request_type = trans.sa_session.query( trans.app.model.RequestType ).get( int( params.select_request_type ) )
                if not util.restore_text(params.get('name', '')):
                    message = 'Please enter the <b>Name</b> of the request'
                    kwd['create'] = 'True'
                    kwd['status'] = 'error'
                    kwd['message'] = message
                    kwd['create_request_button'] = None
                    kwd['create_request_samples_button'] = None
                    return trans.response.send_redirect( web.url_for( controller='requests',
                                                                      action='new',
                                                                      **kwd) )
                request = self.__save_request(trans, None, **kwd)
                message = 'The new request named <b>%s</b> has been created' % request.name
                if params.get('create_request_button', False) == 'Save':
                    return trans.response.send_redirect( web.url_for( controller='requests',
                                                                      action='list',
                                                                      message=message ,
                                                                      status='done') )
                elif params.get('create_request_samples_button', False) == 'Add samples':
                    new_kwd = {}
                    new_kwd['id'] = trans.security.encode_id(request.id)
                    new_kwd['operation'] = 'show_request'
                    new_kwd['add_sample'] = True
                    return trans.response.send_redirect( web.url_for( controller='requests',
                                                                      action='list',
                                                                      message=message ,
                                                                      status='done',
                                                                      **new_kwd) )
            else:
                return self.__show_request_form(trans, **kwd)
        elif params.get('refresh', False) == 'true':
            return self.__show_request_form(trans, **kwd)
    def __show_request_form(self, trans, **kwd):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        try:
            request_type = trans.sa_session.query( trans.app.model.RequestType ).get( int( params.select_request_type ) )
        except:
            return trans.fill_template( '/requests/new_request.mako',
                                        select_request_type=self.__select_request_type(trans, 'none'),                                 
                                        widgets=[],                                   
                                        message=message,
                                        status=status)
        form_values = None
        select_request_type = self.__select_request_type(trans, request_type.id)
        # list of widgets to be rendered on the request form
        widgets = []
        widgets.append(dict(label='Name of the Experiment', 
                            widget=TextField('name', 40, 
                                             util.restore_text( params.get( 'name', ''  ) )), 
                            helptext='(Required)'))
        widgets.append(dict(label='Description', 
                            widget=TextField('desc', 40,
                                             util.restore_text( params.get( 'desc', ''  ) )), 
                            helptext='(Optional)'))
        widgets = widgets + request_type.request_form.get_widgets( trans.user, **kwd )
        widgets.append(dict(label='Send email notification once the sequencing request is complete', 
                            widget=CheckboxField('email_notify', False), 
                            helptext=''))
        return trans.fill_template( '/requests/new_request.mako',
                                    select_request_type=select_request_type,
                                    request_type=request_type,
                                    widgets=widgets,
                                    message=message,
                                    status=status)
    def __validate(self, trans, request):
        '''
        Validates the request entered by the user 
        '''
        empty_fields = []
        # check rest of the fields of the form
        for index, field in enumerate(request.type.request_form.fields):
            if field['required'] == 'required' and request.values.content[index] in ['', None]:
                empty_fields.append(field['label'])
        if empty_fields:
            message = 'Fill the following fields of the request <b>%s</b> before submitting<br/>' % request.name
            for ef in empty_fields:
                message = message + '<b>' +ef + '</b><br/>'
            return trans.response.send_redirect( web.url_for( controller='requests',
                                                              action='list',
                                                              operation='edit',
                                                              status = 'error',
                                                              message=message,
                                                              id=trans.security.encode_id(request.id) ))
        # now check the required fields of all the samples of this request
        for s in request.samples:
            for index, field in enumerate(request.type.sample_form.fields):
                if field['required'] == 'required' and s.values.content[index] in ['', None]:
                    empty_fields.append((s.name, field['label']))
        if empty_fields:
            message = 'Fill the following fields of the request <b>%s</b> before submitting<br/>' % request.name
            for sname, ef in empty_fields:
                message = message + '<b>%s</b> field of sample <b>%s</b><br/>' % (ef, sname)
            return trans.response.send_redirect( web.url_for( controller='requests',
                                                              action='list',
                                                              operation='show_request',
                                                              status = 'error',
                                                              message=message,
                                                              id=trans.security.encode_id(request.id) ))
    def __save_request(self, trans, request=None, **kwd):
        '''
        This method saves a new request if request_id is None. 
        '''
        params = util.Params( kwd )
        request_type = trans.sa_session.query( trans.app.model.RequestType ).get( int( params.select_request_type ) )
        name = util.restore_text(params.get('name', ''))
        desc = util.restore_text(params.get('desc', ''))
        notify = CheckboxField.is_checked( params.get('email_notify', '') )
        # library
        try:
            library = trans.sa_session.query( trans.app.model.Library ).get( int( params.get( 'library_id', None ) ) )
        except:
            library = None
        try:
            folder = trans.sa_session.query( trans.app.model.LibraryFolder ).get( int( params.get( 'folder_id', None ) ) )
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
                    trans.sa_session.add( user_address )
                    trans.sa_session.flush()
                    trans.sa_session.refresh( trans.user )
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
                                              trans.user, form_values, notify)
            trans.sa_session.add( request )
            trans.sa_session.flush()
            trans.sa_session.refresh( request )
            # create an event with state 'New' for this new request
            comments = "Request created."
            event = trans.app.model.RequestEvent(request, request.states.NEW, comments)
            trans.sa_session.add( event )
            trans.sa_session.flush()
        else:
            request.name = name
            request.desc = desc
            request.type = request_type
            request.user = trans.user
            request.values = form_values
            request.notify = notify
            trans.sa_session.add( request )
            trans.sa_session.flush()
        return request
    @web.expose
    @web.require_login( "create/submit sequencing requests" )
    def edit(self, trans, **kwd):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        try:
            request = trans.sa_session.query( trans.app.model.Request ).get( int( params.get( 'request_id', None ) ) )
        except:
            return trans.response.send_redirect( web.url_for( controller='requests',
                                                              action='list',
                                                              status='error',
                                                              message="Invalid request ID",
                                                              **kwd) )
        if params.get('show', False) == 'True':
            return self.__edit_request(trans, id=trans.security.encode_id(request.id), **kwd)
        elif params.get('save_changes_request_button', False) == 'Save changes' \
             or params.get('edit_samples_button', False) == 'Edit samples':
                request_type = trans.sa_session.query( trans.app.model.RequestType ).get( int( params.select_request_type ) )
                if not util.restore_text(params.get('name', '')):
                    message = 'Please enter the <b>Name</b> of the request'
                    kwd['status'] = 'error'
                    kwd['message'] = message
                    kwd['show'] = 'True'
                    return trans.response.send_redirect( web.url_for( controller='requests',
                                                                      action='edit',
                                                                      **kwd) )
                request = self.__save_request(trans, request, **kwd)
                message = 'The changes made to the request named %s has been saved' % request.name
                if params.get('save_changes_request_button', False) == 'Save changes':
                    return trans.response.send_redirect( web.url_for( controller='requests',
                                                                      action='list',
                                                                      message=message ,
                                                                      status='done') )
                elif params.get('edit_samples_button', False) == 'Edit samples':
                    new_kwd = {}
                    new_kwd['request_id'] = request.id
                    new_kwd['edit_samples_button'] = 'Edit samples'
                    return trans.response.send_redirect( web.url_for( controller='requests',
                                                                      action='show_request',
                                                                      message=message ,
                                                                      status='done',
                                                                      **new_kwd) )
        elif params.get('refresh', False) == 'true':
            return self.__edit_request(trans, id=trans.security.encode_id(request.id), **kwd)
            
    def __edit_request(self, trans, **kwd):
        try:
            request = trans.sa_session.query( trans.app.model.Request ).get( trans.security.decode_id(kwd['id']) )
        except:
            message = "Invalid request ID"
            log.warn( message )
            return trans.response.send_redirect( web.url_for( controller='requests',
                                                              action='list',
                                                              status='error',
                                                              message=message) )
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
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
        widgets = widgets + request.type.request_form.get_widgets( trans.user, request.values.content, **kwd )
        widgets.append(dict(label='Send email notification once the sequencing request is complete', 
                            widget=CheckboxField('email_notify', request.notify), 
                            helptext=''))
        return trans.fill_template( '/requests/edit_request.mako',
                                    select_request_type=select_request_type,
                                    request_type=request.type,
                                    request=request,
                                    widgets=widgets,
                                    message=message,
                                    status=status)
        return self.__show_request_form(trans)
    def __delete_request(self, trans, **kwd):
        id_list = util.listify( kwd['id'] )
        delete_failed = []
        for id in id_list:
            try:
                request = trans.sa_session.query( trans.app.model.Request ).get( trans.security.decode_id(id) )
            except:
                message = "Invalid request ID"
                log.warn( message )
                return trans.response.send_redirect( web.url_for( controller='requests',
                                                                  action='list',
                                                                  status='error',
                                                                  message=message,
                                                                  **kwd) )
            # a request cannot be deleted once its submitted
            if not request.new():
                delete_failed.append(request.name)
            else:
                request.deleted = True
                trans.sa_session.add( request )
                # delete all the samples belonging to this request
                for s in request.samples:
                    s.deleted = True
                    trans.sa_session.add( s )
                trans.sa_session.flush()
        if not len(delete_failed):
            message = '%i request(s) has been deleted.' % len(id_list)
            status = 'done'
        else:
            message = '%i request(s) has been deleted. %i request %s could not be deleted as they have been submitted.' % (len(id_list)-len(delete_failed), 
                                                                                                               len(delete_failed), str(delete_failed))
            status = 'warning'
        return trans.response.send_redirect( web.url_for( controller='requests',
                                                          action='list',
                                                          status=status,
                                                          message=message) )
    def __undelete_request(self, trans, **kwd):
        id_list = util.listify( kwd['id'] )
        for id in id_list:
            try:
                request = trans.sa_session.query( trans.app.model.Request ).get( trans.security.decode_id(id) )
            except:
                message = "Invalid request ID"
                log.warn( message )
                return trans.response.send_redirect( web.url_for( controller='requests',
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
        return trans.response.send_redirect( web.url_for( controller='requests',
                                                          action='list',
                                                          status='done',
                                                          message='%i request(s) has been undeleted.' % len(id_list) ) )
    def __submit_request(self, trans, **kwd):
        try:
            request = trans.sa_session.query( trans.app.model.Request ).get( trans.security.decode_id(kwd['id']) )
        except:
            message = "Invalid request ID"
            log.warn( message )
            return trans.response.send_redirect( web.url_for( controller='requests',
                                                              action='list',
                                                              status='error',
                                                              message=message,
                                                              **kwd) )
        # check if all the required request and its sample fields have been filled 
        self.__validate(trans, request)
        # change the request state to 'Submitted'
        comments = "Sequencing request is in progress."
        event = trans.app.model.RequestEvent(request, request.states.SUBMITTED, comments)
        trans.sa_session.add( event )
        trans.sa_session.flush()
        # get the new state
        new_state = request.type.states[0]
        for s in request.samples:
            event = trans.app.model.SampleEvent(s, new_state, 'Samples submitted to the system')
            trans.sa_session.add( event )
            trans.sa_session.flush()
        return trans.response.send_redirect( web.url_for( controller='requests',
                                                          action='list',
                                                          id=trans.security.encode_id(request.id),
                                                          status='done',
                                                          message='The request <b>%s</b> has been submitted.' % request.name
                                                          ) )
    @web.expose
    @web.require_login( "create/submit sequencing requests" )
    def show_events(self, trans, **kwd):
        params = util.Params( kwd )
        try:
            sample_id = int(params.get('sample_id', False))
            sample = trans.sa_session.query( trans.app.model.Sample ).get( sample_id )
        except:
            message = "Invalid sample ID"
            return trans.response.send_redirect( web.url_for( controller='requests',
                                                              action='list',
                                                              status='error',
                                                              message=message,
                                                              **kwd) )
        events_list = []
        all_events = sample.events
        for event in all_events:
            events_list.append((event.state.name, event.state.desc, time_ago(event.update_time), event.comment))
        return trans.fill_template( '/sample/sample_events.mako', 
                                    events_list=events_list,
                                    sample_name=sample.name,
                                    request=sample.request)
    #
    # Data transfer from sequencer
    #
    @web.expose
    @web.require_login( "create/submit sequencing requests" )
    def show_datatx_page( self, trans, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' ) 
        try:
            sample = trans.sa_session.query( trans.app.model.Sample ).get( trans.security.decode_id( kwd['sample_id'] ) )
        except:
            return trans.response.send_redirect( web.url_for( controller='requests',
                                                              action='list',
                                                              status='error',
                                                              message="Invalid sample ID",
                                                              **kwd) )
        return trans.fill_template( '/requests/show_data.mako', 
                                    sample=sample, dataset_files=sample.dataset_files )
