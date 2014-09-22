"""
Manager and Serializer for Library Folders.
"""

import galaxy.web
from galaxy import exceptions
from galaxy.model import orm

import logging
log = logging.getLogger( __name__ )


# =============================================================================
class FolderManager( object ):
    """
    Interface/service object for interacting with folders.
    """

    def get( self, trans, decoded_folder_id, check_ownership=False, check_accessible=True):
        """
        Get the folder from the DB.

        :param  decoded_folder_id:       decoded folder id
        :type   decoded_folder_id:       int
        :param  check_ownership:         flag whether the check that user is owner
        :type   check_ownership:         bool
        :param  check_accessible:        flag whether to check that user can access item
        :type   check_accessible:        bool

        :returns:   the requested folder
        :rtype:     LibraryFolder
        """
        try:
            folder = trans.sa_session.query( trans.app.model.LibraryFolder ).filter( trans.app.model.LibraryFolder.table.c.id == decoded_folder_id ).one()
        except MultipleResultsFound:
            raise exceptions.InconsistentDatabase( 'Multiple folders found with the same id.' )
        except NoResultFound:
            raise exceptions.RequestParameterInvalidException( 'No folder found with the id provided.' )
        except Exception, e:
            raise exceptions.InternalServerError( 'Error loading from the database.' + str( e ) )
        folder = self.secure( trans, folder, check_ownership, check_accessible )
        return folder

    def secure( self, trans, folder, check_ownership=True, check_accessible=True ):
        """
        Check if (a) user owns folder or (b) folder is accessible to user.

        :param  folder:                  folder item
        :type   folder:                  LibraryFolder
        :param  check_ownership:         flag whether the check that user is owner
        :type   check_ownership:         bool
        :param  check_accessible:        flag whether to check that user can access item
        :type   check_accessible:        bool

        :returns:   the original folder
        :rtype:     LibraryFolder
        """
        # all folders are accessible to an admin
        if trans.user_is_admin():
            return folder
        if check_ownership:
            folder = self.check_ownership( trans, folder )
        if check_accessible:
            folder = self.check_accessible( trans, folder )
        return folder

    def check_ownership( self, trans, folder ):
        """
        Check whether the user is owner of the folder.

        :returns:   the original folder
        :rtype:     LibraryFolder
        """
        if not trans.user:
            raise exceptions.AuthenticationRequired( "Must be logged in to manage Galaxy items", type='error' )
        if folder.user != trans.user:
            raise exceptions.ItemOwnershipException( "Folder is not owned by the current user", type='error' )
        else:
            return folder

    def check_accessible( self, trans, folder ):
        """
        Check whether the folder is accessible to current user.
        By default every folder is accessible (contents have their own permissions).
        """
        return folder

    def get_folder_dict( self, trans, folder ):
        """
        Return folder data in the form of a dictionary.

        :param  folder:       folder item
        :type   folder:       LibraryFolder

        :returns:   dict with data about the folder
        :rtype:     dictionary

        """
        folder_dict = folder.to_dict( view='element' )
        folder_dict = trans.security.encode_all_ids( folder_dict, True )
        folder_dict[ 'id' ] = 'F' + folder_dict[ 'id' ]
        if folder_dict[ 'parent_id' ] is not None:
            folder_dict[ 'parent_id' ] = 'F' + folder_dict[ 'parent_id' ]
        return folder_dict

    def create( self, trans, parent_folder_id, new_folder_name, new_folder_description='' ):
        """
        Create a new folder under the given folder.

        :param  parent_folder_id:       decoded id
        :type   parent_folder_id:       int
        :param  new_folder_name:        name of the new folder
        :type   new_folder_name:        str
        :param  new_folder_description: description of the folder (optional, defaults to empty string)
        :type   new_folder_description: str

        :returns:   the new folder
        :rtype:     LibraryFolder

        :raises: InsufficientPermissionsException
        """
        parent_folder = self.get( trans, parent_folder_id )
        current_user_roles = trans.get_current_user_roles()
        if not ( trans.user_is_admin or trans.app.security_agent.can_add_library_item( current_user_roles, parent_folder ) ):
            raise exceptions.InsufficientPermissionsException( 'You do not have proper permission to create folders under given folder.' )
        new_folder = trans.app.model.LibraryFolder( name=new_folder_name, description=new_folder_description )
        # We are associating the last used genome build with folders, so we will always
        # initialize a new folder with the first dbkey in genome builds list which is currently
        # ?    unspecified (?)
        new_folder.genome_build = trans.app.genome_builds.default_value
        parent_folder.add_folder( new_folder )
        trans.sa_session.add( new_folder )
        trans.sa_session.flush()
        # New folders default to having the same permissions as their parent folder
        trans.app.security_agent.copy_library_permissions( trans, parent_folder, new_folder )
        return new_folder

    def get_current_roles( self, trans, folder ):
        """
        Find all roles currently connected to relevant permissions 
        on the folder.

        :param  folder:      the model object
        :type   folder:      LibraryFolder

        :returns:   dict of current roles for all available permission types
        :rtype:     dictionary
        """
        # Omit duplicated roles by converting to set 
        modify_roles = set( trans.app.security_agent.get_roles_for_action( folder, trans.app.security_agent.permitted_actions.LIBRARY_MODIFY ) )
        manage_roles = set( trans.app.security_agent.get_roles_for_action( folder, trans.app.security_agent.permitted_actions.LIBRARY_MANAGE ) )
        add_roles = set( trans.app.security_agent.get_roles_for_action( folder, trans.app.security_agent.permitted_actions.LIBRARY_ADD ) )

        modify_folder_role_list = [ ( modify_role.name, trans.security.encode_id( modify_role.id ) ) for modify_role in modify_roles ]
        manage_folder_role_list = [ ( manage_role.name, trans.security.encode_id( manage_role.id ) ) for manage_role in manage_roles ]
        add_library_item_role_list = [ ( add_role.name, trans.security.encode_id( add_role.id ) ) for add_role in add_roles ]
        return dict( modify_folder_role_list=modify_folder_role_list, manage_folder_role_list=manage_folder_role_list, add_library_item_role_list=add_library_item_role_list )

    def can_add_item( self, trans, folder ):
        """
        Return true if the user has permissions to add item to the given folder.
        """
        if trans.user_is_admin:
            return True
        current_user_roles = trans.get_current_user_roles()
        add_roles = set( trans.app.security_agent.get_roles_for_action( folder, trans.app.security_agent.permitted_actions.LIBRARY_ADD ) )
        for role in current_user_roles:
            if role in add_roles:
                return True
        return False

    def cut_the_prefix( self, encoded_folder_id ):
        """
        Remove the prefix from the encoded folder id.
        """
        if ( ( len( encoded_folder_id ) % 16 == 1 ) and encoded_folder_id.startswith( 'F' ) ):
            cut_id = encoded_folder_id[ 1: ]
        else:
            raise exceptions.MalformedId( 'Malformed folder id ( %s ) specified, unable to decode.' % str( encoded_id ) )
        return cut_id

    def decode_folder_id( self, trans, encoded_folder_id ):
        """
        Decode the folder id given that it has already lost the prefixed 'F'.
        """
        try:
            decoded_id = trans.security.decode_id( encoded_folder_id )
        except ValueError:
            raise exceptions.MalformedId( "Malformed folder id ( %s ) specified, unable to decode" % ( str( encoded_folder_id ) ) )
        return decoded_id

    def cut_and_decode( self, trans, encoded_folder_id ):
        """
        Cuts the folder prefix (the prepended 'F') and returns the decoded id.
        """
        return self.decode_folder_id( trans, self.cut_the_prefix( encoded_folder_id ) )
