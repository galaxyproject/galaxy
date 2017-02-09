import glob
import logging
import operator
import os
import os.path
import string
import sys
import tarfile
import tempfile
import urllib
import urllib2
import zipfile
from json import dumps, loads

from markupsafe import escape
from sqlalchemy import and_, false
from sqlalchemy.orm import eagerload_all

from galaxy import util, web
from galaxy.security import Action
from galaxy.tools.actions import upload_common
from galaxy.tools.parameters import populate_state
from galaxy.util import inflector, unicodify, FILENAME_VALID_CHARS
from galaxy.util.streamball import StreamBall
from galaxy.web.base.controller import BaseUIController, UsesFormDefinitionsMixin, UsesExtendedMetadataMixin, UsesLibraryMixinItems
from galaxy.web.form_builder import AddressField, CheckboxField, SelectField, build_select_field

# Whoosh is compatible with Python 2.5+ Try to import Whoosh and set flag to indicate whether tool search is enabled.
try:
    import whoosh.index
    from whoosh.fields import Schema, STORED, TEXT
    from whoosh.scoring import BM25F
    from whoosh.qparser import MultifieldParser
    whoosh_search_enabled = True
    # The following must be defined exactly like the
    # schema in ~/scripts/data_libraries/build_whoosh_index.py
    schema = Schema( id=STORED, name=TEXT, info=TEXT, dbkey=TEXT, message=TEXT )
except ImportError as e:
    whoosh_search_enabled = False
    schema = None

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
try:
    import zlib  # noqa: F401
    comptypes.append( 'zip' )
except ImportError:
    pass

try:
    os.rmdir( tmpd )
except:
    pass


class LibraryCommon( BaseUIController, UsesFormDefinitionsMixin, UsesExtendedMetadataMixin, UsesLibraryMixinItems ):
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
                    rval[id] = {
                        "state": data.state,
                        "html": unicodify( trans.fill_template( "library/common/library_item_info.mako", ldda=data ), 'utf-8' )
                        # "force_history_refresh": force_history_refresh
                    }
        return rval

    @web.expose
    def browse_library( self, trans, cntrller='library', **kwd ):
        message = escape( kwd.get( 'message', '' ) )
        status = kwd.get( 'status', 'done' )
        # If use_panels is True, the library is being accessed via an external link
        # which did not originate from within the Galaxy instance, and the library will
        # be displayed correctly with the mast head.
        use_panels = util.string_as_bool( kwd.get( 'use_panels', False ) )
        library_id = kwd.get( 'id', None )
        if not library_id:
            # To handle bots
            message = "You must specify a library id."
            status = 'error'
        is_admin = trans.user_is_admin() and cntrller == 'library_admin'
        current_user_roles = trans.get_current_user_roles()
        try:
            library = trans.sa_session.query( trans.app.model.Library ).get( trans.security.decode_id( library_id ) )
        except:
            # Protect against attempts to phish for valid keys that return libraries
            library = None
        # Most security for browsing libraries is handled in the template, but do a basic check here.
        if not library or not ( is_admin or trans.app.security_agent.can_access_library( current_user_roles, library ) ):
            message = "Invalid library id ( %s ) specified." % str( library_id )
            status = 'error'
        else:
            show_deleted = util.string_as_bool( kwd.get( 'show_deleted', False ) )
            created_ldda_ids = kwd.get( 'created_ldda_ids', '' )
            hidden_folder_ids = util.listify( kwd.get( 'hidden_folder_ids', '' ) )
            if created_ldda_ids and not message:
                message = "%d datasets are uploading in the background to the library '%s' (each is selected).  " % \
                    ( len( created_ldda_ids.split( ',' ) ), escape( library.name ) )
                message += "Don't navigate away from Galaxy or use the browser's \"stop\" or \"reload\" buttons (on this tab) until the "
                message += "message \"This job is running\" is cleared from the \"Information\" column below for each selected dataset."
                status = "info"
            comptypes = get_comptypes( trans )
            try:
                if self.app.config.new_lib_browse:
                    return trans.fill_template( 'library/common/browse_library_opt.mako',
                                                cntrller=cntrller,
                                                use_panels=use_panels,
                                                library=library,
                                                created_ldda_ids=created_ldda_ids,
                                                hidden_folder_ids=hidden_folder_ids,
                                                show_deleted=show_deleted,
                                                comptypes=comptypes,
                                                current_user_roles=current_user_roles,
                                                message=escape( message ),
                                                status=escape( status ) )
                else:
                    return trans.fill_template( 'library/common/browse_library.mako',
                                                cntrller=cntrller,
                                                use_panels=use_panels,
                                                library=library,
                                                created_ldda_ids=created_ldda_ids,
                                                hidden_folder_ids=hidden_folder_ids,
                                                show_deleted=show_deleted,
                                                comptypes=comptypes,
                                                current_user_roles=current_user_roles,
                                                message=escape( message ),
                                                status=escape( status ) )
            except Exception as e:
                message = 'Error attempting to display contents of library (%s): %s.' % ( escape( str( library.name ) ), str( e ) )
                status = 'error'
        default_action = kwd.get( 'default_action', None )

        return trans.response.send_redirect( web.url_for( use_panels=use_panels,
                                                          controller=cntrller,
                                                          action='browse_libraries',
                                                          default_action=default_action,
                                                          message=message,
                                                          status=status ) )

    @web.expose
    def library_info( self, trans, cntrller, **kwd ):
        message = escape( kwd.get( 'message', '' ) )
        status = kwd.get( 'status', 'done' )
        use_panels = util.string_as_bool( kwd.get( 'use_panels', False ) )
        show_deleted = util.string_as_bool( kwd.get( 'show_deleted', False ) )
        is_admin = trans.user_is_admin() and cntrller == 'library_admin'
        current_user_roles = trans.get_current_user_roles()
        library_id = kwd.get( 'id', None )
        try:
            library = trans.sa_session.query( trans.app.model.Library ).get( trans.security.decode_id( library_id ) )
        except:
            library = None
        self._check_access( trans, cntrller, is_admin, library, current_user_roles, use_panels, library_id, show_deleted )
        if kwd.get( 'library_info_button', False ):
            self._check_modify( trans, cntrller, is_admin, library, current_user_roles, use_panels, library_id, show_deleted )
            new_name = kwd.get( 'name', 'No name' )
            if not new_name:
                message = 'Enter a valid name'
                status = 'error'
            else:
                new_description = kwd.get( 'description', '' )
                new_synopsis = kwd.get( 'synopsis', '' )
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
                message = "Information updated for library '%s'." % library.name
                return trans.response.send_redirect( web.url_for( controller='library_common',
                                                                  action='library_info',
                                                                  cntrller=cntrller,
                                                                  use_panels=use_panels,
                                                                  id=trans.security.encode_id( library.id ),
                                                                  show_deleted=show_deleted,
                                                                  message=message,
                                                                  status='done' ) )
        # See if we have any associated templates
        info_association, inherited = library.get_info_association()
        widgets = library.get_template_widgets( trans )
        widget_fields_have_contents = self.widget_fields_have_contents( widgets )
        return trans.fill_template( '/library/common/library_info.mako',
                                    cntrller=cntrller,
                                    use_panels=use_panels,
                                    library=library,
                                    widgets=widgets,
                                    widget_fields_have_contents=widget_fields_have_contents,
                                    current_user_roles=current_user_roles,
                                    show_deleted=show_deleted,
                                    info_association=info_association,
                                    inherited=inherited,
                                    message=escape( message ),
                                    status=escape( status ) )

    @web.expose
    def library_permissions( self, trans, cntrller, **kwd ):
        message = escape( kwd.get( 'message', '' ) )
        status = kwd.get( 'status', 'done' )
        use_panels = util.string_as_bool( kwd.get( 'use_panels', False ) )
        show_deleted = util.string_as_bool( kwd.get( 'show_deleted', False ) )
        is_admin = trans.user_is_admin() and cntrller == 'library_admin'
        current_user_roles = trans.get_current_user_roles()
        library_id = kwd.get( 'id', None )
        try:
            library = trans.sa_session.query( trans.app.model.Library ).get( trans.security.decode_id( library_id ) )
        except:
            library = None
        self._check_access( trans, cntrller, is_admin, library, current_user_roles, use_panels, library_id, show_deleted )
        self._check_manage( trans, cntrller, is_admin, library, current_user_roles, use_panels, library_id, show_deleted )
        if kwd.get( 'update_roles_button', False ):
            # The user clicked the Save button on the 'Associate With Roles' form
            permissions = {}
            for k, v in trans.app.model.Library.permitted_actions.items():
                in_roles = [ trans.sa_session.query( trans.app.model.Role ).get( x ) for x in util.listify( kwd.get( k + '_in', [] ) ) ]
                permissions[ trans.app.security_agent.get_action( v.action ) ] = in_roles
            trans.app.security_agent.set_all_library_permissions( trans, library, permissions )
            trans.sa_session.refresh( library )
            # Copy the permissions to the root folder
            trans.app.security_agent.copy_library_permissions( trans, library, library.root_folder )
            message = "Permissions updated for library '%s'." % escape( library.name )
            return trans.response.send_redirect( web.url_for( controller='library_common',
                                                              action='library_permissions',
                                                              cntrller=cntrller,
                                                              use_panels=use_panels,
                                                              id=trans.security.encode_id( library.id ),
                                                              show_deleted=show_deleted,
                                                              message=message,
                                                              status='done' ) )
        roles = trans.app.security_agent.get_legitimate_roles( trans, library, cntrller )
        all_roles = trans.app.security_agent.get_all_roles( trans, cntrller )
        return trans.fill_template( '/library/common/library_permissions.mako',
                                    cntrller=cntrller,
                                    use_panels=use_panels,
                                    library=library,
                                    current_user_roles=current_user_roles,
                                    roles=roles,
                                    all_roles=all_roles,
                                    show_deleted=show_deleted,
                                    message=escape( message ),
                                    status=escape( status ) )

    @web.expose
    def create_folder( self, trans, cntrller, parent_id, library_id, **kwd ):
        message = escape( kwd.get( 'message', '' ) )
        status = kwd.get( 'status', 'done' )
        show_deleted = util.string_as_bool( kwd.get( 'show_deleted', False ) )
        use_panels = util.string_as_bool( kwd.get( 'use_panels', False ) )
        is_admin = trans.user_is_admin() and cntrller in ( 'library_admin', 'api' )
        current_user_roles = trans.get_current_user_roles()
        try:
            parent_folder = trans.sa_session.query( trans.app.model.LibraryFolder ).get( trans.security.decode_id( parent_id ) )
        except:
            parent_folder = None
        # Check the library which actually contains the user-supplied parent folder, not the user-supplied
        # library, which could be anything.
        self._check_access( trans, cntrller, is_admin, parent_folder, current_user_roles, use_panels, library_id, show_deleted )
        self._check_add( trans, cntrller, is_admin, parent_folder, current_user_roles, use_panels, library_id, show_deleted )
        if kwd.get( 'new_folder_button', False ) or cntrller == 'api':
            new_folder = trans.app.model.LibraryFolder( name=kwd.get( 'name', '' ),
                                                        description=kwd.get( 'description', '' ) )
            # We are associating the last used genome build with folders, so we will always
            # initialize a new folder with the first dbkey in genome builds list which is currently
            # ?    unspecified (?)
            new_folder.genome_build = trans.app.genome_builds.default_value
            parent_folder.add_folder( new_folder )
            trans.sa_session.add( new_folder )
            trans.sa_session.flush()
            # New folders default to having the same permissions as their parent folder
            trans.app.security_agent.copy_library_permissions( trans, parent_folder, new_folder )
            # If we're creating in the API, we're done
            if cntrller == 'api':
                return 200, dict( created=new_folder )
            # If we have an inheritable template, redirect to the folder_info page so information
            # can be filled in immediately.
            widgets = []
            info_association, inherited = new_folder.get_info_association()
            if info_association and ( not( inherited ) or info_association.inheritable ):
                widgets = new_folder.get_template_widgets( trans )
            if info_association:
                message = "The new folder named '%s' has been added to the data library.  " % escape( new_folder.name )
                message += "Additional information about this folder may be added using the inherited template."
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
                                            message=escape( message ),
                                            status='done' )
            # If not inheritable info_association, redirect to the library.
            message = "The new folder named '%s' has been added to the data library." % escape( new_folder.name )
            # SM: This is the second place where the API controller would
            # reference the library id:
            return trans.response.send_redirect( web.url_for( controller='library_common',
                                                              action='browse_library',
                                                              cntrller=cntrller,
                                                              use_panels=use_panels,
                                                              id=library_id,
                                                              show_deleted=show_deleted,
                                                              message=message,
                                                              status='done' ) )
        # We do not render any template widgets on creation pages since saving the info_association
        # cannot occur before the associated item is saved.
        return trans.fill_template( '/library/common/new_folder.mako',
                                    cntrller=cntrller,
                                    use_panels=use_panels,
                                    library_id=library_id,
                                    folder=parent_folder,
                                    show_deleted=show_deleted,
                                    message=escape( message ),
                                    status=escape( status ) )

    @web.expose
    def folder_info( self, trans, cntrller, id, library_id, **kwd ):
        message = escape( kwd.get( 'message', '' ) )
        status = kwd.get( 'status', 'done' )
        show_deleted = util.string_as_bool( kwd.get( 'show_deleted', False ) )
        use_panels = util.string_as_bool( kwd.get( 'use_panels', False ) )
        is_admin = trans.user_is_admin() and cntrller == 'library_admin'
        current_user_roles = trans.get_current_user_roles()
        try:
            folder = trans.sa_session.query( trans.app.model.LibraryFolder ).get( trans.security.decode_id( id ) )
        except:
            folder = None
        self._check_access( trans, cntrller, is_admin, folder, current_user_roles, use_panels, library_id, show_deleted )
        if kwd.get( 'rename_folder_button', False ):
            self._check_modify( trans, cntrller, is_admin, folder, current_user_roles, use_panels, library_id, show_deleted )
            new_name = kwd.get( 'name', '' )
            new_description = kwd.get( 'description', '' )
            if not new_name:
                message = 'Enter a valid name'
                status = 'error'
            else:
                folder.name = new_name
                folder.description = new_description
                trans.sa_session.add( folder )
                trans.sa_session.flush()
                message = "Information updated for folder '%s'." % escape( folder.name )
                return trans.response.send_redirect( web.url_for( controller='library_common',
                                                                  action='folder_info',
                                                                  cntrller=cntrller,
                                                                  use_panels=use_panels,
                                                                  id=id,
                                                                  library_id=library_id,
                                                                  show_deleted=show_deleted,
                                                                  message=message,
                                                                  status='done' ) )
        # See if we have any associated templates
        widgets = []
        widget_fields_have_contents = False
        info_association, inherited = folder.get_info_association()
        if info_association and ( not( inherited ) or info_association.inheritable ):
            widgets = folder.get_template_widgets( trans )
            widget_fields_have_contents = self.widget_fields_have_contents( widgets )
        return trans.fill_template( '/library/common/folder_info.mako',
                                    cntrller=cntrller,
                                    use_panels=use_panels,
                                    folder=folder,
                                    library_id=library_id,
                                    widgets=widgets,
                                    widget_fields_have_contents=widget_fields_have_contents,
                                    current_user_roles=current_user_roles,
                                    show_deleted=show_deleted,
                                    info_association=info_association,
                                    inherited=inherited,
                                    message=escape( message ),
                                    status=escape( status ) )

    @web.expose
    def folder_permissions( self, trans, cntrller, id, library_id, **kwd ):
        message = escape( kwd.get( 'message', '' ) )
        status = kwd.get( 'status', 'done' )
        show_deleted = util.string_as_bool( kwd.get( 'show_deleted', False ) )
        use_panels = util.string_as_bool( kwd.get( 'use_panels', False ) )
        is_admin = trans.user_is_admin() and cntrller == 'library_admin'
        current_user_roles = trans.get_current_user_roles()
        try:
            folder = trans.sa_session.query( trans.app.model.LibraryFolder ).get( trans.security.decode_id( id ) )
        except:
            folder = None
        self._check_access( trans, cntrller, is_admin, folder, current_user_roles, use_panels, library_id, show_deleted )
        self._check_manage( trans, cntrller, is_admin, folder, current_user_roles, use_panels, library_id, show_deleted )
        if kwd.get( 'update_roles_button', False ):
            # The user clicked the Save button on the 'Associate With Roles' form
            permissions = {}
            for k, v in trans.app.model.Library.permitted_actions.items():
                if k != 'LIBRARY_ACCESS':
                    # LIBRARY_ACCESS is a special permission set only at the library level
                    # and it is not inherited.
                    in_roles = [ trans.sa_session.query( trans.app.model.Role ).get( int( x ) ) for x in util.listify( kwd.get( k + '_in', [] ) ) ]
                    permissions[ trans.app.security_agent.get_action( v.action ) ] = in_roles
            trans.app.security_agent.set_all_library_permissions( trans, folder, permissions )
            trans.sa_session.refresh( folder )
            message = "Permissions updated for folder '%s'." % escape( folder.name )
            return trans.response.send_redirect( web.url_for( controller='library_common',
                                                              action='folder_permissions',
                                                              cntrller=cntrller,
                                                              use_panels=use_panels,
                                                              id=trans.security.encode_id( folder.id ),
                                                              library_id=library_id,
                                                              show_deleted=show_deleted,
                                                              message=message,
                                                              status='done' ) )
        # If the library is public all roles are legitimate, but if the library
        # is restricted, only those roles associated with the LIBRARY_ACCESS
        # permission are legitimate.
        roles = trans.app.security_agent.get_legitimate_roles( trans, folder.parent_library, cntrller )
        return trans.fill_template( '/library/common/folder_permissions.mako',
                                    cntrller=cntrller,
                                    use_panels=use_panels,
                                    folder=folder,
                                    library_id=library_id,
                                    current_user_roles=current_user_roles,
                                    roles=roles,
                                    show_deleted=show_deleted,
                                    message=escape( message ),
                                    status=escape( status ) )

    @web.expose
    def ldda_edit_info( self, trans, cntrller, library_id, folder_id, id, **kwd ):
        message = escape( kwd.get( 'message', '' ) )
        status = kwd.get( 'status', 'done' )
        show_deleted = util.string_as_bool( kwd.get( 'show_deleted', False ) )
        use_panels = util.string_as_bool( kwd.get( 'use_panels', False ) )
        is_admin = trans.user_is_admin() and cntrller == 'library_admin'
        current_user_roles = trans.get_current_user_roles()
        try:
            ldda = trans.sa_session.query( trans.app.model.LibraryDatasetDatasetAssociation ).get( trans.security.decode_id( id ) )
        except:
            ldda = None
        self._check_access( trans, cntrller, is_admin, ldda, current_user_roles, use_panels, library_id, show_deleted )
        self._check_modify( trans, cntrller, is_admin, ldda, current_user_roles, use_panels, library_id, show_deleted )
        dbkey = kwd.get( 'dbkey', '?' )
        if isinstance( dbkey, list ):
            dbkey = dbkey[0]
        file_formats = [ dtype_name for dtype_name, dtype_value in trans.app.datatypes_registry.datatypes_by_extension.iteritems() if dtype_value.allow_datatype_change ]
        file_formats.sort()

        def __ok_to_edit_metadata( ldda_id ):
            # prevent modifying metadata when dataset is queued or running as input/output
            # This code could be more efficient, i.e. by using mappers, but to prevent slowing down loading a History panel, we'll leave the code here for now
            for job_to_dataset_association in trans.sa_session.query(
                    self.app.model.JobToInputLibraryDatasetAssociation ) \
                    .filter_by( ldda_id=ldda_id ) \
                    .all() \
                    + trans.sa_session.query( self.app.model.JobToOutputLibraryDatasetAssociation ) \
                    .filter_by( ldda_id=ldda_id ) \
                    .all():
                if job_to_dataset_association.job.state not in [ job_to_dataset_association.job.states.OK, job_to_dataset_association.job.states.ERROR, job_to_dataset_association.job.states.DELETED ]:
                    return False
            return True

        # See if we have any associated templates
        widgets = []
        info_association, inherited = ldda.get_info_association()
        if info_association and ( not( inherited ) or info_association.inheritable ):
            widgets = ldda.get_template_widgets( trans )
        if kwd.get( 'change', False ):
            # The user clicked the Save button on the 'Change data type' form
            if __ok_to_edit_metadata( ldda.id ):
                if ldda.datatype.allow_datatype_change and trans.app.datatypes_registry.get_datatype_by_extension( kwd.get( 'datatype' ) ).allow_datatype_change:
                    trans.app.datatypes_registry.change_datatype( ldda, kwd.get( 'datatype' ) )
                    trans.sa_session.flush()
                    message = "Data type changed for library dataset '%s'." % escape( ldda.name )
                    status = 'done'
                else:
                    message = "You are unable to change datatypes in this manner. Changing %s to %s is not allowed." % ( escape( ldda.extension ), escape( kwd.get( 'datatype' ) ) )
                    status = 'error'
            else:
                message = "This dataset is currently being used as input or output.  You cannot change datatype until the jobs have completed or you have canceled them."
                status = "error"
        elif kwd.get( 'save', False ):
            # The user clicked the Save button on the 'Edit Attributes' form
            new_name = kwd.get( 'name', '' )
            new_info = kwd.get( 'info', '' )
            new_message = escape( kwd.get( 'message', ''  ) )
            if not new_name:
                message = 'Enter a valid name'
                status = 'error'
            else:
                ldda.name = new_name
                ldda.info = new_info
                ldda.message = new_message
                if __ok_to_edit_metadata( ldda.id ):
                    # The following for loop will save all metadata_spec items
                    for name, spec in ldda.datatype.metadata_spec.items():
                        if spec.get("readonly"):
                            continue
                        optional = kwd.get( "is_" + name, None )
                        if optional and optional == '__NOTHING__':
                            # optional element... == '__NOTHING__' actually means it is NOT checked (and therefore ommitted)
                            setattr( ldda.metadata, name, None )
                        else:
                            setattr( ldda.metadata, name, spec.unwrap( kwd.get( name, None ) ) )
                    ldda.metadata.dbkey = dbkey
                    ldda.datatype.after_setting_metadata( ldda )
                    message = "Attributes updated for library dataset '%s'." % escape( ldda.name )
                    status = 'done'
                else:
                    message = "Attributes updated, but metadata could not be changed because this dataset is currently being used as input or output. You must cancel or wait for these jobs to complete before changing metadata."
                    status = 'warning'
                trans.sa_session.flush()
        elif kwd.get( 'detect', False ):
            # The user clicked the Auto-detect button on the 'Edit Attributes' form
            if __ok_to_edit_metadata( ldda.id ):
                for name, spec in ldda.datatype.metadata_spec.items():
                    # We need to be careful about the attributes we are resetting
                    if name not in [ 'name', 'info', 'dbkey' ]:
                        if spec.get( 'default' ):
                            setattr( ldda.metadata, name, spec.unwrap( spec.get( 'default' ) ) )
                message = "Attributes have been queued to be updated for library dataset '%s'." % escape( ldda.name )
                status = 'done'
                trans.app.datatypes_registry.set_external_metadata_tool.tool_action.execute( trans.app.datatypes_registry.set_external_metadata_tool, trans, incoming={ 'input1': ldda } )
            else:
                message = "This dataset is currently being used as input or output.  You cannot change metadata until the jobs have completed or you have canceled them."
                status = 'error'
            trans.sa_session.flush()
        elif kwd.get( 'change_extended_metadata', False):
            em_string = kwd.get("extended_metadata", "" )
            if len(em_string):
                payload = None
                try:
                    payload = loads(em_string)
                except Exception:
                    message = 'Invalid JSON input'
                    status = 'error'
                if payload is not None:
                    if ldda is not None:
                        ex_obj = self.get_item_extended_metadata_obj(trans, ldda)
                        if ex_obj is not None:
                            self.unset_item_extended_metadata_obj(trans, ldda)
                            self.delete_extended_metadata(trans, ex_obj)
                        ex_obj = self.create_extended_metadata(trans, payload)
                        self.set_item_extended_metadata_obj(trans, ldda, ex_obj)
                        message = "Updated Extended metadata '%s'." % escape( ldda.name )
                        status = 'done'
                    else:
                        message = "LDDA not found"
                        status = 'error'
            else:
                if ldda is not None:
                    ex_obj = self.get_item_extended_metadata_obj(trans, ldda)
                    if ex_obj is not None:
                        self.unset_item_extended_metadata_obj(trans, ldda)
                        self.delete_extended_metadata(trans, ex_obj)
                message = "Deleted Extended metadata '%s'." % escape( ldda.name )
                status = 'done'

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
                                    message=escape( message ),
                                    status=escape( status ) )

    @web.expose
    def ldda_info( self, trans, cntrller, library_id, folder_id, id, **kwd ):
        message = escape( kwd.get( 'message', '' ) )
        status = kwd.get( 'status', 'done' )
        show_deleted = util.string_as_bool( kwd.get( 'show_deleted', False ) )
        show_associated_hdas_and_lddas = util.string_as_bool( kwd.get( 'show_associated_hdas_and_lddas', False ) )
        use_panels = util.string_as_bool( kwd.get( 'use_panels', False ) )
        is_admin = trans.user_is_admin() and cntrller == 'library_admin'
        current_user_roles = trans.get_current_user_roles()
        ldda = trans.sa_session.query( trans.app.model.LibraryDatasetDatasetAssociation ).get( trans.security.decode_id( id ) )
        self._check_access( trans, cntrller, is_admin, ldda, current_user_roles, use_panels, library_id, show_deleted )
        if is_admin and show_associated_hdas_and_lddas:
            # Get all associated hdas and lddas that use the same disk file.
            associated_hdas = trans.sa_session.query( trans.model.HistoryDatasetAssociation ) \
                                              .filter( and_( trans.model.HistoryDatasetAssociation.deleted == false(),
                                                             trans.model.HistoryDatasetAssociation.dataset_id == ldda.dataset_id ) ) \
                                              .all()
            associated_lddas = trans.sa_session.query( trans.model.LibraryDatasetDatasetAssociation ) \
                                               .filter( and_( trans.model.LibraryDatasetDatasetAssociation.deleted == false(),
                                                              trans.model.LibraryDatasetDatasetAssociation.dataset_id == ldda.dataset_id,
                                                              trans.model.LibraryDatasetDatasetAssociation.id != ldda.id ) ) \
                                               .all()
        else:
            associated_hdas = []
            associated_lddas = []
        # See if we have any associated templates
        widgets = []
        widget_fields_have_contents = False
        info_association, inherited = ldda.get_info_association()
        if info_association and ( not( inherited ) or info_association.inheritable ):
            widgets = ldda.get_template_widgets( trans )
            widget_fields_have_contents = self.widget_fields_have_contents( widgets )
        return trans.fill_template( '/library/common/ldda_info.mako',
                                    cntrller=cntrller,
                                    use_panels=use_panels,
                                    ldda=ldda,
                                    library=ldda.library_dataset.folder.parent_library,
                                    show_associated_hdas_and_lddas=show_associated_hdas_and_lddas,
                                    associated_hdas=associated_hdas,
                                    associated_lddas=associated_lddas,
                                    show_deleted=show_deleted,
                                    widgets=widgets,
                                    widget_fields_have_contents=widget_fields_have_contents,
                                    current_user_roles=current_user_roles,
                                    info_association=info_association,
                                    inherited=inherited,
                                    message=escape( message ),
                                    status=escape( status ) )

    @web.expose
    def ldda_permissions( self, trans, cntrller, library_id, folder_id, id, **kwd ):
        message = str( escape( kwd.get( 'message', '' ) ) )
        status = kwd.get( 'status', 'done' )
        show_deleted = util.string_as_bool( kwd.get( 'show_deleted', False ) )
        use_panels = util.string_as_bool( kwd.get( 'use_panels', False ) )
        ids = util.listify( id )
        lddas = []
        libraries = []
        is_admin = trans.user_is_admin() and cntrller == 'library_admin'
        current_user_roles = trans.get_current_user_roles()
        for id in ids:
            try:
                ldda = trans.sa_session.query( trans.app.model.LibraryDatasetDatasetAssociation ).get( trans.security.decode_id( id ) )
            except:
                ldda = None
            if ldda:
                library = ldda.library_dataset.folder.parent_library
            self._check_access( trans, cntrller, is_admin, ldda, current_user_roles, use_panels, library_id, show_deleted )
            lddas.append( ldda )
            libraries.append( library )
        library = libraries[0]
        if filter( lambda x: x != library, libraries ):
            message = "Library datasets specified span multiple libraries."
            return trans.response.send_redirect( web.url_for( controller='library_common',
                                                              action='browse_library',
                                                              id=library_id,
                                                              cntrller=cntrller,
                                                              use_panels=use_panels,
                                                              message=message,
                                                              status='error' ) )
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
        if kwd.get( 'update_roles_button', False ):
            # Dataset permissions
            access_action = trans.app.security_agent.get_action( trans.app.security_agent.permitted_actions.DATASET_ACCESS.action )
            manage_permissions_action = trans.app.security_agent.get_action( trans.app.security_agent.permitted_actions.DATASET_MANAGE_PERMISSIONS.action )
            permissions, in_roles, error, message = \
                trans.app.security_agent.derive_roles_from_access( trans, trans.app.security.decode_id( library_id ), cntrller, library=True, **kwd )
            # Keep roles for DATASET_MANAGE_PERMISSIONS on the dataset
            if not ldda.has_manage_permissions_roles( trans ):
                # Permission setting related to DATASET_MANAGE_PERMISSIONS was broken for a period of time,
                # so it is possible that some Datasets have no roles associated with the DATASET_MANAGE_PERMISSIONS
                # permission.  In this case, we'll reset this permission to the ldda user's private role.
                # dataset_manage_permissions_roles = [ trans.app.security_agent.get_private_user_role( ldda.user ) ]
                permissions[ manage_permissions_action ] = [ trans.app.security_agent.get_private_user_role( ldda.user ) ]
            else:
                permissions[ manage_permissions_action ] = ldda.get_manage_permissions_roles( trans )
            for ldda in lddas:
                # Set the DATASET permissions on the Dataset.
                if error:
                    # Keep the original role associations for the DATASET_ACCESS permission on the ldda.
                    permissions[ access_action ] = ldda.get_access_roles( trans )
                    status = 'error'
                else:
                    error = trans.app.security_agent.set_all_dataset_permissions( ldda.dataset, permissions )
                    if error:
                        message += error
                        status = 'error'
                    trans.sa_session.refresh( ldda.dataset )
            if not error:
                # Set the LIBRARY permissions on the LibraryDataset.  The LibraryDataset and
                # LibraryDatasetDatasetAssociation will be set with the same permissions.
                permissions = {}
                for k, v in trans.app.model.Library.permitted_actions.items():
                    if k != 'LIBRARY_ACCESS':
                        # LIBRARY_ACCESS is a special permission set only at the library level and it is not inherited.
                        in_roles = [ trans.sa_session.query( trans.app.model.Role ).get( x ) for x in util.listify( kwd.get( k + '_in', [] ) ) ]
                        permissions[ trans.app.security_agent.get_action( v.action ) ] = in_roles
                for ldda in lddas:
                    error = trans.app.security_agent.set_all_library_permissions( trans, ldda.library_dataset, permissions )
                    trans.sa_session.refresh( ldda.library_dataset )
                    if error:
                        message = error
                    else:
                        # Set the LIBRARY permissions on the LibraryDatasetDatasetAssociation
                        trans.app.security_agent.set_all_library_permissions( trans, ldda, permissions )
                        trans.sa_session.refresh( ldda )
                if len( lddas ) == 1:
                    message = "Permissions updated for dataset '%s'." % escape( ldda.name )
                else:
                    message = 'Permissions updated for %d datasets.' % len( lddas )
                status = 'done'
            return trans.fill_template( "/library/common/ldda_permissions.mako",
                                        cntrller=cntrller,
                                        use_panels=use_panels,
                                        lddas=lddas,
                                        library_id=library_id,
                                        roles=roles,
                                        show_deleted=show_deleted,
                                        message=escape( message ),
                                        status=escape( status ) )
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
                    message = 'The datasets you selected do not have identical permissions, so they can not be updated together'
                    trans.response.send_redirect( web.url_for( controller='library_common',
                                                               action='browse_library',
                                                               cntrller=cntrller,
                                                               use_panels=use_panels,
                                                               id=library_id,
                                                               show_deleted=show_deleted,
                                                               message=message,
                                                               status='error' ) )
        # Display permission form, permissions will be updated for all lddas simultaneously.
        return trans.fill_template( "/library/common/ldda_permissions.mako",
                                    cntrller=cntrller,
                                    use_panels=use_panels,
                                    lddas=lddas,
                                    library_id=library_id,
                                    roles=roles,
                                    show_deleted=show_deleted,
                                    message=escape( message ),
                                    status=escape( status ) )

    @web.expose
    def upload_library_dataset( self, trans, cntrller, library_id, folder_id, **kwd ):
        message = escape( kwd.get( 'message', '' ) )
        status = kwd.get( 'status', 'done' )
        ldda_message = escape( kwd.get( 'ldda_message', '' ) )
        # deleted = util.string_as_bool( kwd.get( 'deleted', False ) )
        show_deleted = util.string_as_bool( kwd.get( 'show_deleted', False ) )
        use_panels = util.string_as_bool( kwd.get( 'use_panels', False ) )
        replace_id = kwd.get( 'replace_id', None )
        replace_dataset = None
        upload_option = kwd.get( 'upload_option', 'upload_file' )
        if kwd.get( 'files_0|uni_to_posix', False ):
            to_posix_lines = kwd.get( 'files_0|to_posix_lines', '' )
        else:
            to_posix_lines = kwd.get( 'to_posix_lines', '' )
        if kwd.get( 'files_0|space_to_tab', False ):
            space_to_tab = kwd.get( 'files_0|space_to_tab', '' )
        else:
            space_to_tab = kwd.get( 'space_to_tab', '' )
        link_data_only = kwd.get( 'link_data_only', 'copy_files' )
        dbkey = kwd.get( 'dbkey', '?' )
        if isinstance( dbkey, list ):
            last_used_build = dbkey[0]
        else:
            last_used_build = dbkey
        roles = kwd.get( 'roles', '' )
        is_admin = trans.user_is_admin() and cntrller in ( 'library_admin', 'api' )
        current_user_roles = trans.get_current_user_roles()
        widgets = []
        info_association, inherited = None, None
        template_id = "None"
        if replace_id not in [ '', None, 'None' ]:
            replace_dataset = trans.sa_session.query( trans.app.model.LibraryDataset ).get( trans.security.decode_id( replace_id ) )
            self._check_access( trans, cntrller, is_admin, replace_dataset, current_user_roles, use_panels, library_id, show_deleted )
            self._check_modify( trans, cntrller, is_admin, replace_dataset, current_user_roles, use_panels, library_id, show_deleted )
            library = replace_dataset.folder.parent_library
            folder = replace_dataset.folder
            info_association, inherited = replace_dataset.library_dataset_dataset_association.get_info_association()
            if info_association and ( not( inherited ) or info_association.inheritable ):
                widgets = replace_dataset.library_dataset_dataset_association.get_template_widgets( trans )
            # The name is stored - by the time the new ldda is created, replace_dataset.name
            # will point to the new ldda, not the one it's replacing.
            replace_dataset_name = replace_dataset.name
            if not last_used_build:
                last_used_build = replace_dataset.library_dataset_dataset_association.dbkey
        else:
            folder = trans.sa_session.query( trans.app.model.LibraryFolder ).get( trans.security.decode_id( folder_id ) )
            self._check_access( trans, cntrller, is_admin, folder, current_user_roles, use_panels, library_id, show_deleted )
            self._check_add( trans, cntrller, is_admin, folder, current_user_roles, use_panels, library_id, show_deleted )
            library = folder.parent_library
        if folder and last_used_build in [ 'None', None, '?' ]:
            last_used_build = folder.genome_build
        if kwd.get( 'runtool_btn', False ) or kwd.get( 'ajax_upload', False ) or cntrller == 'api':
            error = False
            if upload_option == 'upload_paths' and not trans.app.config.allow_library_path_paste:
                error = True
                message = '"allow_library_path_paste" is not defined in the Galaxy configuration file'
            elif upload_option == 'upload_paths' and not is_admin:
                error = True
                message = 'Uploading files via filesystem paths can only be performed by administrators'
            elif roles:
                # Check to see if the user selected roles to associate with the DATASET_ACCESS permission
                # on the dataset that would cause accessibility issues.
                vars = dict( DATASET_ACCESS_in=roles )
                permissions, in_roles, error, message = \
                    trans.app.security_agent.derive_roles_from_access( trans, library.id, cntrller, library=True, **vars )
            if error:
                if cntrller == 'api':
                    return 400, message
                trans.response.send_redirect( web.url_for( controller='library_common',
                                                           action='upload_library_dataset',
                                                           cntrller=cntrller,
                                                           library_id=library_id,
                                                           folder_id=folder_id,
                                                           replace_id=replace_id,
                                                           upload_option=upload_option,
                                                           show_deleted=show_deleted,
                                                           message=message,
                                                           status='error' ) )
            else:
                # See if we have any inherited templates.
                if not info_association:
                    info_association, inherited = folder.get_info_association( inherited=True )
                if info_association and info_association.inheritable:
                    template_id = str( info_association.template.id )
                    widgets = folder.get_template_widgets( trans, get_contents=True )
                    processed_widgets = []
                    # The list of widgets may include an AddressField which we need to save if it is new
                    for index, widget_dict in enumerate( widgets ):
                        widget = widget_dict[ 'widget' ]
                        if isinstance( widget, AddressField ):
                            value = kwd.get( widget.name, '' )
                            if value == 'new':
                                if self.field_param_values_ok( widget.name, 'AddressField', **kwd ):
                                    # Save the new address
                                    address = trans.app.model.UserAddress( user=trans.user )
                                    self.save_widget_field( trans, address, widget.name, **kwd )
                                    widget.value = str( address.id )
                                    widget_dict[ 'widget' ] = widget
                                    processed_widgets.append( widget_dict )
                                    # It is now critical to update the value of 'field_%i', replacing the string
                                    # 'new' with the new address id.  This is necessary because the upload_dataset()
                                    # method below calls the handle_library_params() method, which does not parse the
                                    # widget fields, it instead pulls form values from kwd.  See the FIXME comments in the
                                    # handle_library_params() method, and the CheckboxField code in the next conditional.
                                    kwd[ widget.name ] = str( address.id )
                                else:
                                    # The invalid address won't be saved, but we cannot display error
                                    # messages on the upload form due to the ajax upload already occurring.
                                    # When we re-engineer the upload process ( currently under way ), we
                                    # will be able to check the form values before the ajax upload occurs
                                    # in the background.  For now, we'll do nothing...
                                    pass
                        elif isinstance( widget, CheckboxField ):
                            # We need to check the value from kwd since util.Params would have munged the list if
                            # the checkbox is checked.
                            value = kwd.get( widget.name, '' )
                            if CheckboxField.is_checked( value ):
                                widget.value = 'true'
                                widget_dict[ 'widget' ] = widget
                                processed_widgets.append( widget_dict )
                                kwd[ widget.name ] = 'true'
                        else:
                            processed_widgets.append( widget_dict )
                    widgets = processed_widgets
                created_outputs_dict = trans.webapp.controllers[ 'library_common' ].upload_dataset( trans,
                                                                                                    cntrller=cntrller,
                                                                                                    library_id=trans.security.encode_id( library.id ),
                                                                                                    folder_id=trans.security.encode_id( folder.id ),
                                                                                                    template_id=template_id,
                                                                                                    widgets=widgets,
                                                                                                    replace_dataset=replace_dataset,
                                                                                                    **kwd )
                if created_outputs_dict:
                    if cntrller == 'api':
                        # created_outputs_dict can be a string only if cntrller == 'api'
                        if type( created_outputs_dict ) == str:
                            return 400, created_outputs_dict
                        elif type( created_outputs_dict ) == tuple:
                            return created_outputs_dict[0], created_outputs_dict[1]
                        return 200, created_outputs_dict
                    total_added = len( created_outputs_dict.keys() )
                    ldda_id_list = [ str( v.id ) for k, v in created_outputs_dict.items() ]
                    created_ldda_ids = ",".join( ldda_id_list )
                    if replace_dataset:
                        message = "Added %d dataset versions to the library dataset '%s' in the folder '%s'." % ( total_added, escape( replace_dataset_name ), escape( folder.name ) )
                    else:
                        if not folder.parent:
                            # Libraries have the same name as their root_folder
                            message = "Added %d datasets to the library '%s' (each is selected).  " % ( total_added, escape( folder.name ) )
                        else:
                            message = "Added %d datasets to the folder '%s' (each is selected).  " % ( total_added, escape( folder.name ) )
                        if cntrller == 'library_admin':
                            message += "Click the Go button at the bottom of this page to edit the permissions on these datasets if necessary."
                            status = 'done'
                        else:
                            # Since permissions on all LibraryDatasetDatasetAssociations must be the same at this point, we only need
                            # to check one of them to see if the current user can manage permissions on them.
                            check_ldda = trans.sa_session.query( trans.app.model.LibraryDatasetDatasetAssociation ).get( ldda_id_list[0] )
                            if trans.app.security_agent.can_manage_library_item( current_user_roles, check_ldda ):
                                if replace_dataset:
                                    default_action = ''
                                else:
                                    message += "Click the Go button at the bottom of this page to edit the permissions on these datasets if necessary."
                                    default_action = 'manage_permissions'
                            else:
                                default_action = 'import_to_current_history'
                            trans.response.send_redirect( web.url_for( controller='library_common',
                                                                       action='browse_library',
                                                                       cntrller=cntrller,
                                                                       id=library_id,
                                                                       default_action=default_action,
                                                                       created_ldda_ids=created_ldda_ids,
                                                                       show_deleted=show_deleted,
                                                                       message=message,
                                                                       status='done' ) )
                else:
                    created_ldda_ids = ''
                    message = "Upload failed"
                    status = 'error'
                    if cntrller == 'api':
                        return 400, message
                trans.response.send_redirect( web.url_for( controller='library_common',
                                                           action='browse_library',
                                                           cntrller=cntrller,
                                                           id=library_id,
                                                           created_ldda_ids=created_ldda_ids,
                                                           show_deleted=show_deleted,
                                                           message=message,
                                                           status=status ) )
        # Note: if the upload form was submitted due to refresh_on_change for a form field, we cannot re-populate
        # the field for the selected file ( files_0|file_data ) if the user selected one.  This is because the value
        # attribute of the html input file type field is typically ignored by browsers as a security precaution.

        # See if we have any inherited templates.
        if not info_association:
            info_association, inherited = folder.get_info_association( inherited=True )
            if info_association and info_association.inheritable:
                widgets = folder.get_template_widgets( trans, get_contents=True )
        if info_association:
            # Retain contents of widget fields when form was submitted via refresh_on_change.
            widgets = self.populate_widgets_from_kwd( trans, widgets, **kwd )
            template_id = str( info_association.template.id )

        # Send list of data formats to the upload form so the "extension" select list can be populated dynamically
        file_formats = trans.app.datatypes_registry.upload_file_formats

        dbkeys = trans.app.genomes.get_dbkeys( trans )
        dbkeys.sort( key=lambda dbkey: dbkey[0].lower() )

        # Send the current history to the form to enable importing datasets from history to library
        history = trans.get_history()
        if history is not None:
            trans.sa_session.refresh( history )
        if upload_option == 'upload_file' and trans.app.config.nginx_upload_path:
            # If we're using nginx upload, override the form action -
            # url_for is intentionally not used on the base URL here -
            # nginx_upload_path is expected to include the proxy prefix if the
            # administrator intends for it to be part of the URL.
            action = trans.app.config.nginx_upload_path + '?nginx_redir=' + web.url_for( controller='library_common', action='upload_library_dataset' )
        else:
            action = web.url_for( controller='library_common', action='upload_library_dataset' )
        do_not_display_options = []
        if replace_dataset:
            # TODO: Not sure why, but 'upload_paths' is not allowed if replacing a dataset.  See self.make_library_uploaded_dataset().
            do_not_display_options = [ 'upload_directory', 'upload_paths' ]
        upload_option_select_list = self._build_upload_option_select_list( trans, upload_option, is_admin, do_not_display_options )
        roles_select_list = self._build_roles_select_list( trans, cntrller, library, util.listify( roles ) )
        return trans.fill_template( '/library/common/upload.mako',
                                    cntrller=cntrller,
                                    upload_option_select_list=upload_option_select_list,
                                    upload_option=upload_option,
                                    action=action,
                                    library_id=library_id,
                                    folder_id=folder_id,
                                    replace_dataset=replace_dataset,
                                    file_formats=file_formats,
                                    dbkeys=dbkeys,
                                    last_used_build=last_used_build,
                                    roles_select_list=roles_select_list,
                                    history=history,
                                    widgets=widgets,
                                    template_id=template_id,
                                    to_posix_lines=to_posix_lines,
                                    space_to_tab=space_to_tab,
                                    link_data_only=link_data_only,
                                    show_deleted=show_deleted,
                                    ldda_message=ldda_message,
                                    message=escape( message ),
                                    status=escape( status ) )

    def upload_dataset( self, trans, cntrller, library_id, folder_id, replace_dataset=None, **kwd ):
        # Set up the traditional tool state/params
        tool_id = 'upload1'
        tool = trans.app.toolbox.get_tool( tool_id )
        state = tool.new_state( trans )
        populate_state( trans, tool.inputs, kwd, state.inputs )
        tool_params = state.inputs
        dataset_upload_inputs = []
        for input_name, input in tool.inputs.iteritems():
            if input.type == "upload_dataset":
                dataset_upload_inputs.append( input )
        # Library-specific params
        show_deleted = util.string_as_bool( kwd.get( 'show_deleted', False ) )
        message = escape( kwd.get( 'message', '' ) )
        server_dir = kwd.get( 'server_dir', '' )
        if replace_dataset not in [ None, 'None' ]:
            replace_id = trans.security.encode_id( replace_dataset.id )
        else:
            replace_id = None
        upload_option = kwd.get( 'upload_option', 'upload_file' )
        response_code = 200
        if upload_option == 'upload_directory':
            if server_dir in [ None, 'None', '' ]:
                response_code = 400
            if cntrller == 'library_admin' or ( cntrller == 'api' and trans.user_is_admin ):
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
                message = 'Select a directory'
            else:
                response_code = 403
                message = '"%s" is not defined in the Galaxy configuration file' % import_dir_desc
        elif upload_option == 'upload_paths':
            if not trans.app.config.allow_library_path_paste:
                response_code = 403
                message = '"allow_library_path_paste" is not defined in the Galaxy configuration file'
        # Some error handling should be added to this method.
        try:
            # FIXME: instead of passing params here ( which have been processed by util.Params(), the original kwd
            # should be passed so that complex objects that may have been included in the initial request remain.
            library_bunch = upload_common.handle_library_params( trans, kwd, folder_id, replace_dataset )
        except:
            response_code = 500
            message = "Unable to parse upload parameters, please report this error."
        # Proceed with (mostly) regular upload processing if we're still errorless
        if response_code == 200:
            precreated_datasets = upload_common.get_precreated_datasets( trans, tool_params, trans.app.model.LibraryDatasetDatasetAssociation, controller=cntrller )
            if upload_option == 'upload_file':
                tool_params = upload_common.persist_uploads( tool_params )
                uploaded_datasets = upload_common.get_uploaded_datasets( trans, cntrller, tool_params, precreated_datasets, dataset_upload_inputs, library_bunch=library_bunch )
            elif upload_option == 'upload_directory':
                uploaded_datasets, response_code, message = self.get_server_dir_uploaded_datasets( trans, cntrller, kwd, full_dir, import_dir_desc, library_bunch, response_code, message )
            elif upload_option == 'upload_paths':
                uploaded_datasets, response_code, message = self.get_path_paste_uploaded_datasets( trans, cntrller, kwd, library_bunch, response_code, message )
            upload_common.cleanup_unused_precreated_datasets( precreated_datasets )
            if upload_option == 'upload_file' and not uploaded_datasets:
                response_code = 400
                message = 'Select a file, enter a URL or enter text'
        if response_code != 200:
            if cntrller == 'api':
                return ( response_code, message )
            trans.response.send_redirect( web.url_for( controller='library_common',
                                                       action='upload_library_dataset',
                                                       cntrller=cntrller,
                                                       library_id=library_id,
                                                       folder_id=folder_id,
                                                       replace_id=replace_id,
                                                       upload_option=upload_option,
                                                       show_deleted=show_deleted,
                                                       message=message,
                                                       status='error' ) )
        json_file_path = upload_common.create_paramfile( trans, uploaded_datasets )
        data_list = [ ud.data for ud in uploaded_datasets ]
        job_params = {}
        job_params['link_data_only'] = dumps( kwd.get( 'link_data_only', 'copy_files' ) )
        job_params['uuid'] = dumps( kwd.get( 'uuid', None ) )
        job, output = upload_common.create_job( trans, tool_params, tool, json_file_path, data_list, folder=library_bunch.folder, job_params=job_params )
        trans.sa_session.add( job )
        trans.sa_session.flush()
        return output

    def make_library_uploaded_dataset( self, trans, cntrller, params, name, path, type, library_bunch, in_folder=None ):
        link_data_only = params.get( 'link_data_only', 'copy_files' )
        uuid_str = params.get( 'uuid', None )
        file_type = params.get( 'file_type', None )
        library_bunch.replace_dataset = None  # not valid for these types of upload
        uploaded_dataset = util.bunch.Bunch()
        new_name = name
        # Remove compressed file extensions, if any, but only if
        # we're copying files into Galaxy's file space.
        if link_data_only == 'copy_files':
            if new_name.endswith( '.gz' ):
                new_name = new_name.rstrip( '.gz' )
            elif new_name.endswith( '.zip' ):
                new_name = new_name.rstrip( '.zip' )
        uploaded_dataset.name = new_name
        uploaded_dataset.path = path
        uploaded_dataset.type = type
        uploaded_dataset.ext = None
        uploaded_dataset.file_type = file_type
        uploaded_dataset.dbkey = params.get( 'dbkey', None )
        uploaded_dataset.to_posix_lines = params.get('to_posix_lines', None)
        uploaded_dataset.space_to_tab = params.get( 'space_to_tab', None )
        if in_folder:
            uploaded_dataset.in_folder = in_folder
        uploaded_dataset.data = upload_common.new_upload( trans, cntrller, uploaded_dataset, library_bunch )
        uploaded_dataset.link_data_only = link_data_only
        uploaded_dataset.uuid = uuid_str
        if link_data_only == 'link_to_files':
            uploaded_dataset.data.file_name = os.path.abspath( path )
            # Since we are not copying the file into Galaxy's managed
            # default file location, the dataset should never be purgable.
            uploaded_dataset.data.dataset.purgable = False
            trans.sa_session.add_all( ( uploaded_dataset.data, uploaded_dataset.data.dataset ) )
            trans.sa_session.flush()
        return uploaded_dataset

    def get_server_dir_uploaded_datasets( self, trans, cntrller, params, full_dir, import_dir_desc, library_bunch, response_code, message ):
        dir_response = self._get_server_dir_files(params, full_dir, import_dir_desc)
        files = dir_response[0]
        if not files:
            return dir_response
        uploaded_datasets = []
        for file in files:
            name = os.path.basename( file )
            uploaded_datasets.append( self.make_library_uploaded_dataset( trans, cntrller, params, name, file, 'server_dir', library_bunch ) )
        return uploaded_datasets, 200, None

    def _get_server_dir_files( self, params, full_dir, import_dir_desc ):
        files = []
        try:
            for entry in os.listdir( full_dir ):
                # Only import regular files
                path = os.path.join( full_dir, entry )
                link_data_only = params.get( 'link_data_only', 'copy_files' )
                if os.path.islink( full_dir ) and link_data_only == 'link_to_files':
                    # If we're linking instead of copying and the
                    # sub-"directory" in the import dir is actually a symlink,
                    # dereference the symlink, but not any of its contents.
                    link_path = os.readlink( full_dir )
                    if os.path.isabs( link_path ):
                        path = os.path.join( link_path, entry )
                    else:
                        path = os.path.abspath( os.path.join( link_path, entry ) )
                elif os.path.islink( path ) and os.path.isfile( path ) and link_data_only == 'link_to_files':
                    # If we're linking instead of copying and the "file" in the
                    # sub-directory of the import dir is actually a symlink,
                    # dereference the symlink (one dereference only, Vasili).
                    link_path = os.readlink( path )
                    if os.path.isabs( link_path ):
                        path = link_path
                    else:
                        path = os.path.abspath( os.path.join( os.path.dirname( path ), link_path ) )
                if os.path.isfile( path ):
                    files.append( path )
        except Exception as e:
            message = "Unable to get file list for configured %s, error: %s" % ( import_dir_desc, str( e ) )
            response_code = 500
            return None, response_code, message
        if not files:
            message = "The directory '%s' contains no valid files" % full_dir
            response_code = 400
            return None, response_code, message
        return files, None, None

    def get_path_paste_uploaded_datasets( self, trans, cntrller, params, library_bunch, response_code, message ):
        preserve_dirs = util.string_as_bool( params.get( 'preserve_dirs', False ) )
        uploaded_datasets = []
        (files_and_folders, _response_code, _message) = self._get_path_files_and_folders(params, preserve_dirs)
        if _response_code:
            return (uploaded_datasets, _response_code, _message)
        for (path, name, folder) in files_and_folders:
            uploaded_datasets.append( self.make_library_uploaded_dataset( trans, cntrller, params, name, path, 'path_paste', library_bunch, folder ) )
        return uploaded_datasets, 200, None

    def _get_path_files_and_folders( self, params, preserve_dirs ):
        problem_response = self._check_path_paste_params( params )
        if problem_response:
            return problem_response
        files_and_folders = []
        for (line, path) in self._paths_list( params ):
            line_files_and_folders = self._get_single_path_files_and_folders( line, path, preserve_dirs )
            files_and_folders.extend( line_files_and_folders )
        return files_and_folders, None, None

    def _get_single_path_files_and_folders(self, line, path, preserve_dirs):
        files_and_folders = []
        if os.path.isfile( path ):
            name = os.path.basename( path )
            files_and_folders.append((path, name, None))
        for basedir, dirs, files in os.walk( line ):
            for file in files:
                file_path = os.path.abspath( os.path.join( basedir, file ) )
                if preserve_dirs:
                    in_folder = os.path.dirname( file_path.replace( path, '', 1 ).lstrip( '/' ) )
                else:
                    in_folder = None
                files_and_folders.append((file_path, file, in_folder))
        return files_and_folders

    def _paths_list(self, params):
        return [ (l.strip(), os.path.abspath(l.strip())) for l in params.get( 'filesystem_paths', '' ).splitlines() if l.strip() ]

    def _check_path_paste_params(self, params):
        if params.get( 'filesystem_paths', '' ) == '':
            message = "No paths entered in the upload form"
            response_code = 400
            return None, response_code, message
        bad_paths = []
        for (_, path) in self._paths_list( params ):
            if not os.path.exists( path ):
                bad_paths.append( path )
        if bad_paths:
            message = 'Invalid paths: "%s".' % '", "'.join( bad_paths )
            response_code = 400
            return None, response_code, message
        return None

    @web.expose
    def add_history_datasets_to_library( self, trans, cntrller, library_id, folder_id, hda_ids='', **kwd ):
        message = escape( kwd.get( 'message', '' ) )
        status = kwd.get( 'status', 'done' )
        ldda_message = escape( kwd.get( 'ldda_message', '' ) )
        show_deleted = kwd.get( 'show_deleted', False )
        use_panels = util.string_as_bool( kwd.get( 'use_panels', False ) )
        replace_id = kwd.get( 'replace_id', None )
        replace_dataset = None
        upload_option = kwd.get( 'upload_option', 'import_from_history' )
        if kwd.get( 'files_0|to_posix_lines', False ):
            to_posix_lines = kwd.get( 'files_0|to_posix_lines', '' )
        else:
            to_posix_lines = kwd.get( 'to_posix_lines', '' )
        if kwd.get( 'files_0|space_to_tab', False ):
            space_to_tab = kwd.get( 'files_0|space_to_tab', '' )
        else:
            space_to_tab = kwd.get( 'space_to_tab', '' )
        link_data_only = kwd.get( 'link_data_only', 'copy_files' )
        dbkey = kwd.get( 'dbkey', '?' )
        if isinstance( dbkey, list ):
            last_used_build = dbkey[0]
        else:
            last_used_build = dbkey
        roles = kwd.get( 'roles', '' )
        is_admin = trans.user_is_admin() and cntrller in ( 'library_admin', 'api' )
        current_user_roles = trans.get_current_user_roles()
        info_association, inherited = None, None
        template_id = "None"
        if replace_id not in [ None, 'None' ]:
            try:
                replace_dataset = trans.sa_session.query( trans.app.model.LibraryDataset ).get( trans.security.decode_id( replace_id ) )
            except:
                replace_dataset = None
            self._check_access( trans, cntrller, is_admin, replace_dataset, current_user_roles, use_panels, library_id, show_deleted )
            self._check_modify( trans, cntrller, is_admin, replace_dataset, current_user_roles, use_panels, library_id, show_deleted )
            library = replace_dataset.folder.parent_library
            folder = replace_dataset.folder
            last_used_build = replace_dataset.library_dataset_dataset_association.dbkey
            info_association, inherited = replace_dataset.library_dataset_dataset_association.get_info_association()
            if info_association and ( not( inherited ) or info_association.inheritable ):
                template_id = str( info_association.template.id )
        else:
            folder = trans.sa_session.query( trans.app.model.LibraryFolder ).get( trans.security.decode_id( folder_id ) )
            self._check_access( trans, cntrller, is_admin, folder, current_user_roles, use_panels, library_id, show_deleted )
            self._check_add( trans, cntrller, is_admin, folder, current_user_roles, use_panels, library_id, show_deleted )
            library = folder.parent_library
            last_used_build = folder.genome_build
        # See if the current history is empty
        history = trans.get_history()
        trans.sa_session.refresh( history )
        if not history.active_datasets:
            message = 'Your current history is empty'
            return trans.response.send_redirect( web.url_for( controller='library_common',
                                                              action='browse_library',
                                                              cntrller=cntrller,
                                                              id=library_id,
                                                              show_deleted=show_deleted,
                                                              message=message,
                                                              status='error' ) )
        if kwd.get( 'add_history_datasets_to_library_button', False ):
            hda_ids = util.listify( hda_ids )
            if hda_ids:
                dataset_names = []
                created_ldda_ids = ''
                for hda_id in hda_ids:
                    try:
                        hda = trans.sa_session.query( trans.app.model.HistoryDatasetAssociation ).get( trans.security.decode_id( hda_id ) )
                    except:
                        hda = None
                    self._check_access( trans, cntrller, is_admin, hda, current_user_roles, use_panels, library_id, show_deleted )
                    if roles:
                        role_ids = roles.split( ',' )
                        role_obj_list = [ trans.sa_session.query( trans.model.Role ).get( role_id ) for role_id in role_ids ]
                    else:
                        role_obj_list = []
                    ldda = hda.to_library_dataset_dataset_association( trans,
                                                                       target_folder=folder,
                                                                       replace_dataset=replace_dataset,
                                                                       roles=role_obj_list,
                                                                       ldda_message=ldda_message )
                    created_ldda_ids = '%s,%s' % ( created_ldda_ids, str( ldda.id ) )
                    dataset_names.append( ldda.name )
                    if not replace_dataset:
                        # If replace_dataset is None, the Library level permissions will be taken from the folder and applied to the new
                        # LDDA and LibraryDataset.
                        trans.app.security_agent.copy_library_permissions( trans, folder, ldda )
                        trans.app.security_agent.copy_library_permissions( trans, folder, ldda.library_dataset )
                    else:
                        library_bunch = upload_common.handle_library_params( trans, kwd, folder_id, replace_dataset )
                        if library_bunch.template and library_bunch.template_field_contents:
                            # Since information templates are inherited, the template fields can be displayed on the upload form.
                            # If the user has added field contents, we'll need to create a new form_values and info_association
                            # for the new library_dataset_dataset_association object.
                            # Create a new FormValues object, using the template we previously retrieved
                            form_values = trans.app.model.FormValues( library_bunch.template, library_bunch.template_field_contents )
                            trans.sa_session.add( form_values )
                            trans.sa_session.flush()
                            # Create a new info_association between the current ldda and form_values
                            info_association = trans.app.model.LibraryDatasetDatasetInfoAssociation( ldda, library_bunch.template, form_values )
                            trans.sa_session.add( info_association )
                            trans.sa_session.flush()
                    # Make sure to apply any defined dataset permissions, allowing the permissions inherited from the folder to
                    # over-ride the same permissions on the dataset, if they exist.
                    dataset_permissions_dict = trans.app.security_agent.get_permissions( hda.dataset )
                    current_library_dataset_actions = [ permission.action for permission in ldda.library_dataset.actions ]
                    # The DATASET_MANAGE_PERMISSIONS permission on a dataset is a special case because if
                    # it exists, then we need to apply the LIBRARY_MANAGE permission to the library dataset.
                    dataset_manage_permissions_action = trans.app.security_agent.get_action( 'DATASET_MANAGE_PERMISSIONS' ).action
                    flush_needed = False
                    for action, dataset_permissions_roles in dataset_permissions_dict.items():
                        if isinstance( action, Action ):
                            action = action.action
                        if action == dataset_manage_permissions_action:
                            # Apply the LIBRARY_MANAGE permission to the library dataset.
                            action = trans.app.security_agent.get_action( 'LIBRARY_MANAGE' ).action
                        # Allow the permissions inherited from the folder to over-ride the same permissions on the dataset.
                        if action not in current_library_dataset_actions:
                            for ldp in [ trans.model.LibraryDatasetPermissions( action, ldda.library_dataset, role ) for role in dataset_permissions_roles ]:
                                trans.sa_session.add( ldp )
                                flush_needed = True
                    if flush_needed:
                        trans.sa_session.flush()
                    # Permissions must be the same on the LibraryDatasetDatasetAssociation and the associated LibraryDataset
                    trans.app.security_agent.copy_library_permissions( trans, ldda.library_dataset, ldda )
                if created_ldda_ids:
                    created_ldda_ids = created_ldda_ids.lstrip( ',' )
                    ldda_id_list = created_ldda_ids.split( ',' )
                    total_added = len( ldda_id_list )
                    if replace_dataset:
                        message = "Added %d dataset versions to the library dataset '%s' in the folder '%s'." % ( total_added, escape( replace_dataset.name ), escape( folder.name ) )
                    else:
                        if not folder.parent:
                            # Libraries have the same name as their root_folder
                            message = "Added %d datasets to the library '%s' (each is selected).  " % ( total_added, escape( folder.name ) )
                        else:
                            message = "Added %d datasets to the folder '%s' (each is selected).  " % ( total_added, escape( folder.name ) )
                        if cntrller == 'library_admin':
                            message += "Click the Go button at the bottom of this page to edit the permissions on these datasets if necessary."
                        else:
                            # Since permissions on all LibraryDatasetDatasetAssociations must be the same at this point, we only need
                            # to check one of them to see if the current user can manage permissions on them.
                            check_ldda = trans.sa_session.query( trans.app.model.LibraryDatasetDatasetAssociation ).get( ldda_id_list[0] )
                            if trans.app.security_agent.can_manage_library_item( current_user_roles, check_ldda ):
                                if not replace_dataset:
                                    message += "Click the Go button at the bottom of this page to edit the permissions on these datasets if necessary."
                    return trans.response.send_redirect( web.url_for( controller='library_common',
                                                                      action='browse_library',
                                                                      cntrller=cntrller,
                                                                      id=library_id,
                                                                      created_ldda_ids=created_ldda_ids,
                                                                      show_deleted=show_deleted,
                                                                      message=message,
                                                                      status='done' ) )
            else:
                message = 'Select at least one dataset from the list of active datasets in your current history'
                status = 'error'
                upload_option = kwd.get( 'upload_option', 'import_from_history' )
                # Send list of data formats to the upload form so the "extension" select list can be populated dynamically
                file_formats = trans.app.datatypes_registry.upload_file_formats
                # Send list of genome builds to the form so the "dbkey" select list can be populated dynamically

                def get_dbkey_options( last_used_build ):
                    for dbkey, build_name in trans.app.genome_builds.get_genome_build_names( trans=trans ):
                        yield build_name, dbkey, ( dbkey == last_used_build )
                dbkeys = get_dbkey_options( last_used_build )
                # Send the current history to the form to enable importing datasets from history to library
                history = trans.get_history()
                trans.sa_session.refresh( history )
                action = 'add_history_datasets_to_library'
                upload_option_select_list = self._build_upload_option_select_list( trans, upload_option, is_admin )
                roles_select_list = self._build_roles_select_list( trans, cntrller, library, util.listify( roles ) )
                return trans.fill_template( "/library/common/upload.mako",
                                            cntrller=cntrller,
                                            upload_option_select_list=upload_option_select_list,
                                            upload_option=upload_option,
                                            action=action,
                                            library_id=library_id,
                                            folder_id=folder_id,
                                            replace_dataset=replace_dataset,
                                            file_formats=file_formats,
                                            dbkeys=dbkeys,
                                            last_used_build=last_used_build,
                                            roles_select_list=roles_select_list,
                                            history=history,
                                            widgets=[],
                                            template_id=template_id,
                                            to_posix_lines=to_posix_lines,
                                            space_to_tab=space_to_tab,
                                            link_data_only=link_data_only,
                                            show_deleted=show_deleted,
                                            ldda_message=ldda_message,
                                            message=escape( message ),
                                            status=escape( status ) )

    def _build_roles_select_list( self, trans, cntrller, library, selected_role_ids=[] ):
        # Get the list of legitimate roles to display on the upload form.  If the library is public,
        # all active roles are legitimate.  If the library is restricted by the LIBRARY_ACCESS permission, only
        # the set of all roles associated with users that have that permission are legitimate.
        legitimate_roles = trans.app.security_agent.get_legitimate_roles( trans, library, cntrller )
        if legitimate_roles:
            # Build the roles multi-select list using the list of legitimate roles, making sure to select any that
            # were selected before refresh_on_change, if one occurred.
            roles_select_list = SelectField( "roles", multiple="true", size="5" )
            for role in legitimate_roles:
                selected = str( role.id ) in selected_role_ids
                roles_select_list.add_option( text=role.name, value=str( role.id ), selected=selected )
            return roles_select_list
        else:
            return None

    def _build_upload_option_select_list( self, trans, upload_option, is_admin, do_not_include_values=[] ):
        # Build the upload_option select list.  The do_not_include_values param can contain options that
        # should not be included in the list.  For example, the 'upload_directory' option should not be
        # included if uploading a new version of a library dataset.
        upload_refresh_on_change_values = []
        for option_value, option_label in trans.model.LibraryDataset.upload_options:
            if option_value not in do_not_include_values:
                upload_refresh_on_change_values.append( option_value )
        upload_option_select_list = SelectField( 'upload_option',
                                                 refresh_on_change=True,
                                                 refresh_on_change_values=upload_refresh_on_change_values )
        for option_value, option_label in trans.model.LibraryDataset.upload_options:
            if option_value not in do_not_include_values:
                if option_value == 'upload_directory':
                    if is_admin and not trans.app.config.library_import_dir:
                        continue
                    elif not is_admin:
                        if not trans.app.config.user_library_import_dir:
                            continue
                        path = os.path.join( trans.app.config.user_library_import_dir, trans.user.email )
                        if not os.path.isdir( path ):
                            try:
                                os.makedirs( path )
                            except:
                                continue
                elif option_value == 'upload_paths':
                    if not is_admin or not trans.app.config.allow_library_path_paste:
                        continue
                upload_option_select_list.add_option( option_label, option_value, selected=option_value == upload_option )
        return upload_option_select_list

    @web.expose
    def download_dataset_from_folder( self, trans, cntrller, id, library_id=None, **kwd ):
        """Catches the dataset id and displays file contents as directed"""
        show_deleted = util.string_as_bool( kwd.get( 'show_deleted', False ) )
        use_panels = util.string_as_bool( kwd.get( 'use_panels', False ) )
        is_admin = trans.user_is_admin() and cntrller == 'library_admin'
        current_user_roles = trans.get_current_user_roles()
        try:
            ldda = trans.sa_session.query( trans.app.model.LibraryDatasetDatasetAssociation ).get( trans.security.decode_id( id ) )
        except:
            ldda = None
        self._check_access( trans, cntrller, is_admin, ldda, current_user_roles, use_panels, library_id, show_deleted )
        composite_extensions = trans.app.datatypes_registry.get_composite_extensions( )
        ext = ldda.extension
        if ext in composite_extensions:
            # is composite - must return a zip of contents and the html file itself - ugh - should be reversible at upload!
            # use act_on_multiple_datasets( self, trans, cntrller, library_id, ldda_ids='', **kwd ) since it does what we need
            kwd['do_action'] = 'zip'
            return self.act_on_multiple_datasets( trans, cntrller, library_id, ldda_ids=[id, ], **kwd )
        else:
            trans.response.set_content_type( ldda.get_mime() )
            fStat = os.stat( ldda.file_name )
            trans.response.headers[ 'Content-Length' ] = int( fStat.st_size )
            fname = ldda.name
            fname = ''.join( c in FILENAME_VALID_CHARS and c or '_' for c in fname )[ 0:150 ]
            trans.response.headers[ "Content-Disposition" ] = 'attachment; filename="%s"' % fname
            try:
                return open( ldda.file_name )
            except:
                message = 'This dataset contains no content'
        return trans.response.send_redirect( web.url_for( controller='library_common',
                                                          action='browse_library',
                                                          cntrller=cntrller,
                                                          use_panels=use_panels,
                                                          id=library_id,
                                                          show_deleted=show_deleted,
                                                          message=message,
                                                          status='error' ) )

    @web.expose
    def library_dataset_info( self, trans, cntrller, id, library_id, **kwd ):
        message = escape( kwd.get( 'message', '' ) )
        status = kwd.get( 'status', 'done' )
        show_deleted = util.string_as_bool( kwd.get( 'show_deleted', False ) )
        use_panels = util.string_as_bool( kwd.get( 'use_panels', False ) )
        is_admin = trans.user_is_admin() and cntrller == 'library_admin'
        current_user_roles = trans.get_current_user_roles()
        try:
            library_dataset = trans.sa_session.query( trans.app.model.LibraryDataset ).get( trans.security.decode_id( id ) )
        except:
            library_dataset = None
        self._check_access( trans, cntrller, is_admin, library_dataset, current_user_roles, use_panels, library_id, show_deleted )
        if kwd.get( 'edit_attributes_button', False ):
            self._check_modify( trans, cntrller, is_admin, library_dataset, current_user_roles, use_panels, library_id, show_deleted )
            new_name = kwd.get( 'name', '' )
            new_info = kwd.get( 'info', '' )
            if not new_name:
                message = 'Enter a valid name'
                status = 'error'
            else:
                library_dataset.name = new_name
                library_dataset.info = new_info
                trans.sa_session.add( library_dataset )
                trans.sa_session.flush()
                message = "Information updated for library dataset '%s'." % escape( library_dataset.name )
                status = 'done'
        # See if we have any associated templates
        widgets = []
        widget_fields_have_contents = False
        info_association, inherited = library_dataset.library_dataset_dataset_association.get_info_association()
        if info_association and ( not( inherited ) or info_association.inheritable ):
            widgets = library_dataset.library_dataset_dataset_association.get_template_widgets( trans )
            widget_fields_have_contents = self.widget_fields_have_contents( widgets )
        return trans.fill_template( '/library/common/library_dataset_info.mako',
                                    cntrller=cntrller,
                                    use_panels=use_panels,
                                    library_dataset=library_dataset,
                                    library_id=library_id,
                                    current_user_roles=current_user_roles,
                                    info_association=info_association,
                                    inherited=inherited,
                                    widgets=widgets,
                                    widget_fields_have_contents=widget_fields_have_contents,
                                    show_deleted=show_deleted,
                                    message=escape( message ),
                                    status=escape( status ) )

    @web.expose
    def library_dataset_permissions( self, trans, cntrller, id, library_id, **kwd ):
        message = escape( kwd.get( 'message', '' ) )
        status = kwd.get( 'status', 'done' )
        show_deleted = util.string_as_bool( kwd.get( 'show_deleted', False ) )
        use_panels = util.string_as_bool( kwd.get( 'use_panels', False ) )
        is_admin = trans.user_is_admin() and cntrller == 'library_admin'
        current_user_roles = trans.get_current_user_roles()
        try:
            library_dataset = trans.sa_session.query( trans.app.model.LibraryDataset ).get( trans.security.decode_id( id ) )
        except:
            library_dataset = None
        self._check_access( trans, cntrller, is_admin, library_dataset, current_user_roles, use_panels, library_id, show_deleted )
        self._check_manage( trans, cntrller, is_admin, library_dataset, current_user_roles, use_panels, library_id, show_deleted )
        if kwd.get( 'update_roles_button', False ):
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
            error = trans.app.security_agent.set_all_library_permissions( trans, library_dataset, permissions )
            trans.sa_session.refresh( library_dataset )
            if error:
                message = error
                status = 'error'
            else:
                # Set the LIBRARY permissions on the LibraryDatasetDatasetAssociation
                trans.app.security_agent.set_all_library_permissions( trans, library_dataset.library_dataset_dataset_association, permissions )
                trans.sa_session.refresh( library_dataset.library_dataset_dataset_association )
                message = "Permisisons updated for library dataset '%s'." % escape( library_dataset.name )
                status = 'done'
        roles = trans.app.security_agent.get_legitimate_roles( trans, library_dataset, cntrller )
        return trans.fill_template( '/library/common/library_dataset_permissions.mako',
                                    cntrller=cntrller,
                                    use_panels=use_panels,
                                    library_dataset=library_dataset,
                                    library_id=library_id,
                                    roles=roles,
                                    current_user_roles=current_user_roles,
                                    show_deleted=show_deleted,
                                    message=escape( message ),
                                    status=escape( status ) )

    @web.expose
    def make_library_item_public( self, trans, cntrller, library_id, item_type, id, **kwd ):
        message = escape( kwd.get( 'message', '' ) )
        status = kwd.get( 'status', 'done' )
        show_deleted = util.string_as_bool( kwd.get( 'show_deleted', False ) )
        use_panels = util.string_as_bool( kwd.get( 'use_panels', False ) )
        current_user_roles = trans.get_current_user_roles()
        is_admin = trans.user_is_admin() and cntrller == 'library_admin'
        if item_type == 'library':
            library = trans.sa_session.query( trans.model.Library ).get( trans.security.decode_id( id ) )
            self._check_access( trans, cntrller, is_admin, library, current_user_roles, use_panels, library_id, show_deleted )
            self._check_manage( trans, cntrller, is_admin, library, current_user_roles, use_panels, library_id, show_deleted )
            contents = util.string_as_bool( kwd.get( 'contents', 'False' ) )
            trans.app.security_agent.make_library_public( library, contents=contents )
            if contents:
                message = "The data library (%s) and all its contents have been made publicly accessible." % escape( library.name )
            else:
                message = "The data library (%s) has been made publicly accessible, but access to its contents has been left unchanged." % escape( library.name )
        elif item_type == 'folder':
            folder = trans.sa_session.query( trans.model.LibraryFolder ).get( trans.security.decode_id( id ) )
            self._check_access( trans, cntrller, is_admin, folder, current_user_roles, use_panels, library_id, show_deleted )
            self._check_manage( trans, cntrller, is_admin, folder, current_user_roles, use_panels, library_id, show_deleted )
            trans.app.security_agent.make_folder_public( folder )
            message = "All of the contents of folder (%s) have been made publicly accessible." % escape( folder.name )
        elif item_type == 'ldda':
            ldda = trans.sa_session.query( trans.model.LibraryDatasetDatasetAssociation ).get( trans.security.decode_id( id ) )
            self._check_access( trans, cntrller, is_admin, ldda.library_dataset, current_user_roles, use_panels, library_id, show_deleted )
            self._check_manage( trans, cntrller, is_admin, ldda.library_dataset, current_user_roles, use_panels, library_id, show_deleted )
            trans.app.security_agent.make_dataset_public( ldda.dataset )
            message = "The libary dataset (%s) has been made publicly accessible." % escape( ldda.name )
        else:
            message = "Invalid item_type (%s) received." % escape( str( item_type ) )
            status = 'error'
        return trans.response.send_redirect( web.url_for( controller='library_common',
                                                          action='browse_library',
                                                          cntrller=cntrller,
                                                          use_panels=use_panels,
                                                          id=library_id,
                                                          show_deleted=show_deleted,
                                                          message=message,
                                                          status=status ) )

    @web.expose
    def act_on_multiple_datasets( self, trans, cntrller, library_id=None, ldda_ids='', **kwd ):
        # This method is called from 1 of 3 places:
        # - this controller's download_dataset_from_folder() method
        # - he browse_library.mako template
        # - the library_dataset_search_results.mako template
        # In the last case above, we will not have a library_id
        class NgxZip( object ):
            def __init__( self, url_base ):
                self.files = {}
                self.url_base = url_base

            def add( self, file, relpath ):
                self.files[file] = relpath

            def __str__( self ):
                rval = ''
                for fname, relpath in self.files.items():
                    crc = '-'
                    size = os.stat( fname ).st_size
                    quoted_fname = urllib.quote_plus( fname, '/' )
                    rval += '%s %i %s%s %s\r\n' % ( crc, size, self.url_base, quoted_fname, relpath )
                return rval
        # Perform an action on a list of library datasets.
        message = escape( kwd.get( 'message', '' ) )
        status = kwd.get( 'status', 'done' )
        show_deleted = util.string_as_bool( kwd.get( 'show_deleted', False ) )
        use_panels = util.string_as_bool( kwd.get( 'use_panels', False ) )
        action = kwd.get( 'do_action', None )
        lddas = []
        error = False
        is_admin = trans.user_is_admin() and cntrller == 'library_admin'
        current_user_roles = trans.get_current_user_roles()
        current_history = trans.get_history()
        if not ldda_ids:
            error = True
            message = 'You must select at least one dataset.'
        elif not action:
            error = True
            message = 'You must select an action to perform on the selected datasets.'
        else:
            if action in [ 'import_to_current_history', 'import_to_histories' ]:
                new_kwd = {}
                if current_history is not None and action == 'import_to_current_history':
                    encoded_current_history_id = trans.security.encode_id( current_history.id )
                    selected_history_id = encoded_current_history_id
                    new_kwd[ 'do_action' ] = action
                    new_kwd[ 'target_history_ids' ] = encoded_current_history_id
                    new_kwd[ 'import_datasets_to_histories_button' ] = 'Import library datasets'
                else:
                    selected_history_id = ''
                return trans.response.send_redirect( web.url_for( controller='library_common',
                                                                  action='import_datasets_to_histories',
                                                                  cntrller=cntrller,
                                                                  library_id=library_id,
                                                                  selected_history_id=selected_history_id,
                                                                  ldda_ids=ldda_ids,
                                                                  use_panels=use_panels,
                                                                  show_deleted=show_deleted,
                                                                  message=message,
                                                                  status=status,
                                                                  **new_kwd ) )
            if action == 'move':
                if library_id in [ 'none', 'None', None ]:
                    source_library_id = ''
                else:
                    source_library_id = library_id
                return trans.response.send_redirect( web.url_for( controller='library_common',
                                                                  action='move_library_item',
                                                                  cntrller=cntrller,
                                                                  source_library_id=source_library_id,
                                                                  item_type='ldda',
                                                                  item_id=ldda_ids,
                                                                  use_panels=use_panels,
                                                                  show_deleted=show_deleted,
                                                                  message=message,
                                                                  status=status ) )
            ldda_ids = util.listify( ldda_ids )
            for ldda_id in ldda_ids:
                try:
                    # Load the ldda requested and check whether the user has access to them
                    ldda = self.get_library_dataset_dataset_association( trans, ldda_id )
                    assert not ldda.dataset.purged
                    lddas.append( ldda )
                except:
                    ldda = None
                    message += "Invalid library dataset id (%s) specified.  " % str( ldda_id )
        if not error:
            if action == 'manage_permissions':
                valid_ldda_ids = []
                valid_lddas = []
                invalid_lddas = []
                for ldda in lddas:
                    if is_admin or trans.app.security_agent.can_manage_library_item( current_user_roles, ldda ):
                        valid_lddas.append( ldda )
                        valid_ldda_ids.append( ldda.id )
                    else:
                        invalid_lddas.append( ldda )
                if invalid_lddas:
                    message += "You are not authorized to manage permissions on %s: " % inflector.cond_plural( len( invalid_lddas ), "dataset" )
                    for ldda in invalid_lddas:
                        message += '(%s)' % escape( ldda.name )
                    message += '.  '
                if valid_ldda_ids:
                    encoded_ldda_ids = [ trans.security.encode_id( ldda_id ) for ldda_id in valid_ldda_ids ]
                    folder_id = trans.security.encode_id( valid_lddas[0].library_dataset.folder.id )
                    trans.response.send_redirect( web.url_for( controller='library_common',
                                                               action='ldda_permissions',
                                                               cntrller=cntrller,
                                                               use_panels=use_panels,
                                                               library_id=library_id,
                                                               folder_id=folder_id,
                                                               id=",".join( encoded_ldda_ids ),
                                                               show_deleted=show_deleted,
                                                               message=message,
                                                               status=status ) )
                else:
                    message = "You are not authorized to manage permissions on any of the selected datasets."
            elif action == 'delete':
                valid_lddas = []
                invalid_lddas = []
                for ldda in lddas:
                    if is_admin or trans.app.security_agent.can_modify_library_item( current_user_roles, ldda ):
                        valid_lddas.append( ldda )
                    else:
                        invalid_lddas.append( ldda )
                if invalid_lddas:
                    message += "You are not authorized to delete %s: " % inflector.cond_plural( len( invalid_lddas ), "dataset" )
                    for ldda in invalid_lddas:
                        message += '(%s)' % ldda.name
                    message += '.  '
                if valid_lddas:
                    for ldda in valid_lddas:
                        # Do not delete the association, just delete the library_dataset.  The
                        # cleanup_datasets.py script handles everything else.
                        ld = ldda.library_dataset
                        ld.deleted = True
                        trans.sa_session.add( ld )
                    trans.sa_session.flush()
                    num_valid_lddas = len( valid_lddas )
                    message += "Deleted %i %s." % ( num_valid_lddas, inflector.cond_plural( num_valid_lddas, "dataset" ) )
                else:
                    message = "You are not authorized to delete any of the selected datasets."
            elif action in [ 'zip', 'tgz', 'tbz', 'ngxzip' ]:
                error = False
                killme = string.punctuation + string.whitespace
                trantab = string.maketrans(killme, '_' * len(killme))
                try:
                    outext = 'zip'
                    if action == 'zip':
                        # Can't use mkstemp - the file must not exist first
                        tmpd = tempfile.mkdtemp()
                        util.umask_fix_perms( tmpd, trans.app.config.umask, 0777, self.app.config.gid )
                        tmpf = os.path.join( tmpd, 'library_download.' + action )
                        if trans.app.config.upstream_gzip:
                            archive = zipfile.ZipFile( tmpf, 'w', zipfile.ZIP_STORED, True )
                        else:
                            archive = zipfile.ZipFile( tmpf, 'w', zipfile.ZIP_DEFLATED, True )
                        archive.add = lambda x, y: archive.write( x, y.encode('CP437') )
                    elif action == 'tgz':
                        if trans.app.config.upstream_gzip:
                            archive = StreamBall( 'w|' )
                            outext = 'tar'
                        else:
                            archive = StreamBall( 'w|gz' )
                            outext = 'tgz'
                    elif action == 'tbz':
                        archive = StreamBall( 'w|bz2' )
                        outext = 'tbz2'
                    elif action == 'ngxzip':
                        archive = NgxZip( trans.app.config.nginx_x_archive_files_base )
                except ( OSError, zipfile.BadZipfile ):
                    error = True
                    log.exception( "Unable to create archive for download" )
                    message = "Unable to create archive for download, please report this error"
                    status = 'error'
                except:
                    error = True
                    log.exception( "Unexpected error %s in create archive for download" % sys.exc_info()[0] )
                    message = "Unable to create archive for download, please report - %s" % sys.exc_info()[0]
                    status = 'error'
                if not error:
                    composite_extensions = trans.app.datatypes_registry.get_composite_extensions()
                    seen = []
                    for ldda in lddas:
                        if ldda.dataset.state in [ 'new', 'upload', 'queued', 'running', 'empty', 'discarded' ]:
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
                        while path in seen:
                            path += '_'
                        seen.append( path )
                        zpath = os.path.split(path)[-1]  # comes as base_name/fname
                        outfname, zpathext = os.path.splitext(zpath)
                        if is_composite:
                            # need to add all the components from the extra_files_path to the zip
                            if zpathext == '':
                                zpath = '%s.html' % zpath  # fake the real nature of the html file
                            try:
                                archive.add(ldda.dataset.file_name, zpath)  # add the primary of a composite set
                            except IOError:
                                error = True
                                log.exception( "Unable to add composite parent %s to temporary library download archive" % ldda.dataset.file_name)
                                message = "Unable to create archive for download, please report this error"
                                status = 'error'
                                continue
                            flist = glob.glob(os.path.join(ldda.dataset.extra_files_path, '*.*'))  # glob returns full paths
                            for fpath in flist:
                                efp, fname = os.path.split(fpath)
                                if fname > '':
                                    fname = fname.translate(trantab)
                                try:
                                    archive.add( fpath, fname )
                                except IOError:
                                    error = True
                                    log.exception( "Unable to add %s to temporary library download archive %s" % (fname, outfname))
                                    message = "Unable to create archive for download, please report this error"
                                    status = 'error'
                                    continue
                        else:  # simple case
                            try:
                                archive.add( ldda.dataset.file_name, path )
                            except IOError:
                                error = True
                                log.exception( "Unable to write %s to temporary library download archive" % ldda.dataset.file_name)
                                message = "Unable to create archive for download, please report this error"
                                status = 'error'
                    if not error:
                        if library_id:
                            lname = trans.sa_session.query( trans.app.model.Library ).get( trans.security.decode_id( library_id ) ).name
                        else:
                            # Request must have coe from the library_dataset_search_results page.
                            lname = 'selected_dataset'
                        fname = lname.replace( ' ', '_' ) + '_files'
                        if action == 'zip':
                            archive.close()
                            trans.response.set_content_type( "application/x-zip-compressed" )
                            trans.response.headers[ "Content-Disposition" ] = 'attachment; filename="%s.%s"' % (fname, outext)
                            archive = util.streamball.ZipBall(tmpf, tmpd)
                            archive.wsgi_status = trans.response.wsgi_status()
                            archive.wsgi_headeritems = trans.response.wsgi_headeritems()
                            return archive.stream
                        elif action == 'ngxzip':
                            trans.response.set_content_type( "application/zip" )
                            trans.response.headers[ "Content-Disposition" ] = 'attachment; filename="%s.%s"' % (fname, outext)
                            trans.response.headers[ "X-Archive-Files" ] = "zip"
                            return archive
                        else:
                            trans.response.set_content_type( "application/x-tar" )
                            trans.response.headers[ "Content-Disposition" ] = 'attachment; filename="%s.%s"' % (fname, outext)
                            archive.wsgi_status = trans.response.wsgi_status()
                            archive.wsgi_headeritems = trans.response.wsgi_headeritems()
                            return archive.stream
            else:
                status = 'error'
                message = 'Invalid action (%s) specified.' % escape( str( action ) )
        if library_id:
            # If we have a library_id, browse the associated library
            return trans.response.send_redirect( web.url_for( controller='library_common',
                                                              action='browse_library',
                                                              cntrller=cntrller,
                                                              current_user_roles=current_user_roles,
                                                              use_panels=use_panels,
                                                              id=library_id,
                                                              show_deleted=show_deleted,
                                                              message=message,
                                                              status=status ) )
        else:
            # We arrived here from the library_dataset_search_results page, so redirect there.
            search_term = kwd.get( 'search_term', '' )
            comptypes = get_comptypes( trans )
            return trans.fill_template( '/library/common/library_dataset_search_results.mako',
                                        cntrller=cntrller,
                                        current_user_roles=current_user_roles,
                                        search_term=search_term,
                                        comptypes=comptypes,
                                        lddas=lddas,
                                        show_deleted=show_deleted,
                                        use_panels=use_panels,
                                        message=escape( message ),
                                        status=escape( status ) )

    @web.expose
    def import_datasets_to_histories( self, trans, cntrller, library_id='', folder_id='', ldda_ids='', target_history_id='', target_history_ids='', new_history_name='', **kwd ):
        # This method is called from one of the following places:
        # - a menu option for a library dataset ( ldda_ids is a single ldda id )
        # - a menu option for a library folder ( folder_id has a value )
        # - a select list option for acting on multiple selected datasets within a library
        #   ( ldda_ids is a comma separated string of ldda ids )
        # - a menu option for a library dataset search result set ( ldda_ids is a comma separated string of ldda ids )
        message = escape( kwd.get( 'message', '' ) )
        status = kwd.get( 'status', 'done' )
        show_deleted = util.string_as_bool( kwd.get( 'show_deleted', False ) )
        use_panels = util.string_as_bool( kwd.get( 'use_panels', False ) )
        action = kwd.get( 'do_action', None )
        user = trans.get_user()
        current_history = trans.get_history()
        if library_id:
            library = trans.sa_session.query( trans.model.Library ).get( trans.security.decode_id( library_id ) )
        else:
            library = None
        if folder_id:
            folder = trans.sa_session.query( trans.model.LibraryFolder ).get( trans.security.decode_id( folder_id ) )
        else:
            folder = None
        ldda_ids = util.listify( ldda_ids )
        if ldda_ids:
            ldda_ids = map( trans.security.decode_id, ldda_ids )
        if target_history_ids:
            target_history_ids = util.listify( target_history_ids )
            target_history_ids = set(
                [ trans.security.decode_id( thid )
                    for thid in target_history_ids if thid ] )
        elif target_history_id:
            target_history_ids = [ trans.security.decode_id( target_history_id ) ]
        if kwd.get( 'import_datasets_to_histories_button', False ):
            invalid_datasets = 0
            if not ldda_ids or not ( target_history_ids or new_history_name ):
                message = "You must provide one or more source library datasets and one or more target histories."
                status = 'error'
            else:
                if new_history_name:
                    new_history = trans.app.model.History()
                    new_history.name = new_history_name
                    new_history.user = user
                    trans.sa_session.add( new_history )
                    trans.sa_session.flush()
                    target_history_ids = [ new_history.id ]
                    target_histories = [ new_history ]
                elif user:
                    target_histories = [ hist for hist in map( trans.sa_session.query( trans.app.model.History ).get, target_history_ids ) if ( hist is not None and hist.user == user )]
                else:
                    target_histories = [ current_history ]
                if len( target_histories ) != len( target_history_ids ):
                    message += "You do not have permission to add datasets to %i requested histories.  " % ( len( target_history_ids ) - len( target_histories ) )
                    status = 'error'
                flush_needed = False
                for ldda in map( trans.sa_session.query( trans.app.model.LibraryDatasetDatasetAssociation ).get, ldda_ids ):
                    if ldda is None:
                        message += "You tried to import a dataset that does not exist.  "
                        status = 'error'
                        invalid_datasets += 1
                    elif ldda.dataset.state not in [ trans.model.Dataset.states.OK, trans.model.Dataset.states.ERROR ]:
                        message += "You cannot import dataset '%s' since its state is '%s'.  " % ( escape( ldda.name ), ldda.dataset.state )
                        status = 'error'
                        invalid_datasets += 1
                    elif not ldda.has_data():
                        message += "You cannot import empty dataset '%s'.  " % escape( ldda.name )
                        status = 'error'
                        invalid_datasets += 1
                    else:
                        for target_history in target_histories:
                            ldda.to_history_dataset_association( target_history=target_history, add_to_history=True )
                            if not flush_needed:
                                flush_needed = True
                if flush_needed:
                    trans.sa_session.flush()
                    hist_names_str = ", ".join( [ target_history.name for target_history in target_histories ] )
                    num_source = len( ldda_ids ) - invalid_datasets
                    num_target = len( target_histories )
                    message += "%i %s imported into %i %s: %s" % ( num_source,
                                                                   inflector.cond_plural( num_source, "dataset" ),
                                                                   num_target,
                                                                   inflector.cond_plural( num_target, "history" ),
                                                                   hist_names_str )
                trans.sa_session.refresh( current_history )
        current_user_roles = trans.get_current_user_roles()
        source_lddas = []
        if folder:
            for library_dataset in folder.datasets:
                ldda = library_dataset.library_dataset_dataset_association
                if not ldda.deleted and trans.app.security_agent.can_access_library_item( current_user_roles, ldda, trans.user ):
                    source_lddas.append( ldda )
        elif ldda_ids:
            for ldda_id in ldda_ids:
                # Secuirty access permiision chcck is not needed here since the current user had access
                # to the lddas in order for the menu optin  to be available.
                ldda = trans.sa_session.query( trans.model.LibraryDatasetDatasetAssociation ).get( ldda_id )
                source_lddas.append( ldda )
        if current_history is None:
            current_history = trans.get_history( create=True )
        if current_history is not None:
            target_histories = [ current_history ]
        else:
            target_histories = []
            message = 'You must have a history before you can import datasets.  You can do this by loading the analysis interface.'
            status = 'error'
        if user:
            target_histories = user.active_histories
        if action == 'import_to_current_history' and library_id:
            # To streamline this as much as possible, go back to browsing the library.
            return trans.response.send_redirect( web.url_for( controller='library_common',
                                                              action='browse_library',
                                                              cntrller=cntrller,
                                                              id=library_id,
                                                              message=message,
                                                              status=status ) )
        return trans.fill_template( "/library/common/import_datasets_to_histories.mako",
                                    cntrller=cntrller,
                                    library=library,
                                    current_history=current_history,
                                    ldda_ids=ldda_ids,
                                    target_history_id=target_history_id,
                                    target_history_ids=target_history_ids,
                                    source_lddas=source_lddas,
                                    target_histories=target_histories,
                                    new_history_name=new_history_name,
                                    show_deleted=show_deleted,
                                    use_panels=use_panels,
                                    message=escape( message ),
                                    status=escape( status ) )

    @web.expose
    def manage_template_inheritance( self, trans, cntrller, item_type, library_id, folder_id=None, ldda_id=None, **kwd ):
        show_deleted = util.string_as_bool( kwd.get( 'show_deleted', False ) )
        use_panels = util.string_as_bool( kwd.get( 'use_panels', False ) )
        message = escape( kwd.get( 'message', '' ) )
        is_admin = ( trans.user_is_admin() and cntrller == 'library_admin' )
        current_user_roles = trans.get_current_user_roles()
        try:
            item, item_desc, action, id = self.get_item_and_stuff( trans,
                                                                   item_type=item_type,
                                                                   library_id=library_id,
                                                                   folder_id=folder_id,
                                                                   ldda_id=ldda_id,
                                                                   is_admin=is_admin )
        except ValueError:
            return None
        if not ( is_admin or trans.app.security_agent.can_modify_library_item( current_user_roles, item ) ):
            message = "You are not authorized to modify %s '%s'." % ( escape( item_desc ), escape( item.name ) )
            return trans.response.send_redirect( web.url_for( controller='library_common',
                                                              action='browse_library',
                                                              cntrller=cntrller,
                                                              id=library_id,
                                                              show_deleted=show_deleted,
                                                              message=message,
                                                              status='error' ) )
        info_association, inherited = item.get_info_association( restrict=True )
        if info_association:
            if info_association.inheritable:
                message = "The template for this %s will no longer be inherited to contained folders and datasets." % escape( item_desc )
            else:
                message = "The template for this %s will now be inherited to contained folders and datasets." % escape( item_desc )
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
                                                          message=message,
                                                          status='done' ) )

    @web.expose
    def move_library_item( self, trans, cntrller, item_type, item_id, source_library_id='', make_target_current=True, **kwd ):
        # This method is called from one of the following places:
        # - a menu option for a library dataset ( item_type is 'ldda' and item_id is a single ldda id )
        # - a menu option for a library folder ( item_type is 'folder' and item_id is a single folder id )
        # - a select list option for acting on multiple selected datasets within a library ( item_type is
        #   'ldda' and item_id is a comma separated string of ldda ids )
        # - a menu option for a library dataset search result set ( item_type is 'ldda' and item_id is a
        #   comma separated string of ldda ids )
        message = escape( kwd.get( 'message', '' ) )
        status = kwd.get( 'status', 'done' )
        show_deleted = util.string_as_bool( kwd.get( 'show_deleted', False ) )
        use_panels = util.string_as_bool( kwd.get( 'use_panels', False ) )
        make_target_current = util.string_as_bool( make_target_current )
        is_admin = trans.user_is_admin() and cntrller == 'library_admin'
        user = trans.get_user()
        current_user_roles = trans.get_current_user_roles()
        move_ldda_ids = []
        move_lddas = []
        move_folder_id = []
        move_folder = None
        if source_library_id:
            source_library = trans.sa_session.query( trans.model.Library ).get( trans.security.decode_id( source_library_id ) )
        else:
            # Request sent from the library_dataset_search_results page.
            source_library = None
        target_library_id = kwd.get( 'target_library_id', '' )
        if target_library_id not in [ '', 'none', None ]:
            target_library = trans.sa_session.query( trans.model.Library ).get( trans.security.decode_id( target_library_id ) )
        elif make_target_current:
            target_library = source_library
        else:
            target_library = None
        target_folder_id = kwd.get( 'target_folder_id', '' )
        if target_folder_id not in [ '', 'none', None ]:
            target_folder = trans.sa_session.query( trans.model.LibraryFolder ).get( trans.security.decode_id( target_folder_id ) )
            if target_library is None:
                target_library = target_folder.parent_library
        else:
            target_folder = None
        if item_type == 'ldda':
            # We've been called from a menu option for a library dataset search result set
            move_ldda_ids = util.listify( item_id )
            if move_ldda_ids:
                move_ldda_ids = map( trans.security.decode_id, move_ldda_ids )
        elif item_type == 'folder':
            move_folder_id = item_id
            move_folder = trans.sa_session.query( trans.model.LibraryFolder ).get( trans.security.decode_id( move_folder_id ) )
        if kwd.get( 'move_library_item_button', False ):
            if not ( move_ldda_ids or move_folder_id ) or target_folder_id in [ '', 'none', None ]:
                message = "You must select a source folder or one or more source datasets, and a target folder."
                status = 'error'
            else:
                valid_lddas = []
                invalid_lddas = []
                invalid_items = 0
                flush_required = False
                if item_type == 'ldda':
                    for ldda in map( trans.sa_session.query( trans.app.model.LibraryDatasetDatasetAssociation ).get, move_ldda_ids ):
                        if ldda is None:
                            message += "You tried to move a dataset that does not exist.  "
                            status = 'error'
                            invalid_items += 1
                        elif ldda.dataset.state not in [ trans.model.Dataset.states.OK, trans.model.Dataset.states.ERROR ]:
                            message += "You cannot move dataset '%s' since its state is '%s'.  " % ( ldda.name, ldda.dataset.state )
                            status = 'error'
                            invalid_items += 1
                        elif not ldda.has_data():
                            message += "You cannot move empty dataset '%s'.  " % ldda.name
                            status = 'error'
                            invalid_items += 1
                        else:
                            if is_admin:
                                library_dataset = ldda.library_dataset
                                library_dataset.folder = target_folder
                                trans.sa_session.add( library_dataset )
                                flush_required = True
                            else:
                                if trans.app.security_agent.can_modify_library_item( current_user_roles, ldda ):
                                    valid_lddas.append( ldda )
                                    library_dataset = ldda.library_dataset
                                    library_dataset.folder = target_folder
                                    trans.sa_session.add( library_dataset )
                                    flush_required = True
                                else:
                                    invalid_items += 1
                                    invalid_lddas.append( ldda )
                    if not valid_lddas:
                        message = "You are not authorized to move any of the selected datasets."
                    elif invalid_lddas:
                        message += "You are not authorized to move %s: " % inflector.cond_plural( len( invalid_lddas ), "dataset" )
                        for ldda in invalid_lddas:
                            message += '(%s)' % escape( ldda.name )
                        message += '.  '
                    num_source = len( move_ldda_ids ) - invalid_items
                    message = "%i %s moved to folder (%s) within data library (%s)" % ( num_source,
                                                                                        inflector.cond_plural( num_source, "dataset" ),
                                                                                        target_folder.name,
                                                                                        target_library.name )
                elif item_type == 'folder':
                    move_folder = trans.sa_session.query( trans.app.model.LibraryFolder ) \
                                                  .get( trans.security.decode_id( move_folder_id ) )
                    if move_folder is None:
                        message += "You tried to move a folder that does not exist.  "
                        status = 'error'
                        invalid_items += 1
                    else:
                        move_folder.parent = target_folder
                        trans.sa_session.add( move_folder )
                        flush_required = True
                    message = "Moved folder (%s) to folder (%s) within data library (%s) " % ( escape( move_folder.name ),
                                                                                               escape( target_folder.name ),
                                                                                               escape( target_library.name ) )
                if flush_required:
                    trans.sa_session.flush()
        if target_library:
            if is_admin:
                target_library_folders = target_library.get_active_folders( target_library.root_folder )
            else:
                folders_with_permission_to_add = []
                for folder in target_library.get_active_folders( target_library.root_folder ):
                    if trans.app.security_agent.can_add_library_item( current_user_roles, folder ):
                        folders_with_permission_to_add.append( folder )
                target_library_folders = folders_with_permission_to_add
        else:
            target_library_folders = []
        if item_type == 'ldda':
            for ldda_id in move_ldda_ids:
                # TODO: It is difficult to filter out undesired folders (e.g. the ldda's current
                # folder) if we have a list of lddas, but we may want to filter folders that
                # are easily handled.
                ldda = trans.sa_session.query( trans.model.LibraryDatasetDatasetAssociation ).get( ldda_id )
                move_lddas.append( ldda )
        elif item_type == 'folder':
            def __is_contained_in( folder1, folder2 ):
                # Return True if folder1 is contained in folder2
                if folder1.parent:
                    if folder1.parent == folder2:
                        return True
                    return __is_contained_in( folder1.parent, folder2 )
                return False
            filtered_folders = []
            for folder in target_library_folders:
                include = True
                if move_folder:
                    if __is_contained_in( folder, move_folder ):
                        # Don't allow moving a folder to one of its sub-folders (circular issues in db)
                        include = False
                    if move_folder.id == folder.id:
                        # Don't allow moving a folder to itself
                        include = False
                    if move_folder.parent and move_folder.parent.id == folder.id:
                        # Don't allow moving a folder to its current parent folder
                        include = False
                if include:
                    filtered_folders.append( folder )
            target_library_folders = filtered_folders

        def __build_target_library_id_select_field( trans, selected_value='none' ):
            # Get all the libraries for which the current user can add items.
            target_libraries = []
            if is_admin:
                for library in trans.sa_session.query( trans.model.Library ) \
                                               .filter( trans.model.Library.deleted == false() ) \
                                               .order_by( trans.model.Library.table.c.name ):
                    if source_library is None or library.id != source_library.id:
                        target_libraries.append( library )
            else:
                for library in trans.app.security_agent.get_accessible_libraries( trans, user ):
                    if source_library is None:
                        if trans.app.security_agent.can_add_library_item( current_user_roles, library ):
                            target_libraries.append( library )
                    elif library.id != source_library.id:
                        if trans.app.security_agent.can_add_library_item( current_user_roles, library ):
                            target_libraries.append( library )
            # A refresh_on_change is required to display the selected library's folders
            return build_select_field( trans,
                                       objs=target_libraries,
                                       label_attr='name',
                                       select_field_name='target_library_id',
                                       selected_value=selected_value,
                                       refresh_on_change=True )

        def __build_target_folder_id_select_field( trans, folders, selected_value='none' ):
            for folder in folders:
                if not folder.parent:
                    folder.name = 'Data library root'
                    break
            return build_select_field( trans,
                                       objs=folders,
                                       label_attr='name',
                                       select_field_name='target_folder_id',
                                       selected_value=selected_value,
                                       refresh_on_change=False )
        if target_library:
            selected_value = target_library.id
        else:
            selected_value = 'none'
        target_library_id_select_field = __build_target_library_id_select_field( trans, selected_value=selected_value )
        target_folder_id_select_field = __build_target_folder_id_select_field( trans, target_library_folders )
        return trans.fill_template( "/library/common/move_library_item.mako",
                                    cntrller=cntrller,
                                    make_target_current=make_target_current,
                                    source_library=source_library,
                                    item_type=item_type,
                                    item_id=item_id,
                                    move_ldda_ids=move_ldda_ids,
                                    move_lddas=move_lddas,
                                    move_folder=move_folder,
                                    target_library=target_library,
                                    target_library_id_select_field=target_library_id_select_field,
                                    target_folder_id_select_field=target_folder_id_select_field,
                                    show_deleted=show_deleted,
                                    use_panels=use_panels,
                                    message=escape( message ),
                                    status=escape( status ) )

    @web.expose
    def delete_library_item( self, trans, cntrller, library_id, item_id, item_type, **kwd ):
        # This action will handle deleting all types of library items.  State is saved for libraries and
        # folders ( i.e., if undeleted, the state of contents of the library or folder will remain, so previously
        # deleted / purged contents will have the same state ).  When a library or folder has been deleted for
        # the amount of time defined in the cleanup_datasets.py script, the library or folder and all of its
        # contents will be purged.  The association between this method and the cleanup_datasets.py script
        # enables clean maintenance of libraries and library dataset disk files.  This is also why the item_types
        # are not any of the associations ( the cleanup_datasets.py script handles everything ).
        status = kwd.get( 'status', 'done' )
        show_deleted = util.string_as_bool( kwd.get( 'show_deleted', False ) )
        item_types = { 'library': trans.app.model.Library,
                       'folder': trans.app.model.LibraryFolder,
                       'library_dataset': trans.app.model.LibraryDataset }
        is_admin = ( trans.user_is_admin() and cntrller == 'library_admin' )
        current_user_roles = trans.get_current_user_roles()
        if item_type not in item_types:
            message = 'Bad item_type specified: %s' % escape( str( item_type ) )
            status = 'error'
        else:
            if item_type == 'library_dataset':
                item_desc = 'Dataset'
            else:
                item_desc = item_type.capitalize()
            library_item_ids = util.listify( item_id )
            valid_items = 0
            invalid_items = 0
            not_authorized_items = 0
            flush_needed = False
            message = ''
            for library_item_id in library_item_ids:
                try:
                    library_item = trans.sa_session.query( item_types[ item_type ] ).get( trans.security.decode_id( library_item_id ) )
                except:
                    library_item = None
                if not library_item or not ( is_admin or trans.app.security_agent.can_access_library_item( current_user_roles, library_item, trans.user ) ):
                    invalid_items += 1
                elif not ( is_admin or trans.app.security_agent.can_modify_library_item( current_user_roles, library_item ) ):
                    not_authorized_items += 1
                else:
                    valid_items += 1
                    library_item.deleted = True
                    trans.sa_session.add( library_item )
                    flush_needed = True
            if flush_needed:
                trans.sa_session.flush()
            if valid_items:
                message += "%d %s marked deleted.  " % ( valid_items, escape( inflector.cond_plural( valid_items, item_desc ) ) )
            if invalid_items:
                message += '%d invalid %s specifield.  ' % ( invalid_items, escape( inflector.cond_plural( invalid_items, item_desc ) ) )
                status = 'error'
            if not_authorized_items:
                message += 'You are not authorized to delete %d %s.  ' % ( not_authorized_items, escape( inflector.cond_plural( not_authorized_items, item_desc ) ) )
                status = 'error'
        if item_type == 'library':
            return trans.response.send_redirect( web.url_for( controller=cntrller,
                                                              action='browse_libraries',
                                                              message=message,
                                                              status=status ) )
        else:
            return trans.response.send_redirect( web.url_for( controller='library_common',
                                                              action='browse_library',
                                                              cntrller=cntrller,
                                                              id=library_id,
                                                              show_deleted=show_deleted,
                                                              message=message,
                                                              status=status ) )

    @web.expose
    def undelete_library_item( self, trans, cntrller, library_id, item_id, item_type, **kwd ):
        # This action will handle undeleting all types of library items
        status = kwd.get( 'status', 'done' )
        show_deleted = util.string_as_bool( kwd.get( 'show_deleted', False ) )
        item_types = { 'library': trans.app.model.Library,
                       'folder': trans.app.model.LibraryFolder,
                       'library_dataset': trans.app.model.LibraryDataset }
        is_admin = ( trans.user_is_admin() and cntrller == 'library_admin' )
        current_user_roles = trans.get_current_user_roles()
        if item_type not in item_types:
            message = 'Bad item_type specified: %s' % escape( str( item_type ) )
            status = 'error'
        else:
            if item_type == 'library_dataset':
                item_desc = 'Dataset'
            else:
                item_desc = item_type.capitalize()

            library_item_ids = util.listify( item_id )
            valid_items = 0
            invalid_items = 0
            purged_items = 0
            not_authorized_items = 0
            flush_needed = False
            message = ''
            for library_item_id in library_item_ids:
                try:
                    library_item = trans.sa_session.query( item_types[ item_type ] ).get( trans.security.decode_id( library_item_id ) )
                except:
                    library_item = None
                if not library_item or not ( is_admin or trans.app.security_agent.can_access_library_item( current_user_roles, library_item, trans.user ) ):
                    invalid_items += 1
                elif library_item.purged:
                    purged_items += 1
                elif not ( is_admin or trans.app.security_agent.can_modify_library_item( current_user_roles, library_item ) ):
                    not_authorized_items += 1
                else:
                    valid_items += 1
                    library_item.deleted = False
                    trans.sa_session.add( library_item )
                    flush_needed = True
            if flush_needed:
                trans.sa_session.flush()
            if valid_items:
                message += "%d %s marked undeleted.  " % ( valid_items, escape( inflector.cond_plural( valid_items, item_desc ) ) )
            if invalid_items:
                message += '%d invalid %s specifield.  ' % ( invalid_items, escape( inflector.cond_plural( invalid_items, item_desc ) ) )
                status = 'error'
            if not_authorized_items:
                message += 'You are not authorized to undelete %d %s.  ' % ( not_authorized_items, escape( inflector.cond_plural( not_authorized_items, item_desc ) ) )
                status = 'error'
            if purged_items:
                message += '%d %s marked purged, so cannot be undeleted.  ' % ( purged_items, escape( inflector.cond_plural( purged_items, item_desc ) ) )
                status = 'error'
        if item_type == 'library':
            return trans.response.send_redirect( web.url_for( controller=cntrller,
                                                              action='browse_libraries',
                                                              message=message,
                                                              status=status ) )
        else:
            return trans.response.send_redirect( web.url_for( controller='library_common',
                                                              action='browse_library',
                                                              cntrller=cntrller,
                                                              id=library_id,
                                                              show_deleted=show_deleted,
                                                              message=message,
                                                              status=status ) )

    def _check_access( self, trans, cntrller, is_admin, item, current_user_roles, use_panels, library_id, show_deleted ):
        can_access = True
        if isinstance( item, trans.model.HistoryDatasetAssociation ):
            # Make sure the user has the DATASET_ACCESS permission on the history_dataset_association.
            if not item:
                message = "Invalid history dataset (%s) specified." % escape( str( item ) )
                can_access = False
            elif not trans.app.security_agent.can_access_dataset( current_user_roles, item.dataset ) and item.history.user == trans.user:
                message = "You do not have permission to access the history dataset with id (%s)." % str( item.id )
                can_access = False
        else:
            # Make sure the user has the LIBRARY_ACCESS permission on the library item.
            if not item:
                message = "Invalid library item (%s) specified." % escape( str( item ) )
                can_access = False
            elif not ( is_admin or trans.app.security_agent.can_access_library_item( current_user_roles, item, trans.user ) ):
                if isinstance( item, trans.model.Library ):
                    item_type = 'data library'
                elif isinstance( item, trans.model.LibraryFolder ):
                    item_type = 'folder'
                else:
                    item_type = '(unknown item type)'
                message = "You do not have permission to access the %s with id (%s)." % ( escape( item_type ), str( item.id ) )
                can_access = False
        if not can_access:
            if cntrller == 'api':
                return 400, message
            if isinstance( item, trans.model.Library ):
                return trans.response.send_redirect( web.url_for( controller=cntrller,
                                                                  action='browse_libraries',
                                                                  cntrller=cntrller,
                                                                  use_panels=use_panels,
                                                                  message=message,
                                                                  status='error' ) )
            return trans.response.send_redirect( web.url_for( controller='library_common',
                                                              action='browse_library',
                                                              cntrller=cntrller,
                                                              use_panels=use_panels,
                                                              id=library_id,
                                                              show_deleted=show_deleted,
                                                              message=message,
                                                              status='error' ) )

    def _check_add( self, trans, cntrller, is_admin, item, current_user_roles, use_panels, library_id, show_deleted ):
        # Deny access if the user is not an admin and does not have the LIBRARY_ADD permission.
        if not ( is_admin or trans.app.security_agent.can_add_library_item( current_user_roles, item ) ):
            message = "You are not authorized to add an item to (%s)." % escape( item.name )
            # Redirect to the real parent library since we know we have access to it.
            if cntrller == 'api':
                return 403, message
            return trans.response.send_redirect( web.url_for( controller='library_common',
                                                              action='browse_library',
                                                              cntrller=cntrller,
                                                              use_panels=use_panels,
                                                              id=library_id,
                                                              show_deleted=show_deleted,
                                                              message=message,
                                                              status='error' ) )

    def _check_manage( self, trans, cntrller, is_admin, item, current_user_roles, use_panels, library_id, show_deleted ):
        if isinstance( item, trans.model.LibraryDataset ):
            # Deny access if the user is not an admin and does not have the LIBRARY_MANAGE and DATASET_MANAGE_PERMISSIONS permissions.
            if not ( is_admin or
                     ( trans.app.security_agent.can_manage_library_item( current_user_roles, item ) and
                       trans.app.security_agent.can_manage_dataset( current_user_roles, item.library_dataset_dataset_association.dataset ) ) ):
                message = "You are not authorized to manage permissions on library dataset (%s)." % escape( item.name )
                if cntrller == 'api':
                    return 403, message
                return trans.response.send_redirect( web.url_for( controller='library_common',
                                                                  action='browse_library',
                                                                  id=library_id,
                                                                  cntrller=cntrller,
                                                                  use_panels=use_panels,
                                                                  message=message,
                                                                  status='error' ) )
        # Deny access if the user is not an admin and does not have the LIBRARY_MANAGE permission.
        if not ( is_admin or trans.app.security_agent.can_manage_library_item( current_user_roles, item ) ):
            message = "You are not authorized to manage permissions on (%s)." % escape( item.name )
            if cntrller == 'api':
                return 403, message
            return trans.response.send_redirect( web.url_for( controller='library_common',
                                                              action='browse_library',
                                                              id=library_id,
                                                              cntrller=cntrller,
                                                              use_panels=use_panels,
                                                              message=message,
                                                              status='error' ) )

    def _check_modify( self, trans, cntrller, is_admin, item, current_user_roles, use_panels, library_id, show_deleted ):
        # Deny modification if the user is not an admin and does not have the LIBRARY_MODIFY permission.
        if not ( is_admin or trans.app.security_agent.can_modify_library_item( current_user_roles, item ) ):
            message = "You are not authorized to modify (%s)." % escape( item.name )
            if cntrller == 'api':
                return 403, message
            return trans.response.send_redirect( web.url_for( controller='library_common',
                                                              action='browse_library',
                                                              cntrller=cntrller,
                                                              id=library_id,
                                                              use_panels=use_panels,
                                                              show_deleted=show_deleted,
                                                              message=message,
                                                              status='error' ) )

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


def map_library_datasets_to_lddas( trans, lib_datasets ):
    '''
    Given a list of LibraryDatasets, return a map from the LibraryDatasets
    to their LDDAs. If an LDDA does not exist for a LibraryDataset, then
    there will be no entry in the return hash.
    '''
    # Get a list of the LibraryDatasets' ids so that we can pass it along to
    # a query to retrieve the LDDAs. This eliminates querying for each
    # LibraryDataset.
    lib_dataset_ids = [ x.library_dataset_dataset_association_id for x in lib_datasets ]
    lddas = trans.sa_session.query( trans.app.model.LibraryDatasetDatasetAssociation ) \
                            .filter( trans.app.model.LibraryDatasetDatasetAssociation.id.in_( lib_dataset_ids ) ) \
                            .all()

    # Map the LibraryDataset to the returned LDDAs:
    ret_lddas = {}
    for ldda in lddas:
        ret_lddas[ldda.library_dataset_id] = ldda
    return ret_lddas


def datasets_for_lddas( trans, lddas ):
    '''
    Given a list of LDDAs, return a list of Datasets for them.
    '''
    dataset_ids = [ x.dataset_id for x in lddas ]
    datasets = trans.sa_session.query( trans.app.model.Dataset ) \
                               .filter( trans.app.model.Dataset.id.in_( dataset_ids ) ) \
                               .all()
    return datasets


def active_folders_and_library_datasets( trans, folder ):
    folders = active_folders( trans, folder )
    library_datasets = trans.sa_session.query( trans.model.LibraryDataset ).filter(
        and_( trans.model.LibraryDataset.table.c.deleted == false(),
        trans.model.LibraryDataset.table.c.folder_id == folder.id ) ) \
        .order_by( trans.model.LibraryDataset.table.c._name ) \
        .all()
    return folders, library_datasets


def activatable_folders_and_library_datasets( trans, folder ):
    folders = activatable_folders( trans, folder )
    library_datasets = trans.sa_session.query( trans.model.LibraryDataset ) \
                                       .filter( trans.model.LibraryDataset.table.c.folder_id == folder.id ) \
                                       .join( ( trans.model.LibraryDatasetDatasetAssociation.table,
                                                trans.model.LibraryDataset.table.c.library_dataset_dataset_association_id == trans.model.LibraryDatasetDatasetAssociation.table.c.id ) ) \
                                       .join( ( trans.model.Dataset.table,
                                                trans.model.LibraryDatasetDatasetAssociation.table.c.dataset_id == trans.model.Dataset.table.c.id ) ) \
                                       .filter( trans.model.Dataset.table.c.deleted == false() ) \
                                       .order_by( trans.model.LibraryDataset.table.c._name ) \
                                       .all()
    return folders, library_datasets


def branch_deleted( folder ):
    # Return True if a folder belongs to a branch that has been deleted
    if folder.deleted:
        return True
    if folder.parent:
        return branch_deleted( folder.parent )
    return False


def get_containing_library_from_library_dataset( trans, library_dataset ):
    """Given a library_dataset, get the containing library"""
    folder = library_dataset.folder
    while folder.parent:
        folder = folder.parent
    # We have folder set to the library's root folder, which has the same name as the library
    for library in trans.sa_session.query( trans.model.Library ).filter(
        and_( trans.model.Library.table.c.deleted == false(),
            trans.model.Library.table.c.name == folder.name ) ):
        # Just to double-check
        if library.root_folder == folder:
            return library
    return None


def get_comptypes( trans ):
    comptypes_t = comptypes
    if trans.app.config.nginx_x_archive_files_base:
        comptypes_t = ['ngxzip']
    for comptype in trans.app.config.disable_library_comptypes:
        # TODO: do this once, not every time (we're gonna raise an
        # exception every time after the first time)
        try:
            comptypes_t.remove( comptype )
        except:
            pass
    return comptypes_t


def get_sorted_accessible_library_items( trans, cntrller, items, sort_attr ):
    is_admin = trans.user_is_admin() and cntrller == 'library_admin'
    if is_admin:
        accessible_items = items
    else:
        # Enforce access permission settings
        current_user_roles = trans.get_current_user_roles()
        accessible_items = []
        for item in items:
            if trans.app.security_agent.can_access_library_item( current_user_roles, item, trans.user ):
                accessible_items.append( item )
    # Sort by name
    return sort_by_attr( [ item for item in accessible_items ], sort_attr )


def sort_by_attr( seq, attr ):
    """
    Sort the sequence of objects by object's attribute
    Arguments:
    seq  - the list or any sequence (including immutable one) of objects to sort.
    attr - the name of attribute to sort by
    """
    # Use the "Schwartzian transform"
    # Create the auxiliary list of tuples where every i-th tuple has form
    # (seq[i].attr, i, seq[i]) and sort it. The second item of tuple is needed not
    # only to provide stable sorting, but mainly to eliminate comparison of objects
    # (which can be expensive or prohibited) in case of equal attribute values.
    intermed = map( None, map( getattr, seq, ( attr, ) * len( seq ) ), xrange( len( seq ) ), seq )
    intermed.sort()
    return map( operator.getitem, intermed, ( -1, ) * len( intermed ) )


def lucene_search( trans, cntrller, search_term, search_url, **kwd ):
    """Return display of results from a full-text lucene search of data libraries."""
    message = escape( kwd.get( 'message', '' ) )
    status = kwd.get( 'status', 'done' )
    full_url = "%s/find?%s" % ( search_url, urllib.urlencode( { "kwd" : search_term } ) )
    response = urllib2.urlopen( full_url )
    ldda_ids = loads( response.read() )[ "ids" ]
    response.close()
    lddas = [ trans.sa_session.query( trans.app.model.LibraryDatasetDatasetAssociation ).get( ldda_id ) for ldda_id in ldda_ids ]
    return status, message, get_sorted_accessible_library_items( trans, cntrller, lddas, 'name' )


def whoosh_search( trans, cntrller, search_term, **kwd ):
    """Return display of results from a full-text whoosh search of data libraries."""
    message = escape( kwd.get( 'message', '' ) )
    status = kwd.get( 'status', 'done' )
    ok = True
    if whoosh_search_enabled:
        whoosh_index_dir = trans.app.config.whoosh_index_dir
        index_exists = whoosh.index.exists_in( whoosh_index_dir )
        if index_exists:
            index = whoosh.index.open_dir( whoosh_index_dir )
            # Set field boosts for searcher to place equal weight on all search fields.
            searcher = index.searcher( weighting=BM25F( field_B={ 'name_B' : 3.4,
                                                                  'info_B' : 3.2,
                                                                  'dbkey_B' : 3.3,
                                                                  'message_B' : 3.5 } ) )
            # Perform search
            parser = MultifieldParser( [ 'name', 'info', 'dbkey', 'message' ], schema=schema )
            # Search term with wildcards may be slow...
            results = searcher.search( parser.parse( '*' + search_term + '*' ), minscore=0.01 )
            ldda_ids = [ result[ 'id' ] for result in results ]
            lddas = []
            for ldda_id in ldda_ids:
                ldda = trans.sa_session.query( trans.app.model.LibraryDatasetDatasetAssociation ).get( ldda_id )
                if ldda:
                    lddas.append( ldda )
            lddas = get_sorted_accessible_library_items( trans, cntrller, lddas, 'name' )
        else:
            message = "Tell your Galaxy administrator that the directory %s does not contain valid whoosh indexes" % str( whoosh_index_dir )
            ok = False
    else:
        message = "Whoosh is compatible with Python version 2.5 or greater.  Your Python verison is not compatible."
        ok = False
    if not ok:
        status = 'error'
        lddas = []
    return status, message, lddas
