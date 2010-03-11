import os, os.path, shutil, urllib, StringIO, re, gzip, tempfile, shutil, zipfile, copy, glob, string
from galaxy.web.base.controller import *
from galaxy import util, jobs
from galaxy.datatypes import sniff
from galaxy.security import RBACAgent
from galaxy.util.json import to_json_string
from galaxy.tools.actions import upload_common
from galaxy.web.controllers.forms import get_all_forms
from galaxy.web.form_builder import SelectField, CheckboxField
from galaxy.model.orm import *
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
                data = trans.sa_session.query( self.app.model.LibraryDatasetDatasetAssociation ).get( id )
                if data.state != state:
                    job_ldda = data
                    while job_ldda.copied_from_library_dataset_dataset_association:
                        job_ldda = job_ldda.copied_from_library_dataset_dataset_association
                    force_history_refresh = False
                    rval[id] = {
                        "state": data.state,
                        "html": unicode( trans.fill_template( "library/common/library_item_info.mako", ldda=data ), 'utf-8' )
                        #"force_history_refresh": force_history_refresh
                    }
        return rval
    @web.expose
    def browse_library( self, trans, cntrller, **kwd ):
        params = util.Params( kwd )
        msg = util.restore_text( params.get( 'msg', ''  ) )
        messagetype = params.get( 'messagetype', 'done' )
        library_id = params.get( 'id', None )
        if not library_id:
            # To handle bots
            msg = "You must specify a library id."
            messagetype = 'error'
        library = trans.sa_session.query( trans.app.model.Library ).get( trans.security.decode_id( library_id ) )
        if not library:
            # To handle bots
            msg = "Invalid library id ( %s )." % str( library_id )
            messagetype = 'error'
        else:
            # If use_panels is True, the library is being accessed via an external link
            # which did not originate from within the Galaxy instance, and the library will
            # be displayed correctly with the mast head.
            use_panels = util.string_as_bool( params.get( 'use_panels', False ) )
            show_deleted = util.string_as_bool( params.get( 'show_deleted', False ) )
            created_ldda_ids = params.get( 'created_ldda_ids', '' )
            hidden_folder_ids = util.listify( params.get( 'hidden_folder_ids', '' ) )
            current_user_roles = trans.get_current_user_roles()
            if created_ldda_ids and not msg:
                msg = "%d datasets are uploading in the background to the library '%s' (each is selected).  "  % \
                    ( len( created_ldda_ids.split( ',' ) ), library.name )
                msg += "Don't navigate away from Galaxy or use the browser's \"stop\" or \"reload\" buttons (on this tab) until the "
                msg += "message \"This job is running\" is cleared from the \"Information\" column below for each selected dataset."
                messagetype = "info"
            return trans.fill_template( '/library/common/browse_library.mako',
                                        cntrller=cntrller,
                                        use_panels=use_panels,
                                        library=library,
                                        created_ldda_ids=created_ldda_ids,
                                        hidden_folder_ids=hidden_folder_ids,
                                        show_deleted=show_deleted,
                                        comptypes=comptypes,
                                        current_user_roles=current_user_roles,
                                        msg=msg,
                                        messagetype=messagetype )
        return trans.response.send_redirect( web.url_for( use_panels=use_panels,
                                                          controller=cntrller,
                                                          action='browse_libraries',
                                                          default_action=params.get( 'default_action', None ),
                                                          msg=util.sanitize_text( msg ),
                                                          messagetype=messagetype ) )
    @web.expose
    def library_info( self, trans, cntrller, **kwd ):
        params = util.Params( kwd )
        msg = util.restore_text( params.get( 'msg', ''  ) )
        messagetype = params.get( 'messagetype', 'done' )
        use_panels = util.string_as_bool( params.get( 'use_panels', False ) )
        library_id = params.get( 'id', None )
        library = trans.sa_session.query( trans.app.model.Library ).get( trans.security.decode_id( library_id ) )
        # See if we have any associated templates
        info_association, inherited = library.get_info_association()
        widgets = library.get_template_widgets( trans )
        current_user_roles = trans.get_current_user_roles()
        show_deleted = util.string_as_bool( params.get( 'show_deleted', False ) )
        if params.get( 'library_info_button', False ):
            old_name = library.name
            new_name = util.restore_text( params.get( 'name', 'No name' ) )
            if not new_name:
                msg = 'Enter a valid name'
                messagetype='error'
            else:
                new_description = util.restore_text( params.get( 'description', '' ) )
                new_synopsis = util.restore_text( params.get( 'synopsis', '' ) )
                if new_synopsis in [ None, 'None' ]:
                    new_synopsis = ''
                library.name = new_name
                library.description = new_description
                library.synopsis = new_synopsis
                # Rename the root_folder
                library.root_folder.name = new_name
                library.root_folder.description = new_description
                trans.sa_session.add_all( ( library, library.root_folder ) )
                trans.sa_session.flush()
                msg = "Library '%s' has been renamed to '%s'" % ( old_name, new_name )
                return trans.response.send_redirect( web.url_for( controller='library_common',
                                                                  action='library_info',
                                                                  cntrller=cntrller,
                                                                  use_panels=use_panels,
                                                                  id=trans.security.encode_id( library.id ),
                                                                  show_deleted=show_deleted,
                                                                  msg=util.sanitize_text( msg ),
                                                                  messagetype='done' ) )
        return trans.fill_template( '/library/common/library_info.mako',
                                    cntrller=cntrller,
                                    use_panels=use_panels,
                                    library=library,
                                    widgets=widgets,
                                    current_user_roles=current_user_roles,
                                    show_deleted=show_deleted,
                                    info_association=info_association,
                                    inherited=inherited,
                                    msg=msg,
                                    messagetype=messagetype )
    @web.expose
    def library_permissions( self, trans, cntrller, **kwd ):
        params = util.Params( kwd )
        msg = util.restore_text( params.get( 'msg', ''  ) )
        messagetype = params.get( 'messagetype', 'done' )
        use_panels = util.string_as_bool( params.get( 'use_panels', False ) )
        library_id = params.get( 'id', None )
        library = trans.sa_session.query( trans.app.model.Library ).get( trans.security.decode_id( library_id ) )
        current_user_roles = trans.get_current_user_roles()
        show_deleted = util.string_as_bool( params.get( 'show_deleted', False ) )
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
            return trans.response.send_redirect( web.url_for( controller='library_common',
                                                              action='library_permissions',
                                                              cntrller=cntrller,
                                                              use_panels=use_panels,
                                                              id=trans.security.encode_id( library.id ),
                                                              show_deleted=show_deleted,
                                                              msg=util.sanitize_text( msg ),
                                                              messagetype='done' ) )
        roles = trans.app.security_agent.get_legitimate_roles( trans, library, cntrller )
        return trans.fill_template( '/library/common/library_permissions.mako',
                                    cntrller=cntrller,
                                    use_panels=use_panels,
                                    library=library,
                                    current_user_roles=current_user_roles,
                                    roles=roles,
                                    show_deleted=show_deleted,
                                    msg=msg,
                                    messagetype=messagetype )
    @web.expose
    def create_folder( self, trans, cntrller, parent_id, library_id, **kwd ):
        params = util.Params( kwd )
        msg = util.restore_text( params.get( 'msg', ''  ) )
        messagetype = params.get( 'messagetype', 'done' )
        show_deleted = util.string_as_bool( params.get( 'show_deleted', False ) )
        use_panels = util.string_as_bool( params.get( 'use_panels', False ) )
        parent_folder = trans.sa_session.query( trans.app.model.LibraryFolder ).get( trans.security.decode_id( parent_id ) )
        if not parent_folder:
            msg = "Invalid parent folder id (%s) specified" % str( parent_id )
            return trans.response.send_redirect( web.url_for( controller='library_common',
                                                              action='browse_library',
                                                              cntrller=cntrller,
                                                              use_panels=use_panels,
                                                              id=library_id,
                                                              show_deleted=show_deleted,
                                                              msg=util.sanitize_text( msg ),
                                                              messagetype='error' ) )
        if params.get( 'new_folder_button', False ):
            new_folder = trans.app.model.LibraryFolder( name=util.restore_text( params.name ),
                                                        description=util.restore_text( params.description ) )
            # We are associating the last used genome build with folders, so we will always
            # initialize a new folder with the first dbkey in util.dbnames which is currently
            # ?    unspecified (?)
            new_folder.genome_build = util.dbnames.default_value
            parent_folder.add_folder( new_folder )
            trans.sa_session.add( new_folder )
            trans.sa_session.flush()
            # New folders default to having the same permissions as their parent folder
            trans.app.security_agent.copy_library_permissions( parent_folder, new_folder )
            # If we have an inheritable template, redirect to the folder_info page so information
            # can be filled in immediately.
            widgets = []
            info_association, inherited = new_folder.get_info_association()
            if info_association and ( not( inherited ) or info_association.inheritable ):
                widgets = new_folder.get_template_widgets( trans )
            if info_association:
                current_user_roles = trans.get_current_user_roles()
                msg = "The new folder named '%s' has been added to the data library.  " % new_folder.name
                msg += "Additional information about this folder may be added using the inherited template."
                return trans.fill_template( '/library/common/folder_info.mako',
                                            cntrller=cntrller,
                                            use_panels=use_panels,
                                            folder=new_folder,
                                            library_id=library_id,
                                            widgets=widgets,
                                            current_user_roles=current_user_roles,
                                            show_deleted=show_deleted,
                                            info_association=info_association,
                                            inherited=inherited,
                                            msg=msg,
                                            messagetype='done' )
            # If not inheritable info_association, redirect to the library.
            msg = "The new folder named '%s' has been added to the data library." % new_folder.name
            return trans.response.send_redirect( web.url_for( controller='library_common',
                                                              action='browse_library',
                                                              cntrller=cntrller,
                                                              use_panels=use_panels,
                                                              id=library_id,
                                                              show_deleted=show_deleted,
                                                              msg=util.sanitize_text( msg ),
                                                              messagetype='done' ) )
        # We do not render any template widgets on creation pages since saving the info_association
        # cannot occur before the associated item is saved.
        return trans.fill_template( '/library/common/new_folder.mako',
                                    cntrller=cntrller,
                                    use_panels=use_panels,
                                    library_id=library_id,
                                    folder=parent_folder,
                                    show_deleted=show_deleted,
                                    msg=msg,
                                    messagetype=messagetype )
    @web.expose
    def folder_info( self, trans, cntrller, id, library_id, **kwd ):
        params = util.Params( kwd )
        msg = util.restore_text( params.get( 'msg', ''  ) )
        messagetype = params.get( 'messagetype', 'done' )
        show_deleted = util.string_as_bool( params.get( 'show_deleted', False ) )
        use_panels = util.string_as_bool( params.get( 'use_panels', False ) )
        folder = trans.sa_session.query( trans.app.model.LibraryFolder ).get( trans.security.decode_id( id ) )
        current_user_roles = trans.get_current_user_roles()
        # See if we have any associated templates
        widgets = []
        info_association, inherited = folder.get_info_association()
        if info_association and ( not( inherited ) or info_association.inheritable ):
            widgets = folder.get_template_widgets( trans )
        if params.get( 'rename_folder_button', False ):
            if cntrller=='library_admin' or trans.app.security_agent.can_modify_library_item( current_user_roles, folder ):
                old_name = folder.name
                new_name = util.restore_text( params.name )
                new_description = util.restore_text( params.description )
                if not new_name:
                    msg = 'Enter a valid name'
                    messagetype='error'
                else:
                    folder.name = new_name
                    folder.description = new_description
                    trans.sa_session.add( folder )
                    trans.sa_session.flush()
                    msg = "Folder '%s' has been renamed to '%s'" % ( old_name, new_name )
                    messagetype='done'
            else:
                msg = "You are not authorized to edit this folder"
                messagetype='error'
        return trans.fill_template( '/library/common/folder_info.mako',
                                    cntrller=cntrller,
                                    use_panels=use_panels,
                                    folder=folder,
                                    library_id=library_id,
                                    widgets=widgets,
                                    current_user_roles=current_user_roles,
                                    show_deleted=show_deleted,
                                    info_association=info_association,
                                    inherited=inherited,
                                    msg=msg,
                                    messagetype=messagetype )
    @web.expose
    def folder_permissions( self, trans, cntrller, id, library_id, **kwd ):
        params = util.Params( kwd )
        msg = util.restore_text( params.get( 'msg', ''  ) )
        messagetype = params.get( 'messagetype', 'done' )
        show_deleted = util.string_as_bool( params.get( 'show_deleted', False ) )
        use_panels = util.string_as_bool( params.get( 'use_panels', False ) )
        folder = trans.sa_session.query( trans.app.model.LibraryFolder ).get( trans.security.decode_id( id ) )
        if not folder:
            msg = "Invalid folder specified, id: %s" % str( id )
            return trans.response.send_redirect( web.url_for( controller='library_common',
                                                              action='browse_library',
                                                              cntrller=cntrller,
                                                              use_panels=use_panels,
                                                              id=library_id,
                                                              show_deleted=show_deleted,
                                                              msg=util.sanitize_text( msg ),
                                                              messagetype='error' ) )
        current_user_roles = trans.get_current_user_roles()
        if params.get( 'update_roles_button', False ):
            # The user clicked the Save button on the 'Associate With Roles' form
            if cntrller == 'library_admin' or trans.app.security_agent.can_manage_library_item( current_user_roles, folder ):
                permissions = {}
                for k, v in trans.app.model.Library.permitted_actions.items():
                    if k != 'LIBRARY_ACCESS':
                        # LIBRARY_ACCESS is a special permission set only at the library level
                        # and it is not inherited.
                        in_roles = [ trans.sa_session.query( trans.app.model.Role ).get( int( x ) ) for x in util.listify( params.get( k + '_in', [] ) ) ]
                        permissions[ trans.app.security_agent.get_action( v.action ) ] = in_roles
                trans.app.security_agent.set_all_library_permissions( folder, permissions )
                trans.sa_session.refresh( folder )
                msg = 'Permissions updated for folder %s' % folder.name
                messagetype='done'
            else:
                msg = "You are not authorized to manage permissions on this folder"
                messagetype = "error"
            return trans.response.send_redirect( web.url_for( controller='library_common',
                                                              action='folder_permissions',
                                                              cntrller=cntrller,
                                                              use_panels=use_panels,
                                                              id=trans.security.encode_id( folder.id ),
                                                              library_id=library_id,
                                                              show_deleted=show_deleted,
                                                              msg=util.sanitize_text( msg ),
                                                              messagetype=messagetype ) )
        # If the library is public all roles are legitimate, but if the library is restricted, only those
        # roles associated with the LIBRARY_ACCESS permission are legitimate.
        library = trans.sa_session.query( trans.app.model.Library ).get( trans.security.decode_id( library_id ) )
        roles = trans.app.security_agent.get_legitimate_roles( trans, library, cntrller )
        return trans.fill_template( '/library/common/folder_permissions.mako',
                                    cntrller=cntrller,
                                    use_panels=use_panels,
                                    folder=folder,
                                    library_id=library_id,
                                    current_user_roles=current_user_roles,
                                    roles=roles,
                                    show_deleted=show_deleted,
                                    msg=msg,
                                    messagetype=messagetype )
    @web.expose
    def ldda_edit_info( self, trans, cntrller, library_id, folder_id, id, **kwd ):
        params = util.Params( kwd )
        msg = util.restore_text( params.get( 'msg', ''  ) )
        messagetype = params.get( 'messagetype', 'done' )
        show_deleted = util.string_as_bool( params.get( 'show_deleted', False ) )
        use_panels = util.string_as_bool( params.get( 'use_panels', False ) )
        ldda = trans.sa_session.query( trans.app.model.LibraryDatasetDatasetAssociation ).get( trans.security.decode_id( id ) )
        if not ldda:
            msg = "Invalid LibraryDatasetDatasetAssociation specified, id: %s" % str( id )
            return trans.response.send_redirect( web.url_for( controller='library_common',
                                                              action='browse_library',
                                                              cntrller=cntrller,
                                                              use_panels=use_panels,
                                                              id=library_id,
                                                              show_deleted=show_deleted,
                                                              msg=util.sanitize_text( msg ),
                                                              messagetype='error' ) )
        dbkey = params.get( 'dbkey', '?' )
        if isinstance( dbkey, list ):
            dbkey = dbkey[0]
        current_user_roles = trans.get_current_user_roles()
        file_formats = [ dtype_name for dtype_name, dtype_value in trans.app.datatypes_registry.datatypes_by_extension.iteritems() if dtype_value.allow_datatype_change ]
        file_formats.sort()
        # See if we have any associated templates
        widgets = []
        info_association, inherited = ldda.get_info_association()
        if info_association and ( not( inherited ) or info_association.inheritable ):
            widgets = ldda.get_template_widgets( trans )
        if params.get( 'change', False ):
            # The user clicked the Save button on the 'Change data type' form
            if cntrller=='library_admin' or trans.app.security_agent.can_modify_library_item( current_user_roles, ldda ):
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
        elif params.get( 'save', False ):
            # The user clicked the Save button on the 'Edit Attributes' form
            if cntrller=='library_admin' or trans.app.security_agent.can_modify_library_item( current_user_roles, ldda ):
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
                    ldda.datatype.after_setting_metadata( ldda )
                    trans.sa_session.flush()
                    msg = 'Attributes updated for library dataset %s' % ldda.name
                    messagetype = 'done'
            else:
                msg = "You are not authorized to edit the attributes of dataset '%s'" % ldda.name
                messagetype = 'error'
        elif params.get( 'detect', False ):
            # The user clicked the Auto-detect button on the 'Edit Attributes' form
            if cntrller=='library_admin' or trans.app.security_agent.can_modify_library_item( current_user_roles, ldda ):
                for name, spec in ldda.datatype.metadata_spec.items():
                    # We need to be careful about the attributes we are resetting
                    if name not in [ 'name', 'info', 'dbkey' ]:
                        if spec.get( 'default' ):
                            setattr( ldda.metadata, name, spec.unwrap( spec.get( 'default' ) ) )
                ldda.datatype.set_meta( ldda )
                ldda.datatype.after_setting_metadata( ldda )
                trans.sa_session.flush()
                msg = 'Attributes updated for library dataset %s' % ldda.name
                messagetype = 'done'
            else:
                msg = "You are not authorized to edit the attributes of dataset '%s'" % ldda.name
                messagetype = 'error'
        if cntrller=='library_admin' or trans.app.security_agent.can_modify_library_item( current_user_roles, ldda ):
            if "dbkey" in ldda.datatype.metadata_spec and not ldda.metadata.dbkey:
                # Copy dbkey into metadata, for backwards compatability
                # This looks like it does nothing, but getting the dbkey
                # returns the metadata dbkey unless it is None, in which
                # case it resorts to the old dbkey.  Setting the dbkey
                # sets it properly in the metadata
                ldda.metadata.dbkey = ldda.dbkey
        return trans.fill_template( "/library/common/ldda_edit_info.mako",
                                    cntrller=cntrller,
                                    use_panels=use_panels,
                                    ldda=ldda,
                                    library_id=library_id,
                                    file_formats=file_formats,
                                    widgets=widgets,
                                    current_user_roles=current_user_roles,
                                    show_deleted=show_deleted,
                                    info_association=info_association,
                                    inherited=inherited,
                                    msg=msg,
                                    messagetype=messagetype )
    @web.expose
    def ldda_info( self, trans, cntrller, library_id, folder_id, id, **kwd ):
        params = util.Params( kwd )
        msg = util.restore_text( params.get( 'msg', ''  ) )
        messagetype = params.get( 'messagetype', 'done' )
        show_deleted = util.string_as_bool( params.get( 'show_deleted', False ) )
        use_panels = util.string_as_bool( params.get( 'use_panels', False ) )
        ldda = trans.sa_session.query( trans.app.model.LibraryDatasetDatasetAssociation ).get( trans.security.decode_id( id ) )
        if not ldda:
            msg = "Invalid LibraryDatasetDatasetAssociation specified, id: %s" % str( id )
            return trans.response.send_redirect( web.url_for( controller='library_common',
                                                              action='browse_library',
                                                              cntrller=cntrller,
                                                              use_panels=use_panels,
                                                              id=library_id,
                                                              show_deleted=show_deleted,
                                                              msg=util.sanitize_text( msg ),
                                                              messagetype='error' ) )
        library = trans.sa_session.query( trans.app.model.Library ).get( trans.security.decode_id( library_id ) )
        # See if we have any associated templates
        widgets = []
        info_association, inherited = ldda.get_info_association()
        if info_association and ( not( inherited ) or info_association.inheritable ):
            widgets = ldda.get_template_widgets( trans )
        current_user_roles = trans.get_current_user_roles()
        return trans.fill_template( '/library/common/ldda_info.mako',
                                    cntrller=cntrller,
                                    use_panels=use_panels,
                                    ldda=ldda,
                                    library=library,
                                    show_deleted=show_deleted,
                                    widgets=widgets,
                                    current_user_roles=current_user_roles,
                                    info_association=info_association,
                                    inherited=inherited,
                                    msg=msg,
                                    messagetype=messagetype )
    @web.expose
    def ldda_permissions( self, trans, cntrller, library_id, folder_id, id, **kwd ):
        params = util.Params( kwd )
        msg = util.restore_text( params.get( 'msg', ''  ) )
        messagetype = params.get( 'messagetype', 'done' )
        show_deleted = util.string_as_bool( params.get( 'show_deleted', False ) )
        use_panels = util.string_as_bool( params.get( 'use_panels', False ) )
        ids = util.listify( id )
        lddas = []
        for id in [ trans.security.decode_id( id ) for id in ids ]:
            ldda = trans.sa_session.query( trans.app.model.LibraryDatasetDatasetAssociation ).get( id )
            if ldda is None:
                msg = 'You specified an invalid LibraryDatasetDatasetAssociation id: %s' %str( id )
                trans.response.send_redirect( web.url_for( controller='library_common',
                                                           action='browse_library',
                                                           cntrller=cntrller,
                                                           use_panels=use_panels,
                                                           id=library_id,
                                                           show_deleted=show_deleted,
                                                           msg=util.sanitize_text( msg ),
                                                           messagetype='error' ) )
            lddas.append( ldda )
        library = trans.sa_session.query( trans.app.model.Library ).get( trans.security.decode_id( library_id ) )
        # If access to the dataset is restricted, then use the roles associated with the DATASET_ACCESS permission to
        # determine the legitimate roles.  If the dataset is public, see if access to the library is restricted.  If
        # it is, use the roles associated with the LIBRARY_ACCESS permission to determine the legitimate roles.  If both
        # the dataset and the library are public, all roles are legitimate.  All of the datasets will have the same
        # permissions at this point.
        ldda = lddas[0]
        if trans.app.security_agent.dataset_is_public( ldda.dataset ):
            # The dataset is public, so check access to the library
            roles = trans.app.security_agent.get_legitimate_roles( trans, library, cntrller )
        else:
            roles = trans.app.security_agent.get_legitimate_roles( trans, ldda.dataset, cntrller )
        if params.get( 'update_roles_button', False ):
            current_user_roles = trans.get_current_user_roles()
            if cntrller=='library_admin' or ( trans.app.security_agent.can_manage_library_item( current_user_roles, ldda ) and \
                                              trans.app.security_agent.can_manage_dataset( current_user_roles, ldda.dataset ) ):
                a = trans.app.security_agent.get_action( trans.app.security_agent.permitted_actions.DATASET_ACCESS.action )
                permissions, in_roles, error, msg = \
                    trans.app.security_agent.derive_roles_from_access( trans, trans.app.security.decode_id( library_id ), cntrller, library=True, **kwd )
                for ldda in lddas:
                    # Set the DATASET permissions on the Dataset.
                    if error:
                        # Keep the original role associations for the DATASET_ACCESS permission on the ldda.
                        permissions[ a ] = ldda.get_access_roles( trans )
                    trans.app.security_agent.set_all_dataset_permissions( ldda.dataset, permissions )
                    trans.sa_session.refresh( ldda.dataset )
                # Set the LIBRARY permissions on the LibraryDataset.  The LibraryDataset and
                # LibraryDatasetDatasetAssociation will be set with the same permissions.
                permissions = {}
                for k, v in trans.app.model.Library.permitted_actions.items():
                    if k != 'LIBRARY_ACCESS':
                        # LIBRARY_ACCESS is a special permission set only at the library level and it is not inherited.
                        in_roles = [ trans.sa_session.query( trans.app.model.Role ).get( x ) for x in util.listify( kwd.get( k + '_in', [] ) ) ]
                        permissions[ trans.app.security_agent.get_action( v.action ) ] = in_roles
                for ldda in lddas:
                    trans.app.security_agent.set_all_library_permissions( ldda.library_dataset, permissions )
                    trans.sa_session.refresh( ldda.library_dataset )
                    # Set the LIBRARY permissions on the LibraryDatasetDatasetAssociation
                    trans.app.security_agent.set_all_library_permissions( ldda, permissions )
                    trans.sa_session.refresh( ldda )
                if error:
                    messagetype = 'error'
                else:
                    msg = 'Permissions have been updated on %d datasets.' % len( lddas )
                    messagetype= 'done'
            else:
                msg = "You are not authorized to change the permissions of dataset '%s'" % ldda.name
                messagetype = 'error'
            return trans.fill_template( "/library/common/ldda_permissions.mako",
                                        cntrller=cntrller,
                                        use_panels=use_panels,
                                        lddas=lddas,
                                        library_id=library_id,
                                        roles=roles,
                                        show_deleted=show_deleted,
                                        msg=msg,
                                        messagetype=messagetype )
        if len( ids ) > 1:
            # Ensure that the permissions across all library items are identical, otherwise we can't update them together.
            check_list = []
            for ldda in lddas:
                permissions = []
                # Check the library level permissions - the permissions on the LibraryDatasetDatasetAssociation
                # will always be the same as the permissions on the associated LibraryDataset.
                for library_permission in trans.app.security_agent.get_permissions( ldda.library_dataset ):
                    if library_permission.action not in permissions:
                        permissions.append( library_permission.action )
                for dataset_permission in trans.app.security_agent.get_permissions( ldda.dataset ):
                    if dataset_permission.action not in permissions:
                        permissions.append( dataset_permission.action )
                permissions.sort()
                if not check_list:
                    check_list = permissions
                if permissions != check_list:
                    msg = 'The datasets you selected do not have identical permissions, so they can not be updated together'
                    trans.response.send_redirect( web.url_for( controller='library_common',
                                                               action='browse_library',
                                                               cntrller=cntrller,
                                                               use_panels=use_panels,
                                                               id=library_id,
                                                               show_deleted=show_deleted,
                                                               msg=util.sanitize_text( msg ),
                                                               messagetype='error' ) )
        # Display permission form, permissions will be updated for all lddas simultaneously.
        return trans.fill_template( "/library/common/ldda_permissions.mako",
                                    cntrller=cntrller,
                                    use_panels=use_panels,
                                    lddas=lddas,
                                    library_id=library_id,
                                    roles=roles,
                                    show_deleted=show_deleted,
                                    msg=msg,
                                    messagetype=messagetype )
    @web.expose
    def upload_library_dataset( self, trans, cntrller, library_id, folder_id, **kwd ):
        params = util.Params( kwd )
        msg = util.restore_text( params.get( 'msg', ''  ) )
        messagetype = params.get( 'messagetype', 'done' )
        deleted = util.string_as_bool( params.get( 'deleted', False ) )
        show_deleted = util.string_as_bool( params.get( 'show_deleted', False ) )
        dbkey = params.get( 'dbkey', '?' )
        if isinstance( dbkey, list ):
            last_used_build = dbkey[0]
        else:
            last_used_build = dbkey
        folder = trans.sa_session.query( trans.app.model.LibraryFolder ).get( trans.security.decode_id( folder_id ) )
        if folder and last_used_build in [ 'None', None, '?' ]:
            last_used_build = folder.genome_build
        replace_id = params.get( 'replace_id', None )
        if replace_id not in [ None, 'None' ]:
            replace_dataset = trans.sa_session.query( trans.app.model.LibraryDataset ).get( trans.security.decode_id( replace_id ) )
            # The name is separately - by the time the new ldda is created,
            # replace_dataset.name will point to the new ldda, not the one it's
            # replacing.
            replace_dataset_name = replace_dataset.name
            if not last_used_build:
                last_used_build = replace_dataset.library_dataset_dataset_association.dbkey
            # Don't allow multiple datasets to be uploaded when replacing a dataset with a new version
            upload_option = 'upload_file'
        else:
            replace_dataset = None
            upload_option = params.get( 'upload_option', 'upload_file' )
        if cntrller == 'library':
            current_user_roles = trans.get_current_user_roles()
        if cntrller == 'library_admin' or \
            ( trans.app.security_agent.can_add_library_item( current_user_roles, folder ) or \
              ( replace_dataset and trans.app.security_agent.can_modify_library_item( current_user_roles, replace_dataset ) ) ):
            if params.get( 'runtool_btn', False ) or params.get( 'ajax_upload', False ):
                # Check to see if the user selected roles to associate with the DATASET_ACCESS permission
                # on the dataset that would cause accessibility issues.
                roles = params.get( 'roles', False )
                error = None
                if roles:
                    vars = dict( DATASET_ACCESS_in=roles )
                    permissions, in_roles, error, msg = \
                        trans.app.security_agent.derive_roles_from_access( trans, trans.app.security.decode_id( library_id ), cntrller, library=True, **vars )
                if error:
                    messagetype = 'error'

                    trans.response.send_redirect( web.url_for( controller='library_common',
                                                                           action='upload_library_dataset',
                                                                           cntrller=cntrller,
                                                                           library_id=library_id,
                                                                           folder_id=folder_id,
                                                                           replace_id=replace_id,
                                                                           upload_option=upload_option,
                                                                           show_deleted=show_deleted,
                                                                           msg=util.sanitize_text( msg ),
                                                                           messagetype='error' ) )

                else:
                    # See if we have any inherited templates, but do not inherit contents.
                    info_association, inherited = folder.get_info_association( inherited=True )
                    if info_association and info_association.inheritable:
                        template_id = str( info_association.template.id )
                        widgets = folder.get_template_widgets( trans, get_contents=False )
                    else:
                        template_id = 'None'
                        widgets = []
                    created_outputs_dict = trans.webapp.controllers[ 'library_common' ].upload_dataset( trans,
                                                                                                   cntrller=cntrller,
                                                                                                   library_id=library_id,
                                                                                                   folder_id=folder_id,
                                                                                                   template_id=template_id,
                                                                                                   widgets=widgets,
                                                                                                   replace_dataset=replace_dataset,
                                                                                                   **kwd )
                    if created_outputs_dict:
                        total_added = len( created_outputs_dict.keys() )
                        ldda_id_list = [ str( v.id ) for k, v in created_outputs_dict.items() ]
                        created_ldda_ids=",".join( ldda_id_list )
                        if replace_dataset:
                            msg = "Added %d dataset versions to the library dataset '%s' in the folder '%s'." % ( total_added, replace_dataset_name, folder.name )
                        else:
                            if not folder.parent:
                                # Libraries have the same name as their root_folder
                                msg = "Added %d datasets to the library '%s' (each is selected).  " % ( total_added, folder.name )
                            else:
                                msg = "Added %d datasets to the folder '%s' (each is selected).  " % ( total_added, folder.name )
                            if cntrller == 'library_admin':
                                msg += "Click the Go button at the bottom of this page to edit the permissions on these datasets if necessary."
                                messagetype='done'
                            else:
                                # Since permissions on all LibraryDatasetDatasetAssociations must be the same at this point, we only need
                                # to check one of them to see if the current user can manage permissions on them.
                                check_ldda = trans.sa_session.query( trans.app.model.LibraryDatasetDatasetAssociation ).get( ldda_id_list[0] )
                                if trans.app.security_agent.can_manage_library_item( current_user_roles, check_ldda ):
                                    if replace_dataset:
                                        default_action = ''
                                    else:
                                        msg += "Click the Go button at the bottom of this page to edit the permissions on these datasets if necessary."
                                        default_action = 'manage_permissions'
                                else:
                                    default_action = 'add'
                                trans.response.send_redirect( web.url_for( controller='library_common',
                                                                           action='browse_library',
                                                                           cntrller=cntrller,
                                                                           id=library_id,
                                                                           default_action=default_action,
                                                                           created_ldda_ids=created_ldda_ids,
                                                                           show_deleted=show_deleted,
                                                                           msg=util.sanitize_text( msg ), 
                                                                           messagetype='done' ) )
                        
                    else:
                        created_ldda_ids = ''
                        msg = "Upload failed"
                        messagetype='error'
                    trans.response.send_redirect( web.url_for( controller='library_common',
                                                               action='browse_library',
                                                               cntrller=cntrller,
                                                               id=library_id,
                                                               created_ldda_ids=created_ldda_ids,
                                                               show_deleted=show_deleted,
                                                               msg=util.sanitize_text( msg ),
                                                               messagetype=messagetype ) )
        # See if we have any inherited templates, but do not inherit contents.
        info_association, inherited = folder.get_info_association( inherited=True )
        if info_association and info_association.inheritable:
            widgets = folder.get_template_widgets( trans, get_contents=False )
        else:
            widgets = []
        upload_option = params.get( 'upload_option', 'upload_file' )
        # No dataset(s) specified, so display the upload form.  Send list of data formats to the form
        # so the "extension" select list can be populated dynamically
        file_formats = trans.app.datatypes_registry.upload_file_formats
        # Send list of genome builds to the form so the "dbkey" select list can be populated dynamically
        def get_dbkey_options( last_used_build ):
            for dbkey, build_name in util.dbnames:
                yield build_name, dbkey, ( dbkey==last_used_build )
        dbkeys = get_dbkey_options( last_used_build )
        # Send list of legitimate roles to the form so the dataset can be associated with 1 or more of them.
        # If the library is public, all active roles are legitimate.  If the library is restricted by the
        # LIBRARY_ACCESS permission, only those roles associated with that permission are legitimate.
        library = trans.sa_session.query( trans.app.model.Library ).get( trans.security.decode_id( library_id ) )
        roles = trans.app.security_agent.get_legitimate_roles( trans, library, cntrller )
        # Send the current history to the form to enable importing datasets from history to library
        history = trans.get_history()
        trans.sa_session.refresh( history )
        # If we're using nginx upload, override the form action
        action = web.url_for( controller='library_common', action='upload_library_dataset' )
        if upload_option == 'upload_file' and trans.app.config.nginx_upload_path:
            # url_for is intentionally not used on the base URL here -
            # nginx_upload_path is expected to include the proxy prefix if the
            # administrator intends for it to be part of the URL.
            action = trans.app.config.nginx_upload_path + '?nginx_redir=' + web.url_for( controller='library_common', action='upload_library_dataset' )
        return trans.fill_template( '/library/common/upload.mako',
                                    cntrller=cntrller,
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
                                    show_deleted=show_deleted,
                                    msg=msg,
                                    messagetype=messagetype )
    def upload_dataset( self, trans, cntrller, library_id, folder_id, replace_dataset=None, **kwd ):
        # Set up the traditional tool state/params
        tool_id = 'upload1'
        tool = trans.app.toolbox.tools_by_id[ tool_id ]
        state = tool.new_state( trans )
        errors = tool.update_state( trans, tool.inputs_by_page[0], state.inputs, kwd )
        tool_params = state.inputs
        dataset_upload_inputs = []
        for input_name, input in tool.inputs.iteritems():
            if input.type == "upload_dataset":
                dataset_upload_inputs.append( input )
        # Library-specific params
        params = util.Params( kwd ) # is this filetoolparam safe?
        show_deleted = util.string_as_bool( params.get( 'show_deleted', False ) )
        library_bunch = upload_common.handle_library_params( trans, params, folder_id, replace_dataset )
        msg = util.restore_text( params.get( 'msg', ''  ) )
        messagetype = params.get( 'messagetype', 'done' )
        server_dir = util.restore_text( params.get( 'server_dir', '' ) )
        if replace_dataset not in [ None, 'None' ]:
            replace_id = trans.security.encode_id( replace_dataset.id )
        else:
            replace_id = None
        upload_option = params.get( 'upload_option', 'upload_file' )
        err_redirect = False
        if upload_option == 'upload_directory':
            if server_dir in [ None, 'None', '' ]:
                err_redirect = True
            if cntrller == 'library_admin':
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
        precreated_datasets = upload_common.get_precreated_datasets( trans, tool_params, trans.app.model.LibraryDatasetDatasetAssociation, controller=cntrller )
        if upload_option == 'upload_file':
            tool_params = upload_common.persist_uploads( tool_params )
            uploaded_datasets = upload_common.get_uploaded_datasets( trans, cntrller, tool_params, precreated_datasets, dataset_upload_inputs, library_bunch=library_bunch )
        elif upload_option == 'upload_directory':
            uploaded_datasets, err_redirect, msg = self.get_server_dir_uploaded_datasets( trans, cntrller, params, full_dir, import_dir_desc, library_bunch, err_redirect, msg )
        elif upload_option == 'upload_paths':
            uploaded_datasets, err_redirect, msg = self.get_path_paste_uploaded_datasets( trans, cntrller, params, library_bunch, err_redirect, msg )
        upload_common.cleanup_unused_precreated_datasets( precreated_datasets )
        if upload_option == 'upload_file' and not uploaded_datasets:
            msg = 'Select a file, enter a URL or enter text'
            err_redirect = True
        if err_redirect:
            trans.response.send_redirect( web.url_for( controller='library_common',
                                                       action='upload_library_dataset',
                                                       cntrller=cntrller,
                                                       library_id=library_id,
                                                       folder_id=folder_id,
                                                       replace_id=replace_id,
                                                       upload_option=upload_option,
                                                       show_deleted=show_deleted,
                                                       msg=util.sanitize_text( msg ),
                                                       messagetype='error' ) )
        json_file_path = upload_common.create_paramfile( trans, uploaded_datasets )
        data_list = [ ud.data for ud in uploaded_datasets ]
        return upload_common.create_job( trans, tool_params, tool, json_file_path, data_list, folder=library_bunch.folder )
    def make_library_uploaded_dataset( self, trans, cntrller, params, name, path, type, library_bunch, in_folder=None ):
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
        uploaded_dataset.data = upload_common.new_upload( trans, cntrller, uploaded_dataset, library_bunch )
        if params.get( 'link_data_only', False ):
            uploaded_dataset.link_data_only = True
            uploaded_dataset.data.file_name = os.path.abspath( path )
            trans.sa_session.add( uploaded_dataset.data )
            trans.sa_session.flush()
        return uploaded_dataset
    def get_server_dir_uploaded_datasets( self, trans, cntrller, params, full_dir, import_dir_desc, library_bunch, err_redirect, msg ):
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
            uploaded_datasets.append( self.make_library_uploaded_dataset( trans, cntrller, params, name, file, 'server_dir', library_bunch ) )
        return uploaded_datasets, None, None
    def get_path_paste_uploaded_datasets( self, trans, cntrller, params, library_bunch, err_redirect, msg ):
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
                    uploaded_datasets.append( self.make_library_uploaded_dataset( trans, cntrller, params, name, path, 'path_paste', library_bunch ) )
                for basedir, dirs, files in os.walk( line ):
                    for file in files:
                        file_path = os.path.abspath( os.path.join( basedir, file ) )
                        if preserve_dirs:
                            in_folder = os.path.dirname( file_path.replace( path, '', 1 ).lstrip( '/' ) )
                        else:
                            in_folder = None
                        uploaded_datasets.append( self.make_library_uploaded_dataset( trans,
                                                                                      cntrller,
                                                                                      params,
                                                                                      file,
                                                                                      file_path,
                                                                                      'path_paste',
                                                                                      library_bunch,
                                                                                      in_folder ) )
        if bad_paths:
            msg = "Invalid paths:<br><ul><li>%s</li></ul>" % "</li><li>".join( bad_paths )
            err_redirect = True
            return None, err_redirect, msg
        return uploaded_datasets, None, None
    @web.expose
    def add_history_datasets_to_library( self, trans, cntrller, library_id, folder_id, hda_ids='', **kwd ):
        params = util.Params( kwd )
        show_deleted = util.string_as_bool( params.get( 'show_deleted', False ) )
        msg = util.restore_text( params.get( 'msg', ''  ) )
        messagetype = params.get( 'messagetype', 'done' )
        folder = trans.sa_session.query( trans.app.model.LibraryFolder ).get( trans.security.decode_id( folder_id ) )
        replace_id = params.get( 'replace_id', None )
        if replace_id:
            replace_dataset = trans.sa_session.query( trans.app.model.LibraryDataset ).get( trans.security.decode_id( replace_id ) )
        else:
            replace_dataset = None
        # See if the current history is empty
        history = trans.get_history()
        trans.sa_session.refresh( history )
        if not history.active_datasets:
            msg = 'Your current history is empty'
            return trans.response.send_redirect( web.url_for( controller='library_common',
                                                              action='browse_library',
                                                              cntrller=cntrller,
                                                              id=library_id,
                                                              show_deleted=show_deleted,
                                                              msg=util.sanitize_text( msg ),
                                                              messagetype='error' ) )
        if params.get( 'add_history_datasets_to_library_button', False ):
            hda_ids = util.listify( hda_ids )
            if hda_ids:
                dataset_names = []
                created_ldda_ids = ''
                for hda_id in hda_ids:
                    hda = trans.sa_session.query( trans.app.model.HistoryDatasetAssociation ).get( trans.security.decode_id( hda_id ) )
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
                        return trans.response.send_redirect( web.url_for( controller='library_common',
                                                                          action='browse_library',
                                                                          cntrller=cntrller,
                                                                          id=library_id,
                                                                          show_deleted=show_deleted,
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
                            msg = "Added %d datasets to the library '%s' (each is selected).  " % ( total_added, folder.name )
                        else:
                            msg = "Added %d datasets to the folder '%s' (each is selected).  " % ( total_added, folder.name )
                        if cntrller == 'library_admin':
                            msg += "Click the Go button at the bottom of this page to edit the permissions on these datasets if necessary."
                        else:
                            # Since permissions on all LibraryDatasetDatasetAssociations must be the same at this point, we only need
                            # to check one of them to see if the current user can manage permissions on them.
                            check_ldda = trans.sa_session.query( trans.app.model.LibraryDatasetDatasetAssociation ).get( trans.security.decode_id( ldda_id_list[0] ) )
                            current_user_roles = trans.get_current_user_roles()
                            if trans.app.security_agent.can_manage_library_item( current_user_roles, check_ldda ):
                                if replace_dataset:
                                    default_action = ''
                                else:
                                    msg += "Click the Go button at the bottom of this page to edit the permissions on these datasets if necessary."
                                    default_action = 'manage_permissions'
                            else:
                                default_action = 'add'
                    return trans.response.send_redirect( web.url_for( controller='library_common',
                                                                      action='browse_library',
                                                                      cntrller=cntrller,
                                                                      id=library_id,
                                                                      created_ldda_ids=created_ldda_ids,
                                                                      show_deleted=show_deleted,
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
                # Send list of legitimate roles to the form so the dataset can be associated with 1 or more of them.
                library = trans.sa_session.query( trans.app.model.Library ).get( trans.security.decode_id( library_id ) )
                roles = trans.app.security_agent.get_legitimate_roles( trans, library, cntrller )
                return trans.fill_template( "/library/common/upload.mako",
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
                                            show_deleted=show_deleted,
                                            msg=msg,
                                            messagetype=messagetype )
    @web.expose
    def download_dataset_from_folder( self, trans, cntrller, id, library_id=None, **kwd ):
        """Catches the dataset id and displays file contents as directed"""
        show_deleted = util.string_as_bool( kwd.get( 'show_deleted', False ) )
        params = util.Params( kwd )        
        use_panels = util.string_as_bool( params.get( 'use_panels', False ) )
        ldda = trans.sa_session.query( trans.app.model.LibraryDatasetDatasetAssociation ).get( trans.security.decode_id( id ) )
        if not ldda.dataset:
            msg = 'Invalid LibraryDatasetDatasetAssociation id %s received for file download' % str( id )
            messagetype = 'error'
        else:
            composite_extensions = trans.app.datatypes_registry.get_composite_extensions( )
            ext = ldda.extension
            if ext in composite_extensions: 
                # is composite - must return a zip of contents and the html file itself - ugh - should be reversible at upload!
                # use act_on_multiple_datasets( self, trans, cntrller, library_id, ldda_ids='', **kwd ) since it does what we need
                kwd['do_action'] = 'zip'
                return self.act_on_multiple_datasets( trans, cntrller, library_id, ldda_ids=[id,], **kwd )
            else:
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
        return trans.response.send_redirect( web.url_for( controller='library_common',
                                                          action='browse_library',
                                                          cntrller=cntrller,
                                                          use_panels=use_panels,
                                                          id=library_id,
                                                          show_deleted=show_deleted,
                                                          msg=util.sanitize_text( msg ),
                                                          messagetype='error' ) )
    @web.expose
    def library_dataset_info( self, trans, cntrller, id, library_id, **kwd ):
        params = util.Params( kwd )
        msg = util.restore_text( params.get( 'msg', ''  ) )
        messagetype = params.get( 'messagetype', 'done' )
        show_deleted = util.string_as_bool( params.get( 'show_deleted', False ) )
        use_panels = util.string_as_bool( params.get( 'use_panels', False ) )
        library_dataset = trans.sa_session.query( trans.app.model.LibraryDataset ).get( trans.security.decode_id( id ) )
        if not library_dataset:
            msg = "Invalid library dataset specified, id: %s" %str( id )
            return trans.response.send_redirect( web.url_for( controller='library_common',
                                                              action='browse_library',
                                                              cntrller=cntrller,
                                                              use_panels=use_panels,
                                                              id=library_id,
                                                              show_deleted=show_deleted,
                                                              msg=util.sanitize_text( msg ),
                                                              messagetype='error' ) )
        current_user_roles = trans.get_current_user_roles()
        # See if we have any associated templates
        widgets = []
        info_association, inherited = library_dataset.library_dataset_dataset_association.get_info_association()
        if info_association and ( not( inherited ) or info_association.inheritable ):
            widgets = library_dataset.library_dataset_dataset_association.get_template_widgets( trans )
        if params.get( 'edit_attributes_button', False ):
            if cntrller=='library_admin' or trans.app.security_agent.can_modify_library_item( current_user_roles, library_dataset ):
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
        return trans.fill_template( '/library/common/library_dataset_info.mako',
                                    cntrller=cntrller,
                                    use_panels=use_panels,
                                    library_dataset=library_dataset,
                                    library_id=library_id,
                                    current_user_roles=current_user_roles,
                                    info_association=info_association,
                                    inherited=inherited,
                                    widgets=widgets,
                                    show_deleted=show_deleted,
                                    msg=msg,
                                    messagetype=messagetype )
    @web.expose
    def library_dataset_permissions( self, trans, cntrller, id, library_id, **kwd ):
        params = util.Params( kwd )
        msg = util.restore_text( params.get( 'msg', ''  ) )
        messagetype = params.get( 'messagetype', 'done' )
        show_deleted = util.string_as_bool( params.get( 'show_deleted', False ) )
        use_panels = util.string_as_bool( params.get( 'use_panels', False ) )
        library_dataset = trans.sa_session.query( trans.app.model.LibraryDataset ).get( id )
        if not library_dataset:
            msg = "Invalid library dataset specified, id: %s" %str( id )
            return trans.response.send_redirect( web.url_for( controller='library_common',
                                                              action='browse_library',
                                                              cntrller=cntrller,
                                                              use_panels=use_panels,
                                                              id=library_id,
                                                              show_deleted=show_deleted,
                                                              msg=util.sanitize_text( msg ),
                                                              messagetype='error' ) )
        current_user_roles = trans.get_current_user_roles()
        if params.get( 'update_roles_button', False ):
            if cntrller == 'library_admin' or trans.app.security_agent.can_manage_library_item( current_user_roles, library_dataset ):
                # The user clicked the Save button on the 'Associate With Roles' form
                permissions = {}
                for k, v in trans.app.model.Library.permitted_actions.items():
                    if k != 'LIBRARY_ACCESS':
                        # LIBRARY_ACCESS is a special permission set only at the library level
                        # and it is not inherited.
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
        library = trans.sa_session.query( trans.app.model.Library ).get( trans.security.decode_id( library_id ) )
        roles = trans.app.security_agent.get_legitimate_roles( trans, library, cntrller )
        return trans.fill_template( '/library/common/library_dataset_permissions.mako',
                                    cntrller=cntrller,
                                    use_panels=use_panels,
                                    library_dataset=library_dataset,
                                    library_id=library_id,
                                    roles=roles,
                                    current_user_roles=current_user_roles,
                                    show_deleted=show_deleted,
                                    msg=msg,
                                    messagetype=messagetype )
    @web.expose
    def act_on_multiple_datasets( self, trans, cntrller, library_id, ldda_ids='', **kwd ):
        # Perform an action on a list of library datasets.
        params = util.Params( kwd )
        msg = util.restore_text( params.get( 'msg', ''  ) )
        messagetype = params.get( 'messagetype', 'done' )
        show_deleted = util.string_as_bool( params.get( 'show_deleted', False ) )
        use_panels = util.string_as_bool( params.get( 'use_panels', False ) )
        action = params.get( 'do_action', None )
        if not ldda_ids:
            msg = "You must select at least one dataset"
            messagetype = 'error'
        elif not action:
            msg = "You must select an action to perform on selected datasets"
            messagetype = 'error'
        else:
            ldda_ids = util.listify( ldda_ids )
            if action == 'import_to_history':
                history = trans.get_history()
                if history is None:
                    # Must be a bot sending a request without having a history.
                    msg = "You do not have a current history"
                    return trans.response.send_redirect( web.url_for( controller='library_common',
                                                                      action='browse_library',
                                                                      cntrller=cntrller,
                                                                      use_panels=use_panels,
                                                                      id=library_id,
                                                                      show_deleted=show_deleted,
                                                                      msg=util.sanitize_text( msg ),
                                                                      messagetype='error' ) )
                total_imported_lddas = 0
                msg = ''
                messagetype = 'done'
                for ldda_id in ldda_ids:
                    ldda = trans.sa_session.query( trans.app.model.LibraryDatasetDatasetAssociation ).get( trans.security.decode_id( ldda_id ) )
                    if ldda.dataset.state in [ 'new', 'upload', 'queued', 'running', 'empty', 'discarded' ]:
                        msg += "Cannot import dataset (%s) since it's state is (%s).  " % ( ldda.name, ldda.dataset.state )
                        messagetype = 'error'
                    elif ldda.dataset.state in [ 'ok', 'error' ]:
                        hda = ldda.to_history_dataset_association( target_history=history, add_to_history=True )
                        total_imported_lddas += 1
                if total_imported_lddas:
                    trans.sa_session.add( history )
                    trans.sa_session.flush()
                    msg += "%i dataset(s) have been imported into your history.  " % total_imported_lddas
            elif action == 'manage_permissions':
                # We need the folder containing the LibraryDatasetDatasetAssociation(s)
                ldda = trans.sa_session.query( trans.app.model.LibraryDatasetDatasetAssociation ).get( trans.security.decode_id( ldda_ids[0] ) )
                trans.response.send_redirect( web.url_for( controller='library_common',
                                                           action='ldda_permissions',
                                                           cntrller=cntrller,
                                                           use_panels=use_panels,
                                                           library_id=library_id,
                                                           folder_id=trans.security.encode_id( ldda.library_dataset.folder.id ),
                                                           id=",".join( ldda_ids ),
                                                           show_deleted=show_deleted,
                                                           msg=util.sanitize_text( msg ),
                                                           messagetype=messagetype ) )
            elif action == 'delete':
                for ldda_id in ldda_ids:
                    ldda = trans.sa_session.query( trans.app.model.LibraryDatasetDatasetAssociation ).get( trans.security.decode_id( ldda_id ) )
                    # Do not delete the association, just delete the library_dataset.  The
                    # cleanup_datasets.py script handles everything else.
                    ld = ldda.library_dataset
                    ld.deleted = True
                    trans.sa_session.add( ld )
                trans.sa_session.flush()
                msg = "The selected datasets have been removed from this data library"
            else:
                error = False
                killme = string.punctuation + string.whitespace
    		trantab = string.maketrans(killme,'_'*len(killme))
                try:
                    outext = 'zip'
                    if action == 'zip':
                        # Can't use mkstemp - the file must not exist first
                        tmpd = tempfile.mkdtemp()
                        tmpf = os.path.join( tmpd, 'library_download.' + action )
                        if ziptype == '64':
                            archive = zipfile.ZipFile( tmpf, 'w', zipfile.ZIP_DEFLATED, True )
                        else:
                            archive = zipfile.ZipFile( tmpf, 'w', zipfile.ZIP_DEFLATED )
                        archive.add = lambda x, y: archive.write( x, y.encode('CP437') )
                    elif action == 'tgz':
                        archive = util.streamball.StreamBall( 'w|gz' )
                        outext = 'tgz'
                    elif action == 'tbz':
                        archive = util.streamball.StreamBall( 'w|bz2' )
                        outext = 'tbz2'
                except (OSError, zipfile.BadZipFile):
                    error = True
                    log.exception( "Unable to create archive for download" )
                    msg = "Unable to create archive for download, please report this error"
                    messagetype = 'error'
                if not error:
                    composite_extensions = trans.app.datatypes_registry.get_composite_extensions( )
                    seen = []
                    current_user_roles = trans.get_current_user_roles()
                    for ldda_id in ldda_ids:
                        ldda = trans.sa_session.query( trans.app.model.LibraryDatasetDatasetAssociation ).get( trans.security.decode_id( ldda_id ) )
                        if not ldda \
                            or not trans.app.security_agent.can_access_dataset( current_user_roles, ldda.dataset ) \
                            or ldda.dataset.state in [ 'new', 'upload', 'queued', 'running', 'empty', 'discarded' ]:
                            continue
                        ext = ldda.extension
                        is_composite = ext in composite_extensions
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
    			path = path.translate(trantab)
                        while path in seen:
                            path += '_'
                        seen.append( path )
                        zpath = os.path.split(path)[-1] # comes as base_name/fname
                        outfname,zpathext = os.path.splitext(zpath)
                        if is_composite: # need to add all the components from the extra_files_path to the zip
                            if zpathext == '':
                                zpath = '%s.html' % zpath # fake the real nature of the html file 
                            try:
                                archive.add(ldda.dataset.file_name,zpath) # add the primary of a composite set
                            except IOError:
                                error = True
                                log.exception( "Unable to add composite parent %s to temporary library download archive" % ldda.dataset.file_name)
                                msg = "Unable to create archive for download, please report this error"
                                messagetype = 'error'
                                continue                                
                            flist = glob.glob(os.path.join(ldda.dataset.extra_files_path,'*.*')) # glob returns full paths
                            for fpath in flist:
                                efp,fname = os.path.split(fpath)
               			fname = fname.translate(trantab)
                                try:
                                    archive.add( fpath,fname )
                                except IOError:
                                    error = True
                                    log.exception( "Unable to add %s to temporary library download archive %s" % (fname,outfname))
                                    msg = "Unable to create archive for download, please report this error"
                                    messagetype = 'error'
                                    continue
                        else: # simple case
                            try:
                                archive.add( ldda.dataset.file_name, path )
                            except IOError:
                                error = True
                                log.exception( "Unable to write %s to temporary library download archive" % ldda.dataset.file_name)
                                msg = "Unable to create archive for download, please report this error"
                                messagetype = 'error'                            
                    if not error:    
                        if action == 'zip':
                            archive.close()
                            tmpfh = open( tmpf )
                            # clean up now
                            try:
                                os.unlink( tmpf )
                                os.rmdir( tmpd )
                            except OSError:
                                error = True
                                log.exception( "Unable to remove temporary library download archive and directory" )
                                msg = "Unable to create archive for download, please report this error"
                                messagetype = 'error'
                            if not error:
                                trans.response.set_content_type( "application/x-zip-compressed" )
                                trans.response.headers[ "Content-Disposition" ] = "attachment; filename=%s.%s" % (outfname,outext)
                                return tmpfh
                        else:
                            trans.response.set_content_type( "application/x-tar" )
                            trans.response.headers[ "Content-Disposition" ] = "attachment; filename=%s.%s" % (outfname,outext)
                            archive.wsgi_status = trans.response.wsgi_status()
                            archive.wsgi_headeritems = trans.response.wsgi_headeritems()
                            return archive.stream
        return trans.response.send_redirect( web.url_for( controller='library_common',
                                                          action='browse_library',
                                                          cntrller=cntrller,
                                                          use_panels=use_panels,
                                                          id=library_id,
                                                          show_deleted=show_deleted,
                                                          msg=util.sanitize_text( msg ),
                                                          messagetype=messagetype ) )
    def get_item_and_stuff( self, trans, item_type, library_id, folder_id, ldda_id ):
        # Return an item, description, action and an id based on the item_type.
        if item_type == 'library':
            item = trans.sa_session.query( trans.app.model.Library ).get( trans.security.decode_id( library_id ) )
            item_desc = 'data library'
            action = 'library_info'
            id = library_id
        elif item_type == 'folder':
            item = trans.sa_session.query( trans.app.model.LibraryFolder ).get( trans.security.decode_id( folder_id ) )
            item_desc = 'folder'
            action = 'folder_info'
            id = folder_id
        elif item_type == 'ldda':
            item = trans.sa_session.query( trans.app.model.LibraryDatasetDatasetAssociation ).get( trans.security.decode_id( ldda_id ) )
            item_desc = 'dataset'
            action = 'ldda_edit_info'
            id = ldda_id
        else:
            msg = "Invalid library item type ( %s )" % str( item_type )
            return trans.response.send_redirect( web.url_for( controller='library_common',
                                                              action='browse_library',
                                                              cntrller=cntrller,
                                                              id=library_id,
                                                              show_deleted=show_deleted,
                                                              msg=util.sanitize_text( msg ),
                                                              messagetype='error' ) )
        return item, item_desc, action, id
    @web.expose
    def add_template( self, trans, cntrller, item_type, library_id, folder_id=None, ldda_id=None, **kwd ):
        # Template can only be added to a Library, Folder or LibraryDatasetDatasetAssociation.
        forms = get_all_forms( trans,
                               filter=dict( deleted=False ),
                               form_type=trans.app.model.FormDefinition.types.LIBRARY_INFO_TEMPLATE )
        if not forms:
            msg = "There are no forms on which to base the template, so create a form and then add the template."
            trans.response.send_redirect( web.url_for( controller='forms',
                                                       action='new',
                                                       msg=msg,
                                                       messagetype='done',
                                                       form_type=trans.app.model.FormDefinition.types.LIBRARY_INFO_TEMPLATE ) )
        else:
            params = util.Params( kwd )
            show_deleted = util.string_as_bool( params.get( 'show_deleted', False ) )
            use_panels = util.string_as_bool( params.get( 'use_panels', False ) )
            msg = util.restore_text( params.get( 'msg', ''  ) )
            action = ''
            messagetype = params.get( 'messagetype', 'done' )
            item, item_desc, action, id = self.get_item_and_stuff( trans, item_type, library_id, folder_id, ldda_id )
            # If the inheritable checkbox is checked, the param will be in the request
            inheritable = CheckboxField.is_checked( params.get( 'inheritable', '' ) )
            if params.get( 'add_template_button', False ):
                form_id = params.get( 'form_id', 'none' )
                if form_id not in [ None, 'None', 'none' ]:
                    form = trans.sa_session.query( trans.app.model.FormDefinition ).get( trans.security.decode_id( form_id ) )
                    form_values = trans.app.model.FormValues( form, [] )
                    trans.sa_session.add( form_values )
                    trans.sa_session.flush()
                    if item_type == 'library':
                        assoc = trans.app.model.LibraryInfoAssociation( item, form, form_values, inheritable=inheritable )
                    elif item_type == 'folder':
                        assoc = trans.app.model.LibraryFolderInfoAssociation( item, form, form_values, inheritable=inheritable )
                    elif item_type == 'ldda':
                        assoc = trans.app.model.LibraryDatasetDatasetInfoAssociation( item, form, form_values )
                    trans.sa_session.add( assoc )
                    trans.sa_session.flush()
                    msg = 'A template based on the form "%s" has been added to this %s.' % ( form.name, item_desc )
                    trans.response.send_redirect( web.url_for( controller='library_common',
                                                               action=action,
                                                               cntrller=cntrller,
                                                               use_panels=use_panels,
                                                               library_id=library_id,
                                                               folder_id=folder_id,
                                                               id=id,
                                                               show_deleted=show_deleted,
                                                               msg=msg,
                                                               messagetype='done' ) )
                else:
                    msg = "Select a form on which to base the template."
                    messagetype = "error"
        def generate_template_stuff( trans, forms, form_id ):
            # Returns the following:
            # - a list of template ids
            # - a list of dictionaries whose keys are template ids and whose values are templates widgets.
            #   The dictionary built using the received forms param
            # - a select list whose options are templates
            template_ids = [ 'none' ]
            widgets = []
            for form in forms:
                template_ids.append( trans.security.encode_id( form.id ) )
            template_select_list = SelectField( 'form_id', 
                                    refresh_on_change=True, 
                                    refresh_on_change_values=template_ids[1:] )
            if form_id == 'none':
                template_select_list.add_option( 'Select one', 'none', selected=True )
                decoded_form_id = None
            else:
                template_select_list.add_option( 'Select one', 'none' )
                decoded_form_id = trans.security.decode_id( form_id )
            for form in forms:
                if decoded_form_id and decoded_form_id == form.id:
                    template_select_list.add_option( form.name, trans.security.encode_id( form.id ), selected=True )
                    widgets = form.get_widgets( trans.user )
                else:
                    template_select_list.add_option( form.name, trans.security.encode_id( form.id ) )
            return template_ids, widgets, template_select_list
        if params.get( 'refresh', False ):
            template_ids, widgets, template_select_list = generate_template_stuff( trans, forms, kwd.get( 'form_id' ) )
        else:
            template_ids, widgets, template_select_list = generate_template_stuff( trans, forms, 'none' )
        return trans.fill_template( '/library/common/select_template.mako',
                                    cntrller=cntrller,
                                    use_panels=use_panels,
                                    item_name=item.name,
                                    item_desc=item_desc,
                                    item_type=item_type,
                                    library_id=library_id,
                                    folder_id=folder_id,
                                    ldda_id=ldda_id,
                                    template_ids=template_ids,
                                    widgets=widgets,
                                    template_select_list=template_select_list,
                                    inheritable_checked=inheritable,
                                    show_deleted=show_deleted,
                                    msg=msg,
                                    messagetype=messagetype )
    @web.expose
    def manage_template_inheritance( self, trans, cntrller, item_type, library_id, folder_id=None, ldda_id=None, **kwd ):
        params = util.Params( kwd )
        show_deleted = util.string_as_bool( params.get( 'show_deleted', False ) )
        use_panels = util.string_as_bool( params.get( 'use_panels', False ) )
        msg = util.restore_text( params.get( 'msg', ''  ) )
        messagetype = params.get( 'messagetype', 'done' )
        item, item_desc, action, id = self.get_item_and_stuff( trans, item_type, library_id, folder_id, ldda_id )
        info_association, inherited = item.get_info_association( restrict=True )
        if info_association:
            if info_association.inheritable:
                msg = "The template for this %s will no longer be inherited to contained folders and datasets." % item_desc
            else:
                msg = "The template for this %s will now be inherited to contained folders and datasets." % item_desc
            info_association.inheritable = not( info_association.inheritable )
            trans.sa_session.add( info_association )
            trans.sa_session.flush()
        return trans.response.send_redirect( web.url_for( controller='library_common',
                                                          action=action,
                                                          cntrller=cntrller,
                                                          use_panels=use_panels,
                                                          library_id=library_id,
                                                          folder_id=folder_id,
                                                          id=id,
                                                          show_deleted=show_deleted,
                                                          msg=util.sanitize_text( msg ),
                                                          messagetype='done' ) )
    @web.expose
    def edit_template( self, trans, cntrller, item_type, library_id, folder_id=None, ldda_id=None, edited=False, **kwd ):
        # Edit the template itself, keeping existing field contents, if any.
        params = util.Params( kwd )
        show_deleted = util.string_as_bool( params.get( 'show_deleted', False ) )
        use_panels = util.string_as_bool( params.get( 'use_panels', False ) )
        msg = util.restore_text( params.get( 'msg', ''  ) )
        messagetype = params.get( 'messagetype', 'done' )
        item, item_desc, action, id = self.get_item_and_stuff( trans, item_type, library_id, folder_id, ldda_id )
        # An info_association must exist at this point
        info_association, inherited = item.get_info_association( restrict=True )
        template = info_association.template
        info = info_association.info
        form_values = trans.sa_session.query( trans.app.model.FormValues ).get( info.id )
        if edited:
            # The form on which the template is based has been edited, so we need to update the
            # info_association with the current form
            fdc = trans.sa_session.query( trans.app.model.FormDefinitionCurrent ).get( template.form_definition_current_id )
            info_association.template = fdc.latest_form
            trans.sa_session.add( info_association )
            trans.sa_session.flush()
            msg = "The template for this %s has been updated with your changes." % item_desc
            return trans.response.send_redirect( web.url_for( controller='library_common',
                                                              action=action,
                                                              cntrller=cntrller,
                                                              use_panels=use_panels,
                                                              library_id=library_id,
                                                              folder_id=folder_id,
                                                              id=id,
                                                              show_deleted=show_deleted,
                                                              msg=util.sanitize_text( msg ),
                                                              messagetype='done' ) )
        # "template" is a FormDefinition, so since we're changing it, we need to use the latest version of it.
        vars = dict( id=trans.security.encode_id( template.form_definition_current_id ),
                     response_redirect=web.url_for( controller='library_common',
                                                    action='edit_template',
                                                    cntrller=cntrller,
                                                    use_panels=use_panels,
                                                    item_type=item_type,
                                                    library_id=library_id,
                                                    folder_id=folder_id,
                                                    ldda_id=ldda_id,
                                                    edited=True,
                                                    **kwd ) )
        return trans.response.send_redirect( web.url_for( controller='forms', action='edit', **vars ) )
    @web.expose
    def edit_template_info( self, trans, cntrller, item_type, library_id, num_widgets, folder_id=None, ldda_id=None, **kwd ):
        # Edit the contents of the template fields without altering the template itself.
        params = util.Params( kwd )
        show_deleted = util.string_as_bool( params.get( 'show_deleted', False ) )
        use_panels = util.string_as_bool( params.get( 'use_panels', False ) )
        msg = util.restore_text( params.get( 'msg', ''  ) )
        messagetype = params.get( 'messagetype', 'done' )
        item, item_desc, action, id = self.get_item_and_stuff( trans, item_type, library_id, folder_id, ldda_id )
        # Save updated template field contents
        field_contents = []
        for index in range( int( num_widgets ) ):
            field_contents.append( util.restore_text( params.get( 'field_%i' % ( index ), ''  ) ) )
        if field_contents:
            # Since information templates are inherited, the template fields can be displayed on the information
            # page for a folder or ldda when it has no info_association object.  If the user has added
            # field contents on an inherited template via a parent's info_association, we'll need to create a new
            # form_values and info_association for the current object.  The value for the returned inherited variable
            # is not applicable at this level.
            info_association, inherited = item.get_info_association( restrict=True )
            if info_association:
                template = info_association.template
                info = info_association.info
                form_values = trans.sa_session.query( trans.app.model.FormValues ).get( info.id )
                # Update existing content only if it has changed
                if form_values.content != field_contents:
                    form_values.content = field_contents
                    trans.sa_session.add( form_values )
                    trans.sa_session.flush()
            else:
                # Inherit the next available info_association so we can get the template
                info_association, inherited = item.get_info_association()
                template = info_association.template
                # Create a new FormValues object
                form_values = trans.app.model.FormValues( template, field_contents )
                trans.sa_session.add( form_values )
                trans.sa_session.flush()
                # Create a new info_association between the current library item and form_values
                if item_type == 'folder':
                    # A LibraryFolder is a special case because if it inherited the template from it's parent,
                    # we want to set inheritable to True for it's info_association.  This allows for the default
                    # inheritance to be False for each level in the Library hierarchy unless we're creating a new
                    # level in the hierarchy, in which case we'll inherit the "inheritable" setting from the parent
                    # level.
                    info_association = trans.app.model.LibraryFolderInfoAssociation( item, template, form_values, inheritable=inherited )
                    trans.sa_session.add( info_association )
                    trans.sa_session.flush()
                elif item_type == 'ldda':
                    # TODO: Currently info_associations at teh ldda level are not inheritable to the associated LibraryDataset.
                    # We need to figure out if this is optimal.
                    info_association = trans.app.model.LibraryDatasetDatasetInfoAssociation( item, template, form_values )
                    trans.sa_session.add( info_association )
                    trans.sa_session.flush()
        msg = 'The information has been updated.'
        return trans.response.send_redirect( web.url_for( controller='library_common',
                                                          action=action,
                                                          cntrller=cntrller,
                                                          use_panels=use_panels,
                                                          library_id=library_id,
                                                          folder_id=folder_id,
                                                          id=id,
                                                          show_deleted=show_deleted,
                                                          msg=util.sanitize_text( msg ),
                                                          messagetype='done' ) )
    @web.expose
    def delete_template( self, trans, cntrller, item_type, library_id, id=None, folder_id=None, ldda_id=None, **kwd ):
        # Only adding a new template to a library or folder is currently allowed.  Editing an existing template is
        # a future enhancement.
        params = util.Params( kwd )
        show_deleted = util.string_as_bool( params.get( 'show_deleted', False ) )
        use_panels = util.string_as_bool( params.get( 'use_panels', False ) )
        msg = util.restore_text( params.get( 'msg', ''  ) )
        messagetype = params.get( 'messagetype', 'done' )
        item, item_desc, action, id = self.get_item_and_stuff( trans, item_type, library_id, folder_id, ldda_id )
        info_association, inherited = item.get_info_association()
        if not info_association:
            msg = "There is no template for this %s" % item_type
            messagetype = 'error'
        else:
            info_association.deleted = True
            trans.sa_session.add( info_association )
            trans.sa_session.flush()
            msg = 'The template for this %s has been deleted.' % item_type
            messagetype = 'done'
        return trans.response.send_redirect( web.url_for( controller='library_common',
                                                          action=action,
                                                          cntrller=cntrller,
                                                          use_panels=use_panels,
                                                          library_id=library_id,
                                                          folder_id=folder_id,
                                                          id=id,
                                                          show_deleted=show_deleted,
                                                          msg=util.sanitize_text( msg ),
                                                          messagetype=messagetype ) )

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
def branch_deleted( folder ):
    # Return True if a folder belongs to a branc that has been deleted
    if folder.deleted:
        return True
    if folder.parent:
        return branch_deleted( folder.parent )
    return False
