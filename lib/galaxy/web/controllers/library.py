from galaxy.web.base.controller import *
from galaxy.model.orm import *
from galaxy.datatypes import sniff
from galaxy import util
from galaxy.util.streamball import StreamBall
import logging, tempfile, zipfile, tarfile, os, sys

if sys.version_info[:2] < ( 2, 6 ):
    zipfile.BadZipFile = zipfile.error
if sys.version_info[:2] < ( 2, 5 ):
    zipfile.LargeZipFile = zipfile.error

log = logging.getLogger( __name__ )

# Test for available compression types
tmpd = tempfile.mkdtemp()
comptypes = []
for comptype in ( 'gz', 'bz2' ):
    tmpf = os.path.join( tmpd, 'compression_test.tar.' + comptype )
    try:
        archive = tarfile.open( tmpf, 'w:' + comptype )
        archive.close()
        comptypes.append( comptype )
    except tarfile.CompressionError:
        log.exception( "Compression error when testing %s compression.  This option will be disabled for library downloads." % comptype )
    try:
        os.unlink( tmpf )
    except OSError:
        pass
ziptype = '32'
tmpf = os.path.join( tmpd, 'compression_test.zip' )
try:
    archive = zipfile.ZipFile( tmpf, 'w', zipfile.ZIP_DEFLATED, True )
    archive.close()
    comptypes.append( 'zip' )
    ziptype = '64'
except RuntimeError:
    log.exception( "Compression error when testing zip compression. This option will be disabled for library downloads." )
except (TypeError, zipfile.LargeZipFile):
    # ZIP64 is only in Python2.5+.  Remove TypeError when 2.4 support is dropped
    log.warning( 'Max zip file size is 2GB, ZIP64 not supported' )
    comptypes.append( 'zip' )
try:
    os.unlink( tmpf )
except OSError:
    pass
os.rmdir( tmpd )

class Library( BaseController ):
    @web.expose
    def index( self, trans, **kwd ):
        params = util.Params( kwd )
        msg = util.restore_text( params.get( 'msg', ''  ) )
        messagetype = params.get( 'messagetype', 'done' )
        return trans.fill_template( "/library/index.mako",
                                    default_action=params.get( 'default_action', None ),
                                    msg=msg,
                                    messagetype=messagetype )
    @web.expose
    def browse_libraries( self, trans, **kwd ):
        params = util.Params( kwd )
        msg = util.restore_text( params.get( 'msg', ''  ) )
        messagetype = params.get( 'messagetype', 'done' )
        all_libraries = trans.app.model.Library.filter( trans.app.model.Library.table.c.deleted==False ).order_by( trans.app.model.Library.name ).all()
        authorized_libraries = []
        for library in all_libraries:
            if trans.app.security_agent.allow_action( trans.user, trans.app.security_agent.permitted_actions.LIBRARY_ADD, library_item=library ) or \
               trans.app.security_agent.allow_action( trans.user, trans.app.security_agent.permitted_actions.LIBRARY_MODIFY, library_item=library ) or \
               trans.app.security_agent.allow_action( trans.user, trans.app.security_agent.permitted_actions.LIBRARY_MANAGE, library_item=library ) or \
               trans.app.security_agent.check_folder_contents( trans.user, library ) or \
               trans.app.security_agent.show_library_item( trans.user, library ):
                authorized_libraries.append( library )
        return trans.fill_template( '/library/browse_libraries.mako', 
                                    libraries=authorized_libraries,
                                    default_action=params.get( 'default_action', None ),
                                    msg=msg,
                                    messagetype=messagetype )
    @web.expose
    def browse_library( self, trans, **kwd ):
        params = util.Params( kwd )
        msg = util.restore_text( params.get( 'msg', ''  ) )
        messagetype = params.get( 'messagetype', 'done' )
        id = params.get( 'id', None )
        if not id:
            msg = "You must specify a library id."
            return trans.response.send_redirect( web.url_for( controller='library',
                                                              action='browse_libraries',
                                                              default_action=params.get( 'default_action', None ),
                                                              msg=util.sanitize_text( msg ),
                                                              messagetype='error' ) )
        library = library=trans.app.model.Library.get( id )
        if not library:
            msg = "Invalid library id ( %s )."
            return trans.response.send_redirect( web.url_for( controller='library',
                                                              action='browse_libraries',
                                                              default_action=params.get( 'default_action', None ),
                                                              msg=util.sanitize_text( msg ),
                                                              messagetype='error' ) )
        created_ldda_ids = params.get( 'created_ldda_ids', '' )
        return trans.fill_template( '/library/browse_library.mako', 
                                    library=trans.app.model.Library.get( id ),
                                    created_ldda_ids=created_ldda_ids,
                                    default_action=params.get( 'default_action', None ),
                                    comptypes=comptypes,
                                    msg=msg,
                                    messagetype=messagetype )
    @web.expose
    def library( self, trans, id=None, **kwd ):
        params = util.Params( kwd )
        msg = util.restore_text( params.get( 'msg', ''  ) )
        messagetype = params.get( 'messagetype', 'done' )
        # TODO: eventually we'll want the ability for users to create libraries
        if params.get( 'delete', False ):
            action = 'delete'
        elif params.get( 'permissions', False ):
            action = 'permissions'
        else:
            action = 'information'
        if not id:
            msg = "You must specify a library."
            return trans.response.send_redirect( web.url_for( controller='library',
                                                              action='browse_libraries',
                                                              msg=util.sanitize_text( msg ),
                                                              messagetype='error' ) )
        library = trans.app.model.Library.get( int( id ) )
        if not library:
            msg = "Invalid library id ( %s ) specified." % str( id )
            return trans.response.send_redirect( web.url_for( controller='library',
                                                              action='browse_libraries',
                                                              msg=util.sanitize_text( msg ),
                                                              messagetype='error' ) )
        if action == 'information':
            if params.get( 'rename_library_button', False ):
                old_name = library.name
                new_name = util.restore_text( params.name )
                new_description = util.restore_text( params.description )
                if not new_name:
                    msg = 'Enter a valid name'
                    return trans.fill_template( '/library/library_info.mako',
                                                library=library,
                                                restrict=params.get( 'restrict', False ),
                                                render_templates=params.get( 'render_templates', False ),
                                                msg=msg,
                                                messagetype='error' )
                else:
                    library.name = new_name
                    library.description = new_description
                    library.flush()
                    # Rename the root_folder
                    library.root_folder.name = new_name
                    library.root_folder.description = new_description
                    library.root_folder.flush()
                    msg = "Library '%s' has been renamed to '%s'" % ( old_name, new_name )
                    return trans.response.send_redirect( web.url_for( controller='library',
                                                                      action='library',
                                                                      id=id,
                                                                      edit_info=True,
                                                                      msg=util.sanitize_text( msg ),
                                                                      messagetype='done' ) )
            return trans.fill_template( '/library/library_info.mako',
                                        library=library,
                                        restrict=params.get( 'restrict', False ),
                                        render_templates=params.get( 'render_templates', False ),
                                        msg=msg,
                                        messagetype=messagetype )
        elif action == 'permissions':
            if params.get( 'update_roles_button', False ):
                # The user clicked the Save button on the 'Associate With Roles' form
                permissions = {}
                for k, v in trans.app.model.Library.permitted_actions.items():
                    in_roles = [ trans.app.model.Role.get( x ) for x in util.listify( params.get( k + '_in', [] ) ) ]
                    permissions[ trans.app.security_agent.get_action( v.action ) ] = in_roles
                trans.app.security_agent.set_all_library_permissions( library, permissions )
                library.refresh()
                # Copy the permissions to the root folder
                trans.app.security_agent.copy_library_permissions( library, library.root_folder )
                msg = "Permissions updated for library '%s'" % library.name
                return trans.response.send_redirect( web.url_for( controller='library',
                                                                  action='library',
                                                                  id=id,
                                                                  permissions=True,
                                                                  msg=util.sanitize_text( msg ),
                                                                  messagetype='done' ) )
            return trans.fill_template( '/library/library_permissions.mako',
                                        library=library,
                                        msg=msg,
                                        messagetype=messagetype )
    @web.expose
    def datasets( self, trans, library_id, ldda_ids='', **kwd ):
        # This method is used by the select list labeled "Perform action on selected datasets"
        # on the analysis library browser.
        if not ldda_ids:
            msg = "You must select at least one dataset"
            return trans.response.send_redirect( web.url_for( controller='library',
                                                              action='browse_library',
                                                              id=library_id,
                                                              msg=util.sanitize_text( msg ),
                                                              messagetype='error' ) )
        ldda_ids = util.listify( ldda_ids )
        params = util.Params( kwd )
        msg = util.restore_text( params.get( 'msg', ''  ) )
        messagetype = params.get( 'messagetype', 'done' )
        if not params.do_action:
            msg = "You must select an action to perform on selected datasets"
            return trans.response.send_redirect( web.url_for( controller='library',
                                                              action='browse_library',
                                                              id=library_id,
                                                              msg=util.sanitize_text( msg ),
                                                              messagetype='error' ) )
        if params.do_action == 'add':
            history = trans.get_history()
            for ldda_id in ldda_ids:
                ldda = trans.app.model.LibraryDatasetDatasetAssociation.get( ldda_id )
                hda = ldda.to_history_dataset_association( target_history=history, add_to_history = True )
            history.flush()
            msg = "%i dataset(s) have been imported into your history" % len( ldda_ids )
            return trans.response.send_redirect( web.url_for( controller='library',
                                                              action='browse_library',
                                                              id=library_id,
                                                              msg=util.sanitize_text( msg ),
                                                              messagetype='done' ) )
        elif params.do_action == 'manage_permissions':
            # We need the folder containing the LibraryDatasetDatasetAssociation(s)
            ldda = trans.app.model.LibraryDatasetDatasetAssociation.get( ldda_ids[0] )
            trans.response.send_redirect( web.url_for( controller='library',
                                                       action='library_dataset_dataset_association',
                                                       library_id=library_id,
                                                       folder_id=ldda.library_dataset.folder.id,
                                                       id=','.join( ldda_ids ),
                                                       permissions=True,
                                                       msg=util.sanitize_text( msg ),
                                                       messagetype=messagetype ) )
        else:
            try:
                if params.do_action == 'zip':
                    # Can't use mkstemp - the file must not exist first
                    tmpd = tempfile.mkdtemp()
                    tmpf = os.path.join( tmpd, 'library_download.' + params.do_action )
                    if ziptype == '64':
                        archive = zipfile.ZipFile( tmpf, 'w', zipfile.ZIP_DEFLATED, True )
                    else:
                        archive = zipfile.ZipFile( tmpf, 'w', zipfile.ZIP_DEFLATED )
                    archive.add = lambda x, y: archive.write( x, y.encode('CP437') )
                elif params.do_action == 'tgz':
                    archive = util.streamball.StreamBall( 'w|gz' )
                elif params.do_action == 'tbz':
                    archive = util.streamball.StreamBall( 'w|bz2' )
            except (OSError, zipfile.BadZipFile):
                log.exception( "Unable to create archive for download" )
                msg = "Unable to create archive for download, please report this error"
                return trans.response.send_redirect( web.url_for( controller='library',
                                                                  action='browse_library',
                                                                  id=library_id,
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
                    # Exclude the now-hidden "root folder"
                    if parent_folder.parent is None:
                        path = os.path.join( parent_folder.library_root[0].name, path )
                        break
                    path = os.path.join( parent_folder.name, path )
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
                                                                      action='browse_library',
                                                                      id=library_id,
                                                                      msg=util.sanitize_text( msg ),
                                                                      messagetype='error' ) )
            if params.do_action == 'zip':
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
                                                                      action='browse_library',
                                                                      id=library_id,
                                                                      msg=util.sanitize_text( msg ),
                                                                      messagetype='error' ) )
                trans.response.set_content_type( "application/x-zip-compressed" )
                trans.response.headers[ "Content-Disposition" ] = "attachment; filename=GalaxyLibraryFiles.%s" % params.do_action
                return tmpfh
            else:
                trans.response.set_content_type( "application/x-tar" )
                trans.response.headers[ "Content-Disposition" ] = "attachment; filename=GalaxyLibraryFiles.%s" % params.do_action
                archive.wsgi_status = trans.response.wsgi_status()
                archive.wsgi_headeritems = trans.response.wsgi_headeritems()
                return archive.stream
    @web.expose
    def download_dataset_from_folder(self, trans, id, library_id=None, **kwd):
        """Catches the dataset id and displays file contents as directed"""
        # id must refer to a LibraryDatasetDatasetAssociation object
        ldda = trans.app.model.LibraryDatasetDatasetAssociation.get( id )
        if not ldda.dataset:
            msg = 'Invalid LibraryDatasetDatasetAssociation id %s received for file downlaod' % str( id )
            return trans.response.send_redirect( web.url_for( controller='library',
                                                              action='browse_library',
                                                              id=library_id,
                                                              msg=msg,
                                                              messagetype='error' ) )
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
            return trans.response.send_redirect( web.url_for( controller='library',
                                                              action='browse_library',
                                                              id=library_id,
                                                              msg=msg,
                                                              messagetype='error' ) )
    @web.expose
    def library_dataset( self, trans, id, library_id, **kwd ):
        params = util.Params( kwd )
        msg = util.restore_text( params.get( 'msg', ''  ) )
        messagetype = params.get( 'messagetype', 'done' )
        if params.get( 'permissions', False ):
            action = 'permissions'
        else:
            action = 'information'
        library_dataset = trans.app.model.LibraryDataset.get( id )
        if not library_dataset:
            msg = "Invalid library dataset specified, id: %s" %str( id )
            return trans.response.send_redirect( web.url_for( controller='library',
                                                              action='browse_library',
                                                              id=library_id,
                                                              msg=util.sanitize_text( msg ),
                                                              messagetype='error' ) )
        if action == 'information':
            if params.get( 'edit_attributes_button', False ):
                if trans.app.security_agent.allow_action( trans.user,
                                                          trans.app.security_agent.permitted_actions.LIBRARY_MODIFY,
                                                          library_item=library_dataset ):
                    if params.get( 'edit_attributes_button', False ):
                        old_name = library_dataset.name
                        new_name = util.restore_text( params.get( 'name', '' ) )
                        new_info = util.restore_text( params.get( 'info', '' ) )
                        if not new_name:
                            msg = 'Enter a valid name'
                            messagetype = 'error'
                        else:
                            library_dataset.name = new_name
                            library_dataset.info = new_info
                            library_dataset.flush()
                            msg = "Dataset '%s' has been renamed to '%s'" % ( old_name, new_name )
                            messagetype = 'done'
                else:
                    msg = "You are not authorized to change the attributes of this dataset"
                    messagetype = "error"
            return trans.fill_template( '/library/library_dataset_info.mako',
                                        library_dataset=library_dataset,
                                        library_id=library_id,
                                        restrict=params.get( 'restrict', True ),
                                        render_templates=params.get( 'render_templates', False ),
                                        msg=msg,
                                        messagetype=messagetype )
        elif action == 'permissions':
            if params.get( 'update_roles_button', False ):
                if trans.app.security_agent.allow_action( trans.user,
                                                          trans.app.security_agent.permitted_actions.LIBRARY_MANAGE,
                                                          library_item=library_dataset ):
                    # The user clicked the Save button on the 'Associate With Roles' form
                    permissions = {}
                    for k, v in trans.app.model.Library.permitted_actions.items():
                        in_roles = [ trans.app.model.Role.get( x ) for x in util.listify( kwd.get( k + '_in', [] ) ) ]
                        permissions[ trans.app.security_agent.get_action( v.action ) ] = in_roles
                    # Set the LIBRARY permissions on the LibraryDataset
                    # NOTE: the LibraryDataset and LibraryDatasetDatasetAssociation will be set with the same permissions
                    trans.app.security_agent.set_all_library_permissions( library_dataset, permissions )
                    library_dataset.refresh()
                    # Set the LIBRARY permissions on the LibraryDatasetDatasetAssociation
                    trans.app.security_agent.set_all_library_permissions( library_dataset.library_dataset_dataset_association, permissions )
                    library_dataset.library_dataset_dataset_association.refresh()
                    msg = 'Permissions and roles have been updated for library dataset %s' % library_dataset.name
                    messagetype = 'done'
                else:
                    msg = "You are not authorized to managed the permissions of this dataset"
                    messagetype = "error"
                return trans.fill_template( '/library/library_dataset_permissions.mako',
                                            library_dataset=library_dataset,
                                            library_id=library_id,
                                            msg=msg,
                                            messagetype=messagetype )
    @web.expose
    def library_dataset_dataset_association( self, trans, library_id, folder_id, id=None, **kwd ):
        params = util.Params( kwd )
        msg = util.restore_text( params.get( 'msg', ''  ) )
        messagetype = params.get( 'messagetype', 'done' )
        dbkey = params.get( 'dbkey', None )
        if isinstance( dbkey, list ):
            last_used_build = dbkey[0]
        else:
            last_used_build = dbkey
        folder = trans.app.model.LibraryFolder.get( folder_id )
        if folder and last_used_build in [ 'None', None, '?' ]:
            last_used_build = folder.genome_build
        replace_id = params.get( 'replace_id', None )
        if replace_id:
            replace_dataset = trans.app.model.LibraryDataset.get( params.get( 'replace_id', None ) )
            if not last_used_build:
                last_used_build = replace_dataset.library_dataset_dataset_association.dbkey
        else:
            replace_dataset = None
        # Let's not overwrite the imported datatypes module with the variable datatypes?
        # The built-in 'id' is overwritten in lots of places as well
        ldatatypes = [ x for x in trans.app.datatypes_registry.datatypes_by_extension.iterkeys() ]
        ldatatypes.sort()
        if id:
            if params.get( 'permissions', False ):
                action = 'permissions'
            elif params.get( 'edit_info', False ):
                action = 'edit_info'
            else:
                action = 'info'
            if id.count( ',' ):
                ids = id.split( ',' )
                id = None
            else:
                ids = None
        else:
            ids = None
        if id:
            # ldda_id specified, display attributes form
            ldda = trans.app.model.LibraryDatasetDatasetAssociation.get( id )
            if not ldda:
                msg = "Invalid LibraryDatasetDatasetAssociation specified, id: %s" % str( id )
                return trans.response.send_redirect( web.url_for( controller='library',
                                                                  action='browse_library',
                                                                  id=library_id,
                                                                  msg=util.sanitize_text( msg ),
                                                                  messagetype='error' ) )
            if action == 'permissions':
                if params.get( 'update_roles_button', False ):
                    # The user clicked the Save button on the 'Associate With Roles' form
                    if trans.app.security_agent.allow_action( trans.user,
                                                              trans.app.security_agent.permitted_actions.LIBRARY_MANAGE,
                                                              library_item=ldda ) and \
                        trans.app.security_agent.allow_action( trans.user,
                                                               trans.app.security_agent.permitted_actions.DATASET_MANAGE_PERMISSIONS,
                                                               dataset=ldda.dataset ):
                        permissions = {}
                        for k, v in trans.app.model.Dataset.permitted_actions.items():
                            in_roles = [ trans.app.model.Role.get( x ) for x in util.listify( params.get( k + '_in', [] ) ) ]
                            permissions[ trans.app.security_agent.get_action( v.action ) ] = in_roles
                        # Set the DATASET permissions on the Dataset
                        trans.app.security_agent.set_all_dataset_permissions( ldda.dataset, permissions )
                        ldda.dataset.refresh()
                        permissions = {}
                        for k, v in trans.app.model.Library.permitted_actions.items():
                            in_roles = [ trans.app.model.Role.get( x ) for x in util.listify( kwd.get( k + '_in', [] ) ) ]
                            permissions[ trans.app.security_agent.get_action( v.action ) ] = in_roles
                        # Set the LIBRARY permissions on the LibraryDataset
                        # NOTE: the LibraryDataset and LibraryDatasetDatasetAssociation will be set with the same permissions
                        trans.app.security_agent.set_all_library_permissions( ldda.library_dataset, permissions )
                        ldda.library_dataset.refresh()
                        # Set the LIBRARY permissions on the LibraryDatasetDatasetAssociation
                        trans.app.security_agent.set_all_library_permissions( ldda, permissions )
                        ldda.refresh()
                        msg = "Permissions updated for dataset '%s'" % ldda.name
                        messagetype = 'done'
                    else:
                        msg = "You are not authorized to change the permissions of dataset '%s'" % ldda.name
                        messagetype = 'error'
                return trans.fill_template( '/library/ldda_permissions.mako',
                                            ldda=ldda,
                                            library_id=library_id,
                                            msg=msg,
                                            messagetype=messagetype )
            elif action == 'info':
                return trans.fill_template( '/library/ldda_info.mako',
                                            ldda=ldda,
                                            library_id=library_id,
                                            msg=msg,
                                            messagetype=messagetype )
            elif action == 'edit_info':
                if params.get( 'change', False ):
                    # The user clicked the Save button on the 'Change data type' form
                    if trans.app.security_agent.allow_action( trans.user,
                                                              trans.app.security_agent.permitted_actions.LIBRARY_MODIFY,
                                                              library_item=ldda ):
                        trans.app.datatypes_registry.change_datatype( ldda, params.datatype )
                        trans.app.model.flush()
                        msg = "Data type changed for library dataset '%s'" % ldda.name
                        messagetype = 'done'
                    else:
                        msg = "You are not authorized to change the data type of dataset '%s'" % ldda.name
                        messagetype = 'error'
                    return trans.fill_template( "/library/ldda_edit_info.mako", 
                                                ldda=ldda,
                                                library_id=library_id,
                                                datatypes=ldatatypes,
                                                restrict=params.get( 'restrict', True ),
                                                render_templates=params.get( 'render_templates', False ),
                                                msg=msg,
                                                messagetype=messagetype )
                elif params.get( 'save', False ):
                    # The user clicked the Save button on the 'Edit Attributes' form
                    if trans.app.security_agent.allow_action( trans.user,
                                                              trans.app.security_agent.permitted_actions.LIBRARY_MODIFY,
                                                              library_item=ldda ):
                        old_name = ldda.name
                        new_name = util.restore_text( params.get( 'name', '' ) )
                        new_info = util.restore_text( params.get( 'info', '' ) )
                        new_message = util.restore_text( params.get( 'message', '' ) )
                        if not new_name:
                            msg = 'Enter a valid name'
                            messagetype = 'error'
                        else:
                            ldda.name = new_name
                            ldda.info = new_info
                            ldda.message = new_message
                            # The following for loop will save all metadata_spec items
                            for name, spec in ldda.datatype.metadata_spec.items():
                                if spec.get("readonly"):
                                    continue
                                optional = params.get( "is_" + name, None )
                                if optional and optional == 'true':
                                    # optional element... == 'true' actually means it is NOT checked (and therefore ommitted)
                                    setattr( ldda.metadata, name, None )
                                else:
                                    setattr( ldda.metadata, name, spec.unwrap( params.get ( name, None ) ) )
                            ldda.metadata.dbkey = dbkey
                            ldda.datatype.after_edit( ldda )
                            trans.app.model.flush()
                            msg = 'Attributes updated for library dataset %s' % ldda.name
                            messagetype = 'done'
                    else:
                        msg = "you are not authorized to edit the attributes of dataset '%s'" % ldda.name
                        messagetype = 'error'
                    return trans.fill_template( "/library/ldda_edit_info.mako", 
                                                ldda=ldda,
                                                library_id=library_id,
                                                datatypes=ldatatypes,
                                                restrict=params.get( 'restrict', True ),
                                                render_templates=params.get( 'render_templates', False ),
                                                msg=msg,
                                                messagetype=messagetype )
                elif params.get( 'detect', False ):
                    # The user clicked the Auto-detect button on the 'Edit Attributes' form
                    if trans.app.security_agent.allow_action( trans.user,
                                                              trans.app.security_agent.permitted_actions.LIBRARY_MODIFY,
                                                              library_item=ldda ):
                        for name, spec in ldda.datatype.metadata_spec.items():
                            # We need to be careful about the attributes we are resetting
                            if name not in [ 'name', 'info', 'dbkey' ]:
                                if spec.get( 'default' ):
                                    setattr( ldda.metadata, name, spec.unwrap( spec.get( 'default' ) ) )
                        ldda.datatype.set_meta( ldda )
                        ldda.datatype.after_edit( ldda )
                        trans.app.model.flush()
                        msg = 'Attributes updated for library dataset %s' % ldda.name
                        messagetype = 'done'
                    else:
                        msg = "you are not authorized to edit the attributes of dataset '%s'" % ldda.name
                        messagetype = 'error'
                    return trans.fill_template( "/library/ldda_edit_info.mako", 
                                                ldda=ldda,
                                                library_id=library_id,
                                                datatypes=ldatatypes,
                                                restrict=params.get( 'restrict', True ),
                                                render_templates=params.get( 'render_templates', False ),
                                                msg=msg,
                                                messagetype=messagetype )
                elif params.get( 'delete', False ):
                    if trans.app.security_agent.allow_action( trans.user,
                                                              trans.app.security_agent.permitted_actions.LIBRARY_MODIFY,
                                                              library_item=folder ):
                        ldda.deleted = True
                        ldda.flush()
                        msg = 'Dataset %s has been removed from this library' % ldda.name
                        messagetype = 'done'
                    else:
                        msg = "you are not authorized to delete dataset '%s'" % ldda.name
                        messagetype = 'error'
                    return trans.fill_template( "/library/ldda_edit_info.mako", 
                                                ldda=ldda,
                                                library_id=library_id,
                                                datatypes=ldatatypes,
                                                restrict=params.get( 'restrict', True ),
                                                render_templates=params.get( 'render_templates', False ),
                                                msg=msg,
                                                messagetype=messagetype )
                if trans.app.security_agent.allow_action( trans.user,
                                                          trans.app.security_agent.permitted_actions.LIBRARY_MODIFY,
                                                          library_item=ldda ):
                    ldda.datatype.before_edit( ldda )
                    if "dbkey" in ldda.datatype.metadata_spec and not ldda.metadata.dbkey:
                        # Copy dbkey into metadata, for backwards compatability
                        # This looks like it does nothing, but getting the dbkey
                        # returns the metadata dbkey unless it is None, in which
                        # case it resorts to the old dbkey.  Setting the dbkey
                        # sets it properly in the metadata
                        ldda.metadata.dbkey = ldda.dbkey
                return trans.fill_template( "/library/ldda_edit_info.mako", 
                                            ldda=ldda,
                                            library_id=library_id,
                                            datatypes=ldatatypes,
                                            restrict=params.get( 'restrict', True ),
                                            render_templates=params.get( 'render_templates', False ),
                                            msg=msg,
                                            messagetype=messagetype )
        elif ids:
            # Multiple ids specfied, display permission form, permissions will be updated for all simultaneously.
            lddas = []
            for id in [ int( id ) for id in ids ]:
                ldda = trans.app.model.LibraryDatasetDatasetAssociation.get( id )
                if ldda is None:
                    msg = 'You specified an invalid LibraryDatasetDatasetAssociation id: %s' %str( id )
                    trans.response.send_redirect( web.url_for( controller='library',
                                                               action='browse_library',
                                                               id=library_id,
                                                               msg=util.sanitize_text( msg ),
                                                               messagetype='error' ) )
                lddas.append( ldda )
            if len( lddas ) < 2:
                msg = 'You must specify at least two datasets on which to modify permissions, ids you sent: %s' % str( ids )
                trans.response.send_redirect( web.url_for( controller='library',
                                                           action='browse_library',
                                                           id=library_id,
                                                           msg=util.sanitize_text( msg ),
                                                           messagetype='error' ) )
            if action == 'permissions':
                if params.get( 'update_roles_button', False ):
                    if trans.app.security_agent.allow_action( trans.user,
                                                              trans.app.security_agent.permitted_actions.LIBRARY_MANAGE,
                                                              library_item=ldda ) and \
                        trans.app.security_agent.allow_action( trans.user,
                                                               trans.app.security_agent.permitted_actions.DATASET_MANAGE_PERMISSIONS,
                                                               dataset=ldda.dataset ):
                        permissions = {}
                        for k, v in trans.app.model.Dataset.permitted_actions.items():
                            in_roles = [ trans.app.model.Role.get( x ) for x in util.listify( params.get( k + '_in', [] ) ) ]
                            permissions[ trans.app.security_agent.get_action( v.action ) ] = in_roles
                        for ldda in lddas:
                            # Set the DATASET permissions on the Dataset
                            trans.app.security_agent.set_all_dataset_permissions( ldda.dataset, permissions )
                            ldda.dataset.refresh()
                        permissions = {}
                        for k, v in trans.app.model.Library.permitted_actions.items():
                            in_roles = [ trans.app.model.Role.get( x ) for x in util.listify( kwd.get( k + '_in', [] ) ) ]
                            permissions[ trans.app.security_agent.get_action( v.action ) ] = in_roles
                        for ldda in lddas:
                            # Set the LIBRARY permissions on the LibraryDataset
                            # NOTE: the LibraryDataset and LibraryDatasetDatasetAssociation will be set with the same permissions
                            trans.app.security_agent.set_all_library_permissions( ldda.library_dataset, permissions )
                            ldda.library_dataset.refresh()
                            # Set the LIBRARY permissions on the LibraryDatasetDatasetAssociation
                            trans.app.security_agent.set_all_library_permissions( ldda, permissions )
                            ldda.refresh()
                        msg = 'Permissions and roles have been updated on %d datasets' % len( lddas )
                        messagetype = 'done'
                    else:
                        msg = "You are not authorized to change the permissions of dataset '%s'" % ldda.name
                        messagetype = 'error'
                    return trans.fill_template( "/library/ldda_permissions.mako",
                                                ldda=lddas,
                                                library_id=library_id,
                                                msg=msg,
                                                messagetype=messagetype )
                if trans.app.security_agent.allow_action( trans.user,
                                                          trans.app.security_agent.permitted_actions.LIBRARY_MANAGE,
                                                          library_item=ldda ) and \
                    trans.app.security_agent.allow_action( trans.user,
                                                           trans.app.security_agent.permitted_actions.DATASET_MANAGE_PERMISSIONS,
                                                           dataset=ldda.dataset ):
                    # Ensure that the permissions across all library items are identical, otherwise we can't update them together.
                    check_list = []
                    for ldda in lddas:
                        permissions = []
                        # Check the library level permissions - the permissions on the LibraryDatasetDatasetAssociation
                        # will always be the same as the permissions on the associated LibraryDataset, so we only need to
                        # check one Library object
                        for library_permission in trans.app.security_agent.get_library_dataset_permissions( ldda.library_dataset ):
                            if library_permission.action not in permissions:
                                permissions.append( library_permission.action )
                        for dataset_permission in trans.app.security_agent.get_dataset_permissions( ldda.dataset ):
                            if dataset_permission.action not in permissions:
                                permissions.append( dataset_permission.action )
                        permissions.sort()
                        if not check_list:
                            check_list = permissions
                        if permissions != check_list:
                            msg = 'The datasets you selected do not have identical permissions, so they can not be updated together'
                            trans.response.send_redirect( web.url_for( controller='library',
                                                                       action='browse_library',
                                                                       id=library_id,
                                                                       msg=util.sanitize_text( msg ),
                                                                       messagetype='error' ) )
                else:
                    msg = "You are not authorized to change the permissions of dataset '%s'" % ldda.name
                    messagetype = 'error'
                return trans.fill_template( "/library/ldda_permissions.mako",
                                            ldda=lddas,
                                            library_id=library_id,
                                            msg=msg,
                                            messagetype=messagetype )
        if trans.app.security_agent.allow_action( trans.user,
                                                  trans.app.security_agent.permitted_actions.LIBRARY_ADD,
                                                  library_item=folder ) or \
             ( replace_dataset and trans.app.security_agent.allow_action( trans.user,
                                                                          trans.app.security_agent.permitted_actions.LIBRARY_MODIFY,
                                                                          library_item=replace_dataset ) ):
            if params.get( 'new_dataset_button', False ):
                upload_option = params.get( 'upload_option', 'upload_file' )
                created_ldda_ids = trans.webapp.controllers[ 'library_dataset' ].upload_dataset( trans,
                                                                                                 controller='library', 
                                                                                                 library_id=library_id,
                                                                                                 folder_id=folder_id,
                                                                                                 replace_dataset=replace_dataset, 
                                                                                                 **kwd )
                if created_ldda_ids:
                    ldda_id_list = created_ldda_ids.split( ',' )
                    total_added = len( ldda_id_list )
                    if replace_dataset:
                        msg = "Added %d dataset versions to the library dataset '%s' in the folder '%s'." % ( total_added, replace_dataset.name, folder.name )
                    else:
                        if not folder.parent:
                            # Libraries have the same name as their root_folder
                            msg = "Added %d datasets to the library '%s' ( each is selected ).  " % ( total_added, folder.name )
                        else:
                            msg = "Added %d datasets to the folder '%s' ( each is selected ).  " % ( total_added, folder.name )
                    # Since permissions on all LibraryDatasetDatasetAssociations must be the same at this point, we only need
                    # to check one of them to see if the current user can manage permissions on them.
                    check_ldda = trans.app.model.LibraryDatasetDatasetAssociation.get( ldda_id_list[0] )
                    if trans.app.security_agent.allow_action( trans.user,
                                                              trans.app.security_agent.permitted_actions.LIBRARY_MANAGE,
                                                              library_item=check_ldda ):
                        if replace_dataset:
                            default_action = ''
                        else:
                            msg += "Click the Go button at the bottom of this page to edit the permissions on these datasets if necessary."
                            default_action = 'manage_permissions'
                    else:
                        default_action = 'add'
                    trans.response.send_redirect( web.url_for( controller='library',
                                                               action='browse_library',
                                                               id=library_id,
                                                               default_action=default_action,
                                                               created_ldda_ids=created_ldda_ids, 
                                                               msg=util.sanitize_text( msg ), 
                                                               messagetype='done' ) )
                    
                else:
                    msg = "Upload failed"
                    trans.response.send_redirect( web.url_for( controller='library',
                                                               action='browse_library',
                                                               id=library_id,
                                                               created_ldda_ids=created_ldda_ids, 
                                                               msg=util.sanitize_text( msg ), 
                                                               messagetype='error' ) )
        if not id or replace_dataset:
            upload_option = params.get( 'upload_option', 'upload_file' )
            # No dataset(s) specified, so display the upload form.  Send list of data formats to the form
            # so the "extension" select list can be populated dynamically
            file_formats = trans.app.datatypes_registry.upload_file_formats
            # Send list of genome builds to the form so the "dbkey" select list can be populated dynamically
            def get_dbkey_options( last_used_build ):
                for dbkey, build_name in util.dbnames:
                    yield build_name, dbkey, ( dbkey==last_used_build )
            dbkeys = get_dbkey_options( last_used_build )
            # Send list of roles to the form so the dataset can be associated with 1 or more of them.
            roles = trans.app.model.Role.filter( trans.app.model.Role.table.c.deleted==False ).order_by( trans.app.model.Role.c.name ).all()
            # Send the current history to the form to enable importing datasets from history to library
            history = trans.get_history()
            history.refresh()
            return trans.fill_template( '/library/new_dataset.mako',
                                        upload_option=upload_option,
                                        library_id=library_id,
                                        folder_id=folder_id,
                                        replace_id=replace_id,
                                        file_formats=file_formats,
                                        dbkeys=dbkeys,
                                        last_used_build=last_used_build,
                                        roles=roles,
                                        history=history,
                                        msg=msg,
                                        messagetype=messagetype,
                                        replace_dataset=replace_dataset )
    @web.expose
    def add_history_datasets_to_library( self, trans, library_id, folder_id, hda_ids='', **kwd ):
        params = util.Params( kwd )
        msg = util.restore_text( params.get( 'msg', ''  ) )
        messagetype = params.get( 'messagetype', 'done' )
        try:
            folder = trans.app.model.LibraryFolder.get( int( folder_id ) )
        except:
            msg = "Invalid folder id: %s" % str( folder_id )
            return trans.response.send_redirect( web.url_for( controller='library',
                                                              action='browse_library',
                                                              id=library_id,
                                                              msg=util.sanitize_text( msg ),
                                                              messagetype='error' ) )
        replace_id = params.get( 'replace_id', None )
        if replace_id:
            replace_dataset = trans.app.model.LibraryDataset.get( replace_id )
        else:
            replace_dataset = None
        # See if the current history is empty
        history = trans.get_history()
        history.refresh()
        if not history.active_datasets:
            msg = 'Your current history is empty'
            return trans.response.send_redirect( web.url_for( controller='library',
                                                              action='browse_library',
                                                              id=library_id,
                                                              msg=util.sanitize_text( msg ),
                                                              messagetype='error' ) )
        if params.get( 'add_history_datasets_to_library_button', False ):
            hda_ids = util.listify( hda_ids )
            if hda_ids:
                dataset_names = []
                created_ldda_ids = ''
                for hda_id in hda_ids:
                    hda = trans.app.model.HistoryDatasetAssociation.get( hda_id )
                    if hda:
                        ldda = hda.to_library_dataset_dataset_association( target_folder=folder, replace_dataset=replace_dataset )
                        created_ldda_ids = '%s,%s' % ( created_ldda_ids, str( ldda.id ) )
                        dataset_names.append( ldda.name )
                        if not replace_dataset:
                            # If replace_dataset is None, the Library level permissions will be taken from the folder and applied to the new 
                            # LDDA and LibraryDataset.
                            trans.app.security_agent.copy_library_permissions( folder, ldda )
                            trans.app.security_agent.copy_library_permissions( folder, ldda.library_dataset )
                        # Permissions must be the same on the LibraryDatasetDatasetAssociation and the associated LibraryDataset
                        trans.app.security_agent.copy_library_permissions( ldda.library_dataset, ldda )
                    else:
                        msg = "The requested HistoryDatasetAssociation id %s is invalid" % str( hda_id )
                        return trans.response.send_redirect( web.url_for( controller='library',
                                                                          action='browse_library',
                                                                          id=library_id,
                                                                          msg=util.sanitize_text( msg ), 
                                                                          messagetype='error' ) )
                if created_ldda_ids:
                    created_ldda_ids = created_ldda_ids.lstrip( ',' )
                    ldda_id_list = created_ldda_ids.split( ',' )
                    total_added = len( ldda_id_list )
                    if replace_dataset:
                        msg = "Added %d dataset versions to the library dataset '%s' in the folder '%s'." % ( total_added, replace_dataset.name, folder.name )
                    else:
                        if not folder.parent:
                            # Libraries have the same name as their root_folder
                            msg = "Added %d datasets to the library '%s' ( each is selected ).  " % ( total_added, folder.name )
                        else:
                            msg = "Added %d datasets to the folder '%s' ( each is selected ).  " % ( total_added, folder.name )
                    # Since permissions on all LibraryDatasetDatasetAssociations must be the same at this point, we only need
                    # to check one of them to see if the current user can manage permissions on them.
                    check_ldda = trans.app.model.LibraryDatasetDatasetAssociation.get( ldda_id_list[0] )
                    if trans.app.security_agent.allow_action( trans.user,
                                                              trans.app.security_agent.permitted_actions.LIBRARY_MANAGE,
                                                              library_item=check_ldda ):
                        if replace_dataset:
                            default_action = ''
                        else:
                            msg += "Click the Go button at the bottom of this page to edit the permissions on these datasets if necessary."
                            default_action = 'manage_permissions'
                    else:
                        default_action = 'add'
                    return trans.response.send_redirect( web.url_for( controller='library',
                                                                      action='browse_library',
                                                                      id=library_id,
                                                                      created_ldda_ids=created_ldda_ids.lstrip( ',' ),
                                                                      default_action=default_action,
                                                                      msg=util.sanitize_text( msg ),
                                                                      messagetype='done' ) )
            else:
                msg = 'Select at least one dataset from the list of active datasets in your current history'
                messagetype = 'error'
                last_used_build = folder.genome_build
                upload_option = params.get( 'upload_option', 'import_from_history' )
                # Send list of data formats to the form so the "extension" select list can be populated dynamically
                file_formats = trans.app.datatypes_registry.upload_file_formats
                # Send list of genome builds to the form so the "dbkey" select list can be populated dynamically
                def get_dbkey_options( last_used_build ):
                    for dbkey, build_name in util.dbnames:
                        yield build_name, dbkey, ( dbkey==last_used_build )
                dbkeys = get_dbkey_options( last_used_build )
                # Send list of roles to the form so the dataset can be associated with 1 or more of them.
                roles = trans.app.model.Role.filter( trans.app.model.Role.table.c.deleted==False ).order_by( trans.app.model.Role.c.name ).all()
                return trans.fill_template( "/library/new_dataset.mako",
                                            upload_option=upload_option,
                                            library_id=library_id,
                                            folder_id=folder_id,
                                            replace_id=replace_id,
                                            file_formats=file_formats,
                                            dbkeys=dbkeys,
                                            last_used_build=last_used_build,
                                            roles=roles,
                                            history=history,
                                            msg=msg,
                                            messagetype=messagetype )
    @web.expose
    def folder( self, trans, id, library_id, **kwd ):
        params = util.Params( kwd )
        msg = util.restore_text( params.get( 'msg', ''  ) )
        messagetype = params.get( 'messagetype', 'done' )
        if params.get( 'new', False ):
            action = 'new'
        elif params.get( 'delete', False ):
            action = 'delete'
        elif params.get( 'permissions', False ):
            action = 'permissions'
        else:
            # 'information' will be the default
            action = 'information'
        folder = trans.app.model.LibraryFolder.get( int( id ) )
        if not folder:
            msg = "Invalid folder specified, id: %s" % str( id )
            return trans.response.send_redirect( web.url_for( controller='library',
                                                              action='browse_library',
                                                              id=library_id,
                                                              msg=util.sanitize_text( msg ),
                                                              messagetype='error' ) )
        if action == 'new':
            if params.new == 'submitted':
                new_folder = trans.app.model.LibraryFolder( name=util.restore_text( params.name ),
                                                            description=util.restore_text( params.description ) )
                # We are associating the last used genome build with folders, so we will always
                # initialize a new folder with the first dbkey in util.dbnames which is currently
                # ?    unspecified (?)
                new_folder.genome_build = util.dbnames.default_value
                folder.add_folder( new_folder )
                new_folder.flush()
                # New folders default to having the same permissions as their parent folder
                trans.app.security_agent.copy_library_permissions( folder, new_folder )
                msg = "New folder named '%s' has been added to the library" % new_folder.name
                return trans.response.send_redirect( web.url_for( controller='library',
                                                                  action='browse_library',
                                                                  id=library_id,
                                                                  msg=util.sanitize_text( msg ),
                                                                  messagetype='done' ) )
            return trans.fill_template( '/library/new_folder.mako',
                                        library_id=library_id,
                                        folder=folder,
                                        msg=msg,
                                        messagetype=messagetype )
        elif action == 'information':
            if params.get( 'rename_folder_button', False ):
                if trans.app.security_agent.allow_action( trans.user, 
                                                          trans.app.security_agent.permitted_actions.LIBRARY_MODIFY, 
                                                          library_item=folder ):
                    old_name = folder.name
                    new_name = util.restore_text( params.name )
                    new_description = util.restore_text( params.description )
                    if not new_name:
                        msg = 'Enter a valid name'
                        return trans.fill_template( "/library/folder_info.mako",
                                                    folder=folder,
                                                    library_id=library_id,
                                                    restrict=params.get( 'restrict', True ),
                                                    render_templates=params.get( 'render_templates', False ),
                                                    msg=msg,
                                                    messagetype='error' )
                    else:
                        folder.name = new_name
                        folder.description = new_description
                        folder.flush()
                        msg = "Folder '%s' has been renamed to '%s'" % ( old_name, new_name )
                        return trans.response.send_redirect( web.url_for( controller='library',
                                                                          action='folder',
                                                                          id=id,
                                                                          library_id=library_id,
                                                                          rename=True,
                                                                          msg=util.sanitize_text( msg ),
                                                                          messagetype='done' ) )
                else:
                    msg = "You are not authorized to edit this folder"
                    return trans.fill_template( "/library/folder_info.mako",
                                                folder=folder,
                                                library_id=library_id,
                                                restrict=params.get( 'restrict', True ),
                                                render_templates=params.get( 'render_templates', False ),
                                                msg=msg,
                                                messagetype='error' )
            return trans.fill_template( '/library/folder_info.mako',
                                        folder=folder,
                                        library_id=library_id,
                                        restrict=params.get( 'restrict', True ),
                                        render_templates=params.get( 'render_templates', False ),
                                        msg=msg,
                                        messagetype=messagetype )
        elif action == 'permissions':
            if params.get( 'update_roles_button', False ):
                # The user clicked the Save button on the 'Associate With Roles' form
                if trans.app.security_agent.allow_action( trans.user, 
                                                          trans.app.security_agent.permitted_actions.LIBRARY_MANAGE, 
                                                          library_item=folder ):
                    permissions = {}
                    for k, v in trans.app.model.Library.permitted_actions.items():
                        in_roles = [ trans.app.model.Role.get( int( x ) ) for x in util.listify( params.get( k + '_in', [] ) ) ]
                        permissions[ trans.app.security_agent.get_action( v.action ) ] = in_roles
                    trans.app.security_agent.set_all_library_permissions( folder, permissions )
                    folder.refresh()
                    msg = 'Permissions updated for folder %s' % folder.name
                    return trans.response.send_redirect( web.url_for( controller='library',
                                                                      action='folder',
                                                                      id=id,
                                                                      library_id=library_id,
                                                                      permissions=True,
                                                                      msg=util.sanitize_text( msg ),
                                                                      messagetype='done' ) )
                else:
                    msg = "You are not authorized to manage permissions on this folder"
                    return trans.response.send_redirect( web.url_for( controller='library',
                                                                      action='folder',
                                                                      id=id,
                                                                      library_id=library_id,
                                                                      permissions=True,
                                                                      msg=util.sanitize_text( msg ),
                                                                      messagetype='error' ) )
            return trans.fill_template( '/library/folder_permissions.mako',
                                        folder=folder,
                                        library_id=library_id,
                                        msg=msg,
                                        messagetype=messagetype )
    @web.expose
    def info_template( self, trans, library_id, id=None, num_fields=0, folder_id=None, ldda_id=None, library_dataset_id=None, **kwd ):
        params = util.Params( kwd )
        msg = util.restore_text( params.get( 'msg', ''  ) )
        messagetype = params.get( 'messagetype', 'done' )
        if not num_fields:
            num_fields = 0
        else:
            num_fields = int( num_fields )
        if params.get( 'new_template', False ):
            action = 'new_template'
        elif params.get( 'permissions', False ):
            action = 'permissions'
        else:
            action = 'edit_template'
        if id:
            library_item = trans.app.model.LibraryItemInfoTemplate.get( int( id ) )
            library_item_desc = 'information template'
            response_action = 'info_template'
            response_id = id
        elif folder_id:
            library_item = trans.app.model.LibraryFolder.get( int( folder_id ) )
            library_item_desc = 'folder'
            response_action = 'folder'
            response_id = folder_id
        elif ldda_id:
            library_item = trans.app.model.LibraryDatasetDatasetAssociation.get( int( ldda_id ) )
            library_item_desc = 'library dataset'
            response_action = 'library_dataset_dataset_association'
            response_id = ldda_id
        elif library_dataset_id:
            library_item = trans.app.model.LibraryDataset.get( int( library_dataset_id ) )
            library_item_desc = 'dataset'
            response_action = 'library_dataset_dataset_association'
            response_id = library_item.library_dataset_dataset_association.id
        else:
            library_item = trans.app.model.Library.get( int( library_id ) )
            library_item_desc = 'library'
            response_action = 'browse_library'
            response_id = library_id
        if action == 'new_template':
            if params.get( 'create_info_template_button', False ):
                return trans.fill_template( '/library/new_info_template.mako',
                                            library_item=library_item,
                                            library_item_name=library_item.name,
                                            library_item_desc=library_item_desc,
                                            num_fields=num_fields,
                                            library_id=library_id,
                                            folder_id=folder_id,
                                            ldda_id=ldda_id,
                                            library_dataset_id=library_dataset_id,
                                            msg=msg,
                                            messagetype=messagetype )
            elif params.get( 'new_info_template_button', False ):
                # Make sure at least 1 template field is filled in
                # TODO: Eventually we'll enhance templates to allow for required and optional fields.
                proceed = False
                for i in range( int( params.get( 'set_num_fields', 0 ) ) ):
                    elem_name = params.get( 'new_element_name_%i' % i, None )
                    elem_description = params.get( 'new_element_description_%i' % i, None )
                    if elem_name or elem_description:
                        proceed = True
                        break
                if not proceed:
                    msg = "At least 1 of the fields must be completed."
                    return trans.fill_template( '/library/new_info_template.mako',
                                                library_item=library_item,
                                                library_item_name=library_item.name,
                                                library_item_desc=library_item_desc,
                                                num_fields=num_fields,
                                                library_id=library_id,
                                                folder_id=folder_id,
                                                ldda_id=ldda_id,
                                                library_dataset_id=library_dataset_id,
                                                msg=msg,
                                                messagetype=messagetype )
                # Create template
                liit = trans.app.model.LibraryItemInfoTemplate()
                liit.name = util.restore_text( params.get( 'name', '' ) )
                liit.description = util.restore_text( params.get( 'description', '' ) )
                liit.flush()
                # Inherit the template's permissions from the library_item
                trans.app.security_agent.copy_library_permissions( liit, library_item )
                # Create template association
                if folder_id:
                    liit_assoc = trans.app.model.LibraryFolderInfoTemplateAssociation()
                    liit_assoc.folder = trans.app.model.LibraryFolder.get( folder_id )
                elif ldda_id:
                    liit_assoc = trans.app.model.LibraryDatasetDatasetInfoTemplateAssociation()
                    ldda = trans.app.model.LibraryDatasetDatasetAssociation.get( ldda_id )
                    liit_assoc.library_dataset_dataset_association = ldda
                    # This response_action method requires a folder_id
                    folder_id = ldda.library_dataset.folder.id
                elif library_dataset_id:
                    liit_assoc = trans.app.model.LibraryDatasetInfoTemplateAssociation()
                    library_dataset = trans.app.model.LibraryDataset.get( library_dataset_id )
                    liit_assoc.library_dataset = library_dataset
                    # This response_action method requires a folder_id
                    folder_id = library_dataset.folder.id
                else:
                    # We'll always be sent a library_id
                    liit_assoc = trans.app.model.LibraryInfoTemplateAssociation()
                    liit_assoc.library = trans.app.model.Library.get( library_id )
                liit_assoc.library_item_info_template = liit
                liit_assoc.flush()
                # Create and add elements
                for i in range( int( params.get( 'set_num_fields', 0 ) ) ):
                    elem_name = params.get( 'new_element_name_%i' % i, None )
                    elem_description = params.get( 'new_element_description_%i' % i, None )
                    if elem_description and not elem_name:
                        # If we have a description but no name, the description will be both
                        # ( a name cannot be empty, but a description can )
                        elem_name = elem_description
                    if elem_name:
                        # Skip any elements that have a missing name
                        liit.add_element( name=elem_name, description=elem_description )
                msg = "The new information template has been created."
                return trans.response.send_redirect( web.url_for( controller='library',
                                                                  action=response_action,
                                                                  id=response_id,
                                                                  library_id=library_id,
                                                                  folder_id=folder_id,
                                                                  msg=util.sanitize_text( msg ),
                                                                  messagetype='done' ) )
            return trans.fill_template( '/library/create_info_template.mako',
                                        library_item=library_item,
                                        library_id=library_id,
                                        msg=msg,
                                        messagetype=messagetype )
        elif action == 'edit_template':
            if params.get( 'edit_info_template_button', False ):
                # Save changes to existing attributes, only set name if nonempty/nonNone is passed, but always set description
                name = params.get( 'name', None )
                if name:
                    library_item.name = name
                library_item.description = params.get( 'description', '' )
                library_item.flush()
                # Save changes to exisiting elements
                for elem_id in params.get( 'element_ids', [] ):
                    liit_element = trans.app.model.LibraryItemInfoTemplateElement.get( elem_id )
                    name = params.get( 'element_name_%s' % elem_id, None )
                    if name:
                        liit_element.name = name
                    liit_element.description = params.get( 'element_description_%s' % elem_id, None )
                    liit_element.flush()
                # Add new elements
                for i in range( int( params.get( 'set_num_fields', 0 ) ) ):
                    elem_name = params.get( 'new_element_name_%i' % i, None )
                    elem_description = params.get( 'new_element_description_%i' % i, None )
                    # Skip any elements that have a missing name and description
                    if not elem_name:
                         # If we have a description but no name, the description will be both
                         # ( a name cannot be empty, but a description can )
                        elem_name = elem_description
                    if elem_name:
                        library_item.add_element( name=elem_name, description=elem_description )
                library_item.refresh()
                msg = 'Information template %s has been updated' % library_item.name
            return trans.fill_template( "/library/edit_info_template.mako",
                                        liit=library_item,
                                        num_fields=num_fields,
                                        library_id=library_id,
                                        library_dataset_id=library_dataset_id,
                                        ldda_id=ldda_id,
                                        folder_id=folder_id,
                                        library_item_name=library_item.name,
                                        library_item_desc=library_item_desc,
                                        msg=msg,
                                        messagetype=messagetype )
        elif action == 'permissions':
            if params.get( 'update_roles_button', False ):
                # The user clicked the Save button on the 'Associate With Roles' form
                permissions = {}
                for k, v in trans.app.model.Library.permitted_actions.items():
                    in_roles = [ trans.app.model.Role.get( x ) for x in util.listify( kwd.get( k + '_in', [] ) ) ]
                    permissions[ trans.app.security_agent.get_action( v.action ) ] = in_roles
                trans.app.security_agent.set_all_library_permissions( library_item, permissions )
                library_item.refresh()
                msg = "Permissions updated for information template '%s'" % library_item.name
                return trans.response.send_redirect( web.url_for( controller='library',
                                                                  action='info_template',
                                                                  library_id=library_id,
                                                                  id=id,
                                                                  permissions=True,
                                                                  msg=util.sanitize_text( msg ),
                                                                  messagetype='done' ) )
            return trans.fill_template( '/library/info_template_permissions.mako',
                                        liit=library_item,
                                        library_id=library_id,
                                        msg=msg,
                                        messagetype=messagetype )
    @web.expose
    def library_item_info( self, trans, library_id, id=None, library_item_id=None, library_item_type=None, **kwd ):
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
            return trans.response.send_redirect( web.url_for( controller='library',
                                                              action='browse_library',
                                                              id=library_id,
                                                              msg=util.sanitize_text( msg ),
                                                              messagetype='error' ) )
        if params.get( 'new_info', False ):
            if library_item:
                if params.get( 'create_new_info_button', False ):
                    library_item_info_template_id = params.get( 'library_item_info_template_id', None )
                    library_item_info_template = trans.app.model.LibraryItemInfoTemplate.get( int( library_item_info_template_id ) )
                    # Make sure at least 1 template field is filled in
                    # TODO: Eventually we'll enhance templates to allow for required and optional fields.
                    proceed = False
                    for template_element in library_item_info_template.elements:
                        if params.get( "info_element_%s_%s" % ( library_item_info_template.id, template_element.id ), None ):
                            proceed = True
                            break
                    if not proceed:
                        msg = "At least 1 of the fields must be completed."
                        return trans.response.send_redirect( web.url_for( controller='admin',
                                                                          action=library_item_type,
                                                                          id=library_item.id,
                                                                          library_id=library_id,
                                                                          folder_id=folder_id,
                                                                          edit_info=True,
                                                                          msg=util.sanitize_text( msg ),
                                                                          messagetype='error' ) )
                    user = trans.get_user()
                    library_item_info = trans.app.model.LibraryItemInfo( user=user )
                    library_item_info.library_item_info_template = library_item_info_template
                    library_item_info.flush()
                    trans.app.security_agent.copy_library_permissions( library_item_info_template, library_item_info )
                    for template_element in library_item_info_template.elements:
                        info_element_value = params.get( "info_element_%s_%s" % ( library_item_info_template.id, template_element.id ), None )
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
                        library_item_info_association = info_association_class( user=user )
                        library_item_info_association.set_library_item( library_item )
                        library_item_info_association.library_item_info = library_item_info
                        library_item_info_association.flush()
                    else:
                        raise 'Invalid class (%s) specified for library_item (%s)' % ( library_item.__class__, library_item.__class__.__name__ )
                    msg = 'The information has been saved.'
                    return trans.response.send_redirect( web.url_for( controller='library',
                                                                      action=library_item_type,
                                                                      id=library_item.id,
                                                                      library_id=library_id,
                                                                      folder_id=folder_id,
                                                                      edit_info=True,
                                                                      msg=util.sanitize_text( msg ),
                                                                      messagetype='done' ) )
                return trans.fill_template( "/library/new_info.mako",
                                            library_id=library_id,
                                            library_item=library_item,
                                            library_item_type=library_item_type,
                                            msg=msg,
                                            messagetype=messagetype )
        elif params.get( 'edit_info', False ):
            if params.get( 'edit_info_button', False ):
                ids = util.listify( id )
                for id in ids:
                    library_item_info_element = trans.app.model.LibraryItemInfoElement.get( int( id ) )
                    new_contents = util.restore_text( params.get( ( 'info_element_%s' % id ), '' ) )
                    library_item_info_element.contents = new_contents
                    library_item_info_element.flush()
                msg = 'The information has been updated.'
                return trans.response.send_redirect( web.url_for( controller='library',
                                                                  action=library_item_type,
                                                                  id=library_item.id,
                                                                  library_id=library_id,
                                                                  folder_id=folder_id,
                                                                  edit_info=True,
                                                                  msg=util.sanitize_text( msg ),
                                                                  messagetype='done' ) )
        elif params.get( 'permissions', False ):
            if params.get( 'update_roles_button', False ):
                permissions = {}
                for k, v in trans.app.model.Library.permitted_actions.items():
                    in_roles = [ trans.app.model.Role.get( x ) for x in util.listify( kwd.get( k + '_in', [] ) ) ]
                    permissions[ trans.app.security_agent.get_action( v.action ) ] = in_roles
                trans.app.security_agent.set_all_library_permissions( library_item.library_item_info, permissions )
                library_item.library_item_info.refresh()
                library_item.refresh()
                msg = "Permissions updated for field '%s'" % library_item.name
                return trans.response.send_redirect( web.url_for( controller='library',
                                                                  action='library_item_info',
                                                                  library_id=library_id,
                                                                  id=id,
                                                                  library_item_type=library_item_type,
                                                                  permissions=True,
                                                                  msg=util.sanitize_text( msg ),
                                                                  messagetype='done' ) )
            return trans.fill_template( '/library/info_permissions.mako',
                                        library_item_info_element=library_item_info_element,
                                        library_id=library_id,
                                        msg=msg,
                                        messagetype=messagetype )
