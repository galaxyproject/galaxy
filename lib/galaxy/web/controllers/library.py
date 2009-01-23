from galaxy.web.base.controller import *
from galaxy.model.orm import *
from galaxy.datatypes import sniff
import logging, tempfile, zipfile, tarfile, os, sys, StringIO, shutil, urllib

if sys.version_info[:2] < ( 2, 6 ):
    zipfile.BadZipFile = zipfile.error
if sys.version_info[:2] < ( 2, 5 ):
    zipfile.LargeZipFile = zipfile.error

log = logging.getLogger( __name__ )

class Library( BaseController ):
    @web.expose
    def browse( self, trans, msg=None, messagetype=None, **kwd ):
        libraries = trans.app.model.Library.filter( trans.app.model.Library.table.c.deleted==False ) \
                                           .order_by( trans.app.model.Library.table.c.name ).all()
        return trans.fill_template( '/library/browser.mako', libraries=libraries, default_action=kwd.get( 'default_action', None ), msg=msg, messagetype=messagetype )
    index = browse
    @web.expose
    def import_datasets( self, trans, import_ids=[], **kwd ):
        if not import_ids:
            return trans.show_error_message( "You must select at least one dataset" )
        if not isinstance( import_ids, list ):
            import_ids = [ import_ids ]
        p = util.Params( kwd )
        if not p.do_action:
            return trans.show_error_message( "You must select an action to perform on selected datasets" )
        if p.do_action == 'add':
            history = trans.get_history()
            for id in import_ids:
                dataset = trans.app.model.LibraryFolderDatasetAssociation.get( id ).to_history_dataset_association()
                history.add_dataset( dataset )
                dataset.flush()
            history.flush()
            return trans.show_ok_message( "%i dataset(s) have been imported in to your history" % len( import_ids ), refresh_frames=['history'] )
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
                        return trans.show_error_message( "ZIP compression is not available in this Python, please notify an administrator" )
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
                        return trans.show_error_message( "gzip compression is not available in this Python, please notify an administrator" )
                elif p.do_action == 'tbz':
                    try:
                        archive = tarfile.open( tmpf, 'w:bz2' )
                    except tarfile.CompressionError:
                        log.exception( "Compression error when opening tarfile for library download" )
                        return trans.show_error_message( "bzip2 compression is not available in this Python, please notify an administrator" )
            except (OSError, zipfile.BadZipFile, tarfile.ReadError):
                log.exception( "Unable to create archive for download" )
                return trans.show_error_message( "Unable to create archive for download, please report this error" )
            seen = []
            for id in import_ids:
                lfda = trans.app.model.LibraryFolderDatasetAssociation.get( id )
                if not lfda or not trans.app.security_agent.allow_action( trans.user, trans.app.security_agent.permitted_actions.DATASET_ACCESS, dataset = lfda.dataset ):
                    continue
                path = ""
                parent_folder = lfda.folder
                while parent_folder is not None:
                    path = os.path.join( parent_folder.name, path )
                    if parent_folder.parent is None:
                        path = os.path.join( parent_folder.library_root[0].name, path )
                    parent_folder = parent_folder.parent
                path += lfda.name
                while path in seen:
                    path += '_'
                seen.append( path )
                try:
                    archive.add( lfda.dataset.file_name, path )
                except IOError:
                    log.exception( "Unable to write to temporary library download archive" )
                    return trans.show_error_message( "Unable to create archive for download, please report this error" )
            archive.close()
            tmpfh = open( tmpf )
            # clean up now
            try:
                os.unlink( tmpf )
                os.rmdir( tmpd )
            except OSError:
                log.exception( "Unable to remove temporary library download archive and directory" )
                return trans.show_error_message( "Unable to create archive for download, please report this error" )
            trans.response.headers[ "Content-Disposition" ] = "attachment; filename=GalaxyLibraryFiles.%s" % kwd['action']
            return tmpfh
    @web.expose
    def download_dataset_from_folder(self, trans, id, **kwd):
        """Catches the dataset id and displays file contents as directed"""
        # id refers to a LibraryFolderDatasetAssociation object
        lfda = trans.app.model.LibraryFolderDatasetAssociation.get( id )
        dataset = trans.app.model.Dataset.get( lfda.dataset_id )
        if not dataset:
            msg = 'Invalid id %s received for file downlaod' % str( id )
            return trans.response.send_redirect( web.url_for( action='library_browser', msg=msg, messagetype='error' ) )
        mime = trans.app.datatypes_registry.get_mimetype_by_extension( lfda.extension.lower() )
        trans.response.set_content_type( mime )
        fStat = os.stat( lfda.file_name )
        trans.response.headers[ 'Content-Length' ] = int( fStat.st_size )
        valid_chars = '.,^_-()[]0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
        fname = lfda.name
        fname = ''.join( c in valid_chars and c or '_' for c in fname )[ 0:150 ]
        trans.response.headers[ "Content-Disposition" ] = "attachment; filename=GalaxyLibraryDataset-%s-[%s]" % ( str( id ), fname )
        try:
            return open( lfda.file_name )
        except: 
            msg = 'This dataset contains no content'
            return trans.response.send_redirect( web.url_for( action='library_browser', msg=msg, messagetype='error' ) )
    
    @web.expose
    def add_dataset( self, trans, folder_id=None, replace_id = None, name = None, info = None, refer_id = None, **kwd ):
        folder = replace_dataset = None
        if folder_id:
            folder = trans.app.model.LibraryFolder.get( folder_id )
            permission_source = folder
        else:
            replace_dataset = trans.app.model.LibraryDataset.get( replace_id )
            permission_source = replace_dataset
        msg = ""
        messagetype="done"
        
        
        
        #### Copied/modified from admin controller this should be modular
        # add_file method
        def add_file( file_obj, name, extension, dbkey, last_used_build, roles, info='no info', space_to_tab=False, replace_dataset=None ):
            data_type = None
            temp_name = sniff.stream_to_file( file_obj )

            # See if we have a gzipped file, which, if it passes our restrictions, we'll uncompress on the fly.
            is_gzipped, is_valid = self.check_gzip( temp_name )
            if is_gzipped and not is_valid:
                raise BadFileException( "you attempted to upload an inappropriate file." )
            elif is_gzipped and is_valid:
                # We need to uncompress the temp_name file
                CHUNK_SIZE = 2**20 # 1Mb   
                fd, uncompressed = tempfile.mkstemp()   
                gzipped_file = gzip.GzipFile( temp_name )
                while 1:
                    try:
                        chunk = gzipped_file.read( CHUNK_SIZE )
                    except IOError:
                        os.close( fd )
                        os.remove( uncompressed )
                        raise BadFileException( 'problem uncompressing gzipped data.' )
                    if not chunk:
                        break
                    os.write( fd, chunk )
                os.close( fd )
                gzipped_file.close()
                # Replace the gzipped file with the decompressed file
                shutil.move( uncompressed, temp_name )
                name = name.rstrip( '.gz' )
                data_type = 'gzip'

            if space_to_tab:
                line_count = sniff.convert_newlines_sep2tabs( temp_name )
            else:
                line_count = sniff.convert_newlines( temp_name )
            if extension == 'auto':
                data_type = sniff.guess_ext( temp_name, sniff_order=trans.app.datatypes_registry.sniff_order )
            else:
                data_type = extension
            if replace_dataset:
                library_dataset = replace_dataset
            else:
                library_dataset = trans.app.model.LibraryDataset( name=name, info=info, extension=data_type, dbkey=dbkey )
                library_dataset.flush()
                trans.app.model.library_security_agent.copy_permissions( permission_source, library_dataset, user = trans.get_user() )
            
            dataset = trans.app.model.LibraryFolderDatasetAssociation( name=name, 
                                                                       info=info, 
                                                                       extension=data_type, 
                                                                       dbkey=dbkey, 
                                                                       library_dataset = library_dataset,
                                                                       create_dataset=True )
            dataset.flush()
            trans.app.model.library_security_agent.copy_permissions( permission_source, dataset, user = trans.get_user() )
            #library_item.set_library_folder_dataset_association( dataset )
            if not replace_dataset:
                folder = trans.app.model.LibraryFolder.get( folder_id )
                folder.add_dataset( library_dataset, genome_build=last_used_build )
            library_dataset.library_folder_dataset_association_id = dataset.id
            #library_dataset.library_folder_dataset_association = dataset
            library_dataset.flush()
            if roles:
                for role in roles:
                    adra = trans.app.model.ActionDatasetRoleAssociation( RBACAgent.permitted_actions.DATASET_ACCESS.action, dataset.dataset, role )
                    adra.flush()
            shutil.move( temp_name, dataset.dataset.file_name )
            dataset.dataset.state = dataset.dataset.states.OK
            dataset.init_meta()
            if line_count is not None:
                try:
                    dataset.set_peek( line_count=line_count )
                except:
                    dataset.set_peek()
            else:
                dataset.set_peek()
            dataset.set_size()
            if dataset.missing_meta():
                dataset.datatype.set_meta( dataset )
            trans.app.model.flush()
            return dataset
        # END add_file method
        
        
        
        
        if not folder and not replace_dataset:
            msg = "Invalid library target specifed (folder id: %s, Library Dataset: %s)" %( str( folder_id ), replace_id )
            return trans.response.send_redirect( web.url_for( controller='library', action='browse', msg=util.sanitize_text( msg ), messagetype='error' ) )
        
        if ( folder and trans.app.model.library_security_agent.allow_action( trans.user, trans.app.model.library_security_agent.permitted_actions.LIBRARY_ADD, folder ) ) or ( replace_dataset and trans.app.model.library_security_agent.allow_action( trans.user, trans.app.model.library_security_agent.permitted_actions.LIBRARY_ADD, replace_dataset ) ):
            if 'new_dataset_button' in kwd:
                params = util.Params( kwd )
                
                #todo: populate these vars better
                dbkey = params.get( 'dbkey', '?' )
                last_used_build = dbkey
                extension = params.get( 'extension', 'auto' )
                
                #### Copied from admin controller this should be unified
                # Copied from upload tool action
                data_file = params.get( 'file_data', '' )
                url_paste = params.get( 'url_paste', '' )
                server_dir = params.get( 'server_dir', 'None' )
                if data_file == '' and url_paste == '' and server_dir in [ 'None', '' ]:
                    if trans.app.config.library_import_dir is not None:
                        msg = 'Select a file, enter a URL or Text, or select a server directory.'
                    else:
                        msg = 'Select a file, enter a URL or enter Text.'
                    trans.response.send_redirect( web.url_for( action='add_dataset', folder_id=folder_id, replace_id=replace_id, msg=util.sanitize_text( msg ), messagetype='done' ) )
                space_to_tab = params.get( 'space_to_tab', False )
                if space_to_tab and space_to_tab not in [ "None", None ]:
                    space_to_tab = True
                roles = []
                role_ids = params.get( 'roles', [] )
                for role_id in util.listify( role_ids ):
                    roles.append( trans.app.model.Role.get( role_id ) )
                temp_name = ""
                data_list = []
                created_lfda_ids = ''
                if 'filename' in dir( data_file ):
                    file_name = data_file.filename
                    file_name = file_name.split( '\\' )[-1]
                    file_name = file_name.split( '/' )[-1]
                    created_lfda = add_file( data_file.file,
                                             file_name,
                                             extension,
                                             dbkey,
                                             last_used_build,
                                             roles,
                                             info="uploaded file",
                                             space_to_tab=space_to_tab,
                                             replace_dataset=replace_dataset )
                    created_lfda_ids = str( created_lfda.id )
                elif url_paste not in [ None, "" ]:
                    if url_paste.lower().find( 'http://' ) >= 0 or url_paste.lower().find( 'ftp://' ) >= 0:
                        url_paste = url_paste.replace( '\r', '' ).split( '\n' )
                        for line in url_paste:
                            line = line.rstrip( '\r\n' )
                            if line:
                                created_lfda = add_file( urllib.urlopen( line ),
                                                         line,
                                                         extension,
                                                         dbkey,
                                                         last_used_build,
                                                         roles,
                                                         info="uploaded url",
                                                         space_to_tab=space_to_tab,
                                                         replace_dataset=replace_dataset )
                                created_lfda_ids = '%s,%s' % ( created_lfda_ids, str( created_lfda.id ) )
                    else:
                        is_valid = False
                        for line in url_paste:
                            line = line.rstrip( '\r\n' )
                            if line:
                                is_valid = True
                                break
                        if is_valid:
                            created_lfda = add_file( StringIO.StringIO( url_paste ),
                                                     'Pasted Entry',
                                                     extension,
                                                     dbkey,
                                                     last_used_build,
                                                     roles,
                                                     info="pasted entry",
                                                     space_to_tab=space_to_tab,
                                                     replace_dataset=replace_dataset )
                            created_lfda_ids = '%s,%s' % ( created_lfda_ids, str( created_lfda.id ) )
                elif server_dir not in [ None, "", "None" ]:
                    full_dir = os.path.join( trans.app.config.library_import_dir, server_dir )
                    try:
                        files = os.listdir( full_dir )
                    except:
                        log.debug( "Unable to get file list for %s" % full_dir )
                    for file in files:
                        full_file = os.path.join( full_dir, file )
                        if not os.path.isfile( full_file ):
                            continue
                        created_lfda = add_file( open( full_file, 'rb' ),
                                                 file,
                                                 extension,
                                                 dbkey,
                                                 last_used_build,
                                                 roles,
                                                 info="imported file",
                                                 space_to_tab=space_to_tab,
                                                 replace_dataset=replace_dataset )
                        created_lfda_ids = '%s,%s' % ( created_lfda_ids, str( created_lfda.id ) )
                if created_lfda_ids:
                    created_lfda_ids = created_lfda_ids.lstrip( ',' )
                    created_lfda_ids = created_lfda_ids.split(',')
                    msg = "%i new datasets added to the library.  " % len( created_lfda_ids )
                    return trans.fill_template( "/library/dataset_manage_list.mako", 
                                                lfdas=[ trans.app.model.LibraryFolderDatasetAssociation.get( lfda_id ) for lfda_id in created_lfda_ids ],
                                                err=None,
                                                msg=msg,
                                                messagetype=messagetype )
                    
                    #total_added = len( created_lfda_ids.split( ',' ) )
                    #msg = "%i new datasets added to the library ( each is selected below ).  " % total_added
                    #msg += "Click the Go button at the bottom of this page to edit the permissions on these datasets if necessary."
                    #trans.response.send_redirect( web.url_for( action='browse',
                    #                                           created_lfda_ids=created_lfda_ids, 
                    #                                           msg=util.sanitize_text( msg ), 
                    #                                           messagetype='done' ) )
                else:
                    msg = "Upload failed"
                    trans.response.send_redirect( web.url_for( action='browse',
                                                               created_lfda_ids=created_lfda_ids,
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
                                    #if we are replacing versions and we recieve a list, we add all the datasets, and set the last one in the list as current
                                    if trans.app.model.library_security_agent.allow_action( trans.user, trans.app.model.library_security_agent.permitted_actions.LIBRARY_MODIFY, replace_dataset ):
                                        replace_dataset.set_library_folder_dataset_association( data )
                                    else:
                                        data.library_dataset = replace_dataset
                                data.flush()
                            else:
                                msg = "The requested dataset id %s is invalid" % str( data_id )
                                return trans.response.send_redirect( web.url_for( action='library_browser', msg=util.sanitize_text( msg ), messagetype='error' ) )
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
                                        replace_dataset = replace_dataset,
                                        file_formats=trans.app.datatypes_registry.upload_file_formats,
                                        dbkeys = get_dbkey_options( '?' ),
                                        err=None,
                                        msg=msg,
                                        messagetype=messagetype )

    
    @web.expose
    def library_dataset( self, trans, id, name = None, info = None, refer_id = None, **kwd ):
        dataset = trans.app.model.LibraryDataset.get( id )
        if refer_id:
            refered_lda = trans.app.model.LibraryFolderDatasetAssociation.get( refer_id )
        else:
            refered_lda=None
        msg = ""
        messagetype="done"
        
        if not id or not dataset:
            msg = "Invalid library dataset specified, id: %s" %str( library_dataset_id )
            return trans.response.send_redirect( web.url_for( controller='library', action='browse', msg=util.sanitize_text( msg ), messagetype='error' ) )
        
        if 'save' in kwd:
            if trans.app.model.library_security_agent.allow_action( trans.user, trans.app.model.library_security_agent.permitted_actions.LIBRARY_MODIFY, dataset ):
                dataset.name  = name
                dataset.info  = info
                target_lda = trans.app.model.LibraryFolderDatasetAssociation.get( kwd.get( 'set_lda_id' ) )
                dataset.library_folder_dataset_association = target_lda
                trans.app.model.flush()
                msg = 'Attributes updated for library dataset %s' % dataset.name
            else:
                msg = "Permission Denied"
                messagetype = "error"
        elif 'update_roles' in kwd:
            if trans.app.model.library_security_agent.allow_action( trans.user, trans.app.model.library_security_agent.permitted_actions.LIBRARY_MANAGE, dataset ):
            # The user clicked the Save button on the 'Associate With Roles' form
                permissions = {}
                for k, v in trans.app.model.library_security_agent.permitted_actions.items():
                    in_roles = [ trans.app.model.Role.get( x ) for x in util.listify( kwd.get( k + '_in', [] ) ) ]
                    permissions[ trans.app.model.library_security_agent.get_action( v.action ) ] = in_roles
                trans.app.model.library_security_agent.set_all_permissions( dataset, permissions )
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
    def folder( self, trans, id, name = None, description = None, **kwd ):
        folder = trans.app.model.LibraryFolder.get( id )
        msg = ""
        messagetype="done"
        
        if not id or not folder:
            msg = "Invalid library folder specified, id: %s" %str( id )
            return trans.response.send_redirect( web.url_for( controller='library', action='browse', msg=util.sanitize_text( msg ), messagetype='error' ) )
        
        if 'save' in kwd:
            if trans.app.model.library_security_agent.allow_action( trans.user, trans.app.model.library_security_agent.permitted_actions.LIBRARY_MODIFY, folder ):
                folder.name  = name
                folder.description  = description
                trans.app.model.flush()
                msg = 'Attributes updated for library folder %s' % folder.name
            else:
                msg = "Permission Denied"
                messagetype = "error"
        elif 'update_roles' in kwd:
            if trans.app.model.library_security_agent.allow_action( trans.user, trans.app.model.library_security_agent.permitted_actions.LIBRARY_MANAGE, folder ):
            # The user clicked the Save button on the 'Associate With Roles' form
                permissions = {}
                for k, v in trans.app.model.library_security_agent.permitted_actions.items():
                    in_roles = [ trans.app.model.Role.get( x ) for x in util.listify( kwd.get( k + '_in', [] ) ) ]
                    permissions[ trans.app.model.library_security_agent.get_action( v.action ) ] = in_roles
                trans.app.model.library_security_agent.set_all_permissions( folder, permissions )
                folder.refresh()
                msg = 'Permissions updated for library folder %s' % folder.name
            else:
                msg = "Permission Denied"
                messagetype = "error"
        elif 'create_new' in kwd:
            #create folder then return manage_folder template for new folder
            #new folders default to having the same permissions as their parent folder
            new_folder = trans.app.model.LibraryFolder( name = name, description = description )
            new_folder.flush()
            folder.add_folder( new_folder )
            new_folder.flush()
            trans.app.model.library_security_agent.copy_permissions( folder, new_folder, user = trans.get_user() )
            folder = new_folder
            msg = "New folder (%s) created." % ( new_folder.name )
        return trans.fill_template( "/library/manage_folder.mako", 
                                        folder=folder,
                                        err=None,
                                        msg=msg,
                                        messagetype=messagetype )

    @web.expose
    def edit_library( self, trans, id=None, **kwd ):
        raise Exception( 'Not yet implemented' )


    @web.expose
    def library_item_info( self, trans, do_action='display', id=None, library_item_id=None, library_item_type=None, **kwd ):
        #dataset = trans.app.model.LibraryDataset.get( id )
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
        elif library_item_type == 'library_folder_dataset_association':
            library_item = trans.app.model.LibraryFolderDatasetAssociation.get( library_item_id )
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
                if trans.app.model.library_security_agent.allow_action( trans.user, trans.app.model.library_security_agent.permitted_actions.LIBRARY_ADD, library_item ):
                    if 'create_new_info_button' in kwd:
                        user = trans.get_user()
                        #create new info then send back to make more
                        library_item_info_template_id = kwd.get( 'library_item_info_template_id', None )
                        library_item_info_template = trans.app.model.LibraryItemInfoTemplate.get( library_item_info_template_id )
                        library_item_info = trans.app.model.LibraryItemInfo()
                        library_item_info.library_item_info_template = library_item_info_template
                        library_item_info.user = user
                        library_item_info.flush()
                        
                        trans.app.model.library_security_agent.copy_permissions( library_item_info_template, library_item_info, user = user )
                        
                        for template_element in library_item_info_template.elements:
                            info_element_value = kwd.get( "info_element_%s_%s" % ( library_item_info_template.id, template_element.id), None )
                            info_element = trans.app.model.LibraryItemInfoElement()
                            info_element.contents = info_element_value
                            info_element.library_item_info_template_element = template_element
                            info_element.library_item_info = library_item_info
                            info_element.flush()
                        library_item_info_association = trans.app.model.LibraryItemInfoAssociation()
                        library_item_info_association.set_library_item( library_item )
                        library_item_info_association.library_item_info = library_item_info
                        library_item_info_association.user = user
                        library_item_info_association.flush()
                        #don't need to set permissions on the association object?
                        
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



#methods used when adding files, copied from upload...
    def check_gzip( self, temp_name ):
        temp = open( temp_name, "U" )
        magic_check = temp.read( 2 )
        temp.close()
        if magic_check != util.gzip_magic:
            return ( False, False )
        CHUNK_SIZE = 2**15 # 32Kb
        gzipped_file = gzip.GzipFile( temp_name )
        chunk = gzipped_file.read( CHUNK_SIZE )
        gzipped_file.close()
        if self.check_html( temp_name, chunk=chunk ) or self.check_binary( temp_name, chunk=chunk ):
            return( True, False )
        return ( True, True )

    def check_zip( self, temp_name ):
        if not zipfile.is_zipfile( temp_name ):
            return ( False, False, None )
        zip_file = zipfile.ZipFile( temp_name, "r" )
        # Make sure the archive consists of valid files.  The current rules are:
        # 1. Archives can only include .ab1, .scf or .txt files
        # 2. All file extensions within an archive must be the same
        name = zip_file.namelist()[0]
        test_ext = name.split( "." )[1].strip().lower()
        if not ( test_ext == 'scf' or test_ext == 'ab1' or test_ext == 'txt' ):
            return ( True, False, test_ext )
        for name in zip_file.namelist():
            ext = name.split( "." )[1].strip().lower()
            if ext != test_ext:
                return ( True, False, test_ext )
        return ( True, True, test_ext )

    def check_html( self, temp_name, chunk=None ):
        if chunk is None:
            temp = open(temp_name, "U")
        else:
            temp = chunk
        regexp1 = re.compile( "<A\s+[^>]*HREF[^>]+>", re.I )
        regexp2 = re.compile( "<IFRAME[^>]*>", re.I )
        regexp3 = re.compile( "<FRAMESET[^>]*>", re.I )
        regexp4 = re.compile( "<META[^>]*>", re.I )
        lineno = 0
        for line in temp:
            lineno += 1
            matches = regexp1.search( line ) or regexp2.search( line ) or regexp3.search( line ) or regexp4.search( line )
            if matches:
                if chunk is None:
                    temp.close()
                return True
            if lineno > 100:
                break
        if chunk is None:
            temp.close()
        return False

    def check_binary( self, temp_name, chunk=None ):
        if chunk is None:
            temp = open( temp_name, "U" )
        else:
            temp = chunk
        lineno = 0
        for line in temp:
            lineno += 1
            line = line.strip()
            if line:
                for char in line:
                    if ord( char ) > 128:
                        if chunk is None:
                            temp.close()
                        return True
            if lineno > 10:
                break
        if chunk is None:
            temp.close()
        return False

class BadFileException( Exception ):
    pass
