import sys
from galaxy import util
from galaxy.web.base.controller import *
from galaxy.model.orm import *
from galaxy.web.controllers.forms import get_all_forms
# Older py compatibility
try:
    set()
except:
    from sets import Set as set

import logging
log = logging.getLogger( __name__ )

class LibraryAdmin( BaseController ):
    @web.expose
    @web.require_admin
    def browse_libraries( self, trans, **kwd ):
        params = util.Params( kwd )
        msg = util.restore_text( params.get( 'msg', ''  ) )
        messagetype = params.get( 'messagetype', 'done' )
        return trans.fill_template( '/admin/library/browse_libraries.mako', 
                                    libraries=trans.app.model.Library.filter( trans.app.model.Library.table.c.deleted==False ) \
                                                                     .order_by( trans.app.model.Library.name ).all(),
                                    deleted=False,
                                    show_deleted=False,
                                    msg=msg,
                                    messagetype=messagetype )
    @web.expose
    @web.require_admin
    def browse_library( self, trans, **kwd ):
        params = util.Params( kwd )
        msg = util.restore_text( params.get( 'msg', ''  ) )
        messagetype = params.get( 'messagetype', 'done' )
        id = params.get( 'id', None )
        deleted = util.string_as_bool( params.get( 'deleted', False ) )
        show_deleted = util.string_as_bool( params.get( 'show_deleted', False ) )
        if not id:
            msg = "You must specify a library id."
            return trans.response.send_redirect( web.url_for( controller='library_admin',
                                                              action='browse_libraries',
                                                              msg=util.sanitize_text( msg ),
                                                              messagetype='error' ) )
        library = library=trans.app.model.Library.get( id )
        if not library:
            msg = "Invalid library id ( %s )."
            return trans.response.send_redirect( web.url_for( controller='library_admin',
                                                              action='browse_libraries',
                                                              msg=util.sanitize_text( msg ),
                                                              messagetype='error' ) )
        created_ldda_ids = params.get( 'created_ldda_ids', '' )
        return trans.fill_template( '/admin/library/browse_library.mako', 
                                    library=trans.app.model.Library.get( id ),
                                    deleted=deleted,
                                    created_ldda_ids=created_ldda_ids,
                                    forms=get_all_forms( trans, filter=dict(deleted=False) ),
                                    msg=msg,
                                    messagetype=messagetype,
                                    show_deleted=show_deleted )
    @web.expose
    @web.require_admin
    def library( self, trans, id=None, **kwd ):
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
            action = 'information'
        if not id and not action == 'new':
            msg = "You must specify a library to %s." % action
            return trans.response.send_redirect( web.url_for( controller='library_admin',
                                                              action='browse_libraries',
                                                              msg=util.sanitize_text( msg ),
                                                              messagetype='error' ) )
        if not action == 'new':
            library = trans.app.model.Library.get( int( id ) )
        if action == 'new':
            if params.new == 'submitted':
                library = trans.app.model.Library( name = util.restore_text( params.name ), 
                                                   description = util.restore_text( params.description ) )
                root_folder = trans.app.model.LibraryFolder( name = util.restore_text( params.name ), description = "" )
                root_folder.flush()
                library.root_folder = root_folder
                library.flush()
                msg = "The new library named '%s' has been created" % library.name
                return trans.response.send_redirect( web.url_for( controller='library_admin',
                                                                  action='browse_library',
                                                                  id=library.id,
                                                                  msg=util.sanitize_text( msg ),
                                                                  messagetype='done' ) )
            return trans.fill_template( '/admin/library/new_library.mako', msg=msg, messagetype=messagetype )
        elif action == 'information':
            # See if we have any associated templates
            widgets = library.get_template_widgets( trans )
            if params.get( 'rename_library_button', False ):
                old_name = library.name
                new_name = util.restore_text( params.name )
                new_description = util.restore_text( params.description )
                if not new_name:
                    msg = 'Enter a valid name'
                    return trans.fill_template( '/admin/library/library_info.mako',
                                                library=library,
                                                widgets=widgets,
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
                    return trans.response.send_redirect( web.url_for( controller='library_admin',
                                                                      action='library',
                                                                      id=id,
                                                                      edit_info=True,
                                                                      msg=util.sanitize_text( msg ),
                                                                      messagetype='done' ) )
            return trans.fill_template( '/admin/library/library_info.mako',
                                        library=library,
                                        widgets=widgets,
                                        msg=msg,
                                        messagetype=messagetype )
        elif action == 'delete':
            def delete_folder( library_folder ):
                library_folder.refresh()
                for folder in library_folder.folders:
                    delete_folder( folder )
                for library_dataset in library_folder.datasets:
                    library_dataset.refresh()
                    ldda = library_dataset.library_dataset_dataset_association
                    if ldda:
                        ldda.refresh()
                        # We don't set ldda.dataset.deleted to True here because the cleanup_dataset script
                        # will eventually remove it from disk.  The purge_library method below sets the dataset
                        # to deleted.  This allows for the library to be undeleted ( before it is purged ), 
                        # restoring all of its contents.
                        ldda.deleted = True
                        ldda.flush()
                    library_dataset.deleted = True
                    library_dataset.flush()
                library_folder.deleted = True
                library_folder.flush()
            library.refresh()
            delete_folder( library.root_folder )
            library.deleted = True
            library.flush()
            msg = "Library '%s' and all of its contents have been marked deleted" % library.name
            return trans.response.send_redirect( web.url_for( action='browse_libraries', msg=util.sanitize_text( msg ), messagetype='done' ) )
        elif action == 'permissions':
            if params.get( 'update_roles_button', False ):
                # The user clicked the Save button on the 'Associate With Roles' form
                permissions = {}
                for k, v in trans.app.model.Library.permitted_actions.items():
                    in_roles = [ trans.app.model.Role.get( x ) for x in util.listify( kwd.get( k + '_in', [] ) ) ]
                    permissions[ trans.app.security_agent.get_action( v.action ) ] = in_roles
                trans.app.security_agent.set_all_library_permissions( library, permissions )
                library.refresh()
                # Copy the permissions to the root folder
                trans.app.security_agent.copy_library_permissions( library, library.root_folder )
                msg = "Permissions updated for library '%s'" % library.name
                return trans.response.send_redirect( web.url_for( controller='library_admin',
                                                                  action='library',
                                                                  id=id,
                                                                  permissions=True,
                                                                  msg=util.sanitize_text( msg ),
                                                                  messagetype='done' ) )
            return trans.fill_template( '/admin/library/library_permissions.mako',
                                        library=library,
                                        msg=msg,
                                        messagetype=messagetype )
    @web.expose
    @web.require_admin
    def deleted_libraries( self, trans, **kwd ):
        params = util.Params( kwd )
        msg = util.restore_text( params.get( 'msg', ''  ) )
        messagetype = params.get( 'messagetype', 'done' )
        libraries=trans.app.model.Library.filter( and_( trans.app.model.Library.table.c.deleted==True,
                                                        trans.app.model.Library.table.c.purged==False ) ) \
                                         .order_by( trans.app.model.Library.table.c.name ).all()
        return trans.fill_template( '/admin/library/browse_libraries.mako', 
                                    libraries=libraries,
                                    deleted=True,
                                    msg=msg,
                                    messagetype=messagetype,
                                    show_deleted=True )
    @web.expose
    @web.require_admin
    def purge_library( self, trans, **kwd ):
        params = util.Params( kwd )
        library = trans.app.model.Library.get( int( params.id ) )
        def purge_folder( library_folder ):
            for lf in library_folder.folders:
                purge_folder( lf )
            library_folder.refresh()
            for library_dataset in library_folder.datasets:
                library_dataset.refresh()
                ldda = library_dataset.library_dataset_dataset_association
                if ldda:
                    ldda.refresh()
                    dataset = ldda.dataset
                    dataset.refresh()
                    # If the dataset is not associated with any additional undeleted folders, then we can delete it.
                    # We don't set dataset.purged to True here because the cleanup_datasets script will do that for
                    # us, as well as removing the file from disk.
                    #if not dataset.deleted and len( dataset.active_library_associations ) <= 1: # This is our current ldda
                    dataset.deleted = True
                    dataset.flush()
                    ldda.deleted = True
                    ldda.flush()
                library_dataset.deleted = True
                library_dataset.flush()
            library_folder.deleted = True
            library_folder.purged = True
            library_folder.flush()
        if not library.deleted:
            msg = "Library '%s' has not been marked deleted, so it cannot be purged" % ( library.name )
            return trans.response.send_redirect( web.url_for( controller='library_admin',
                                                              action='browse_libraries',
                                                              msg=util.sanitize_text( msg ),
                                                              messagetype='error' ) )
        else:
            purge_folder( library.root_folder )
            library.purged = True
            library.flush()
            msg = "Library '%s' and all of its contents have been purged, datasets will be removed from disk via the cleanup_datasets script" % library.name
            return trans.response.send_redirect( web.url_for( controller='library_admin',
                                                              action='deleted_libraries',
                                                              msg=util.sanitize_text( msg ),
                                                              messagetype='done' ) )
    @web.expose
    @web.require_admin
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
            return trans.response.send_redirect( web.url_for( controller='library_admin',
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
                return trans.response.send_redirect( web.url_for( controller='library_admin',
                                                                  action='browse_library',
                                                                  id=library_id,
                                                                  msg=util.sanitize_text( msg ),
                                                                  messagetype='done' ) )
            return trans.fill_template( '/admin/library/new_folder.mako',
                                        library_id=library_id,
                                        folder=folder,
                                        msg=msg,
                                        messagetype=messagetype )
        elif action == 'information':
            # See if we have any associated templates
            widgets = folder.get_template_widgets( trans )
            if params.get( 'rename_folder_button', False ):
                old_name = folder.name
                new_name = util.restore_text( params.name )
                new_description = util.restore_text( params.description )
                if not new_name:
                    msg = 'Enter a valid name'
                    return trans.fill_template( '/admin/library/folder_info.mako',
                                                folder=folder,
                                                library_id=library_id,
                                                widgets=widgets,
                                                msg=msg,
                                                messagetype='error' )
                else:
                    folder.name = new_name
                    folder.description = new_description
                    folder.flush()
                    msg = "Folder '%s' has been renamed to '%s'" % ( old_name, new_name )
                    return trans.response.send_redirect( web.url_for( controller='library_admin',
                                                                      action='folder',
                                                                      id=id,
                                                                      library_id=library_id,
                                                                      edit_info=True,
                                                                      msg=util.sanitize_text( msg ),
                                                                      messagetype='done' ) )
            return trans.fill_template( '/admin/library/folder_info.mako',
                                        folder=folder,
                                        library_id=library_id,
                                        widgets=widgets,
                                        msg=msg,
                                        messagetype=messagetype )
        elif action == 'delete':
            folder.deleted = True
            folder.flush()
            msg = "Folder '%s' and all of its contents have been marked deleted" % folder.name
            return trans.response.send_redirect( web.url_for( action='browse_library',
                                                              id=library_id,
                                                              msg=util.sanitize_text( msg ),
                                                              messagetype='done' ) )
        elif action =='permissions':
            if params.get( 'update_roles_button', False ):
                # The user clicked the Save button on the 'Associate With Roles' form
                permissions = {}
                for k, v in trans.app.model.Library.permitted_actions.items():
                    in_roles = [ trans.app.model.Role.get( int( x ) ) for x in util.listify( params.get( k + '_in', [] ) ) ]
                    permissions[ trans.app.security_agent.get_action( v.action ) ] = in_roles
                trans.app.security_agent.set_all_library_permissions( folder, permissions )
                folder.refresh()
                msg = "Permissions updated for folder '%s'" % folder.name
                return trans.response.send_redirect( web.url_for( controller='library_admin',
                                                                  action='folder',
                                                                  id=id,
                                                                  library_id=library_id,
                                                                  permissions=True,
                                                                  msg=util.sanitize_text( msg ),
                                                                  messagetype='done' ) )
            return trans.fill_template( '/admin/library/folder_permissions.mako',
                                        folder=folder,
                                        library_id=library_id,
                                        msg=msg,
                                        messagetype=messagetype )
    @web.expose
    @web.require_admin
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
            return trans.response.send_redirect( web.url_for( controller='library_admin',
                                                              action='browse_library',
                                                              id=library_id,
                                                              msg=util.sanitize_text( msg ),
                                                              messagetype='error' ) )
        if action == 'information':
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
            return trans.fill_template( '/admin/library/library_dataset_info.mako',
                                        library_dataset=library_dataset,
                                        library_id=library_id,
                                        msg=msg,
                                        messagetype=messagetype )
        elif action == 'permissions':
            if params.get( 'update_roles_button', False ):
                # The user clicked the Save button on the 'Edit permissions and role associations' form
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
            return trans.fill_template( '/admin/library/library_dataset_permissions.mako',
                                        library_dataset=library_dataset,
                                        library_id=library_id,
                                        msg=msg,
                                        messagetype=messagetype )
    @web.expose
    @web.require_admin
    def library_dataset_dataset_association( self, trans, library_id, folder_id, id=None, **kwd ):
        params = util.Params( kwd )
        msg = util.restore_text( params.get( 'msg', ''  ) )
        messagetype = params.get( 'messagetype', 'done' )
        deleted = util.string_as_bool( params.get( 'deleted', False ) )
        show_deleted = util.string_as_bool( params.get( 'show_deleted', False ) )
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
            replace_dataset = trans.app.model.LibraryDataset.get( int( replace_id ) )
            if not last_used_build:
                last_used_build = replace_dataset.library_dataset_dataset_association.dbkey
        else:
            replace_dataset = None
        # Let's not overwrite the imported datatypes module with the variable datatypes?
        # The built-in 'id' is overwritten in lots of places as well
        ldatatypes = [ dtype_name for dtype_name, dtype_value in trans.app.datatypes_registry.datatypes_by_extension.iteritems() if dtype_value.allow_datatype_change ]
        ldatatypes.sort()
        if params.get( 'new_dataset_button', False ):
            # See if we have any inherited templates, but do not inherit contents.
            info_association, inherited = folder.get_info_association( inherited=True )
            if info_association:
                template_id = str( info_association.template.id )
                widgets = folder.get_template_widgets( trans, get_contents=False )
            else:
                template_id = None
                widgets = []
            upload_option = params.get( 'upload_option', 'upload_file' )
            created_ldda_ids = trans.webapp.controllers[ 'library_dataset' ].upload_dataset( trans,
                                                                                             controller='library_admin',
                                                                                             library_id=library_id,
                                                                                             folder_id=folder_id,
                                                                                             template_id=template_id,
                                                                                             widgets=widgets,
                                                                                             replace_dataset=replace_dataset,
                                                                                             **kwd )
            if created_ldda_ids:
                total_added = len( created_ldda_ids.split( ',' ) )
                if replace_dataset:
                    msg = "Added %d dataset versions to the library dataset '%s' in the folder '%s'." % ( total_added, replace_dataset.name, folder.name )
                else:
                    if not folder.parent:
                        # Libraries have the same name as their root_folder
                        msg = "Added %d datasets to the library '%s' ( each is selected ).  " % ( total_added, folder.name )
                    else:
                        msg = "Added %d datasets to the folder '%s' ( each is selected ).  " % ( total_added, folder.name )
                    msg += "Click the Go button at the bottom of this page to edit the permissions on these datasets if necessary."
                messagetype='done'
            else:
                msg = "Upload failed"
                messagetype='error'
            trans.response.send_redirect( web.url_for( controller='library_admin',
                                                       action='browse_library',
                                                       id=library_id,
                                                       created_ldda_ids=created_ldda_ids,
                                                       msg=util.sanitize_text( msg ),
                                                       messagetype=messagetype ) )
        elif not id or replace_dataset:
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
            roles = trans.app.model.Role.filter( trans.app.model.Role.table.c.deleted==False ).order_by( trans.app.model.Role.c.name ).all()
            # Send the current history to the form to enable importing datasets from history to library
            history = trans.get_history()
            history.refresh()
            return trans.fill_template( '/admin/library/new_dataset.mako',
                                        upload_option=upload_option,
                                        library_id=library_id,
                                        folder_id=folder_id,
                                        replace_id=replace_id,
                                        file_formats=file_formats,
                                        dbkeys=dbkeys,
                                        last_used_build=last_used_build,
                                        roles=roles,
                                        history=history,
                                        widgets=widgets,
                                        msg=msg,
                                        messagetype=messagetype,
                                        replace_dataset=replace_dataset )
        else:
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
        if id:
            # ldda_id specified, display attributes form
            ldda = trans.app.model.LibraryDatasetDatasetAssociation.get( id )
            if not ldda:
                msg = "Invalid LibraryDatasetDatasetAssociation specified, id: %s" % str( id )
                return trans.response.send_redirect( web.url_for( controller='library_admin',
                                                                  action='browse_library',
                                                                  id=library_id,
                                                                  msg=util.sanitize_text( msg ),
                                                                  messagetype='error' ) )
            # See if we have any associated templates
            widgets = ldda.get_template_widgets( trans )
            if action == 'permissions':
                if params.get( 'update_roles_button', False ):
                    permissions = {}
                    accessible = False
                    for k, v in trans.app.model.Dataset.permitted_actions.items():
                        # TODO: need to handle case where a user has the DATASET_MANAGE_PERMISSIONS permission, but not
                        # the DATASET_ACCESS permission, making the former useless.  Need to display a warning message.
                        in_roles = [ trans.app.model.Role.get( x ) for x in util.listify( params.get( k + '_in', [] ) ) ]
                        # At least 1 user must have every role associated with this dataset, or the dataset is inaccessible
                        if v == trans.app.security_agent.permitted_actions.DATASET_ACCESS:
                            if len( in_roles ) > 1:
                                # Get the set of all users that are being associated with the dataset
                                in_roles_set = set()
                                for role in in_roles:
                                    in_roles_set.add( role )
                                users_set = set()
                                for role in in_roles:
                                    for ura in role.users:
                                        users_set.add( ura.user )
                                # Make sure that at least 1 user has every role being associated with the dataset
                                for user in users_set:
                                    user_roles_set = set()
                                    for ura in user.roles:
                                        user_roles_set.add( ura.role )
                                    if in_roles_set.issubset( user_roles_set ):
                                        accessible = True
                                        break
                            else:
                                accessible = True
                        if not accessible and v == trans.app.security_agent.permitted_actions.DATASET_ACCESS:
                            # Don't set the permissions for DATASET_ACCESS if inaccessbile, but set all other permissions
                            # TODO: keep access permissions as they originally were, rather than automatically making public
                            permissions[ trans.app.security_agent.get_action( v.action ) ] = []
                        else:
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
                    if not accessible:
                        msg = "At least 1 user must have every role associated with accessing dataset '%s'. " % ldda.name
                        msg += "The roles you attempted to associate for access would make this dataset inaccessible by everyone, "
                        msg += "so access permissions were not set.  All other permissions were updated for the dataset."
                        messagetype = 'error'
                    else:
                        msg = "Permissions updated for dataset '%s'" % ldda.name
                return trans.fill_template( '/admin/library/ldda_permissions.mako',
                                            ldda=ldda,
                                            library_id=library_id,
                                            msg=msg,
                                            messagetype=messagetype )
            elif action == 'info':
                return trans.fill_template( '/admin/library/ldda_info.mako',
                                            ldda=ldda,
                                            library_id=library_id,
                                            deleted=deleted,
                                            show_deleted=show_deleted,
                                            widgets=widgets,
                                            msg=msg,
                                            messagetype=messagetype )
            elif action == 'edit_info':
                if params.get( 'change', False ):
                    # The user clicked the Save button on the 'Change data type' form
                    if ldda.datatype.allow_datatype_change and trans.app.datatypes_registry.get_datatype_by_extension( params.datatype ).allow_datatype_change:
                        trans.app.datatypes_registry.change_datatype( ldda, params.datatype )
                        trans.app.model.flush()
                        msg = "Data type changed for library dataset '%s'" % ldda.name
                        return trans.fill_template( "/admin/library/ldda_edit_info.mako", 
                                                    ldda=ldda,
                                                    library_id=library_id,
                                                    datatypes=ldatatypes,
                                                    widgets=widgets,
                                                    msg=msg,
                                                    messagetype=messagetype )
                    else:
                        return trans.show_error_message( "You are unable to change datatypes in this manner. Changing %s to %s is not allowed." % ( ldda.extension, params.datatype ) )
                elif params.get( 'save', False ):
                    # The user clicked the Save button on the 'Edit Attributes' form
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
                    return trans.fill_template( "/admin/library/ldda_edit_info.mako", 
                                                ldda=ldda,
                                                library_id=library_id,
                                                datatypes=ldatatypes,
                                                widgets=widgets,
                                                msg=msg,
                                                messagetype=messagetype )
                elif params.get( 'detect', False ):
                    # The user clicked the Auto-detect button on the 'Edit Attributes' form
                    for name, spec in ldda.datatype.metadata_spec.items():
                        # We need to be careful about the attributes we are resetting
                        if name not in [ 'name', 'info', 'dbkey' ]:
                            if spec.get( 'default' ):
                                setattr( ldda.metadata, name, spec.unwrap( spec.get( 'default' ) ) )
                    ldda.datatype.set_meta( ldda )
                    ldda.datatype.after_edit( ldda )
                    trans.app.model.flush()
                    msg = 'Attributes updated for library dataset %s' % ldda.name
                    return trans.fill_template( "/admin/library/ldda_edit_info.mako", 
                                                ldda=ldda,
                                                library_id=library_id,
                                                datatypes=ldatatypes,
                                                widgets=widgets,
                                                msg=msg,
                                                messagetype=messagetype )
                elif params.get( 'delete', False ):
                    ldda.deleted = True
                    ldda.flush()
                    msg = 'Dataset %s has been removed from this library' % ldda.name
                    return trans.fill_template( "/admin/library/ldda_edit_info.mako", 
                                                ldda=ldda,
                                                library_id=library_id,
                                                datatypes=ldatatypes,
                                                widgets=widgets,
                                                msg=msg,
                                                messagetype=messagetype )
                ldda.datatype.before_edit( ldda )
                if "dbkey" in ldda.datatype.metadata_spec and not ldda.metadata.dbkey:
                    # Copy dbkey into metadata, for backwards compatability
                    # This looks like it does nothing, but getting the dbkey
                    # returns the metadata dbkey unless it is None, in which
                    # case it resorts to the old dbkey.  Setting the dbkey
                    # sets it properly in the metadata
                    ldda.metadata.dbkey = ldda.dbkey
                return trans.fill_template( "/admin/library/ldda_edit_info.mako", 
                                            ldda=ldda,
                                            library_id=library_id,
                                            datatypes=ldatatypes,
                                            widgets=widgets,
                                            msg=msg,
                                            messagetype=messagetype )
        elif ids:
            # Multiple ids specfied, display permission form, permissions will be updated for all simultaneously.
            lddas = []
            for id in [ int( id ) for id in ids ]:
                ldda = trans.app.model.LibraryDatasetDatasetAssociation.get( id )
                if ldda is None:
                    msg = 'You specified an invalid LibraryDatasetDatasetAssociation id: %s' %str( id )
                    trans.response.send_redirect( web.url_for( controller='library_admin',
                                                               action='browse_library',
                                                               id=library_id,
                                                               msg=util.sanitize_text( msg ),
                                                               messagetype='error' ) )
                lddas.append( ldda )
            if len( lddas ) < 2:
                msg = 'You must specify at least two datasets on which to modify permissions, ids you sent: %s' % str( ids )
                trans.response.send_redirect( web.url_for( controller='library_admin',
                                                           action='browse_library',
                                                           id=library_id,
                                                           msg=util.sanitize_text( msg ),
                                                           messagetype='error' ) )
            if action == 'permissions':
                if params.get( 'update_roles_button', False ):
                    permissions = {}
                    accessible = False
                    for k, v in trans.app.model.Dataset.permitted_actions.items():
                        # TODO: need to handle case where a user has the DATASET_MANAGE_PERMISSIONS permission, but not
                        # the DATASET_ACCESS permission, making the former useless.  Need to display a warning message.
                        in_roles = [ trans.app.model.Role.get( x ) for x in util.listify( params.get( k + '_in', [] ) ) ]
                        # At least 1 user must have every role associated with this dataset, or the dataset is inaccessible
                        if v == trans.app.security_agent.permitted_actions.DATASET_ACCESS:
                            if len( in_roles ) > 1:
                                # Get the set of all users that are being associated with the dataset
                                in_roles_set = set()
                                for role in in_roles:
                                    in_roles_set.add( role )
                                users_set = set()
                                for role in in_roles:
                                    for ura in role.users:
                                        users_set.add( ura.user )
                                # Make sure that at least 1 user has every role being associated with the dataset
                                for user in users_set:
                                    user_roles_set = set()
                                    for ura in user.roles:
                                        user_roles_set.add( ura.role )
                                    if in_roles_set.issubset( user_roles_set ):
                                        accessible = True
                                        break
                            else:
                                accessible = True
                        if not accessible and v == trans.app.security_agent.permitted_actions.DATASET_ACCESS:
                            # Don't set the permissions for DATASET_ACCESS if inaccessbile, but set all other permissions
                            # TODO: keep access permissions as they originally were, rather than automatically making public
                            permissions[ trans.app.security_agent.get_action( v.action ) ] = []
                        else:
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
                    if not accessible:
                        msg = "At least 1 user must have every role associated with accessing these %d datasets. " % len( lddas )
                        msg += "The roles you attempted to associate for access would make these datasets inaccessible by everyone, "
                        msg += "so access permissions were not set.  All other permissions were updated for the datasets."
                        messagetype = 'error'
                    else:
                        msg = "Permissions have been updated on %d datasets" % len( lddas )
                    return trans.fill_template( "/admin/library/ldda_permissions.mako",
                                                ldda=lddas,
                                                library_id=library_id,
                                                msg=msg,
                                                messagetype=messagetype )
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
                        trans.response.send_redirect( web.url_for( controller='library_admin',
                                                                   action='browse_library',
                                                                   id=library_id,
                                                                   msg=util.sanitize_text( msg ),
                                                                   messagetype='error' ) )
                return trans.fill_template( "/admin/library/ldda_permissions.mako",
                                            ldda=lddas,
                                            library_id=library_id,
                                            msg=msg,
                                            messagetype=messagetype )
    @web.expose
    @web.require_admin
    def add_history_datasets_to_library( self, trans, library_id, folder_id, hda_ids='', **kwd ):
        params = util.Params( kwd )
        msg = util.restore_text( params.get( 'msg', ''  ) )
        messagetype = params.get( 'messagetype', 'done' )
        try:
            folder = trans.app.model.LibraryFolder.get( int( folder_id ) )
        except:
            msg = "Invalid folder id: %s" % str( folder_id )
            return trans.response.send_redirect( web.url_for( controller='library_admin',
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
            return trans.response.send_redirect( web.url_for( controller='library_admin',
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
                        return trans.response.send_redirect( web.url_for( controller='library_admin',
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
                        msg += "Click the Go button at the bottom of this page to edit the permissions on these datasets if necessary."
                    return trans.response.send_redirect( web.url_for( controller='library_admin',
                                                                      action='browse_library',
                                                                      id=library_id,
                                                                      created_ldda_ids=created_ldda_ids,
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
                return trans.fill_template( "/admin/library/new_dataset.mako",
                                            upload_option=upload_option,
                                            library_id=library_id,
                                            folder_id=folder_id,
                                            replace_id=replace_id,
                                            file_formats=file_formats,
                                            dbkeys=dbkeys,
                                            last_used_build=last_used_build,
                                            roles=roles,
                                            history=history,
                                            widgets=widgets,
                                            msg=msg,
                                            messagetype=messagetype )
    @web.expose
    @web.require_admin
    def info_template( self, trans, library_id, id=None, folder_id=None, ldda_id=None, **kwd ):
        params = util.Params( kwd )
        msg = util.restore_text( params.get( 'msg', ''  ) )
        messagetype = params.get( 'messagetype', 'done' )
        if id:
            library_item = trans.app.model.FormDefinition.get( int( id ) )
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
        else:
            library_item = trans.app.model.Library.get( int( library_id ) )
            library_item_desc = 'library'
            response_action = 'browse_library'
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
        if params.get( 'add', False ):
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
                trans.response.send_redirect( web.url_for( controller='library_admin',
                                                           action=response_action,
                                                           id=response_id,
                                                           msg=msg,
                                                           message_type='done' ) )
            return trans.fill_template( '/admin/library/select_info_template.mako',
                                        library_item_name=library_item.name,
                                        library_item_desc=library_item_desc,
                                        library_id=library_id,
                                        folder_id=folder_id,
                                        ldda_id=ldda_id,
                                        forms=forms,
                                        msg=msg,
                                        messagetype=messagetype )
    @web.expose
    @web.require_admin
    def edit_template_info( self, trans, library_id, num_widgets, library_item_id=None, library_item_type=None, **kwd ):
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
            return trans.response.send_redirect( web.url_for( controller='library_admin',
                                                              action='browse_library',
                                                              id=library_id,
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
        return trans.response.send_redirect( web.url_for( controller='library_admin',
                                                          action=library_item_type,
                                                          id=library_item.id,
                                                          library_id=library_id,
                                                          folder_id=folder_id,
                                                          edit_info=True,
                                                          msg=util.sanitize_text( msg ),
                                                          messagetype='done' ) )
    @web.expose
    @web.require_admin
    def download_dataset_from_folder(self, trans, id, library_id=None, **kwd):
        """Catches the dataset id and displays file contents as directed"""
        # id must refer to a LibraryDatasetDatasetAssociation object
        ldda = trans.app.model.LibraryDatasetDatasetAssociation.get( id )
        if not ldda.dataset:
            msg = 'Invalid LibraryDatasetDatasetAssociation id %s received for file downlaod' % str( id )
            return trans.response.send_redirect( web.url_for( controller='library_admin',
                                                              action='browse_library',
                                                              id=library_id,
                                                              msg=util.sanitize_text( msg ),
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
            return trans.response.send_redirect( web.url_for( controller='library_admin',
                                                              action='browse_library',
                                                              id=library_id,
                                                              msg=util.sanitize_text( msg ),
                                                              messagetype='error' ) )
    @web.expose
    @web.require_admin
    def datasets( self, trans, library_id, **kwd ):
        # This method is used by the select list labeled "Perform action on selected datasets"
        # on the admin library browser.
        params = util.Params( kwd )
        msg = util.restore_text( params.get( 'msg', ''  ) )
        messagetype = params.get( 'messagetype', 'done' )
        if params.get( 'action_on_datasets_button', False ):
            if not params.ldda_ids:
                msg = "At least one dataset must be selected for %s" % params.action
                trans.response.send_redirect( web.url_for( controller='library_admin',
                                                           action='browse_library',
                                                           id=library_id,
                                                           msg=util.sanitize_text( msg ),
                                                           messagetype='error' ) )
            ldda_ids = util.listify( params.ldda_ids )
            if params.action == 'edit':
                # We need the folder containing the LibraryDatasetDatasetAssociation(s)
                ldda = trans.app.model.LibraryDatasetDatasetAssociation.get( ldda_ids[0] )
                trans.response.send_redirect( web.url_for( controller='library_admin',
                                                           action='library_dataset_dataset_association',
                                                           library_id=library_id,
                                                           folder_id=ldda.library_dataset.folder.id,
                                                           id=",".join( ldda_ids ),
                                                           permissions=True,
                                                           msg=util.sanitize_text( msg ),
                                                           messagetype=messagetype ) )
            elif params.action == 'delete':
                for id in ldda_ids:
                    ldda = trans.app.model.LibraryDatasetDatasetAssociation.get( id )
                    ldda.deleted = True
                    ldda.flush()
                msg = "The selected datasets have been removed from this library"
                trans.response.send_redirect( web.url_for( controller='library_admin',
                                                           action='browse_library',
                                                           id=library_id,
                                                           show_deleted=False,
                                                           msg=util.sanitize_text( msg ),
                                                           messagetype='done' ) )
            else:
                msg = "Action %s is not yet implemented" % str( params.action )
                trans.response.send_redirect( web.url_for( controller='library_admin',
                                                           action='browse_library',
                                                           id=library_id,
                                                           msg=util.sanitize_text( msg ),
                                                           messagetype='error' ) )
        else:
            trans.response.send_redirect( web.url_for( controller='library_admin',
                                                       action='browse_library',
                                                           id=library_id,
                                                       msg=util.sanitize_text( msg ),
                                                       messagetype=messagetype ) )
    @web.expose
    @web.require_admin
    def delete_library_item( self, trans, library_id, library_item_id, library_item_type ):
        # This action will handle deleting all types of library items.  State is saved for libraries and
        # folders ( i.e., if undeleted, the state of contents of the library or folder will remain, so previously
        # deleted / purged contents will have the same state ).  When a library or folder has been deleted for
        # the amount of time defined in the cleanup_datasets.py script, the library or folder and all of its
        # contents will be purged.  The association between this method and the cleanup_datasets.py script
        # enables clean maintenance of libraries and library dataset disk files.  This is also why the following
        # 3 objects, and not any of the associations ( the cleanup_datasets.py scipot handles everything else ).
        library_item_types = { 'library': trans.app.model.Library,
                               'folder': trans.app.model.LibraryFolder,
                               'library_dataset': trans.app.model.LibraryDataset }
        if library_item_type not in library_item_types:
            msg = 'Bad library_item_type specified: %s' % str( library_item_type )
            messagetype = 'error'
        else:
            if library_item_type == 'library_dataset':
                library_item_desc = 'Dataset'
            else:
                library_item_desc = library_item_type.capitalize()
            library_item = library_item_types[ library_item_type ].get( int( library_item_id ) )
            library_item.deleted = True
            library_item.flush()
            msg = util.sanitize_text( "%s '%s' has been marked deleted" % ( library_item_desc, library_item.name ) )
            messagetype = 'done'
        if library_item_type == 'library':
            return self.browse_libraries( trans, msg=msg, messagetype=messagetype )
        else:
            return self.browse_library( trans, id=library_id , msg=msg, messagetype=messagetype )
    @web.expose
    @web.require_admin
    def undelete_library_item( self, trans, library_id, library_item_id, library_item_type ):
        # This action will handle undeleting all types of library items
        library_item_types = { 'library': trans.app.model.Library,
                               'folder': trans.app.model.LibraryFolder,
                               'library_dataset': trans.app.model.LibraryDataset }
        if library_item_type not in library_item_types:
            msg = 'Bad library_item_type specified: %s' % str( library_item_type )
            messagetype = 'error'
        else:
            if library_item_type == 'library_dataset':
                library_item_desc = 'Dataset'
            else:
                library_item_desc = library_item_type.capitalize()
            library_item = library_item_types[ library_item_type ].get( int( library_item_id ) )
            if library_item.purged:
                msg = '%s %s has been purged, so it cannot be undeleted' % ( library_item_desc, library_item.name )
                messagetype = 'error'
            else:
                library_item.deleted = False
                library_item.flush()
                msg = util.sanitize_text( "%s '%s' has been marked undeleted" % ( library_item_desc, library_item.name ) )
                messagetype = 'done'
        if library_item_type == 'library':
            return self.browse_libraries( trans, msg=msg, messagetype=messagetype )
        else:
            return self.browse_library( trans, id=library_id , msg=msg, messagetype=messagetype )
