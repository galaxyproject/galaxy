"""
Upload class
"""

from galaxy.web.base.controller import *
from galaxy.util.bunch import Bunch
from galaxy.tools import DefaultToolState
from galaxy.tools.parameters.basic import UnvalidatedValue
from galaxy.tools.actions import upload_common

import logging
log = logging.getLogger( __name__ )

class AddFrameData:
    def __init__( self ):
        self.wiki_url = None
        self.debug = None
        self.from_noframe = None

class ToolRunner( BaseUIController ):

    #Hack to get biomart to work, ideally, we could pass tool_id to biomart and receive it back
    @web.expose
    def biomart(self, trans, tool_id='biomart', **kwd):
        """Catches the tool id and redirects as needed"""
        return self.index(trans, tool_id=tool_id, **kwd)

    #test to get hapmap to work, ideally, we could pass tool_id to hapmap biomart and receive it back
    @web.expose
    def hapmapmart(self, trans, tool_id='hapmapmart', **kwd):
        """Catches the tool id and redirects as needed"""
        return self.index(trans, tool_id=tool_id, **kwd)

    @web.expose
    def default(self, trans, tool_id=None, **kwd):
        """Catches the tool id and redirects as needed"""
        return self.index(trans, tool_id=tool_id, **kwd)

    @web.expose
    def index(self, trans, tool_id=None, from_noframe=None, **kwd):
        # No tool id passed, redirect to main page
        if tool_id is None:
            return trans.response.send_redirect( url_for( "/static/welcome.html" ) )
        # Load the tool
        toolbox = self.get_toolbox()
        #Backwards compatibility for datasource tools that have default tool_id configured, but which are now using only GALAXY_URL
        if isinstance( tool_id, list ):
            tool_ids = tool_id
        else:
            tool_ids = [ tool_id ]
        for tool_id in tool_ids:
            tool = toolbox.get_tool( tool_id )
            if tool:
                break
        # No tool matching the tool id, display an error (shouldn't happen)
        if not tool:
            tool_id = ','.join( tool_ids )
            log.error( "index called with tool id '%s' but no such tool exists", tool_id )
            trans.log_event( "Tool id '%s' does not exist" % tool_id )
            return "Tool '%s' does not exist, kwd=%s " % (tool_id, kwd)
        if tool.require_login and not trans.user:
            return trans.response.send_redirect( url_for( controller='user', action='login', cntrller='user', message="You must be logged in to use this tool.", status="info", redirect=url_for( controller='/tool_runner', action='index', tool_id=tool_id, **kwd ) ) )
        params = util.Params( kwd, sanitize = False ) #Sanitize parameters when substituting into command line via input wrappers
        #do param translation here, used by datasource tools
        if tool.input_translator:
            tool.input_translator.translate( params )
        # We may be visiting Galaxy for the first time ( e.g., sending data from UCSC ),
        # so make sure to create a new history if we've never had one before.
        history = trans.get_history( create=True )
        template, vars = tool.handle_input( trans, params.__dict__ )
        if len(params) > 0:
            trans.log_event( "Tool params: %s" % (str(params)), tool_id=tool_id )
        add_frame = AddFrameData()
        add_frame.debug = trans.debug
        if from_noframe is not None:
            add_frame.wiki_url = trans.app.config.wiki_url
            add_frame.from_noframe = True
        return trans.fill_template( template, history=history, toolbox=toolbox, tool=tool, util=util, add_frame=add_frame, **vars )
        
    @web.expose
    def rerun( self, trans, id=None, from_noframe=None, **kwd ):
        """
        Given a HistoryDatasetAssociation id, find the job and that created
        the dataset, extract the parameters, and display the appropriate tool
        form with parameters already filled in.
        """
        if not id:
            error( "'id' parameter is required" );
        try:
            id = int( id )
        except:
            error( "Invalid value for 'id' parameter" )
        # Get the dataset object
        data = trans.sa_session.query( trans.app.model.HistoryDatasetAssociation ).get( id )
        #only allow rerunning if user is allowed access to the dataset.
        if not trans.app.security_agent.can_access_dataset( trans.get_current_user_roles(), data.dataset ):
            error( "You are not allowed to access this dataset" )
        # Get the associated job, if any. If this hda was copied from another,
        # we need to find the job that created the origial hda
        job_hda = data
        while job_hda.copied_from_history_dataset_association:#should this check library datasets as well?
            job_hda = job_hda.copied_from_history_dataset_association
        if not job_hda.creating_job_associations:
            error( "Could not find the job for this dataset" )
        # Get the job object
        job = None
        for assoc in job_hda.creating_job_associations:
            job = assoc.job
            break   
        if not job:
            raise Exception("Failed to get job information for dataset hid %d" % data.hid)
        # Get the tool object
        tool_id = job.tool_id
        tool_version = job.tool_version
        try:
            # Load the tool
            toolbox = self.get_toolbox()
            tools = toolbox.get_tool( tool_id, tool_version=tool_version, get_all_versions=True )
            if len( tools ) > 1:
                tool_id_select_field = self.build_tool_id_select_field( tools, tool_id )
                for tool in tools:
                    if tool.id == tool_id:
                        break
                else:
                    tool = tools[ 0 ]
                tool_id_version_message = 'This job was initially run with tool id "%s", version "%s", and multiple derivations ' % ( job.tool_id, job.tool_version )
                tool_id_version_message += 'of this tool are available.  Rerun the job with the selected tool or choose another derivation of the tool.'
            else:
                tool_id_select_field = None
                tool = tools[ 0 ]
            if tool.id == job.tool_id and tool.version == job.tool_version:
                tool_id_version_message = ''
            elif tool.id == job.tool_id:
                if job.tool_version == None:
                    # For some reason jobs don't always keep track of the tool version.
                    tool_id_version_message = ''
                else:
                    if len( tools ) > 1:
                        tool_id_version_message = 'This job was initially run with tool version "%s", which is not currently available.  ' % job.tool_version
                        tool_id_version_message += 'You can rerun the job with the selected tool or choose another derivation of the tool.'
                    else:
                        tool_id_version_message = 'This job was initially run with tool version "%s", which is not currently available.  ' % job.tool_version
                        tool_id_version_message += 'You can rerun the job with this tool version, which is a derivation of the original tool.'
            else:
                if len( tools ) > 1:
                    tool_id_version_message = 'This job was initially run with tool version "%s", which is not currently available.  ' % job.tool_version
                    tool_id_version_message += 'You can rerun the job with the selected tool or choose another derivation of the tool.'
                else:
                    tool_id_version_message = 'This job was initially run with tool id "%s", version "%s", which is not ' % ( job.tool_id, job.tool_version )
                    tool_id_version_message += 'currently available.  You can rerun the job with this tool, which is a derivation of the original tool.'
            assert tool is not None, 'Requested tool has not been loaded.'
        except:
            # This is expected so not an exception.
            tool_id_version_message = ''
            error( "This dataset was created by an obsolete tool (%s). Can't re-run." % tool_id )
        # Can't rerun upload, external data sources, et cetera. Workflow compatible will proxy this for now
        if not tool.is_workflow_compatible:
            error( "The '%s' tool does not currently support rerunning." % tool.name )
        # Get the job's parameters
        try:
            params_objects = job.get_param_values( trans.app, ignore_errors = True )
        except:
            raise Exception( "Failed to get parameters for dataset id %d " % data.id )
        upgrade_messages = tool.check_and_update_param_values( params_objects, trans )
        # Need to remap dataset parameters. Job parameters point to original 
        # dataset used; parameter should be the analygous dataset in the 
        # current history.
        history = trans.get_history()
        hda_source_dict = {} # Mapping from HDA in history to source HDAs.
        for hda in history.datasets:
            source_hda = hda.copied_from_history_dataset_association
            while source_hda:#should this check library datasets as well?
                #FIXME: could be multiple copies of a hda in a single history, this does a better job of matching on cloned histories, 
                #but is still less than perfect when eg individual datasets are copied between histories
                if source_hda not in hda_source_dict or source_hda.hid == hda.hid:
                    hda_source_dict[ source_hda ] = hda
                source_hda = source_hda.copied_from_history_dataset_association
        # Unpack unvalidated values to strings, they'll be validated when the
        # form is submitted (this happens when re-running a job that was
        # initially run by a workflow)
        #This needs to be done recursively through grouping parameters
        def rerun_callback( input, value, prefixed_name, prefixed_label ):
            if isinstance( value, UnvalidatedValue ):
                return str( value )
            if isinstance( input, DataToolParameter ):
                if value not in history.datasets and value in hda_source_dict:
                    return hda_source_dict[ value ]
        visit_input_values( tool.inputs, params_objects, rerun_callback )
        # Create a fake tool_state for the tool, with the parameters values 
        state = tool.new_state( trans )
        state.inputs = params_objects
        tool_state_string = util.object_to_string(state.encode(tool, trans.app))
        # Setup context for template
        vars = dict( tool_state=state, errors = upgrade_messages )
        # Is the "add frame" stuff neccesary here?
        add_frame = AddFrameData()
        add_frame.debug = trans.debug
        if from_noframe is not None:
            add_frame.wiki_url = trans.app.config.wiki_url
            add_frame.from_noframe = True
        return trans.fill_template( "tool_form.mako",
                                    history=history,
                                    toolbox=toolbox,
                                    tool_id_select_field=tool_id_select_field,
                                    tool=tool,
                                    util=util,
                                    add_frame=add_frame,
                                    tool_id_version_message=tool_id_version_message,
                                    **vars )
    def build_tool_id_select_field( self, tools, selected_tool_id ):
        """Build a SelectField whose options are the ids for the received list of tools."""
        options = []
        refresh_on_change_values = []
        for tool in tools:
            options.append( ( tool.id, tool.id ) )
            refresh_on_change_values.append( tool.id )
        select_field = SelectField( name='tool_id', refresh_on_change=True, refresh_on_change_values=refresh_on_change_values )
        for option_tup in options:
            selected = option_tup[0] == selected_tool_id
            if selected:
                select_field.add_option( option_tup[0], option_tup[1], selected=True )
            else:
                select_field.add_option( option_tup[0], option_tup[1] )
        return select_field
    @web.expose
    def redirect( self, trans, redirect_url=None, **kwd ):
        if not redirect_url:
            return trans.show_error_message( "Required URL for redirection missing" )
        trans.log_event( "Redirecting to: %s" % redirect_url )
        return trans.fill_template( 'root/redirect.mako', redirect_url=redirect_url )
    @web.json
    def upload_async_create( self, trans, tool_id=None, **kwd ):
        """
        Precreate datasets for asynchronous uploading.
        """
        cntrller = kwd.get( 'cntrller', '' )
        roles = kwd.get( 'roles', False )
        if roles:
            # The user associated the DATASET_ACCESS permission on the uploaded datasets with 1 or more roles.
            # We need to ensure that the roles are legitimately derived from the roles associated with the LIBRARY_ACCESS
            # permission if the library is not public ( this should always be the case since any ill-legitimate roles
            # were filtered out of the roles displayed on the upload form.  In addition, we need to ensure that the user
            # did not associated roles that would make the dataset in-accessible by everyone.
            library_id = trans.app.security.decode_id( kwd.get( 'library_id', '' ) )
            vars = dict( DATASET_ACCESS_in=roles )
            permissions, in_roles, error, msg = trans.app.security_agent.derive_roles_from_access( trans, library_id, cntrller, library=True, **vars )
            if error:
                return [ 'error', msg ]
        def create_dataset( name ):
            ud = Bunch( name=name, file_type=None, dbkey=None )
            if nonfile_params.get( 'folder_id', False ):
                replace_id = nonfile_params.get( 'replace_id', None )
                if replace_id not in [ None, 'None' ]:
                    replace_dataset = trans.sa_session.query( trans.app.model.LibraryDataset ).get( trans.security.decode_id( replace_id ) )
                else:
                    replace_dataset = None
                # FIXME: instead of passing params here ( chiech have been process by util.Params(), the original kwd
                # should be passed so that complex objects that may have been included in the initial request remain.
                library_bunch = upload_common.handle_library_params( trans, nonfile_params, nonfile_params.folder_id, replace_dataset )
            else:
                library_bunch = None
            return upload_common.new_upload( trans, cntrller, ud, library_bunch=library_bunch, state=trans.app.model.HistoryDatasetAssociation.states.UPLOAD )
        tool = self.get_toolbox().get_tool( tool_id )
        if not tool:
            return False # bad tool_id
        nonfile_params = util.Params( kwd, sanitize=False )
        if kwd.get( 'tool_state', None ) not in ( None, 'None' ):
            encoded_state = util.string_to_object( kwd["tool_state"] )
            tool_state = DefaultToolState()
            tool_state.decode( encoded_state, tool, trans.app )
        else:
            tool_state = tool.new_state( trans )
        errors = tool.update_state( trans, tool.inputs, tool_state.inputs, kwd, update_only = True )
        datasets = []
        dataset_upload_inputs = []
        for input_name, input in tool.inputs.iteritems():
            if input.type == "upload_dataset":
                dataset_upload_inputs.append( input )
        assert dataset_upload_inputs, Exception( "No dataset upload groups were found." )
        for dataset_upload_input in dataset_upload_inputs:
            d_type = dataset_upload_input.get_datatype( trans, kwd )
            
            if d_type.composite_type is not None:
                datasets.append( create_dataset( dataset_upload_input.get_composite_dataset_name( kwd ) ) )
            else:
                params = Bunch( ** tool_state.inputs[dataset_upload_input.name][0] )
                if params.file_data not in [ None, "" ]:
                    name = params.file_data
                    if name.count('/'):
                        name = name.rsplit('/',1)[1]
                    if name.count('\\'):
                        name = name.rsplit('\\',1)[1]
                    datasets.append( create_dataset( name ) )
                if params.url_paste not in [ None, "" ]:
                    url_paste = params.url_paste.replace( '\r', '' ).split( '\n' )
                    url = False
                    for line in url_paste:
                        line = line.rstrip( '\r\n' ).strip()
                        if not line:
                            continue
                        elif line.lower().startswith( 'http://' ) or line.lower().startswith( 'ftp://' ) or line.lower().startswith( 'https://' ):
                            url = True
                            datasets.append( create_dataset( line ) )
                        else:
                            if url:
                                continue # non-url when we've already processed some urls
                            else:
                                # pasted data
                                datasets.append( create_dataset( 'Pasted Entry' ) )
                                break
        return [ d.id for d in datasets ]
    @web.expose
    def upload_async_message( self, trans, **kwd ):
        # might be more appropriate in a different controller
        msg = """<p>Your upload has been queued.  History entries that are still uploading will be blue, and turn green upon completion.</p>
        <p><b>Please do not use your browser\'s "stop" or "reload" buttons until the upload is complete, or it may be interrupted.</b></p>
        <p>You may safely continue to use Galaxy while the upload is in progress.  Using "stop" and "reload" on pages other than Galaxy is also safe.</p>
        """
        return trans.show_message( msg, refresh_frames='history' )
