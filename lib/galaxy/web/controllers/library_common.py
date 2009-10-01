import os, os.path, shutil, urllib, StringIO, re, gzip, tempfile, shutil, zipfile
from galaxy.web.base.controller import *
from galaxy import util, jobs
from galaxy.datatypes import sniff
from galaxy.security import RBACAgent
from galaxy.util.json import to_json_string
from galaxy.tools.actions import upload_common
from galaxy.web.controllers.forms import get_all_forms
from galaxy.model.orm import *

log = logging.getLogger( __name__ )

class LibraryCommon( BaseController ):
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
        library_bunch = upload_common.handle_library_params( trans, params, folder_id, replace_dataset )
        msg = util.restore_text( params.get( 'msg', ''  ) )
        messagetype = params.get( 'messagetype', 'done' )
        server_dir = util.restore_text( params.get( 'server_dir', '' ) )
        if replace_dataset not in [ None, 'None' ]:
            replace_id = replace_dataset.id
        else:
            replace_id = None
        upload_option = params.get( 'upload_option', 'upload_file' )
        err_redirect = False
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
        # Proceed with (mostly) regular upload processing
        precreated_datasets = upload_common.get_precreated_datasets( trans, tool_params, trans.app.model.LibraryDatasetDatasetAssociation, controller=controller )
        if upload_option == 'upload_file':
            tool_params = upload_common.persist_uploads( tool_params )
            uploaded_datasets = upload_common.get_uploaded_datasets( trans, tool_params, precreated_datasets, dataset_upload_inputs, library_bunch=library_bunch )
        elif upload_option == 'upload_directory':
            uploaded_datasets, err_redirect, msg = self.get_server_dir_uploaded_datasets( trans, params, full_dir, import_dir_desc, library_bunch, err_redirect, msg )
        elif upload_option == 'upload_paths':
            uploaded_datasets, err_redirect, msg = self.get_path_paste_uploaded_datasets( trans, params, library_bunch, err_redirect, msg )
        upload_common.cleanup_unused_precreated_datasets( precreated_datasets )
        if upload_option == 'upload_file' and not uploaded_datasets:
            msg = 'Select a file, enter a URL or enter text'
            err_redirect = True
        if err_redirect:
            trans.response.send_redirect( web.url_for( controller=controller,
                                                       action='upload_library_dataset',
                                                       library_id=library_id,
                                                       folder_id=folder_id,
                                                       replace_id=replace_id,
                                                       upload_option=upload_option,
                                                       msg=util.sanitize_text( msg ),
                                                       messagetype='error' ) )
        json_file_path = upload_common.create_paramfile( uploaded_datasets )
        data_list = [ ud.data for ud in uploaded_datasets ]
        return upload_common.create_job( trans, tool_params, tool, json_file_path, data_list, folder=library_bunch.folder )
    def make_library_uploaded_dataset( self, trans, params, name, path, type, library_bunch, in_folder=None ):
        library_bunch.replace_dataset = None # not valid for these types of upload
        uploaded_dataset = util.bunch.Bunch()
        uploaded_dataset.name = name
        uploaded_dataset.path = path
        uploaded_dataset.type = type
        uploaded_dataset.ext = None
        uploaded_dataset.file_type = params.file_type
        uploaded_dataset.dbkey = params.dbkey
        uploaded_dataset.space_to_tab = params.space_to_tab
        if in_folder:
            uploaded_dataset.in_folder = in_folder
        uploaded_dataset.data = upload_common.new_upload( trans, uploaded_dataset, library_bunch )
        if params.get( 'link_data_only', False ):
            uploaded_dataset.link_data_only = True
            uploaded_dataset.data.file_name = os.path.abspath( path )
            uploaded_dataset.data.flush()
        return uploaded_dataset
    def get_server_dir_uploaded_datasets( self, trans, params, full_dir, import_dir_desc, library_bunch, err_redirect, msg ):
        files = []
        try:
            for entry in os.listdir( full_dir ):
                # Only import regular files
                path = os.path.join( full_dir, entry )
                if os.path.islink( path ) and os.path.isfile( path ) and params.get( 'link_data_only', False ):
                    # If we're linking instead of copying, link the file the link points to, not the link itself.
                    link_path = os.readlink( path )
                    if os.path.isabs( link_path ):
                        path = link_path
                    else:
                        path = os.path.abspath( os.path.join( os.path.dirname( path ), link_path ) )
                if os.path.isfile( path ):
                    files.append( path )
        except Exception, e:
            msg = "Unable to get file list for configured %s, error: %s" % ( import_dir_desc, str( e ) )
            err_redirect = True
            return None, err_redirect, msg
        if not files:
            msg = "The directory '%s' contains no valid files" % full_dir
            err_redirect = True
            return None, err_redirect, msg
        uploaded_datasets = []
        for file in files:
            name = os.path.basename( file )
            uploaded_datasets.append( self.make_library_uploaded_dataset( trans, params, name, file, 'server_dir', library_bunch ) )
        return uploaded_datasets, None, None
    def get_path_paste_uploaded_datasets( self, trans, params, library_bunch, err_redirect, msg ):
        if params.get( 'filesystem_paths', '' ) == '':
            msg = "No paths entered in the upload form"
            err_redirect = True
            return None, err_redirect, msg
        preserve_dirs = True
        if params.get( 'dont_preserve_dirs', False ):
            preserve_dirs = False
        # locate files
        bad_paths = []
        uploaded_datasets = []
        for line in [ l.strip() for l in params.filesystem_paths.splitlines() if l.strip() ]:
            path = os.path.abspath( line )
            if not os.path.exists( path ):
                bad_paths.append( path )
                continue
            # don't bother processing if we're just going to return an error
            if not bad_paths:
                if os.path.isfile( path ):
                    name = os.path.basename( path )
                    uploaded_datasets.append( self.make_library_uploaded_dataset( trans, params, name, path, 'path_paste', library_bunch ) )
                for basedir, dirs, files in os.walk( line ):
                    for file in files:
                        file_path = os.path.abspath( os.path.join( basedir, file ) )
                        if preserve_dirs:
                            in_folder = os.path.dirname( file_path.replace( path, '', 1 ).lstrip( '/' ) )
                        else:
                            in_folder = None
                        uploaded_datasets.append( self.make_library_uploaded_dataset( trans, params, file, file_path, 'path_paste', library_bunch, in_folder ) )
        if bad_paths:
            msg = "Invalid paths:<br><ul><li>%s</li></ul>" % "</li><li>".join( bad_paths )
            err_redirect = True
            return None, err_redirect, msg
        return uploaded_datasets, None, None
    @web.expose
    def download_dataset_from_folder( self, trans, cntrller, obj_id, library_id=None, **kwd ):
        """Catches the dataset id and displays file contents as directed"""
        # id must refer to a LibraryDatasetDatasetAssociation object
        ldda = trans.app.model.LibraryDatasetDatasetAssociation.get( obj_id )
        if not ldda.dataset:
            msg = 'Invalid LibraryDatasetDatasetAssociation id %s received for file downlaod' % str( obj_id )
            return trans.response.send_redirect( web.url_for( controller=cntrller,
                                                              action='browse_library',
                                                              obj_id=library_id,
                                                              msg=util.sanitize_text( msg ),
                                                              messagetype='error' ) )
        mime = trans.app.datatypes_registry.get_mimetype_by_extension( ldda.extension.lower() )
        trans.response.set_content_type( mime )
        fStat = os.stat( ldda.file_name )
        trans.response.headers[ 'Content-Length' ] = int( fStat.st_size )
        valid_chars = '.,^_-()[]0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
        fname = ldda.name
        fname = ''.join( c in valid_chars and c or '_' for c in fname )[ 0:150 ]
        trans.response.headers[ "Content-Disposition" ] = "attachment; filename=GalaxyLibraryDataset-%s-[%s]" % ( str( obj_id ), fname )
        try:
            return open( ldda.file_name )
        except: 
            msg = 'This dataset contains no content'
            return trans.response.send_redirect( web.url_for( controller=cntrller,
                                                              action='browse_library',
                                                              obj_id=library_id,
                                                              msg=util.sanitize_text( msg ),
                                                              messagetype='error' ) )
    @web.expose
    def info_template( self, trans, cntrller, library_id, response_action='library', obj_id=None, folder_id=None, ldda_id=None, **kwd ):
        # Only adding a new templAte to a library or folder is currently allowed.  Editing an existing template is
        # a future enhancement.  The response_action param is the name of the method to which this method will redirect
        # if a new template is being added to a library or folder.
        params = util.Params( kwd )
        msg = util.restore_text( params.get( 'msg', ''  ) )
        messagetype = params.get( 'messagetype', 'done' )
        if obj_id:
            library_item = trans.app.model.FormDefinition.get( int( obj_id ) )
            library_item_desc = 'information template'
            response_id = obj_id
        elif folder_id:
            library_item = trans.app.model.LibraryFolder.get( int( folder_id ) )
            library_item_desc = 'folder'
            response_id = folder_id
        elif ldda_id:
            library_item = trans.app.model.LibraryDatasetDatasetAssociation.get( int( ldda_id ) )
            library_item_desc = 'library dataset'
            response_id = ldda_id
        else:
            library_item = trans.app.model.Library.get( int( library_id ) )
            library_item_desc = 'library'
            response_id = library_id
        forms = get_all_forms( trans,
                               filter=dict( deleted=False ),
                               form_type=trans.app.model.FormDefinition.types.LIBRARY_INFO_TEMPLATE )
        if not forms:
            msg = "There are no forms on which to base the template, so create a form and "
            msg += "try again to add the information template to the %s." % library_item_desc
            trans.response.send_redirect( web.url_for( controller='forms',
                                                       action='new',
                                                       new=True,
                                                       msg=msg,
                                                       messagetype='done' ) )
        if params.get( 'add_info_template_button', False ):
            form = trans.app.model.FormDefinition.get( int( kwd[ 'form_id' ] ) )
            #fields = list( copy.deepcopy( form.fields ) )
            form_values = trans.app.model.FormValues( form, [] )
            form_values.flush()
            if folder_id:
                assoc = trans.app.model.LibraryFolderInfoAssociation( library_item, form, form_values )
            elif ldda_id:
                assoc = trans.app.model.LibraryDatasetDatasetInfoAssociation( library_item, form, form_values )
            else:
                assoc = trans.app.model.LibraryInfoAssociation( library_item, form, form_values )
            assoc.flush()
            msg = 'An information template based on the form "%s" has been added to this %s.' % ( form.name, library_item_desc )
            trans.response.send_redirect( web.url_for( controller=cntrller,
                                                       action=response_action,
                                                       obj_id=response_id,
                                                       msg=msg,
                                                       message_type='done' ) )
        # TODO: handle this better
        if cntrller == 'library_admin':
            tmplt = '/admin/library/select_info_template.mako'
        else:
            tmplt = '/ibrary/select_info_template.mako'
        return trans.fill_template( tmplt,
                                    library_item_name=library_item.name,
                                    library_item_desc=library_item_desc,
                                    library_id=library_id,
                                    folder_id=folder_id,
                                    ldda_id=ldda_id,
                                    forms=forms,
                                    msg=msg,
                                    messagetype=messagetype )
    @web.expose
    def edit_template_info( self, trans, cntrller, library_id, response_action, num_widgets, library_item_id=None, library_item_type=None, **kwd ):
        params = util.Params( kwd )
        msg = util.restore_text( params.get( 'msg', ''  ) )
        messagetype = params.get( 'messagetype', 'done' )
        folder_id = None
        if library_item_type == 'library':
            library_item = trans.app.model.Library.get( library_item_id )
        elif library_item_type == 'library_dataset':
            library_item = trans.app.model.LibraryDataset.get( library_item_id )
        elif library_item_type == 'folder':
            library_item = trans.app.model.LibraryFolder.get( library_item_id )
        elif library_item_type == 'library_dataset_dataset_association':
            library_item = trans.app.model.LibraryDatasetDatasetAssociation.get( library_item_id )
            # This response_action method requires a folder_id
            folder_id = library_item.library_dataset.folder.id
        else:
            msg = "Invalid library item type ( %s ) specified, id ( %s )" % ( str( library_item_type ), str( library_item_id ) )
            return trans.response.send_redirect( web.url_for( controller=cntrller,
                                                              action='browse_library',
                                                              obj_id=library_id,
                                                              msg=util.sanitize_text( msg ),
                                                              messagetype='error' ) )
        # Save updated template field contents
        field_contents = []
        for index in range( int( num_widgets ) ):
            field_contents.append( util.restore_text( params.get( 'field_%i' % ( index ), ''  ) ) )
        if field_contents:
            # Since information templates are inherited, the template fields can be displayed on the information
            # page for a folder or library dataset when it has no info_association object.  If the user has added
            # field contents on an inherited template via a parent's info_association, we'll need to create a new
            # form_values and info_association for the current object.  The value for the returned inherited variable
            # is not applicable at this level.
            info_association, inherited = library_item.get_info_association( restrict=True )
            if info_association:
                template = info_association.template
                info = info_association.info
                form_values = trans.app.model.FormValues.get( info.id )
                # Update existing content only if it has changed
                if form_values.content != field_contents:
                    form_values.content = field_contents
                    form_values.flush()
            else:
                # Inherit the next available info_association so we can get the template
                info_association, inherited = library_item.get_info_association()
                template = info_association.template
                # Create a new FormValues object
                form_values = trans.app.model.FormValues( template, field_contents )
                form_values.flush()
                # Create a new info_association between the current library item and form_values
                if library_item_type == 'folder':
                    info_association = trans.app.model.LibraryFolderInfoAssociation( library_item, template, form_values )
                    info_association.flush()
                elif library_item_type == 'library_dataset_dataset_association':
                    info_association = trans.app.model.LibraryDatasetDatasetInfoAssociation( library_item, template, form_values )
                    info_association.flush()
        msg = 'The information has been updated.'
        return trans.response.send_redirect( web.url_for( controller=cntrller,
                                                          action=response_action,
                                                          library_id=library_id,
                                                          folder_id=folder_id,
                                                          obj_id=library_item.id,
                                                          msg=util.sanitize_text( msg ),
                                                          messagetype='done' ) )

# ---- Utility methods -------------------------------------------------------

def active_folders( trans, folder ):
    # Much faster way of retrieving all active sub-folders within a given folder than the
    # performance of the mapper.  This query also eagerloads the permissions on each folder.
    return trans.sa_session.query( trans.app.model.LibraryFolder ) \
                           .filter_by( parent=folder, deleted=False ) \
                           .options( eagerload_all( "actions" ) ) \
                           .order_by( trans.app.model.LibraryFolder.table.c.name ) \
                           .all()
def activatable_folders( trans, folder ):
    return trans.sa_session.query( trans.app.model.LibraryFolder ) \
                           .filter_by( parent=folder, purged=False ) \
                           .options( eagerload_all( "actions" ) ) \
                           .order_by( trans.app.model.LibraryFolder.table.c.name ) \
                           .all()
def active_folders_and_lddas( trans, folder ):
    folders = active_folders( trans, folder )
    # This query is much faster than the folder.active_library_datasets property
    lddas = trans.sa_session.query( trans.app.model.LibraryDatasetDatasetAssociation ) \
                            .filter_by( deleted=False ) \
                            .join( "library_dataset" ) \
                            .filter( trans.app.model.LibraryDataset.table.c.folder_id==folder.id ) \
                            .order_by( trans.app.model.LibraryDatasetDatasetAssociation.table.c.name ) \
                            .all()
    return folders, lddas
def activatable_folders_and_lddas( trans, folder ):
    folders = activatable_folders( trans, folder )
    # This query is much faster than the folder.activatable_library_datasets property
    lddas = trans.sa_session.query( trans.app.model.LibraryDatasetDatasetAssociation ) \
                            .join( "library_dataset" ) \
                            .filter( trans.app.model.LibraryDataset.table.c.folder_id==folder.id ) \
                            .join( "dataset" ) \
                            .filter( trans.app.model.Dataset.table.c.deleted==False ) \
                            .order_by( trans.app.model.LibraryDatasetDatasetAssociation.table.c.name ) \
                            .all()
    return folders, lddas
