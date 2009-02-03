from galaxy.web.base.controller import *
from galaxy.web.controllers.dataset import upload_dataset
from galaxy.model.orm import *
from galaxy.datatypes import sniff
from galaxy import util
import logging, tempfile, zipfile, tarfile, os, sys

if sys.version_info[:2] < ( 2, 6 ):
    zipfile.BadZipFile = zipfile.error
if sys.version_info[:2] < ( 2, 5 ):
    zipfile.LargeZipFile = zipfile.error

log = logging.getLogger( __name__ )

class Library( BaseController ):
    @web.expose
    def browse( self, trans, **kwd ):
        params = util.Params( kwd )
        msg = util.restore_text( params.get( 'msg', ''  ) )
        messagetype = params.get( 'messagetype', 'done' )
        libraries = trans.app.model.Library.filter( trans.app.model.Library.table.c.deleted==False ) \
                                           .order_by( trans.app.model.Library.table.c.name ).all()
        return trans.fill_template( '/library/browser.mako',
                                    libraries=libraries,
                                    default_action=kwd.get( 'default_action', None ),
                                    msg=msg,
                                    messagetype=messagetype )
    index = browse
    @web.expose
    def import_datasets( self, trans, import_ids=[], **kwd ):
        if not import_ids:
            msg = "You must select at least one dataset"
            return trans.response.send_redirect( web.url_for( controller='library', action='browse', msg=util.sanitize_text( msg ), messagetype='error' ) )
        import_ids = util.listify( import_ids )
        p = util.Params( kwd )
        if not p.do_action:
            msg = "You must select an action to perform on selected datasets"
            return trans.response.send_redirect( web.url_for( controller='library', action='browse', msg=util.sanitize_text( msg ), messagetype='error' ) )
        if p.do_action == 'add':
            history = trans.get_history()
            for id in import_ids:
                dataset = trans.app.model.LibraryDatasetDatasetAssociation.get( id ).to_history_dataset_association()
                history.add_dataset( dataset )
                dataset.flush()
            history.flush()
            return trans.show_ok_message( "%i dataset(s) have been imported into your history" % len( import_ids ), refresh_frames=['history'] )
        else:
            # Can't use mkstemp - the file must not exist first
            try:
                tmpd = tempfile.mkdtemp()
                tmpf = os.path.join( tmpd, 'library_download.' + p.do_action )
                if p.do_action == 'zip':
                    try:
                        archive = zipfile.ZipFile( tmpf, 'w', zipfile.ZIP_DEFLATED, True )
                    except RuntimeError:
                        log.exception( "Compression error when opening zipfile for library download" )
                        msg = "ZIP compression is not available in this Python, please notify an administrator"
                        return trans.response.send_redirect( web.url_for( controller='library',
                                                                          action='browse',
                                                                          msg=util.sanitize_text( msg ),
                                                                          messagetype='error' ) )
                    except (TypeError, zipfile.LargeZipFile):
                        # ZIP64 is only in Python2.5+.  Remove TypeError when 2.4 support is dropped
                        log.warning( 'Max zip file size is 2GB, ZIP64 not supported' )
                        archive = zipfile.ZipFile( tmpf, 'w', zipfile.ZIP_DEFLATED )
                    archive.add = lambda x, y: archive.write( x, y.encode('CP437') )
                elif p.do_action == 'tgz':
                    try:
                        archive = tarfile.open( tmpf, 'w:gz' )
                    except tarfile.CompressionError:
                        log.exception( "Compression error when opening tarfile for library download" )
                        msg = "gzip compression is not available in this Python, please notify an administrator"
                        return trans.response.send_redirect( web.url_for( controller='library',
                                                                          action='browse',
                                                                          msg=util.sanitize_text( msg ),
                                                                          messagetype='error' ) )
                elif p.do_action == 'tbz':
                    try:
                        archive = tarfile.open( tmpf, 'w:bz2' )
                    except tarfile.CompressionError:
                        log.exception( "Compression error when opening tarfile for library download" )
                        msg = "bzip2 compression is not available in this Python, please notify an administrator"
                        return trans.response.send_redirect( web.url_for( controller='library',
                                                                          action='browse',
                                                                          msg=util.sanitize_text( msg ),
                                                                          messagetype='error' ) )
            except (OSError, zipfile.BadZipFile, tarfile.ReadError):
                log.exception( "Unable to create archive for download" )
                msg = "Unable to create archive for download, please report this error"
                return trans.response.send_redirect( web.url_for( controller='library',
                                                                  action='browse',
                                                                  msg=util.sanitize_text( msg ),
                                                                  messagetype='error' ) )
            seen = []
            for id in import_ids:
                ldda = trans.app.model.LibraryDatasetDatasetAssociation.get( id )
                if not ldda or not trans.app.security_agent.allow_action( trans.user,
                                                                          trans.app.security_agent.permitted_actions.DATASET_ACCESS,
                                                                          dataset = ldda.dataset ):
                    continue
                path = ""
                parent_folder = ldda.folder
                while parent_folder is not None:
                    path = os.path.join( parent_folder.name, path )
                    if parent_folder.parent is None:
                        path = os.path.join( parent_folder.library_root[0].name, path )
                    parent_folder = parent_folder.parent
                path += ldda.name
                while path in seen:
                    path += '_'
                seen.append( path )
                try:
                    archive.add( ldda.dataset.file_name, path )
                except IOError:
                    log.exception( "Unable to write to temporary library download archive" )
                    msg = "Unable to create archive for download, please report this error"
                    return trans.response.send_redirect( web.url_for( controller='library',
                                                                      action='browse',
                                                                      msg=util.sanitize_text( msg ),
                                                                      messagetype='error' ) )
            archive.close()
            tmpfh = open( tmpf )
            # clean up now
            try:
                os.unlink( tmpf )
                os.rmdir( tmpd )
            except OSError:
                log.exception( "Unable to remove temporary library download archive and directory" )
                msg = "Unable to create archive for download, please report this error"
                return trans.response.send_redirect( web.url_for( controller='library',
                                                                  action='browse',
                                                                  msg=util.sanitize_text( msg ),
                                                                  messagetype='error' ) )
            trans.response.headers[ "Content-Disposition" ] = "attachment; filename=GalaxyLibraryFiles.%s" % kwd['action']
            return tmpfh
    @web.expose
    def download_dataset_from_folder(self, trans, id, **kwd):
        """Catches the dataset id and displays file contents as directed"""
        # id refers to a LibraryDatasetDatasetAssociation object
        ldda = trans.app.model.LibraryDatasetDatasetAssociation.get( id )
        dataset = trans.app.model.Dataset.get( ldda.dataset_id )
        if not dataset:
            msg = 'Invalid id %s received for file downlaod' % str( id )
            return trans.response.send_redirect( web.url_for( action='library_browser', msg=msg, messagetype='error' ) )
        mime = trans.app.datatypes_registry.get_mimetype_by_extension( ldda.extension.lower() )
        trans.response.set_content_type( mime )
        fStat = os.stat( ldda.file_name )
        trans.response.headers[ 'Content-Length' ] = int( fStat.st_size )
        valid_chars = '.,^_-()[]0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
        fname = ldda.name
        fname = ''.join( c in valid_chars and c or '_' for c in fname )[ 0:150 ]
        trans.response.headers[ "Content-Disposition" ] = "attachment; filename=GalaxyLibraryDataset-%s-[%s]" % ( str( id ), fname )
        try:
            return open( ldda.file_name )
        except: 
            msg = 'This dataset contains no content'
            return trans.response.send_redirect( web.url_for( action='library_browser', msg=msg, messagetype='error' ) )
    @web.expose
    def dataset( self, trans, folder_id=None, replace_id=None, name=None, info=None, refer_id=None, **kwd ):
        params = util.Params( kwd )
        msg = util.restore_text( params.get( 'msg', ''  ) )
        messagetype = params.get( 'messagetype', 'done' )
        dbkey = params.get( 'dbkey', '?' )
        last_used_build = params.get( 'last_used_build', None )
        folder = replace_dataset = None
        if folder_id:
            folder = trans.app.model.LibraryFolder.get( folder_id )
            if not last_used_build:
                last_used_build = folder.genome_build
            permission_source = folder
        else:
            replace_dataset = trans.app.model.LibraryDataset.get( replace_id )
            if not last_used_build:
                last_used_build = replace_dataset.library_dataset_dataset_association.dbkey
            permission_source = replace_dataset
        if not folder and not replace_dataset:
            msg = "Invalid library target specifed (folder id: %s, Library Dataset: %s)" %( str( folder_id ), replace_id )
            return trans.response.send_redirect( web.url_for( controller='library', action='browse', msg=util.sanitize_text( msg ), messagetype='error' ) )
        if ( folder and \
             trans.app.security_agent.allow_action( trans.user,
                                                    trans.app.security_agent.permitted_actions.LIBRARY_ADD,
                                                    library_item=folder ) ) or \
             ( replace_dataset and \
               trans.app.security_agent.allow_action( trans.user,
                                                      trans.app.security_agent.permitted_actions.LIBRARY_ADD,
                                                      library_item=replace_dataset ) ):
            if 'new_dataset_button' in kwd:
                # Dataset upload
                created_ldda_ids = upload_dataset( trans,
                                                   controller='library', 
                                                   last_used_build=last_used_build,
                                                   folder_id=folder_id, 
                                                   replace_dataset=replace_dataset, 
                                                   replace_id=replace_id, 
                                                   permission_source=permission_source, 
                                                   **kwd )
                if created_ldda_ids:
                    created_ldda_ids = created_ldda_ids.split( ',' )
                    msg = "%i new datasets added to the library.  " % len( created_ldda_ids )
                    return trans.fill_template( "/library/dataset_manage_list.mako", 
                                                lddas=[ trans.app.model.LibraryDatasetDatasetAssociation.get( ldda_id ) for ldda_id in created_ldda_ids ],
                                                err=None,
                                                msg=msg,
                                                messagetype=messagetype )
                else:
                    msg = "Upload failed"
                    trans.response.send_redirect( web.url_for( action='browse', 
                                                               created_ldda_ids=created_ldda_ids, 
                                                               msg=util.sanitize_text( msg ), 
                                                               messagetype='error' ) )
            elif "add_dataset_from_history_button" in kwd:
                # See if the current history is empty
                history = trans.get_history()
                history.refresh()
                if not history.active_datasets:
                    msg = 'Your current history is empty'
                    return trans.response.send_redirect( web.url_for( action='browse', msg=util.sanitize_text( msg ), messagetype='error' ) )
                    hids = kwd.get( 'hids', [] )
                    if not isinstance( hids, list ):
                        if hids:
                            hids = hids.split( "," )
                        else:
                            hids = []
                    dataset_names = []
                    if hids:
                        for data_id in hids:
                            data = trans.app.model.HistoryDatasetAssociation.get( data_id )
                            if data:
                                data = data.to_library_dataset_folder_association()
                                dataset_names.append( data.name )
                                if folder:
                                    folder.add_dataset( data )
                                elif replace_dataset:
                                    # If we are replacing versions and we receive a list,
                                    # we add all the datasets and set the last one in the list as current
                                    if trans.app.security_agent.allow_action( trans.user, 
                                                                              trans.app.security_agent.permitted_actions.LIBRARY_MODIFY, 
                                                                              library_item=replace_dataset ):
                                        replace_dataset.set_library_dataset_dataset_association( data )
                                    else:
                                        data.library_dataset = replace_dataset
                                data.flush()
                            else:
                                msg = "The requested dataset id %s is invalid" % str( data_id )
                                return trans.response.send_redirect( web.url_for( action='library_browser', 
                                                                                  msg=util.sanitize_text( msg ), 
                                                                                  messagetype='error' ) )
                        if dataset_names:
                            if folder:
                                msg = "Added the following datasets to the library folder: %s" % ( ", ".join( dataset_names ) )
                            else:
                                msg = "Added the following datasets to the versioned library dataset: %s" % ( ", ".join( dataset_names ) )
                            return trans.response.send_redirect( web.url_for( action='browse', msg=util.sanitize_text( msg ), messagetype='done' ) )
                    else:
                        msg = 'Select at least one dataset from the list'
                        messagetype = 'error'
                return trans.fill_template( "/library/new_dataset.mako", history=history, folder=folder, msg=msg, messagetype=messagetype )
        
        #copied...
        def get_dbkey_options( last_used_build ):
            for dbkey, build_name in util.dbnames:
                yield build_name, dbkey, ( dbkey==last_used_build )
        return trans.fill_template( "/library/new_dataset.mako", 
                                    folder=folder,
                                    replace_dataset=replace_dataset,
                                    file_formats=trans.app.datatypes_registry.upload_file_formats,
                                    dbkeys=get_dbkey_options( '?' ),
                                    last_used_build=last_used_build,
                                    err=None,
                                    msg=msg,
                                    messagetype=messagetype )
    @web.expose
    def library_dataset( self, trans, id, name = None, info = None, refer_id = None, **kwd ):
        dataset = trans.app.model.LibraryDataset.get( id )
        if refer_id:
            refered_lda = trans.app.model.LibraryDatasetDatasetAssociation.get( refer_id )
        else:
            refered_lda=None
        msg = ""
        messagetype="done"
        
        if not id or not dataset:
            msg = "Invalid library dataset specified, id: %s" %str( library_dataset_id )
            return trans.response.send_redirect( web.url_for( controller='library', action='browse', msg=util.sanitize_text( msg ), messagetype='error' ) )
        
        if 'save' in kwd:
            if trans.app.security_agent.allow_action( trans.user,
                                                      trans.app.security_agent.permitted_actions.LIBRARY_MODIFY,
                                                      library_item=dataset ):
                dataset.name  = name
                dataset.info  = info
                target_lda = trans.app.model.LibraryDatasetDatasetAssociation.get( kwd.get( 'set_lda_id' ) )
                dataset.library_dataset_dataset_association = target_lda
                trans.app.model.flush()
                msg = 'Attributes updated for library dataset %s' % dataset.name
            else:
                msg = "Permission Denied"
                messagetype = "error"
        elif 'update_roles' in kwd:
            if trans.app.security_agent.allow_action( trans.user,
                                                      trans.app.security_agent.permitted_actions.LIBRARY_MANAGE,
                                                      library_item=dataset ):
            # The user clicked the Save button on the 'Associate With Roles' form
                permissions = {}
                for k, v in trans.app.model.Library.permitted_actions.items():
                    in_roles = [ trans.app.model.Role.get( x ) for x in util.listify( kwd.get( k + '_in', [] ) ) ]
                    permissions[ trans.app.security_agent.get_action( v.action ) ] = in_roles
                trans.app.security_agent.set_all_library_permissions( dataset, permissions )
                dataset.refresh()
                msg = 'Permissions updated for library dataset %s' % dataset.name
            else:
                msg = "Permission Denied"
                messagetype = "error"
        return trans.fill_template( "/library/library_dataset.mako", 
                                        dataset=dataset,
                                        refered_lda = refered_lda,
                                        err=None,
                                        msg=msg,
                                        messagetype=messagetype )
    @web.expose
    def folder( self, trans, folder_id, **kwd ):
        params = util.Params( kwd )
        msg = util.restore_text( params.get( 'msg', ''  ) )
        messagetype = params.get( 'messagetype', 'done' )
        if params.get( 'new', False ):
            action = 'new'
        elif params.get( 'rename', False ):
            action = 'rename'
        elif params.get( 'delete', False ):
            action = 'delete'
        elif params.get( 'update_roles', False ):
            action = 'update_roles'
        else:
            msg = "Invalid action attempted on folder."
            return trans.response.send_redirect( web.url_for( controller='library', action='browse', msg=util.sanitize_text( msg ), messagetype='error' ) )
        folder = trans.app.model.LibraryFolder.get( int( folder_id ) )
        if not folder:
            msg = "Invalid folder specified, id: %s" %str( id )
            return trans.response.send_redirect( web.url_for( controller='library', action='browse', msg=util.sanitize_text( msg ), messagetype='error' ) )
        if action == 'new':
            if params.new == 'submitted':
                # Create the new folder, then return manage_folder template for new folder.
                # New folders default to having the same permissions as their parent folder
                new_folder = trans.app.model.LibraryFolder( name=util.restore_text( params.name ),
                                                            description=util.restore_text( params.description ) )
                new_folder.genome_build = util.dbnames.default_value
                folder.add_folder( new_folder )
                new_folder.flush()
                trans.app.security_agent.copy_library_permissions( folder, new_folder, user = trans.get_user() )
                folder = new_folder
                msg = "New folder named '%s' has been added to the library" % new_folder.name
                return trans.response.send_redirect( web.url_for( controller='library',
                                                                  action='browse',
                                                                  msg=util.sanitize_text( msg ),
                                                                  messagetype='done' ) )
            return trans.fill_template( '/library/new_folder.mako', folder=folder, msg=msg, messagetype=messagetype )
        elif action == 'rename':
            if params.rename == 'submitted':
                if trans.app.security_agent.allow_action( trans.user, 
                                                          trans.app.security_agent.permitted_actions.LIBRARY_MODIFY, 
                                                          library_item=folder ):
                    old_name = folder.name
                    new_name = util.restore_text( params.name )
                    new_description = util.restore_text( params.description )
                    if not new_name:
                        msg = 'Enter a valid name'
                        return trans.fill_template( "/library/manage_folder.mako", folder=folder, msg=msg, messagetype='error' )
                    else:
                        folder.name = new_name
                        folder.description = new_description
                        folder.flush()
                        msg = "Folder '%s' has been renamed to '%s'" % ( old_name, new_name )
                        return trans.response.send_redirect( web.url_for( controller='library',
                                                                          action='browse',
                                                                          msg=util.sanitize_text( msg ),
                                                                          messagetype='done' ) )
                else:
                    msg = "You are not authorized to rename this folder"
                    messagetype = "error"
        elif action == 'update_roles':
            # The user clicked the Save button on the 'Associate With Roles' form
            if trans.app.security_agent.allow_action( trans.user, 
                                                      trans.app.security_agent.permitted_actions.LIBRARY_MANAGE, 
                                                      library_item=folder ):
                permissions = {}
                for k, v in trans.app.model.Library.permitted_actions.items():
                    in_roles = [ trans.app.model.Role.get( int( x ) ) for x in util.listify( kwd.get( k + '_in', [] ) ) ]
                    permissions[ trans.app.security_agent.get_action( v.action ) ] = in_roles
                trans.app.security_agent.set_all_library_permissions( folder, permissions )
                folder.refresh()
                msg = 'Permissions updated for folder %s' % folder.name
                return trans.response.send_redirect( web.url_for( controller='library',
                                                                  action='browse',
                                                                  msg=util.sanitize_text( msg ),
                                                                  messagetype='done' ) )
            else:
                msg = "You are not authorized to manage permissions on this folder"
                return trans.response.send_redirect( web.url_for( controller='library',
                                                                  action='browse',
                                                                  msg=util.sanitize_text( msg ),
                                                                  messagetype='error' ) )
        return trans.fill_template( "/library/manage_folder.mako", folder=folder, msg=msg, messagetype=messagetype )
    @web.expose
    def edit_library( self, trans, id=None, **kwd ):
        raise Exception( 'Not yet implemented' )
    @web.expose
    def library_item_info( self, trans, do_action='display', id=None, library_item_id=None, library_item_type=None, **kwd ):
        if id:
            item_info = trans.app.model.LibraryItemInfo.get( id )
        else:
            item_info = None
        
        if library_item_type == 'library':
            library_item = trans.app.model.Library.get( library_item_id )
        elif library_item_type == 'library_dataset':
            library_item = trans.app.model.LibraryDataset.get( library_item_id )
        elif library_item_type == 'folder':
            library_item = trans.app.model.LibraryFolder.get( library_item_id )
        elif library_item_type == 'library_dataset_dataset_association':
            library_item = trans.app.model.LibraryDatasetDatasetAssociation.get( library_item_id )
        else:
            library_item_type == None
            library_item = None
        msg = ""
        messagetype="done"
        if not item_info and not library_item_type:
            msg = "Unable to perform requested action (%s)." % do_action
            return trans.response.send_redirect( web.url_for( controller='library', action='browse', msg=util.sanitize_text( msg ), messagetype='error' ) )
        if do_action == 'display':
            return trans.fill_template( "/library/display_info.mako", 
                                        item_info=item_info,
                                        err=None,
                                        msg=msg,
                                        messagetype=messagetype )
        elif do_action == 'new_info':
            if library_item:
                if trans.app.security_agent.allow_action( trans.user,
                                                          trans.app.security_agent.permitted_actions.LIBRARY_ADD,
                                                          library_item=library_item ):
                    if 'create_new_info_button' in kwd:
                        user = trans.get_user()
                        #create new info then send back to make more
                        library_item_info_template_id = kwd.get( 'library_item_info_template_id', None )
                        library_item_info_template = trans.app.model.LibraryItemInfoTemplate.get( library_item_info_template_id )
                        library_item_info = trans.app.model.LibraryItemInfo()
                        library_item_info.library_item_info_template = library_item_info_template
                        library_item_info.user = user
                        library_item_info.flush()
                        trans.app.security_agent.copy_permissions( library_item_info_template, library_item_info, user = user )
                        for template_element in library_item_info_template.elements:
                            info_element_value = kwd.get( "info_element_%s_%s" % ( library_item_info_template.id, template_element.id), None )
                            info_element = trans.app.model.LibraryItemInfoElement()
                            info_element.contents = info_element_value
                            info_element.library_item_info_template_element = template_element
                            info_element.library_item_info = library_item_info
                            info_element.flush()
                        info_association_class = None
                        for item_class, permission_class, info_association_class in trans.app.security_agent.library_item_assocs:
                            if isinstance( library_item, item_class ):
                                break
                        if info_association_class:
                            library_item_info_association = info_association_class()
                            library_item_info_association.set_library_item( library_item )
                            library_item_info_association.library_item_info = library_item_info
                            library_item_info_association.user = user
                            library_item_info_association.flush()
                        else:
                            raise 'Invalid class (%s) specified for library_item (%s)' % ( library_item.__class__, library_item.__class__.__name__ )
                        # TODO: make sure we don't need to set permissions on the association object.
                        msg = 'Library Item Info has been save, you can now fill out more templates.'
                    return trans.fill_template( "/library/new_info.mako", 
                                            library_item=library_item,
                                            library_item_type=library_item_type,
                                            err=None,
                                            msg=msg,
                                            messagetype=messagetype )
                else:
                    return trans.show_error_message( "You do not have permission to add info to this library item." )
            #add more functionality -> user's should be able to edit/delete, etc, and create/delete and edit templates
            
            return trans.fill_template( "/library/display_info.mako", 
                                        item_info=item_info,
                                        err=None,
                                        msg="Unable to perform requested action (%s)." % do_action,
                                        messagetype=messagetype )
