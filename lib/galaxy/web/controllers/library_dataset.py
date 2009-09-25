import os, os.path, shutil, urllib, StringIO, re, gzip, tempfile, shutil, zipfile
from galaxy.web.base.controller import *
from galaxy import util, jobs
from galaxy.datatypes import sniff
from galaxy.security import RBACAgent
from galaxy.util.json import to_json_string
from galaxy.tools.actions import upload_common

log = logging.getLogger( __name__ )

class UploadLibraryDataset( BaseController ):
    @web.json
    def library_item_updates( self, trans, ids=None, states=None ):
        # Avoid caching
        trans.response.headers['Pragma'] = 'no-cache'
        trans.response.headers['Expires'] = '0'
        # Create new HTML for any that have changed
        rval = {}
        if ids is not None and states is not None:
            ids = map( int, ids.split( "," ) )
            states = states.split( "," )
            for id, state in zip( ids, states ):
                data = self.app.model.LibraryDatasetDatasetAssociation.get( id )
                if data.state != state:
                    job_ldda = data
                    while job_ldda.copied_from_library_dataset_dataset_association:
                        job_ldda = job_ldda.copied_from_library_dataset_dataset_association
                    force_history_refresh = False
                    rval[id] = {
                        "state": data.state,
                        "html": unicode( trans.fill_template( "library/library_item_info.mako", ldda=data ), 'utf-8' )
                        #"force_history_refresh": force_history_refresh
                    }
        return rval
    @web.expose
    def upload_dataset( self, trans, controller, library_id, folder_id, replace_dataset=None, **kwd ):
        # Set up the traditional tool state/params
        tool_id = 'upload1'
        tool = trans.app.toolbox.tools_by_id[ tool_id ]
        state = tool.new_state( trans )
        errors = tool.update_state( trans, tool.inputs_by_page[0], state.inputs, kwd, changed_dependencies={} )
        tool_params = state.inputs
        dataset_upload_inputs = []
        for input_name, input in tool.inputs.iteritems():
            if input.type == "upload_dataset":
                dataset_upload_inputs.append( input )
        # Library-specific params
        params = util.Params( kwd ) # is this filetoolparam safe?
        msg = util.restore_text( params.get( 'msg', ''  ) )
        messagetype = params.get( 'messagetype', 'done' )
        server_dir = util.restore_text( params.get( 'server_dir', '' ) )
        if replace_dataset not in [ None, 'None' ]:
            replace_id = replace_dataset.id
        else:
            replace_id = None
        message = params.get( 'message', '' )
        upload_option = params.get( 'upload_option', 'upload_file' )
        err_redirect = False
        # See if we have any template field contents
        template_field_contents = []
        template_id = params.get( 'template_id', None )
        folder = trans.app.model.LibraryFolder.get( folder_id )
        # We are inheriting the folder's info_association, so we did not
        # receive any inherited contents, but we may have redirected here
        # after the user entered template contents ( due to errors ).
        if template_id not in [ None, 'None' ]:
            template = trans.app.model.FormDefinition.get( template_id )
            for field_index in range( len( template.fields ) ):
                field_name = 'field_%i' % field_index
                if params.get( field_name, False ):
                    field_value = util.restore_text( params.get( field_name, ''  ) )
                    template_field_contents.append( field_value )
        else:
            template = None
        if upload_option == 'upload_directory':
            if server_dir in [ None, 'None', '' ]:
                err_redirect = True
            if controller == 'library_admin':
                import_dir = trans.app.config.library_import_dir
                import_dir_desc = 'library_import_dir'
                full_dir = os.path.join( import_dir, server_dir )
            else:
                import_dir = trans.app.config.user_library_import_dir
                import_dir_desc = 'user_library_import_dir'
                if server_dir == trans.user.email:
                    full_dir = os.path.join( import_dir, server_dir )
                else:
                    full_dir = os.path.join( import_dir, trans.user.email, server_dir )
            if import_dir:
                msg = 'Select a directory'
            else:
                msg = '"%s" is not defined in the Galaxy configuration file' % import_dir_desc
        roles = []
        for role_id in util.listify( params.get( 'roles', [] ) ):
            roles.append( trans.app.model.Role.get( role_id ) )
        # Proceed with (mostly) regular upload processing
        precreated_datasets = upload_common.get_precreated_datasets( trans, tool_params, trans.app.model.HistoryDatasetAssociation )
        if upload_option == 'upload_file':
            tool_params = upload_common.persist_uploads( tool_params )
            json_file_path, data_list = upload_common.create_paramfile( trans, tool_params, precreated_datasets, dataset_upload_inputs, replace_dataset, folder, template, template_field_contents, roles, message )
        elif upload_option == 'upload_directory':
            json_file_path, data_list = self.create_server_dir_paramfile( trans, params, full_dir, import_dir_desc, folder, template, template_field_contents, roles, message, err_redirect, msg )
        upload_common.cleanup_unused_precreated_datasets( precreated_datasets )
        if upload_option == 'upload_file' and not data_list:
            msg = 'Select a file, enter a URL or enter text'
            err_redirect = True
        if err_redirect:
            try:
                os.remove( json_file_path )
            except:
                pass
            trans.response.send_redirect( web.url_for( controller=controller,
                                                       action='library_dataset_dataset_association',
                                                       library_id=library_id,
                                                       folder_id=folder_id,
                                                       replace_id=replace_id,
                                                       upload_option=upload_option,
                                                       msg=util.sanitize_text( msg ),
                                                       messagetype='error' ) )
        return upload_common.create_job( trans, tool_params, tool, json_file_path, data_list, folder=folder )
    def create_server_dir_paramfile( self, trans, params, full_dir, import_dir_desc, folder, template,
                                     template_field_contents, roles, message, err_redirect, msg ):
        """
        Create JSON param file for the upload tool when using the server_dir upload.
        """
        files = []
        try:
            for entry in os.listdir( full_dir ):
                # Only import regular files
                if os.path.isfile( os.path.join( full_dir, entry ) ):
                    files.append( entry )
        except Exception, e:
            msg = "Unable to get file list for configured %s, error: %s" % ( import_dir_desc, str( e ) )
            err_redirect = True
            return ( None, None )
        if not files:
            msg = "The directory '%s' contains no valid files" % full_dir
            err_redirect = True
            return ( None, None )
        data_list = []
        json_file = tempfile.mkstemp()
        json_file_path = json_file[1]
        json_file = os.fdopen( json_file[0], 'w' )
        for file in files:
            full_file = os.path.join( full_dir, file )
            if not os.path.isfile( full_file ):
                continue
            uploaded_dataset = util.bunch.Bunch()
            uploaded_dataset.name = file
            uploaded_dataset.file_type = params.file_type
            uploaded_dataset.dbkey = params.dbkey
            data = upload_common.new_library_upload( trans, uploaded_dataset, None, folder, template, template_field_contents, roles, message )
            json = dict( file_type = uploaded_dataset.file_type,
                         ext = None,
                         name = uploaded_dataset.name,
                         dataset_id = data.dataset.id,
                         dbkey = uploaded_dataset.dbkey,
                         type = 'server_dir',
                         is_binary = None,
                         space_to_tab = params.space_to_tab,
                         path = full_file )
            json_file.write( to_json_string( json ) + '\n' )
            data_list.append( data )
        json_file.close()
        return ( json_file_path, data_list )
