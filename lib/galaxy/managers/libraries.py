"""
Manager and Serializer for libraries.
"""
import logging

from sqlalchemy import and_, false, not_, or_, true
from sqlalchemy.orm.exc import MultipleResultsFound
from sqlalchemy.orm.exc import NoResultFound

from galaxy import exceptions
from galaxy.managers import folders
from galaxy.util import pretty_print_time_interval

log = logging.getLogger( __name__ )


# =============================================================================
class LibraryManager( object ):
    """
    Interface/service object for interacting with libraries.
    """

    def __init__( self, *args, **kwargs ):
        super( LibraryManager, self ).__init__( *args, **kwargs )

    def get( self, trans, decoded_library_id, check_accessible=True ):
        """
        Get the library from the DB.

        :param  decoded_library_id:       decoded library id
        :type   decoded_library_id:       int
        :param  check_accessible:         flag whether to check that user can access item
        :type   check_accessible:         bool

        :returns:   the requested library
        :rtype:     galaxy.model.Library
        """
        try:
            library = trans.sa_session.query( trans.app.model.Library ).filter( trans.app.model.Library.table.c.id == decoded_library_id ).one()
        except MultipleResultsFound:
            raise exceptions.InconsistentDatabase( 'Multiple libraries found with the same id.' )
        except NoResultFound:
            raise exceptions.RequestParameterInvalidException( 'No library found with the id provided.' )
        except Exception as e:
            raise exceptions.InternalServerError( 'Error loading from the database.' + str( e ) )
        library = self.secure( trans, library, check_accessible)
        return library

    def create( self, trans, name, description='', synopsis=''):
        """
        Create a new library.
        """
        if not trans.user_is_admin:
            raise exceptions.ItemAccessibilityException( 'Only administrators can create libraries.' )
        else:
            library = trans.app.model.Library( name=name, description=description, synopsis=synopsis )
            root_folder = trans.app.model.LibraryFolder( name=name, description='' )
            library.root_folder = root_folder
            trans.sa_session.add_all( ( library, root_folder ) )
            trans.sa_session.flush()
            return library

    def update( self, trans, library, name=None, description=None, synopsis=None ):
        """
        Update the given library
        """
        changed = False
        if not trans.user_is_admin():
            raise exceptions.ItemAccessibilityException( 'Only administrators can update libraries.' )
        if library.deleted:
            raise exceptions.RequestParameterInvalidException( 'You cannot modify a deleted library. Undelete it first.' )
        if name is not None:
            library.name = name
            changed = True
            #  When library is renamed the root folder has to be renamed too.
            folder_manager = folders.FolderManager()
            folder_manager.update( trans, library.root_folder, name=name )
        if description is not None:
            library.description = description
            changed = True
        if synopsis is not None:
            library.synopsis = synopsis
            changed = True
        if changed:
            trans.sa_session.add( library )
            trans.sa_session.flush()
        return library

    def delete( self, trans, library, undelete=False ):
        """
        Mark given library deleted/undeleted based on the flag.
        """
        if not trans.user_is_admin():
            raise exceptions.ItemAccessibilityException( 'Only administrators can delete and undelete libraries.' )
        if undelete:
            library.deleted = False
        else:
            library.deleted = True
        trans.sa_session.add( library )
        trans.sa_session.flush()
        return library

    def list( self, trans, deleted=False ):
        """
        Return a list of libraries from the DB.

        :param  deleted: if True, show only ``deleted`` libraries, if False show only ``non-deleted``
        :type   deleted: boolean (optional)

        :returns: query that will emit all accessible libraries
        :rtype: sqlalchemy query
        """
        is_admin = trans.user_is_admin()
        query = trans.sa_session.query( trans.app.model.Library )

        if is_admin:
            if deleted is None:
                #  Flag is not specified, do not filter on it.
                pass
            elif deleted:
                query = query.filter( trans.app.model.Library.table.c.deleted == true() )
            else:
                query = query.filter( trans.app.model.Library.table.c.deleted == false() )
        else:
            #  Nonadmins can't see deleted libraries
            current_user_role_ids = [ role.id for role in trans.get_current_user_roles() ]
            library_access_action = trans.app.security_agent.permitted_actions.LIBRARY_ACCESS.action
            restricted_library_ids = [ lp.library_id for lp in (
                trans.sa_session.query( trans.model.LibraryPermissions ).filter(
                    trans.model.LibraryPermissions.table.c.action == library_access_action
                ).distinct() ) ]
            accessible_restricted_library_ids = [ lp.library_id for lp in (
                trans.sa_session.query( trans.model.LibraryPermissions ).filter(
                    and_(
                        trans.model.LibraryPermissions.table.c.action == library_access_action,
                        trans.model.LibraryPermissions.table.c.role_id.in_( current_user_role_ids )
                    ) ) ) ]
            query = query.filter( or_(
                not_( trans.model.Library.table.c.id.in_( restricted_library_ids ) ),
                trans.model.Library.table.c.id.in_( accessible_restricted_library_ids )
            ) )
        return query

    def secure( self, trans, library, check_accessible=True ):
        """
        Check if library is accessible to user.

        :param  library:                 library
        :type   library:                 galaxy.model.Library
        :param  check_accessible:        flag whether to check that user can access library
        :type   check_accessible:        bool

        :returns:   the original folder
        :rtype:     LibraryFolder
        """
        # all libraries are accessible to an admin
        if trans.user_is_admin():
            return library
        if check_accessible:
            library = self.check_accessible( trans, library )
        return library

    def check_accessible( self, trans, library ):
        """
        Check whether the library is accessible to current user.
        """
        if not trans.app.security_agent.can_access_library( trans.get_current_user_roles(), library ):
            raise exceptions.ObjectNotFound( 'Library with the id provided was not found.' )
        elif library.deleted:
            raise exceptions.ObjectNotFound( 'Library with the id provided is deleted.' )
        else:
            return library

    def get_library_dict( self, trans, library ):
        """
        Return library data in the form of a dictionary.

        :param  library:       library
        :type   library:       galaxy.model.Library

        :returns:   dict with data about the library
        :rtype:     dictionary
        """
        library_dict = library.to_dict( view='element', value_mapper={ 'id': trans.security.encode_id, 'root_folder_id': trans.security.encode_id } )
        if trans.app.security_agent.library_is_public( library, contents=False ):
            library_dict[ 'public' ] = True
        library_dict[ 'create_time_pretty'] = pretty_print_time_interval( library.create_time, precise=True )
        current_user_roles = trans.get_current_user_roles()
        if not trans.user_is_admin():
            library_dict[ 'can_user_add' ] = trans.app.security_agent.can_add_library_item( current_user_roles, library )
            library_dict[ 'can_user_modify' ] = trans.app.security_agent.can_modify_library_item( current_user_roles, library )
            library_dict[ 'can_user_manage' ] = trans.app.security_agent.can_manage_library_item( current_user_roles, library )
        else:
            library_dict[ 'can_user_add' ] = True
            library_dict[ 'can_user_modify' ] = True
            library_dict[ 'can_user_manage' ] = True
        return library_dict

    def get_current_roles( self, trans, library ):
        """
        Load all permissions currently related to the given library.

        :param  library:      the model object
        :type   library:      galaxy.model.Library

        :rtype:     dictionary
        :returns:   dict of current roles for all available permission types
        """
        access_library_role_list = [ ( access_role.name, trans.security.encode_id( access_role.id ) ) for access_role in self.get_access_roles( trans, library ) ]
        modify_library_role_list = [ ( modify_role.name, trans.security.encode_id( modify_role.id ) ) for modify_role in self.get_modify_roles( trans, library ) ]
        manage_library_role_list = [ ( manage_role.name, trans.security.encode_id( manage_role.id ) ) for manage_role in self.get_manage_roles( trans, library ) ]
        add_library_item_role_list = [ ( add_role.name, trans.security.encode_id( add_role.id ) ) for add_role in self.get_add_roles( trans, library ) ]
        return dict( access_library_role_list=access_library_role_list,
                     modify_library_role_list=modify_library_role_list,
                     manage_library_role_list=manage_library_role_list,
                     add_library_item_role_list=add_library_item_role_list )

    def get_access_roles( self, trans, library ):
        """
        Load access roles for all library permissions
        """
        return set( library.get_access_roles( trans ) )

    def get_modify_roles( self, trans, library ):
        """
        Load modify roles for all library permissions
        """
        return set( trans.app.security_agent.get_roles_for_action( library, trans.app.security_agent.permitted_actions.LIBRARY_MODIFY ) )

    def get_manage_roles( self, trans, library ):
        """
        Load manage roles for all library permissions
        """
        return set( trans.app.security_agent.get_roles_for_action( library, trans.app.security_agent.permitted_actions.LIBRARY_MANAGE ) )

    def get_add_roles( self, trans, library ):
        """
        Load add roles for all library permissions
        """
        return set( trans.app.security_agent.get_roles_for_action( library, trans.app.security_agent.permitted_actions.LIBRARY_ADD ) )

    def set_permission_roles( self, trans, library, access_roles, modify_roles, manage_roles, add_roles ):
        """
        Set permissions on the given library.
        """

    def make_public( self, trans, library ):
        """
        Makes the given library public (removes all access roles)
        """
        trans.app.security_agent.make_library_public( library )
        return self.is_public( trans, library )

    def is_public( self, trans, library ):
        """
        Return true if lib is public.
        """
        return trans.app.security_agent.library_is_public( library )
