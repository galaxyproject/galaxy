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

class ToolRunner( BaseController ):

    #Hack to get biomart to work, ideally, we could pass tool_id to biomart and receive it back
    @web.expose
    def biomart(self, trans, tool_id='biomart', **kwd):
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
        tool = toolbox.tools_by_id.get( tool_id, None )
        # No tool matching the tool id, display an error (shouldn't happen)
        if not tool:
            log.error( "index called with tool id '%s' but no such tool exists", tool_id )
            trans.log_event( "Tool id '%s' does not exist" % tool_id )
            return "Tool '%s' does not exist, kwd=%s " % (tool_id, kwd)
        params = util.Params( kwd, sanitize = False ) #Sanitize parameters when substituting into command line via input wrappers
        #do param translation here, used by datasource tools
        if tool.input_translator:
            tool.input_translator.translate( params )
        history = trans.get_history()
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
        try:
            # Load the tool
            toolbox = self.get_toolbox()
            tool = toolbox.tools_by_id.get( tool_id, None )
        except:
            #this is expected, so not an exception
            error( "This dataset was created by an obsolete tool (%s). Can't re-run." % tool_id )
        # Can't rerun upload, external data sources, et cetera. Workflow
        # compatible will proxy this for now
        if not tool.is_workflow_compatible:
            error( "The '%s' tool does not currently support rerunning." % tool.name )
        # Get the job's parameters
        try:
            params_objects = job.get_param_values( trans.app )
        except:
            raise Exception( "Failed to get paramemeters for dataset id %d " % hid )
        # Unpack unvalidated values to strings, they'll be validated when the
        # form is submitted (this happens when re-running a job that was
        # initially run by a workflow)
        validated_params = {}
        for name, value in params_objects.items():
            if isinstance( value, UnvalidatedValue ):
                validated_params [ str(name) ] = str(value)
            else:
                validated_params [ str(name) ] = value
        params_objects = validated_params
        # Create a fake tool_state for the tool, with the parameters values 
        state = tool.new_state( trans )
        state.inputs = params_objects
        tool_state_string = util.object_to_string(state.encode(tool, trans.app))
        # Setup context for template
        history = trans.get_history()
        vars = dict( tool_state=state, errors = {} )
        # Is the "add frame" stuff neccesary here?
        add_frame = AddFrameData()
        add_frame.debug = trans.debug
        if from_noframe is not None:
            add_frame.wiki_url = trans.app.config.wiki_url
            add_frame.from_noframe = True
        return trans.fill_template( "tool_form.mako", history=history, toolbox=toolbox, tool=tool, util=util, add_frame=add_frame, **vars )
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
        permissions = trans.app.security_agent.history_get_default_permissions( trans.history )
        def create_dataset( name ):
            ud = Bunch( name=name, file_type=None, dbkey=None )
            if nonfile_params.get( 'folder_id', False ):
                replace_id = nonfile_params.get( 'replace_id', None )
                if replace_id not in [ None, 'None' ]:
                    replace_dataset = trans.sa_session.query( l.LibraryDataset ).get( trans.security.decode_id( replace_id ) )
                else:
                    replace_dataset = None
                library_bunch = upload_common.handle_library_params( trans, nonfile_params, nonfile_params.folder_id, replace_dataset )
            else:
                library_bunch = None
            return upload_common.new_upload( trans, ud, library_bunch=library_bunch, state=trans.app.model.HistoryDatasetAssociation.states.UPLOAD )
        tool = self.get_toolbox().tools_by_id.get( tool_id, None )
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
                datasets.append( create_dataset( 'Uploaded Composite Dataset (%s)' % dataset_upload_input.get_datatype_ext( trans, kwd ) ) )
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
                        elif line.lower().startswith( 'http://' ) or line.lower().startswith( 'ftp://' ):
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
