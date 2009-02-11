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
    def datasets( self, trans, ldda_ids=[], **kwd ):
        # This method is used by the select list labeled "Perform action on selected datasets"
        # on the analysis library browser.
        if not ldda_ids:
            msg = "You must select at least one dataset"
            return trans.response.send_redirect( web.url_for( controller='library',
                                                              action='browse',
                                                              msg=util.sanitize_text( msg ),
                                                              messagetype='error' ) )
        ldda_ids = util.listify( ldda_ids )
        params = util.Params( kwd )
        msg = util.restore_text( params.get( 'msg', ''  ) )
        messagetype = params.get( 'messagetype', 'done' )
        if not params.do_action:
            msg = "You must select an action to perform on selected datasets"
            return trans.response.send_redirect( web.url_for( controller='library',
                                                              action='browse',
                                                              msg=util.sanitize_text( msg ),
                                                              messagetype='error' ) )
        if params.do_action == 'add':
            history = trans.get_history()
            for id in ldda_ids:
                dataset = trans.app.model.LibraryDatasetDatasetAssociation.get( id ).to_history_dataset_association()
                history.add_dataset( dataset )
                dataset.flush()
            history.flush()
            return trans.show_ok_message( "%i dataset(s) have been imported into your history" % len( ldda_ids ), refresh_frames=['history'] )
        elif params.do_action == 'manage_permissions':
            # Do we need a security check here?
            trans.response.send_redirect( web.url_for( controller='library',
                                                       action='dataset',
                                                       ldda_id=','.join( ldda_ids ),
                                                       msg=util.sanitize_text( msg ),
                                                       messagetype=messagetype ) )
        else:
            # Can't use mkstemp - the file must not exist first
            try:
                tmpd = tempfile.mkdtemp()
                tmpf = os.path.join( tmpd, 'library_download.' + params.do_action )
                if params.do_action == 'zip':
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
                elif params.do_action == 'tgz':
                    try:
                        archive = tarfile.open( tmpf, 'w:gz' )
                    except tarfile.CompressionError:
                        log.exception( "Compression error when opening tarfile for library download" )
                        msg = "gzip compression is not available in this Python, please notify an administrator"
                        return trans.response.send_redirect( web.url_for( controller='library',
                                                                          action='browse',
                                                                          msg=util.sanitize_text( msg ),
                                                                          messagetype='error' ) )
                elif params.do_action == 'tbz':
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
            for id in ldda_ids:
                ldda = trans.app.model.LibraryDatasetDatasetAssociation.get( id )
                if not ldda or not trans.app.security_agent.allow_action( trans.user,
                                                                          trans.app.security_agent.permitted_actions.DATASET_ACCESS,
                                                                          dataset = ldda.dataset ):
                    continue
                path = ""
                parent_folder = ldda.library_dataset.folder
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
            trans.response.headers[ "Content-Disposition" ] = "attachment; filename=GalaxyLibraryFiles.%s" % params.do_action
            return tmpfh
    @web.expose
    def download_dataset_from_folder(self, trans, id, **kwd):
        """Catches the dataset id and displays file contents as directed"""
        # id must refer to a LibraryDatasetDatasetAssociation object
        ldda = trans.app.model.LibraryDatasetDatasetAssociation.get( id )
        if not ldda.dataset:
            msg = 'Invalid LibraryDatasetDatasetAssociation id %s received for file downlaod' % str( id )
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
    def dataset( self, trans, ldda_id=None, name=None, info=None, folder_id=None, replace_id=None, refer_id=None, **kwd ):
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
        try:
            replace_dataset = trans.app.model.LibraryDataset.get( params.get( 'replace_id', None ) )
            if not last_used_build:
                last_used_build = replace_dataset.library_dataset_dataset_association.dbkey
            permission_source = replace_dataset
        except:
            replace_dataset = None
        if ldda_id:
            # The user is updating the permissions on 1 or more datasets
            if ldda_id.count( ',' ):
                ldda_ids = ldda_id.split( ',' )
                ldda_id = None
            else:
                ldda_ids = None
            if ldda_id:
                # ldda_id specified, display attributes form
                ldda = trans.app.model.LibraryDatasetDatasetAssociation.get( ldda_id )
                if not ldda:
                    msg = "Invalid LibraryDatasetDatasetAssociation specified, id: %s" % str( ldda_id )
                    return trans.response.send_redirect( web.url_for( controller='library',
                                                                      action='browser',
                                                                      msg=util.sanitize_text( msg ),
                                                                      messagetype='error' ) )
                if params.get( 'update_roles', False ):
                    # The user clicked the Save button on the 'Associate With Roles' form
                    permissions = {}
                    for k, v in trans.app.model.Dataset.permitted_actions.items():
                        in_roles = [ trans.app.model.Role.get( x ) for x in util.listify( params.get( k + '_in', [] ) ) ]
                        permissions[ trans.app.security_agent.get_action( v.action ) ] = in_roles
                    trans.app.security_agent.set_all_dataset_permissions( ldda.dataset, permissions )
                    # Set/display library security info
                    permissions = {}
                    for k, v in trans.app.model.Library.permitted_actions.items():
                        in_roles = [ trans.app.model.Role.get( x ) for x in util.listify( kwd.get( k + '_in', [] ) ) ]
                        permissions[ trans.app.security_agent.get_action( v.action ) ] = in_roles
                    trans.app.security_agent.set_all_library_permissions( ldda, permissions )
                    ldda.dataset.refresh()
                    msg = "Permissions updated for dataset '%s'" % ldda.name
                    return trans.response.send_redirect( web.url_for( controller='library',
                                                                      action='dataset',
                                                                      ldda_id=ldda_id,
                                                                      msg=util.sanitize_text( msg ),
                                                                      messagetype='done' ) )
            elif ldda_ids:
                # Multiple ids specfied, display permission form, permissions will be updated for all simultaneously.
                lddas = []
                for ldda_id in [ int( ldda_id ) for ldda_id in ldda_ids ]:
                    ldda = trans.app.model.LibraryDatasetDatasetAssociation.get( ldda_id )
                    if ldda is None:
                        msg = 'You specified an invalid LibraryDatasetDatasetAssociation id: %s' %str( ldda_id )
                        trans.response.send_redirect( web.url_for( controller='library',
                                                                   action='browser',
                                                                   msg=util.sanitize_text( msg ),
                                                                   messagetype='error' ) )
                    lddas.append( ldda )
                if len( lddas ) < 2:
                    msg = 'You must specify at least two datasets on which to modify permissions, ids you sent: %s' % str( ldda_ids )
                    trans.response.send_redirect( web.url_for( controller='library',
                                                               action='browser',
                                                               msg=util.sanitize_text( msg ),
                                                               messagetype='error' ) )
                if 'update_roles' in kwd:
                    #p = util.Params( kwd )
                    permissions = {}
                    for k, v in trans.app.model.Dataset.permitted_actions.items():
                        in_roles = [ trans.app.model.Role.get( x ) for x in util.listify( params.get( k + '_in', [] ) ) ]
                        permissions[ trans.app.security_agent.get_action( v.action ) ] = in_roles
                    for ldda in lddas:
                        trans.app.security_agent.set_all_dataset_permissions( ldda.dataset, permissions )
                        ldda.dataset.refresh()
                    msg = 'Permissions and roles have been updated on %d datasets' % len( lddas )
                    return trans.fill_template( "/library/manage_dataset.mako", msg=msg, messagetype=messagetype, dataset=lddas )
                # Ensure that the permissions across all datasets are identical.  Otherwise, we can't update together.
                tmp = []
                for ldda in lddas:
                    perms = trans.app.security_agent.get_dataset_permissions( ldda.dataset )
                    if perms not in tmp:
                        tmp.append( perms )
                if len( tmp ) != 1:
                    msg = 'The datasets you selected do not have identical permissions, so they can not be updated together'
                    trans.response.send_redirect( web.url_for( controller='library',
                                                               action='browse',
                                                               msg=util.sanitize_text( msg ),
                                                               messagetype='error' ) )
                else:
                    return trans.fill_template( "/library/manage_dataset.mako", msg=msg, messagetype=messagetype, dataset=lddas )
        if not folder and not replace_dataset:
            msg = "Invalid library target specified (LibraryFolder id: %s, LibraryDataset id: %s)" % ( str( folder_id ), str( replace_id ) )
            return trans.response.send_redirect( web.url_for( controller='library', action='browse', msg=util.sanitize_text( msg ), messagetype='error' ) )
        if ( folder and trans.app.security_agent.allow_action( trans.user,
                                                               trans.app.security_agent.permitted_actions.LIBRARY_ADD,
                                                               library_item=folder ) ) or \
             ( replace_dataset and trans.app.security_agent.allow_action( trans.user,
                                                                          trans.app.security_agent.permitted_actions.LIBRARY_ADD,
                                                                          library_item=replace_dataset ) ):
            if params.get( 'new_dataset_button', False ):
                created_ldda_ids = upload_dataset( trans,
                                                              controller='library', 
                                                              last_used_build=last_used_build,
                                                              folder_id=folder_id, 
                                                              replace_dataset=replace_dataset, 
                                                              permission_source=permission_source, 
                                                              **kwd )
                if created_ldda_ids:
                    #msg = "%i new datasets added to the library.  " % len( created_ldda_ids )
                    #return trans.fill_template( "/library/dataset_manage_list.mako", 
                    #                            lddas=[ trans.app.model.LibraryDataset.get( id ) for id in util.listify( created_ldda_ids ) ],
                    #                            msg=msg,
                    #                            messagetype=messagetype )
                
                    total_added = len( created_ldda_ids.split( ',' ) )
                    msg = "%i new datasets added to the library ( each is selected below ).  " % total_added
                    if trans.app.security_agent.allow_action( trans.user,
                                                              trans.app.security_agent.permitted_actions.LIBRARY_MANAGE,
                                                              library_item=permission_source ):
                        msg += "Click the Go button at the bottom of this page to edit the permissions on these datasets if necessary."
                        default_action = 'manage_permissions'
                    else:
                        default_action = 'add'
                    trans.response.send_redirect( web.url_for( controller='library',
                                                               action='browse',
                                                               default_action=default_action,
                                                               created_ldda_ids=created_ldda_ids, 
                                                               msg=util.sanitize_text( msg ), 
                                                               messagetype='done' ) )
                    
                else:
                    msg = "Upload failed"
                    trans.response.send_redirect( web.url_for( action='browse', 
                                                               created_ldda_ids=created_ldda_ids, 
                                                               msg=util.sanitize_text( msg ), 
                                                               messagetype='error' ) )
            elif params.get( "add_dataset_from_history_button", False):
                # See if the current history is empty
                history = trans.get_history()
                history.refresh()
                if not history.active_datasets:
                    msg = 'Your current history is empty'
                    return trans.response.send_redirect( web.url_for( action='browse', msg=util.sanitize_text( msg ), messagetype='error' ) )
                hids = util.listify( params.get( 'hids', [] ) )
                dataset_names = []
                if hids:
                    for data_id in hids:
                        data = trans.app.model.HistoryDatasetAssociation.get( data_id )
                        if data:
                            data = data.to_library_dataset_dataset_association( target_folder=folder )
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
                            return trans.response.send_redirect( web.url_for( controller='library',
                                                                              action='browse', 
                                                                              msg=util.sanitize_text( msg ), 
                                                                              messagetype='error' ) )
                    if dataset_names:
                        if folder:
                            msg = "Added %d datasets to the library folder '%s'" % ( len( dataset_names ), folder.name )
                        else:
                            msg = "Added %d datasets to the versioned library dataset '%s'" % ( len( dataset_names ), replace_dataset.name )
                        return trans.response.send_redirect( web.url_for( controller='library',
                                                                          action='browse',
                                                                          msg=util.sanitize_text( msg ),
                                                                          messagetype='done' ) )
                else:
                    # No dataset(s) specified, display upload form
                    file_formats = trans.app.datatypes_registry.upload_file_formats
                    # Send list of genome builds to the form so the "dbkey" select list can be populated dynamically
                    def get_dbkey_options( last_used_build ):
                        for dbkey, build_name in util.dbnames:
                            yield build_name, dbkey, ( dbkey==last_used_build )
                    dbkeys = get_dbkey_options( last_used_build )
                    # Send list of roles to the form so the dataset can be associated with 1 or more of them.
                    roles = trans.app.model.Role.filter( trans.app.model.Role.table.c.deleted==False ).order_by( trans.app.model.Role.c.name ).all()
                    msg = 'Select at least one dataset from the list'
                    return trans.fill_template( "/library/new_dataset.mako",
                                                history=history,
                                                folder_id=folder_id,
                                                file_formats=file_formats,
                                                dbkeys=dbkeys,
                                                last_used_build=last_used_build,
                                                roles=roles,
                                                replace_dataset=replace_dataset,
                                                msg=msg,
                                                messagetype='error' )
        
        #copied...
        def get_dbkey_options( last_used_build ):
            for dbkey, build_name in util.dbnames:
                yield build_name, dbkey, ( dbkey==last_used_build )
        return trans.fill_template( "/library/new_dataset.mako", 
                                    folder_id=folder_id,
                                    replace_dataset=replace_dataset,
                                    file_formats=trans.app.datatypes_registry.upload_file_formats,
                                    dbkeys=get_dbkey_options( '?' ),
                                    last_used_build=last_used_build,
                                    err=None,
                                    msg=msg,
                                    messagetype=messagetype )
    @web.expose
    def library_dataset( self, trans, id, name=None, info=None, refer_id=None, **kwd ):
        params = util.Params( kwd )
        msg = util.restore_text( params.get( 'msg', ''  ) )
        messagetype = params.get( 'messagetype', 'done' )
        library_dataset = trans.app.model.LibraryDataset.get( id )
        if not library_dataset:
            msg = "Invalid library dataset specified, id: %s" %str( id )
            return trans.response.send_redirect( web.url_for( controller='library',
                                                              action='browse',
                                                              msg=util.sanitize_text( msg ),
                                                              messagetype='error' ) )
        if refer_id:
            refered_lda = trans.app.model.LibraryDatasetDatasetAssociation.get( refer_id )
        else:
            refered_lda=None        
        if params.get( 'save', False ):
            if trans.app.security_agent.allow_action( trans.user,
                                                      trans.app.security_agent.permitted_actions.LIBRARY_MODIFY,
                                                      library_item=library_dataset ):
                library_dataset.name = name
                library_dataset.info = info
                target_lda = trans.app.model.LibraryDatasetDatasetAssociation.get( kwd.get( 'set_lda_id' ) )
                library_dataset.library_dataset_dataset_association = target_lda
                trans.app.model.flush()
                msg = 'Attributes updated for library dataset %s' % library_dataset.name
                messagetype = 'done'
            else:
                msg = "You are not authorized to changed the attributes of this dataset"
                messagetype = "error"
            return trans.response.send_redirect( web.url_for( controller='library',
                                                              action='library_dataset',
                                                              id=id,
                                                              msg=util.sanitize_text( msg ),
                                                              messagetype=messagetype ) )
        elif 'update_roles' in kwd:
            if trans.app.security_agent.allow_action( trans.user,
                                                      trans.app.security_agent.permitted_actions.LIBRARY_MANAGE,
                                                      library_item=library_dataset ):
            # The user clicked the Save button on the 'Associate With Roles' form
                permissions = {}
                for k, v in trans.app.model.Library.permitted_actions.items():
                    in_roles = [ trans.app.model.Role.get( x ) for x in util.listify( kwd.get( k + '_in', [] ) ) ]
                    permissions[ trans.app.security_agent.get_action( v.action ) ] = in_roles
                trans.app.security_agent.set_all_library_permissions( library_dataset, permissions )
                library_dataset.refresh()
                msg = 'Permissions updated for library dataset %s' % library_dataset.name
            else:
                msg = "Permission Denied"
                messagetype = "error"
        return trans.fill_template( "/library/manage_library_dataset.mako", 
                                    dataset=library_dataset,
                                    refered_lda=refered_lda,
                                    msg=msg,
                                    messagetype=messagetype )
    @web.expose
    def folder( self, trans, folder_id, **kwd ):
        params = util.Params( kwd )
        msg = util.restore_text( params.get( 'msg', ''  ) )
        messagetype = params.get( 'messagetype', 'done' )
        if params.get( 'manage', False ):
            action = 'manage'
        elif params.get( 'new', False ):
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
            if params.get( 'rename_folder_button', False ):
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
                                                                          action='folder',
                                                                          folder_id=folder_id,
                                                                          rename=True,
                                                                          msg=util.sanitize_text( msg ),
                                                                          messagetype='done' ) )
                else:
                    msg = "You are not authorized to edit this folder"
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
                                                                  action='folder',
                                                                  folder_id=folder_id,
                                                                  manage=True,
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
    def library( self, trans, id=None, **kwd ):
        params = util.Params( kwd )
        msg = util.restore_text( params.get( 'msg', ''  ) )
        messagetype = params.get( 'messagetype', 'done' )
        if params.get( 'manage', False ):
            action = 'manage'
        elif params.get( 'rename', False ):
            action = 'rename'
        elif params.get( 'delete', False ):
            action = 'delete'
        elif params.get( 'update_roles', False ):
            action = 'update_roles'
        else:
            msg = 'Invalid action attempted on library'
            return trans.response.send_redirect( web.url_for( controller='library',
                                                              action='browse',
                                                              msg=util.sanitize_text( msg ),
                                                              messagetype='error' ) )
        if not id:
            msg = "You must specify a library to %s." % action
            return trans.response.send_redirect( web.url_for( controller='library',
                                                              action='browse',
                                                              msg=util.sanitize_text( msg ),
                                                              messagetype='error' ) )
        library = trans.app.model.Library.get( int( id ) )
        if action == 'rename':
            if params.get( 'rename_library_button', False ):
                old_name = library.name
                new_name = util.restore_text( params.name )
                new_description = util.restore_text( params.description )
                if not new_name:
                    msg = 'Enter a valid name'
                    return trans.fill_template( '/library/manage_library.mako', library=library, msg=msg, messagetype='error' )
                else:
                    if params.get( 'root_folder', False ):
                        root_folder = library.root_folder
                        root_folder.name = new_name
                        root_folder.flush()
                    library.name = new_name
                    library.description = new_description
                    library.flush()
                    msg = "Library '%s' has been renamed to '%s'" % ( old_name, new_name )
                    return trans.response.send_redirect( web.url_for( controller='library',
                                                                      action='library',
                                                                      id=id,
                                                                      rename=True,
                                                                      msg=util.sanitize_text( msg ),
                                                                      messagetype='done' ) )
        elif action == 'update_roles':
            permissions = {}
            for k, v in trans.app.model.Library.permitted_actions.items():
                in_roles = [ trans.app.model.Role.get( x ) for x in util.listify( kwd.get( k + '_in', [] ) ) ]
                permissions[ trans.app.security_agent.get_action( v.action ) ] = in_roles
            trans.app.security_agent.set_all_library_permissions( library, permissions )
            library.refresh()
            msg = "Permissions updated for library '%s'" % library.name
            return trans.response.send_redirect( web.url_for( controller='library',
                                                              action='browse',
                                                              msg=util.sanitize_text( msg ),
                                                              messagetype='done' ) )
        return trans.fill_template( '/library/manage_library.mako', library=library, msg=msg, messagetype=messagetype )
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
