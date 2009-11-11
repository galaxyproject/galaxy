from galaxy.web.base.controller import *
from galaxy.model.orm import *
from galaxy.datatypes import sniff
from galaxy import util
from galaxy.util.odict import odict
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
        user, roles = trans.get_user_and_roles()
        all_libraries = trans.sa_session.query( trans.app.model.Library ) \
                                        .filter( trans.app.model.Library.table.c.deleted==False ) \
                                        .order_by( trans.app.model.Library.name )
        library_actions = [ trans.app.security_agent.permitted_actions.LIBRARY_ADD,
                            trans.app.security_agent.permitted_actions.LIBRARY_MODIFY,
                            trans.app.security_agent.permitted_actions.LIBRARY_MANAGE ]
        # The authorized_libraries dictionary looks like: { library : '1,2' }, library : '3' }
        # Its keys are the libraries that should be displayed for the current user and whose values are a
        # string of comma-separated folder ids of the associated folders that should NOT be displayed.
        # The folders that should not be displayed may not be a complete list, but it is ultimately passed
        # to the browse_library() method and the browse_library.mako template to keep from re-checking the
        # same folders when the library is rendered.
        authorized_libraries = odict()
        for library in all_libraries:
            can_access, hidden_folder_ids = trans.app.security_agent.check_folder_contents( user, roles, library.root_folder )
            if can_access:
                authorized_libraries[ library ] = hidden_folder_ids
            else:
                can_show, hidden_folder_ids = trans.app.security_agent.show_library_item( user, roles, library, library_actions )
                if can_show:
                    authorized_libraries[ library ] = hidden_folder_ids
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
        library_id = params.get( 'obj_id', None )
        if not library_id:
            # To handle bots
            msg = "You must specify a library id."
            return trans.response.send_redirect( web.url_for( controller='library',
                                                              action='browse_libraries',
                                                              default_action=params.get( 'default_action', None ),
                                                              msg=util.sanitize_text( msg ),
                                                              messagetype='error' ) )
        library = trans.sa_session.query( trans.app.model.Library ).get( library_id )
        if not library:
            # To handle bots
            msg = "Invalid library id ( %s )." % str( library_id )
            return trans.response.send_redirect( web.url_for( controller='library',
                                                              action='browse_libraries',
                                                              default_action=params.get( 'default_action', None ),
                                                              msg=util.sanitize_text( msg ),
                                                              messagetype='error' ) )
        created_ldda_ids = params.get( 'created_ldda_ids', '' )
        hidden_folder_ids = util.listify( util.restore_text( params.get( 'hidden_folder_ids', '' ) ) )
        if created_ldda_ids and not msg:
            msg = "%d datasets are now uploading in the background to the library '%s' ( each is selected ).  "  % ( len( created_ldda_ids.split(',') ), library.name )
            msg += "Do not navigate away from Galaxy or use the browser's \"stop\" or \"reload\" buttons ( on this tab ) until the upload(s) change from the \"uploading\" state."
            messagetype = "info"
        return trans.fill_template( '/library/browse_library.mako', 
                                    library=library,
                                    created_ldda_ids=created_ldda_ids,
                                    hidden_folder_ids=hidden_folder_ids,
                                    default_action=params.get( 'default_action', None ),
                                    comptypes=comptypes,
                                    msg=msg,
                                    messagetype=messagetype )
    @web.expose
    def library( self, trans, **kwd ):
        params = util.Params( kwd )
        msg = util.restore_text( params.get( 'msg', ''  ) )
        messagetype = params.get( 'messagetype', 'done' )
        library_id = params.get( 'obj_id', None )
        # TODO: eventually we'll want the ability for users to create libraries
        if params.get( 'delete', False ):
            action = 'delete'
        elif params.get( 'permissions', False ):
            action = 'permissions'
        else:
            action = 'information'
        if not library_id:
            msg = "You must specify a library."
            return trans.response.send_redirect( web.url_for( controller='library',
                                                              action='browse_libraries',
                                                              msg=util.sanitize_text( msg ),
                                                              messagetype='error' ) )
        library = trans.sa_session.query( trans.app.model.Library ).get( int( library_id ) )
        if not library:
            msg = "Invalid library id ( %s ) specified." % str( obj_id )
            return trans.response.send_redirect( web.url_for( controller='library',
                                                              action='browse_libraries',
                                                              msg=util.sanitize_text( msg ),
                                                              messagetype='error' ) )
        if action == 'information':
            # See if we have any associated templates
            widgets = library.get_template_widgets( trans )
            if params.get( 'rename_library_button', False ):
                old_name = library.name
                new_name = util.restore_text( params.name )
                new_description = util.restore_text( params.description )
                if not new_name:
                    msg = 'Enter a valid name'
                    return trans.fill_template( '/library/library_info.mako',
                                                library=library,
                                                widgets=widgets,
                                                msg=msg,
                                                messagetype='error' )
                else:
                    library.name = new_name
                    library.description = new_description
                    # Rename the root_folder
                    library.root_folder.name = new_name
                    library.root_folder.description = new_description
                    trans.sa_session.add_all( ( library, library.root_folder ) )
                    trans.sa_session.flush()
                    msg = "Library '%s' has been renamed to '%s'" % ( old_name, new_name )
                    return trans.response.send_redirect( web.url_for( controller='library',
                                                                      action='library',
                                                                      obj_id=library.id,
                                                                      edit_info=True,
                                                                      msg=util.sanitize_text( msg ),
                                                                      messagetype='done' ) )
            return trans.fill_template( '/library/library_info.mako',
                                        library=library,
                                        widgets=widgets,
                                        msg=msg,
                                        messagetype=messagetype )
        elif action == 'permissions':
            if params.get( 'update_roles_button', False ):
                # The user clicked the Save button on the 'Associate With Roles' form
                permissions = {}
                for k, v in trans.app.model.Library.permitted_actions.items():
                    in_roles = [ trans.sa_session.query( trans.app.model.Role ).get( x ) for x in util.listify( params.get( k + '_in', [] ) ) ]
                    permissions[ trans.app.security_agent.get_action( v.action ) ] = in_roles
                trans.app.security_agent.set_all_library_permissions( library, permissions )
                trans.sa_session.refresh( library )
                # Copy the permissions to the root folder
                trans.app.security_agent.copy_library_permissions( library, library.root_folder )
                msg = "Permissions updated for library '%s'" % library.name
                return trans.response.send_redirect( web.url_for( controller='library',
                                                                  action='library',
                                                                  obj_id=library.id,
                                                                  permissions=True,
                                                                  msg=util.sanitize_text( msg ),
                                                                  messagetype='done' ) )
            return trans.fill_template( '/library/library_permissions.mako',
                                        library=library,
                                        msg=msg,
                                        messagetype=messagetype )
    @web.expose
    def folder( self, trans, obj_id, library_id, **kwd ):
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
        folder = trans.sa_session.query( trans.app.model.LibraryFolder ).get( int( obj_id ) )
        if not folder:
            msg = "Invalid folder specified, id: %s" % str( obj_id )
            return trans.response.send_redirect( web.url_for( controller='library',
                                                              action='browse_library',
                                                              obj_id=library_id,
                                                              msg=util.sanitize_text( msg ),
                                                              messagetype='error' ) )
        user, roles = trans.get_user_and_roles()
        if action == 'new':
            if params.new == 'submitted':
                new_folder = trans.app.model.LibraryFolder( name=util.restore_text( params.name ),
                                                            description=util.restore_text( params.description ) )
                # We are associating the last used genome build with folders, so we will always
                # initialize a new folder with the first dbkey in util.dbnames which is currently
                # ?    unspecified (?)
                new_folder.genome_build = util.dbnames.default_value
                folder.add_folder( new_folder )
                trans.sa_session.add( new_folder )
                trans.sa_session.flush()
                # New folders default to having the same permissions as their parent folder
                trans.app.security_agent.copy_library_permissions( folder, new_folder )
                msg = "New folder named '%s' has been added to the library" % new_folder.name
                return trans.response.send_redirect( web.url_for( controller='library',
                                                                  action='browse_library',
                                                                  obj_id=library_id,
                                                                  msg=util.sanitize_text( msg ),
                                                                  messagetype='done' ) )
            return trans.fill_template( '/library/new_folder.mako',
                                        library_id=library_id,
                                        folder=folder,
                                        msg=msg,
                                        messagetype=messagetype )
        elif action == 'information':
            # See if we have any associated templates
            widgets = folder.get_template_widgets( trans )
            if params.get( 'rename_folder_button', False ):
                if trans.app.security_agent.can_modify_library_item( user, roles, folder ):
                    old_name = folder.name
                    new_name = util.restore_text( params.name )
                    new_description = util.restore_text( params.description )
                    if not new_name:
                        msg = 'Enter a valid name'
                        return trans.fill_template( "/library/folder_info.mako",
                                                    folder=folder,
                                                    library_id=library_id,
                                                    widgets=widgets,
                                                    msg=msg,
                                                    messagetype='error' )
                    else:
                        folder.name = new_name
                        folder.description = new_description
                        trans.sa_session.add( folder )
                        trans.sa_session.flush()
                        msg = "Folder '%s' has been renamed to '%s'" % ( old_name, new_name )
                        return trans.response.send_redirect( web.url_for( controller='library',
                                                                          action='folder',
                                                                          obj_id=folder.id,
                                                                          library_id=library_id,
                                                                          rename=True,
                                                                          msg=util.sanitize_text( msg ),
                                                                          messagetype='done' ) )
                else:
                    msg = "You are not authorized to edit this folder"
                    return trans.fill_template( "/library/folder_info.mako",
                                                folder=folder,
                                                library_id=library_id,
                                                widgets=widgets,
                                                msg=msg,
                                                messagetype='error' )
            return trans.fill_template( '/library/folder_info.mako',
                                        folder=folder,
                                        library_id=library_id,
                                        widgets=widgets,
                                        msg=msg,
                                        messagetype=messagetype )
        elif action == 'permissions':
            if params.get( 'update_roles_button', False ):
                # The user clicked the Save button on the 'Associate With Roles' form
                if trans.app.security_agent.can_manage_library_item( user, roles, folder ):
                    permissions = {}
                    for k, v in trans.app.model.Library.permitted_actions.items():
                        in_roles = [ trans.sa_session.query( trans.app.model.Role ).get( int( x ) ) for x in util.listify( params.get( k + '_in', [] ) ) ]
                        permissions[ trans.app.security_agent.get_action( v.action ) ] = in_roles
                    trans.app.security_agent.set_all_library_permissions( folder, permissions )
                    trans.sa_session.refresh( folder )
                    msg = 'Permissions updated for folder %s' % folder.name
                    return trans.response.send_redirect( web.url_for( controller='library',
                                                                      action='folder',
                                                                      obj_id=folder.id,
                                                                      library_id=library_id,
                                                                      permissions=True,
                                                                      msg=util.sanitize_text( msg ),
                                                                      messagetype='done' ) )
                else:
                    msg = "You are not authorized to manage permissions on this folder"
                    return trans.response.send_redirect( web.url_for( controller='library',
                                                                      action='folder',
                                                                      obj_id=folder.id,
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
    def library_dataset( self, trans, obj_id, library_id, **kwd ):
        params = util.Params( kwd )
        msg = util.restore_text( params.get( 'msg', ''  ) )
        messagetype = params.get( 'messagetype', 'done' )
        if params.get( 'permissions', False ):
            action = 'permissions'
        else:
            action = 'information'
        library_dataset = trans.sa_session.query( trans.app.model.LibraryDataset ).get( obj_id )
        if not library_dataset:
            msg = "Invalid library dataset specified, id: %s" %str( obj_id )
            return trans.response.send_redirect( web.url_for( controller='library',
                                                              action='browse_library',
                                                              obj_id=library_id,
                                                              msg=util.sanitize_text( msg ),
                                                              messagetype='error' ) )
        user, roles = trans.get_user_and_roles()
        if action == 'information':
            if params.get( 'edit_attributes_button', False ):
                if trans.app.security_agent.can_modify_library_item( user, roles, library_dataset ):
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
                            trans.sa_session.add( library_dataset )
                            trans.sa_session.flush()
                            msg = "Dataset '%s' has been renamed to '%s'" % ( old_name, new_name )
                            messagetype = 'done'
                else:
                    msg = "You are not authorized to change the attributes of this dataset"
                    messagetype = "error"
            return trans.fill_template( '/library/library_dataset_info.mako',
                                        library_dataset=library_dataset,
                                        library_id=library_id,
                                        msg=msg,
                                        messagetype=messagetype )
        elif action == 'permissions':
            if params.get( 'update_roles_button', False ):
                if trans.app.security_agent.can_manage_library_item( user, roles, library_dataset ):
                    # The user clicked the Save button on the 'Associate With Roles' form
                    permissions = {}
                    for k, v in trans.app.model.Library.permitted_actions.items():
                        in_roles = [ trans.sa_session.query( trans.app.model.Role ).get( x ) for x in util.listify( kwd.get( k + '_in', [] ) ) ]
                        permissions[ trans.app.security_agent.get_action( v.action ) ] = in_roles
                    # Set the LIBRARY permissions on the LibraryDataset
                    # NOTE: the LibraryDataset and LibraryDatasetDatasetAssociation will be set with the same permissions
                    trans.app.security_agent.set_all_library_permissions( library_dataset, permissions )
                    trans.sa_session.refresh( library_dataset )
                    # Set the LIBRARY permissions on the LibraryDatasetDatasetAssociation
                    trans.app.security_agent.set_all_library_permissions( library_dataset.library_dataset_dataset_association, permissions )
                    trans.sa_session.refresh( library_dataset.library_dataset_dataset_association )
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
    def ldda_edit_info( self, trans, library_id, folder_id, obj_id, **kwd ):
        params = util.Params( kwd )
        msg = util.restore_text( params.get( 'msg', ''  ) )
        messagetype = params.get( 'messagetype', 'done' )
        ldda = trans.sa_session.query( trans.app.model.LibraryDatasetDatasetAssociation ).get( obj_id )
        if not ldda:
            msg = "Invalid LibraryDatasetDatasetAssociation specified, obj_id: %s" % str( obj_id )
            return trans.response.send_redirect( web.url_for( controller='library',
                                                              action='browse_library',
                                                              obj_id=library_id,
                                                              msg=util.sanitize_text( msg ),
                                                              messagetype='error' ) )
        dbkey = params.get( 'dbkey', '?' )
        if isinstance( dbkey, list ):
            dbkey = dbkey[0]
        user, roles = trans.get_user_and_roles()
        file_formats = [ dtype_name for dtype_name, dtype_value in trans.app.datatypes_registry.datatypes_by_extension.iteritems() if dtype_value.allow_datatype_change ]
        file_formats.sort()
        # See if we have any associated templates
        widgets = ldda.get_template_widgets( trans )
        if params.get( 'change', False ):
            # The user clicked the Save button on the 'Change data type' form
            if trans.app.security_agent.can_modify_library_item( user, roles, ldda ):
                if ldda.datatype.allow_datatype_change and trans.app.datatypes_registry.get_datatype_by_extension( params.datatype ).allow_datatype_change:
                    trans.app.datatypes_registry.change_datatype( ldda, params.datatype )
                    trans.sa_session.flush()
                    msg = "Data type changed for library dataset '%s'" % ldda.name
                    messagetype = 'done'
                else:
                    msg = "You are unable to change datatypes in this manner. Changing %s to %s is not allowed." % ( ldda.extension, params.datatype )
                    messagetype = 'error'
            else:
                msg = "You are not authorized to change the data type of dataset '%s'" % ldda.name
                messagetype = 'error'
            return trans.fill_template( "/library/ldda_edit_info.mako", 
                                        ldda=ldda,
                                        library_id=library_id,
                                        file_formats=file_formats,
                                        widgets=widgets,
                                        msg=msg,
                                        messagetype=messagetype )
        elif params.get( 'save', False ):
            # The user clicked the Save button on the 'Edit Attributes' form
            if trans.app.security_agent.can_modify_library_item( user, roles, ldda ):
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
                    trans.sa_session.flush()
                    msg = 'Attributes updated for library dataset %s' % ldda.name
                    messagetype = 'done'
            else:
                msg = "you are not authorized to edit the attributes of dataset '%s'" % ldda.name
                messagetype = 'error'
            return trans.fill_template( "/library/ldda_edit_info.mako", 
                                        ldda=ldda,
                                        library_id=library_id,
                                        file_formats=file_formats,
                                        widgets=widgets,
                                        msg=msg,
                                        messagetype=messagetype )
        elif params.get( 'detect', False ):
            # The user clicked the Auto-detect button on the 'Edit Attributes' form
            if trans.app.security_agent.can_modify_library_item( user, roles, ldda ):
                for name, spec in ldda.datatype.metadata_spec.items():
                    # We need to be careful about the attributes we are resetting
                    if name not in [ 'name', 'info', 'dbkey' ]:
                        if spec.get( 'default' ):
                            setattr( ldda.metadata, name, spec.unwrap( spec.get( 'default' ) ) )
                ldda.datatype.set_meta( ldda )
                ldda.datatype.after_edit( ldda )
                trans.sa_session.flush()
                msg = 'Attributes updated for library dataset %s' % ldda.name
                messagetype = 'done'
            else:
                msg = "you are not authorized to edit the attributes of dataset '%s'" % ldda.name
                messagetype = 'error'
            return trans.fill_template( "/library/ldda_edit_info.mako", 
                                        ldda=ldda,
                                        library_id=library_id,
                                        file_formats=file_formats,
                                        widgets=widgets,
                                        msg=msg,
                                        messagetype=messagetype )
        elif params.get( 'delete', False ):
            if trans.app.security_agent.can_modify_library_item( user, roles, folder ):
                ldda.deleted = True
                trans.sa_session.add( ldda )
                trans.sa_session.flush()
                msg = 'Dataset %s has been removed from this data library' % ldda.name
                messagetype = 'done'
            else:
                msg = "you are not authorized to delete dataset '%s'" % ldda.name
                messagetype = 'error'
            return trans.fill_template( "/library/ldda_edit_info.mako", 
                                        ldda=ldda,
                                        library_id=library_id,
                                        file_formats=file_formats,
                                        widgets=widgets,
                                        msg=msg,
                                        messagetype=messagetype )
        if trans.app.security_agent.can_modify_library_item( user, roles, ldda ):
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
                                    file_formats=file_formats,
                                    widgets=widgets,
                                    msg=msg,
                                    messagetype=messagetype )
    @web.expose
    def ldda_display_info( self, trans, library_id, folder_id, obj_id, **kwd ):
        params = util.Params( kwd )
        msg = util.restore_text( params.get( 'msg', ''  ) )
        messagetype = params.get( 'messagetype', 'done' )
        ldda = trans.sa_session.query( trans.app.model.LibraryDatasetDatasetAssociation ).get( obj_id )
        if not ldda:
            msg = "Invalid LibraryDatasetDatasetAssociation specified, id: %s" % str( obj_id )
            return trans.response.send_redirect( web.url_for( controller='admin',
                                                              action='browse_library',
                                                              obj_id=library_id,
                                                              msg=util.sanitize_text( msg ),
                                                              messagetype='error' ) )
        # See if we have any associated templates
        widgets = ldda.get_template_widgets( trans )
        return trans.fill_template( '/library/ldda_info.mako',
                                    ldda=ldda,
                                    library_id=library_id,
                                    widgets=widgets,
                                    msg=msg,
                                    messagetype=messagetype )
    @web.expose
    def ldda_manage_permissions( self, trans, library_id, folder_id, obj_id, **kwd ):
        params = util.Params( kwd )
        msg = util.restore_text( params.get( 'msg', ''  ) )
        messagetype = params.get( 'messagetype', 'done' )
        obj_ids = util.listify( obj_id )
        # Display permission form, permissions will be updated for all lddas simultaneously.
        lddas = []
        for obj_id in [ int( obj_id ) for obj_id in obj_ids ]:
            ldda = trans.sa_session.query( trans.app.model.LibraryDatasetDatasetAssociation ).get( obj_id )
            if ldda is None:
                msg = 'You specified an invalid LibraryDatasetDatasetAssociation id: %s' %str( obj_id )
                trans.response.send_redirect( web.url_for( controller='library',
                                                           action='browse_library',
                                                           obj_id=library_id,
                                                           msg=util.sanitize_text( msg ),
                                                           messagetype='error' ) )
            lddas.append( ldda )
        if params.get( 'update_roles_button', False ):
            if trans.app.security_agent.can_manage_library_item( user, roles, ldda ) and \
                trans.app.security_agent.can_manage_dataset( roles, ldda.dataset ):
                permissions = {}
                for k, v in trans.app.model.Dataset.permitted_actions.items():
                    in_roles = [ trans.sa_session.query( trans.app.model.Role ).get( x ) for x in util.listify( params.get( k + '_in', [] ) ) ]
                    permissions[ trans.app.security_agent.get_action( v.action ) ] = in_roles
                for ldda in lddas:
                    # Set the DATASET permissions on the Dataset
                    trans.app.security_agent.set_all_dataset_permissions( ldda.dataset, permissions )
                    trans.sa_session.refresh( ldda.dataset )
                permissions = {}
                for k, v in trans.app.model.Library.permitted_actions.items():
                    in_roles = [ trans.sa_session.query( trans.app.model.Role ).get( x ) for x in util.listify( kwd.get( k + '_in', [] ) ) ]
                    permissions[ trans.app.security_agent.get_action( v.action ) ] = in_roles
                for ldda in lddas:
                    # Set the LIBRARY permissions on the LibraryDataset
                    # NOTE: the LibraryDataset and LibraryDatasetDatasetAssociation will be set with the same permissions
                    trans.app.security_agent.set_all_library_permissions( ldda.library_dataset, permissions )
                    trans.sa_session.refresh( ldda.library_dataset )
                    # Set the LIBRARY permissions on the LibraryDatasetDatasetAssociation
                    trans.app.security_agent.set_all_library_permissions( ldda, permissions )
                    trans.sa_session.refresh( ldda )
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
        if trans.app.security_agent.can_manage_library_item( user, roles, ldda ) and \
            trans.app.security_agent.can_manage_dataset( roles, ldda.dataset ):
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
                                                               obj_id=library_id,
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
    @web.expose
    def upload_library_dataset( self, trans, library_id, folder_id, **kwd ):
        params = util.Params( kwd )
        msg = util.restore_text( params.get( 'msg', ''  ) )
        messagetype = params.get( 'messagetype', 'done' )
        dbkey = params.get( 'dbkey', None )
        if isinstance( dbkey, list ):
            last_used_build = dbkey[0]
        else:
            last_used_build = dbkey
        folder = trans.sa_session.query( trans.app.model.LibraryFolder ).get( folder_id )
        if folder and last_used_build in [ 'None', None, '?' ]:
            last_used_build = folder.genome_build
        replace_id = params.get( 'replace_id', None )
        if replace_id not in [ None, 'None' ]:
            replace_dataset = trans.sa_session.query( trans.app.model.LibraryDataset ).get( replace_id )
            if not last_used_build:
                last_used_build = replace_dataset.library_dataset_dataset_association.dbkey
            # Don't allow multiple datasets to be uploaded when replacing a dataset with a new version
            upload_option = 'upload_file'
        else:
            replace_dataset = None
            upload_option = params.get( 'upload_option', 'upload_file' )
        user, roles = trans.get_user_and_roles()
        if trans.app.security_agent.can_add_library_item( user, roles, folder ) or \
             ( replace_dataset and trans.app.security_agent.can_modify_library_item( user, roles, replace_dataset ) ):
            if params.get( 'runtool_btn', False ) or params.get( 'ajax_upload', False ):
                # See if we have any inherited templates, but do not inherit contents.
                info_association, inherited = folder.get_info_association( inherited=True )
                if info_association:
                    template_id = str( info_association.template.id )
                    widgets = folder.get_template_widgets( trans, get_contents=False )
                else:
                    template_id = 'None'
                    widgets = []
                created_outputs = trans.webapp.controllers[ 'library_common' ].upload_dataset( trans,
                                                                                               controller='library', 
                                                                                               library_id=library_id,
                                                                                               folder_id=folder_id,
                                                                                               template_id=template_id,
                                                                                               widgets=widgets,
                                                                                               replace_dataset=replace_dataset,
                                                                                               **kwd )
                if created_outputs:
                    ldda_id_list = [ str( v.id ) for v in created_outputs.values() ]
                    total_added = len( created_outputs.values() )
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
                    check_ldda = trans.sa_session.query( trans.app.model.LibraryDatasetDatasetAssociation ).get( ldda_id_list[0] )
                    if trans.app.security_agent.can_manage_library_item( user, roles, check_ldda ):
                        if replace_dataset:
                            default_action = ''
                        else:
                            msg += "Click the Go button at the bottom of this page to edit the permissions on these datasets if necessary."
                            default_action = 'manage_permissions'
                    else:
                        default_action = 'add'
                    trans.response.send_redirect( web.url_for( controller='library',
                                                               action='browse_library',
                                                               obj_id=library_id,
                                                               default_action=default_action,
                                                               created_ldda_ids=",".join( ldda_id_list ), 
                                                               msg=util.sanitize_text( msg ), 
                                                               messagetype='done' ) )
                    
                else:
                    msg = "Upload failed"
                    trans.response.send_redirect( web.url_for( controller='library',
                                                               action='browse_library',
                                                               obj_id=library_id,
                                                               created_ldda_ids=",".join( ldda_id_list ), 
                                                               msg=util.sanitize_text( msg ), 
                                                               messagetype='error' ) )
        # See if we have any inherited templates, but do not inherit contents.
        widgets = folder.get_template_widgets( trans, get_contents=False )
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
        roles = trans.sa_session.query( trans.app.model.Role ) \
                                .filter( trans.app.model.Role.table.c.deleted==False ) \
                                .order_by( trans.app.model.Role.table.c.name )
        # Send the current history to the form to enable importing datasets from history to library
        history = trans.get_history()
        trans.sa_session.refresh( history )
        # If we're using nginx upload, override the form action
        action = web.url_for( controller='library', action='upload_library_dataset' )
        if upload_option == 'upload_file' and trans.app.config.nginx_upload_path:
            action = web.url_for( trans.app.config.nginx_upload_path ) + '?nginx_redir=' + action
        return trans.fill_template( '/library/upload.mako',
                                    upload_option=upload_option,
                                    action=action,
                                    library_id=library_id,
                                    folder_id=folder_id,
                                    replace_dataset=replace_dataset,
                                    file_formats=file_formats,
                                    dbkeys=dbkeys,
                                    last_used_build=last_used_build,
                                    roles=roles,
                                    history=history,
                                    widgets=widgets,
                                    msg=msg,
                                    messagetype=messagetype )
    @web.expose
    def add_history_datasets_to_library( self, trans, library_id, folder_id, hda_ids='', **kwd ):
        params = util.Params( kwd )
        msg = util.restore_text( params.get( 'msg', ''  ) )
        messagetype = params.get( 'messagetype', 'done' )
        try:
            folder = trans.sa_session.query( trans.app.model.LibraryFolder ).get( int( folder_id ) )
        except:
            msg = "Invalid folder id: %s" % str( folder_id )
            return trans.response.send_redirect( web.url_for( controller='library',
                                                              action='browse_library',
                                                              obj_id=library_id,
                                                              msg=util.sanitize_text( msg ),
                                                              messagetype='error' ) )
        replace_id = params.get( 'replace_id', None )
        if replace_id:
            replace_dataset = trans.sa_session.query( trans.app.model.LibraryDataset ).get( replace_id )
        else:
            replace_dataset = None
        # See if the current history is empty
        history = trans.get_history()
        trans.sa_session.refresh( history )
        if not history.active_datasets:
            msg = 'Your current history is empty'
            return trans.response.send_redirect( web.url_for( controller='library',
                                                              action='browse_library',
                                                              obj_id=library_id,
                                                              msg=util.sanitize_text( msg ),
                                                              messagetype='error' ) )
        if params.get( 'add_history_datasets_to_library_button', False ):
            hda_ids = util.listify( hda_ids )
            if hda_ids:
                dataset_names = []
                created_ldda_ids = ''
                for hda_id in hda_ids:
                    hda = trans.sa_session.query( trans.app.model.HistoryDatasetAssociation ).get( hda_id )
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
                                                                          obj_id=library_id,
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
                    check_ldda = trans.sa_session.query( trans.app.model.LibraryDatasetDatasetAssociation ).get( ldda_id_list[0] )
                    user, roles = trans.get_user_and_roles()
                    if trans.app.security_agent.can_manage_library_item( user, roles, check_ldda ):
                        if replace_dataset:
                            default_action = ''
                        else:
                            msg += "Click the Go button at the bottom of this page to edit the permissions on these datasets if necessary."
                            default_action = 'manage_permissions'
                    else:
                        default_action = 'add'
                    return trans.response.send_redirect( web.url_for( controller='library',
                                                                      action='browse_library',
                                                                      obj_id=library_id,
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
                roles = trans.sa_session.query( trans.app.model.Role ) \
                                        .filter( trans.app.model.Role.table.c.deleted==False ) \
                                        .order_by( trans.app.model.Role.table.c.name )
                return trans.fill_template( "/library/upload.mako",
                                            upload_option=upload_option,
                                            library_id=library_id,
                                            folder_id=folder_id,
                                            replace_dataset=replace_dataset,
                                            file_formats=file_formats,
                                            dbkeys=dbkeys,
                                            last_used_build=last_used_build,
                                            roles=roles,
                                            history=history,
                                            widgets=[],
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
                                                              obj_id=library_id,
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
                                                              obj_id=library_id,
                                                              msg=util.sanitize_text( msg ),
                                                              messagetype='error' ) )
        if params.do_action == 'add':
            history = trans.get_history()
            for ldda_id in ldda_ids:
                ldda = trans.sa_session.query( trans.app.model.LibraryDatasetDatasetAssociation ).get( ldda_id )
                hda = ldda.to_history_dataset_association( target_history=history, add_to_history = True )
            trans.sa_session.add( history )
            trans.sa_session.flush()
            msg = "%i dataset(s) have been imported into your history" % len( ldda_ids )
            return trans.response.send_redirect( web.url_for( controller='library',
                                                              action='browse_library',
                                                              obj_id=library_id,
                                                              msg=util.sanitize_text( msg ),
                                                              messagetype='done' ) )
        elif params.do_action == 'manage_permissions':
            # We need the folder containing the LibraryDatasetDatasetAssociation(s)
            ldda = trans.sa_session.query( trans.app.model.LibraryDatasetDatasetAssociation ).get( ldda_ids[0] )
            trans.response.send_redirect( web.url_for( controller='library',
                                                       action='upload_library_dataset',
                                                       library_id=library_id,
                                                       folder_id=ldda.library_dataset.folder.id,
                                                       obj_id=','.join( ldda_ids ),
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
                                                                  obj_id=library_id,
                                                                  msg=util.sanitize_text( msg ),
                                                                  messagetype='error' ) )
            seen = []
            user, roles = trans.get_user_and_roles()
            for ldda_id in ldda_ids:
                ldda = trans.sa_session.query( trans.app.model.LibraryDatasetDatasetAssociation ).get( ldda_id )
                if not ldda or not trans.app.security_agent.can_access_dataset( roles, ldda.dataset ):
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
                                                                      obj_id=library_id,
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
                                                                      obj_id=library_id,
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
