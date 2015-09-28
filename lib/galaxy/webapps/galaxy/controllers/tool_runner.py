"""
Upload class
"""
import logging

from galaxy import eggs
eggs.require( "MarkupSafe" )
from markupsafe import escape

import galaxy.util
from galaxy import web
from galaxy.tools import DefaultToolState
from galaxy.tools import DataSourceTool
from galaxy.tools.actions import upload_common
from galaxy.util.bunch import Bunch
from galaxy.web import error, url_for
from galaxy.web.base.controller import BaseUIController

log = logging.getLogger( __name__ )


class AddFrameData:
    def __init__( self ):
        self.wiki_url = None
        self.debug = None
        self.from_noframe = None


class ToolRunner( BaseUIController ):

    # Hack to get biomart to work, ideally, we could pass tool_id to biomart and receive it back
    @web.expose
    def biomart(self, trans, tool_id='biomart', **kwd):
        """Catches the tool id and redirects as needed"""
        return self.index(trans, tool_id=tool_id, **kwd)

    # test to get hapmap to work, ideally, we could pass tool_id to hapmap biomart and receive it back
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
        tool_version_select_field, tools, tool = self.__get_tool_components( tool_id )
        # No tool matching the tool id, display an error (shouldn't happen)
        if not tool or not tool.allow_user_access( trans.user ):
            log.error( "index called with tool id '%s' but no such tool exists", tool_id )
            trans.log_event( "Tool id '%s' does not exist" % tool_id )
            trans.response.status = 404
            return trans.show_error_message("Tool '%s' does not exist." % ( escape(tool_id) ))
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
        if tool.tool_type == 'default':
            return trans.response.send_redirect( url_for( controller="root", tool_id=tool_id ) )

        def _validated_params_for( kwd ):
            params = galaxy.util.Params( kwd, sanitize=False )  # Sanitize parameters when substituting into command line via input wrappers
            # do param translation here, used by datasource tools
            if tool.input_translator:
                tool.input_translator.translate( params )
            return params

        params = _validated_params_for( kwd )
        # We may be visiting Galaxy for the first time ( e.g., sending data from UCSC ),
        # so make sure to create a new history if we've never had one before.
        history = tool.get_default_history_by_trans( trans, create=True )
        try:
            template, vars = tool.handle_input( trans, params.__dict__ )
        except KeyError:
            # This error indicates (or at least can indicate) there was a
            # problem with the stored tool_state - it is incompatible with
            # this variant of the tool - possibly because the tool changed
            # or because the tool version changed.
            del kwd[ "tool_state" ]
            params = _validated_params_for( kwd )
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
    def rerun( self, trans, id=None, job_id=None, **kwd ):
        """
        Given a HistoryDatasetAssociation id, find the job and that created
        the dataset, extract the parameters, and display the appropriate tool
        form with parameters already filled in.
        """

        if job_id is None:
            if not id:
                error( "'id' parameter is required" )
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
            # only allow rerunning if user is allowed access to the dataset.
            if not ( trans.user_is_admin() or trans.app.security_agent.can_access_dataset( trans.get_current_user_roles(), data.dataset ) ):
                error( "You are not allowed to access this dataset" )
            # Get the associated job, if any.
            job = data.creating_job
            if job:
                job_id = trans.security.encode_id( job.id )
            else:
                raise Exception("Failed to get job information for dataset hid %d" % data.hid)
        return trans.response.send_redirect( url_for( controller="root", job_id=job_id ) )

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
            return trans.show_error_message("Tool '%s' does not exist." % ( escape(tool_id) ))

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
            return False  # bad tool_id
        nonfile_params = galaxy.util.Params( kwd, sanitize=False )
        if kwd.get( 'tool_state', None ) not in ( None, 'None' ):
            encoded_state = galaxy.util.string_to_object( kwd["tool_state"] )
            tool_state = DefaultToolState()
            tool_state.decode( encoded_state, tool, trans.app )
        else:
            tool_state = tool.new_state( trans )
        tool.update_state( trans, tool.inputs, tool_state.inputs, kwd, update_only=True )
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
                        name = name.rsplit('/', 1)[1]
                    if name.count('\\'):
                        name = name.rsplit('\\', 1)[1]
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
                                continue  # non-url when we've already processed some urls
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
        # return trans.show_message( msg, refresh_frames=[ 'history' ] )
        return trans.show_message( msg )
