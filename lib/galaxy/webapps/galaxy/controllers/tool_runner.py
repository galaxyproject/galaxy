"""
Upload class
"""
import os
import logging
import galaxy.util
from galaxy import web
from galaxy.tools import DefaultToolState
from galaxy.tools import DataSourceTool
from galaxy.tools.actions import upload_common
from galaxy.tools.parameters import params_to_incoming
from galaxy.tools.parameters import visit_input_values
from galaxy.tools.parameters.basic import DataToolParameter
from galaxy.tools.parameters.basic import DataCollectionToolParameter
from galaxy.tools.parameters.basic import UnvalidatedValue
from galaxy.util.bunch import Bunch
from galaxy.util.hash_util import is_hashable
from galaxy.web import error
from galaxy.web import url_for
from galaxy.web.base.controller import BaseUIController
import tool_shed.util.shed_util_common as suc

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

    def __get_tool_components( self, tool_id, tool_version=None, get_loaded_tools_by_lineage=False, set_selected=False ):
        return self.get_toolbox().get_tool_components( tool_id, tool_version, get_loaded_tools_by_lineage, set_selected )

    @web.expose
    def index( self, trans, tool_id=None, from_noframe=None, **kwd ):
        # No tool id passed, redirect to main page
        if tool_id is None:
            return trans.response.send_redirect( url_for( controller="root", action="welcome" ) )
        # When the tool form is initially loaded, the received kwd will not include a 'refresh'
        # entry (which only is included when another option is selected in the tool_version_select_field),
        # so the default selected option should be the most recent version of the tool.  The following 
        # check will mae sure this occurs.
        refreshed_on_change = kwd.get( 'refresh', False )
        tool_version_select_field, tools, tool = self.__get_tool_components( tool_id,
                                                                             tool_version=None,
                                                                             get_loaded_tools_by_lineage=False,
                                                                             set_selected=refreshed_on_change )
        # No tool matching the tool id, display an error (shouldn't happen)
        if not tool:
            log.error( "index called with tool id '%s' but no such tool exists", tool_id )
            trans.log_event( "Tool id '%s' does not exist" % tool_id )
            trans.response.status = 404
            return "Tool '%s' does not exist, kwd=%s " % ( tool_id, kwd )
        if tool.require_login and not trans.user:
            message = "You must be logged in to use this tool."
            status = "info"
            redirect = url_for( controller='tool_runner', action='index', tool_id=tool_id, **kwd )
            return trans.response.send_redirect( url_for( controller='user',
                                                          action='login',
                                                          cntrller='user',
                                                          message=message,
                                                          status=status,
                                                          redirect=redirect ) )
        params = galaxy.util.Params( kwd, sanitize = False ) #Sanitize parameters when substituting into command line via input wrappers
        #do param translation here, used by datasource tools
        if tool.input_translator:
            tool.input_translator.translate( params )
        # We may be visiting Galaxy for the first time ( e.g., sending data from UCSC ),
        # so make sure to create a new history if we've never had one before.
        history = tool.get_default_history_by_trans( trans, create=True )
        template, vars = tool.handle_input( trans, params.__dict__ )
        if len( params ) > 0:
            trans.log_event( "Tool params: %s" % ( str( params ) ), tool_id=tool_id )
        add_frame = AddFrameData()
        add_frame.debug = trans.debug
        if from_noframe is not None:
            add_frame.wiki_url = trans.app.config.wiki_url
            add_frame.from_noframe = True
        return trans.fill_template( template,
                                    history=history,
                                    toolbox=self.get_toolbox(),
                                    tool_version_select_field=tool_version_select_field,
                                    tool=tool,
                                    util=galaxy.util,
                                    add_frame=add_frame,
                                    form_input_auto_focus=True,
                                    **vars )

    @web.expose
    def rerun( self, trans, id=None, from_noframe=None, job_id=None, **kwd ):
        """
        Given a HistoryDatasetAssociation id, find the job and that created
        the dataset, extract the parameters, and display the appropriate tool
        form with parameters already filled in.
        """
        if job_id:
            try:
                job_id = trans.security.decode_id( job_id )
                job = trans.sa_session.query( trans.app.model.Job ).get( job_id )
            except:
                error( "Invalid value for 'job_id' parameter" )
            if not trans.user_is_admin():
                for data_assoc in job.output_datasets:
                    #only allow rerunning if user is allowed access to the dataset.
                    if not trans.app.security_agent.can_access_dataset( trans.get_current_user_roles(), data_assoc.dataset.dataset ):
                        error( "You are not allowed to rerun this job" )
            param_error_text = "Failed to get parameters for job id %d " % job_id
        else:
            if not id:
                error( "'id' parameter is required" );
            try:
                id = int( id )
            except:
                # it's not an un-encoded id, try to parse as encoded
                try:
                    id = trans.security.decode_id( id )
                except:
                    error( "Invalid value for 'id' parameter" )
            # Get the dataset object
            data = trans.sa_session.query( trans.app.model.HistoryDatasetAssociation ).get( id )
            #only allow rerunning if user is allowed access to the dataset.
            if not ( trans.user_is_admin() or trans.app.security_agent.can_access_dataset( trans.get_current_user_roles(), data.dataset ) ):
                error( "You are not allowed to access this dataset" )
            # Get the associated job, if any.
            job = data.creating_job
            if not job:
                raise Exception("Failed to get job information for dataset hid %d" % data.hid)
            param_error_text = "Failed to get parameters for dataset id %d " % data.id
        # Get the tool object
        tool_id = job.tool_id
        tool_version = job.tool_version
        try:
            tool_version_select_field, tools, tool = self.__get_tool_components( tool_id,
                                                                                 tool_version=tool_version,
                                                                                 get_loaded_tools_by_lineage=False,
                                                                                 set_selected=True )
            if ( tool.id == job.tool_id or tool.old_id == job.tool_id ) and tool.version == job.tool_version:
                tool_id_version_message = ''
            elif tool.id == job.tool_id:
                if job.tool_version == None:
                    # For some reason jobs don't always keep track of the tool version.
                    tool_id_version_message = ''
                else:
                    tool_id_version_message = 'This job was initially run with tool version "%s", which is not currently available.  ' % job.tool_version
                    if len( tools ) > 1:
                        tool_id_version_message += 'You can rerun the job with the selected tool or choose another derivation of the tool.'
                    else:
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
            raise Exception( param_error_text )
        upgrade_messages = tool.check_and_update_param_values( params_objects, trans, update_values=False )
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
        # Ditto for dataset collections.
        hdca_source_dict = {}
        for hdca in history.dataset_collections:
            source_hdca = hdca.copied_from_history_dataset_collection_association
            while source_hdca:
                if source_hdca not in hdca_source_dict or source_hdca.hid == hdca.hid:
                    hdca_source_dict[ source_hdca ] = hdca
                source_hdca = source_hdca.copied_from_history_dataset_collection_association

        # Unpack unvalidated values to strings, they'll be validated when the
        # form is submitted (this happens when re-running a job that was
        # initially run by a workflow)
        #This needs to be done recursively through grouping parameters
        def rerun_callback( input, value, prefixed_name, prefixed_label ):
            if isinstance( value, UnvalidatedValue ):
                try:
                    return input.to_html_value( value.value, trans.app )
                except Exception, e:
                    # Need to determine when (if ever) the to_html_value call could fail.
                    log.debug( "Failed to use input.to_html_value to determine value of unvalidated parameter, defaulting to string: %s" % ( e ) )
                    return str( value )
            if isinstance( input, DataToolParameter ):
                if isinstance(value,list):
                    values = []
                    for val in value:
                        if is_hashable( val ):
                            if val in history.datasets:
                                values.append( val )
                            elif val in hda_source_dict:
                                values.append( hda_source_dict[ val ])
                    return values
                if is_hashable( value ) and value not in history.datasets and value in hda_source_dict:
                    return hda_source_dict[ value ]
            elif isinstance( input, DataCollectionToolParameter ):
                if is_hashable( value ) and value not in history.dataset_collections and value in hdca_source_dict:
                    return hdca_source_dict[ value ]

        visit_input_values( tool.inputs, params_objects, rerun_callback )
        # Create a fake tool_state for the tool, with the parameters values
        state = tool.new_state( trans )
        state.inputs = params_objects
        # If the job failed and has dependencies, allow dependency remap
        if job.state == job.states.ERROR:
            try:
                if [ hda.dependent_jobs for hda in [ jtod.dataset for jtod in job.output_datasets ] if hda.dependent_jobs ]:
                    state.rerun_remap_job_id = trans.app.security.encode_id(job.id)
            except:
                # Job has no outputs?
                pass
        #create an incoming object from the original job's dataset-modified param objects
        incoming = {}
        params_to_incoming( incoming, tool.inputs, params_objects, trans.app )
        incoming[ "tool_state" ] = galaxy.util.object_to_string( state.encode( tool, trans.app ) )
        template, vars = tool.handle_input( trans, incoming, old_errors=upgrade_messages ) #update new state with old parameters
        # Is the "add frame" stuff neccesary here?
        add_frame = AddFrameData()
        add_frame.debug = trans.debug
        if from_noframe is not None:
            add_frame.wiki_url = trans.app.config.wiki_url
            add_frame.from_noframe = True
        return trans.fill_template( template,
                                    history=history,
                                    toolbox=self.get_toolbox(),
                                    tool_version_select_field=tool_version_select_field,
                                    tool=tool,
                                    util=galaxy.util,
                                    add_frame=add_frame,
                                    tool_id_version_message=tool_id_version_message,
                                    **vars )

    @web.expose
    def data_source_redirect( self, trans, tool_id=None ):
        """
        Redirects a user accessing a Data Source tool to its target action link.
        This method will subvert mix-mode content blocking in several browsers when
        accessing non-https data_source tools from an https galaxy server.

        Tested as working on Safari 7.0 and FireFox 26
        Subverting did not work on Chrome 31
        """
        if tool_id is None:
            return trans.response.send_redirect( url_for( controller="root", action="welcome" ) )
        tool_version_select_field, tools, tool = self.__get_tool_components( tool_id,
                                                                             tool_version=None,
                                                                             get_loaded_tools_by_lineage=False,
                                                                             set_selected=False )
        # No tool matching the tool id, display an error (shouldn't happen)
        if not tool:
            log.error( "data_source_redirect called with tool id '%s' but no such tool exists", tool_id )
            trans.log_event( "Tool id '%s' does not exist" % tool_id )
            trans.response.status = 404
            return "Tool '%s' does not exist, kwd=%s " % ( tool_id, kwd )

        if isinstance( tool, DataSourceTool ):
            link = url_for( tool.action, **tool.get_static_param_values( trans ) )
        else:
            link = url_for( controller='tool_runner', tool_id=tool.id )
        return trans.response.send_redirect( link )

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
        nonfile_params = galaxy.util.Params( kwd, sanitize=False )
        if kwd.get( 'tool_state', None ) not in ( None, 'None' ):
            encoded_state = galaxy.util.string_to_object( kwd["tool_state"] )
            tool_state = DefaultToolState()
            tool_state.decode( encoded_state, tool, trans.app )
        else:
            tool_state = tool.new_state( trans )
        tool.update_state( trans, tool.inputs, tool_state.inputs, kwd, update_only = True )
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
        #return trans.show_message( msg, refresh_frames=[ 'history' ] )
        return trans.show_message( msg )
