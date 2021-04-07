"""
Manager and Serializer for Library Folders.
"""
import logging

from sqlalchemy.orm.exc import (
    MultipleResultsFound,
    NoResultFound
)

from galaxy import util
from galaxy.exceptions import (
    AuthenticationRequired,
    InconsistentDatabase,
    InsufficientPermissionsException,
    InternalServerError,
    ItemAccessibilityException,
    MalformedId,
    RequestParameterInvalidException,
    RequestParameterMissingException,
)
from galaxy.managers.roles import RoleManager
from galaxy.structured_app import StructuredApp

log = logging.getLogger(__name__)


# =============================================================================
class FolderManager:
    """
    Interface/service object for interacting with folders.
    """

    def get(self, trans, decoded_folder_id, check_manageable=False, check_accessible=True):
        """
        Get the folder from the DB.

        :param  decoded_folder_id:       decoded folder id
        :type   decoded_folder_id:       int
        :param  check_manageable:        flag whether the check that user can manage item
        :type   check_manageable:        bool
        :param  check_accessible:        flag whether to check that user can access item
        :type   check_accessible:        bool

        :returns:   the requested folder
        :rtype:     LibraryFolder

        :raises: InconsistentDatabase, RequestParameterInvalidException, InternalServerError
        """
        try:
            folder = trans.sa_session.query(trans.app.model.LibraryFolder).filter(trans.app.model.LibraryFolder.table.c.id == decoded_folder_id).one()
        except MultipleResultsFound:
            raise InconsistentDatabase('Multiple folders found with the same id.')
        except NoResultFound:
            raise RequestParameterInvalidException('No folder found with the id provided.')
        except Exception as e:
            raise InternalServerError('Error loading from the database.' + util.unicodify(e))
        folder = self.secure(trans, folder, check_manageable, check_accessible)
        return folder

    def secure(self, trans, folder, check_manageable=True, check_accessible=True):
        """
        Check if (a) user can manage folder or (b) folder is accessible to user.

        :param  folder:                  folder item
        :type   folder:                  LibraryFolder
        :param  check_manageable:        flag whether to check that user can manage item
        :type   check_manageable:        bool
        :param  check_accessible:        flag whether to check that user can access item
        :type   check_accessible:        bool

        :returns:   the original folder
        :rtype:     LibraryFolder
        """
        # all folders are accessible to an admin
        if trans.user_is_admin:
            return folder
        if check_manageable:
            folder = self.check_manageable(trans, folder)
        if check_accessible:
            folder = self.check_accessible(trans, folder)
        return folder

    def check_modifyable(self, trans, folder):
        """
        Check whether the user can modify the folder (name and description).

        :returns:   the original folder
        :rtype:     LibraryFolder

        :raises: AuthenticationRequired, InsufficientPermissionsException
        """
        if not trans.user:
            raise AuthenticationRequired("Must be logged in to manage Galaxy items.", type='error')
        current_user_roles = trans.get_current_user_roles()
        if not trans.app.security_agent.can_modify_library_item(current_user_roles, folder):
            raise InsufficientPermissionsException("You don't have permissions to modify this folder.", type='error')
        else:
            return folder

    def check_manageable(self, trans, folder):
        """
        Check whether the user can manage the folder.

        :returns:   the original folder
        :rtype:     LibraryFolder

        :raises: AuthenticationRequired, InsufficientPermissionsException
        """
        if not trans.user:
            raise AuthenticationRequired("Must be logged in to manage Galaxy items.", type='error')
        current_user_roles = trans.get_current_user_roles()
        if not trans.app.security_agent.can_manage_library_item(current_user_roles, folder):
            raise InsufficientPermissionsException("You don't have permissions to manage this folder.", type='error')
        else:
            return folder

    def check_accessible(self, trans, folder):
        """
        Check whether the folder is accessible to current user.
        By default every folder is accessible (contents have their own permissions).
        """
        return folder

    def get_folder_dict(self, trans, folder):
        """
        Return folder data in the form of a dictionary.

        :param  folder:       folder item
        :type   folder:       LibraryFolder

        :returns:   dict with data about the folder
        :rtype:     dictionary

        """
        folder_dict = folder.to_dict(view='element')
        folder_dict = trans.security.encode_all_ids(folder_dict, True)
        folder_dict['id'] = 'F' + folder_dict['id']
        if folder_dict['parent_id'] is not None:
            folder_dict['parent_id'] = 'F' + folder_dict['parent_id']
        folder_dict['update_time'] = folder.update_time.strftime("%Y-%m-%d %I:%M %p")
        return folder_dict

    def create(self, trans, parent_folder_id, new_folder_name, new_folder_description=''):
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
        parent_folder = self.get(trans, parent_folder_id)
        current_user_roles = trans.get_current_user_roles()
        if not (trans.user_is_admin or trans.app.security_agent.can_add_library_item(current_user_roles, parent_folder)):
            raise InsufficientPermissionsException('You do not have proper permission to create folders under given folder.')
        new_folder = trans.app.model.LibraryFolder(name=new_folder_name, description=new_folder_description)
        # We are associating the last used genome build with folders, so we will always
        # initialize a new folder with the first dbkey in genome builds list which is currently
        # ?    unspecified (?)
        new_folder.genome_build = trans.app.genome_builds.default_value
        parent_folder.add_folder(new_folder)
        trans.sa_session.add(new_folder)
        trans.sa_session.flush()
        # New folders default to having the same permissions as their parent folder
        trans.app.security_agent.copy_library_permissions(trans, parent_folder, new_folder)
        return new_folder

    def update(self, trans, folder, name=None, description=None):
        """
        Update the given folder's name or description.

        :param  folder:        the model object
        :type   folder:        LibraryFolder
        :param  name:          new name for the library folder
        :type   name:          str
        :param  description:   new description for the library folder
        :type   description:   str

        :returns:   the folder
        :rtype:     LibraryFolder

        :raises: ItemAccessibilityException, InsufficientPermissionsException
        """
        changed = False
        if not trans.user_is_admin:
            folder = self.check_modifyable(trans, folder)
        if folder.deleted is True:
            raise ItemAccessibilityException("You cannot update a deleted library folder. Undelete it first.")
        if name is not None and name != folder.name:
            folder.name = name
            changed = True
        if description is not None and description != folder.description:
            folder.description = description
            changed = True
        if changed:
            trans.sa_session.add(folder)
            trans.sa_session.flush()
        return folder

    def delete(self, trans, folder, undelete=False):
        """
        Mark given folder deleted/undeleted based on the flag.

        :param  folder:        the model object
        :type   folder:        LibraryFolder
        :param  undelete:      flag whether to delete (when False) or undelete
        :type   undelete:      Bool

        :returns:   the folder
        :rtype:     LibraryFolder

        :raises: ItemAccessibilityException
        """
        if not trans.user_is_admin:
            folder = self.check_manageable(trans, folder)
        if undelete:
            folder.deleted = False
        else:
            folder.deleted = True
        trans.sa_session.add(folder)
        trans.sa_session.flush()
        return folder

    def get_current_roles(self, trans, folder):
        """
        Find all roles currently connected to relevant permissions
        on the folder.

        :param  folder:      the model object
        :type   folder:      LibraryFolder

        :returns:   dict of current roles for all available permission types
        :rtype:     dictionary
        """
        # Omit duplicated roles by converting to set
        modify_roles = set(trans.app.security_agent.get_roles_for_action(folder, trans.app.security_agent.permitted_actions.LIBRARY_MODIFY))
        manage_roles = set(trans.app.security_agent.get_roles_for_action(folder, trans.app.security_agent.permitted_actions.LIBRARY_MANAGE))
        add_roles = set(trans.app.security_agent.get_roles_for_action(folder, trans.app.security_agent.permitted_actions.LIBRARY_ADD))

        modify_folder_role_list = [(modify_role.name, trans.security.encode_id(modify_role.id)) for modify_role in modify_roles]
        manage_folder_role_list = [(manage_role.name, trans.security.encode_id(manage_role.id)) for manage_role in manage_roles]
        add_library_item_role_list = [(add_role.name, trans.security.encode_id(add_role.id)) for add_role in add_roles]
        return dict(modify_folder_role_list=modify_folder_role_list,
                    manage_folder_role_list=manage_folder_role_list,
                    add_library_item_role_list=add_library_item_role_list)

    def can_add_item(self, trans, folder):
        """
        Return true if the user has permissions to add item to the given folder.
        """
        if trans.user_is_admin:
            return True
        current_user_roles = trans.get_current_user_roles()
        add_roles = set(trans.app.security_agent.get_roles_for_action(folder, trans.app.security_agent.permitted_actions.LIBRARY_ADD))
        for role in current_user_roles:
            if role in add_roles:
                return True
        return False

    def cut_the_prefix(self, encoded_folder_id):
        """
        Remove the prefix from the encoded folder id.

        :param encoded_folder_id: encoded id of the Folder object with 'F' prepended
        :type  encoded_folder_id: string

        :returns:  encoded Folder id without the 'F' prefix
        :rtype:    string

        :raises: MalformedId
        """
        if ((len(encoded_folder_id) % 16 == 1) and encoded_folder_id.startswith('F')):
            cut_id = encoded_folder_id[1:]
        else:
            raise MalformedId('Malformed folder id ( %s ) specified, unable to decode.' % str(encoded_folder_id))
        return cut_id

    def decode_folder_id(self, trans, encoded_folder_id):
        """
        Decode the folder id given that it has already lost the prefixed 'F'.

        :param encoded_folder_id: encoded id of the Folder object
        :type  encoded_folder_id: string

        :returns:  decoded Folder id
        :rtype:    int

        :raises: MalformedId
        """
        try:
            decoded_id = trans.security.decode_id(encoded_folder_id)
        except ValueError:
            raise MalformedId("Malformed folder id ( %s ) specified, unable to decode" % (str(encoded_folder_id)))
        return decoded_id

    def cut_and_decode(self, trans, encoded_folder_id):
        """
        Cuts the folder prefix (the prepended 'F') and returns the decoded id.

        :param encoded_folder_id: encoded id of the Folder object
        :type  encoded_folder_id: string

        :returns:  decoded Folder id
        :rtype:    int
        """
        return self.decode_folder_id(trans, self.cut_the_prefix(encoded_folder_id))


class FoldersService:
    """Common interface/service logic for interactions with library folders in the context of the API.
    Provides the logic of the actions invoked by API controllers and uses type definitions
    and pydantic models to declare its parameters and return types.
    """

    def __init__(self, app: StructuredApp, folder_manager: FolderManager, role_manager: RoleManager) -> None:
        self._app = app
        self.folder_manager = folder_manager
        self.role_manager = role_manager

    def show(self, trans, id):
        """
        Displays information about a folder.

        :param  id:      the folder's encoded id (required)
        :type   id:      an encoded id string (has to be prefixed by 'F')

        :returns:   dictionary including details of the folder
        :rtype:     dict
        """
        folder_id = self.folder_manager.cut_and_decode(trans, id)
        folder = self.folder_manager.get(trans, folder_id, check_manageable=False, check_accessible=True)
        return_dict = self.folder_manager.get_folder_dict(trans, folder)
        return return_dict

    def create(self, trans, encoded_parent_folder_id, payload: dict):
        """
        Create a new folder object underneath the one specified in the parameters.

        :param  encoded_parent_folder_id:      (required) the parent folder's id
        :type   encoded_parent_folder_id:      an encoded id string (should be prefixed by 'F')
        :param   payload: dictionary structure containing:

            :param  name:                          (required) the name of the new folder
            :type   name:                          str
            :param  description:                   the description of the new folder
            :type   description:                   str

        :type       dictionary
        :returns:   information about newly created folder, notably including ID
        :rtype:     dictionary
        :raises: RequestParameterMissingException
        """
        name = payload.get('name', None)
        if name is None:
            raise RequestParameterMissingException("Missing required parameter 'name'.")
        description = payload.get('description', '')
        decoded_parent_folder_id = self.folder_manager.cut_and_decode(trans, encoded_parent_folder_id)
        parent_folder = self.folder_manager.get(trans, decoded_parent_folder_id)
        new_folder = self.folder_manager.create(trans, parent_folder.id, name, description)
        return self.folder_manager.get_folder_dict(trans, new_folder)

    def get_permissions(self, trans, encoded_folder_id, scope=None, page=None, page_limit=None, query=None):
        """
        Load all permissions for the given folder id and return it.

        :param  encoded_folder_id:     the encoded id of the folder
        :type   encoded_folder_id:     an encoded id string

        :param  scope:      either 'current' or 'available'
        :type   scope:      string

        :returns:   dictionary with all applicable permissions' values
        :rtype:     dictionary

        :raises: InsufficientPermissionsException
        """
        current_user_roles = trans.get_current_user_roles()
        is_admin = trans.user_is_admin
        decoded_folder_id = self.folder_manager.cut_and_decode(trans, encoded_folder_id)
        folder = self.folder_manager.get(trans, decoded_folder_id)

        if not (is_admin or trans.app.security_agent.can_manage_library_item(current_user_roles, folder)):
            raise InsufficientPermissionsException('You do not have proper permission to access permissions of this folder.')

        if scope == 'current' or scope is None:
            return self.folder_manager.get_current_roles(trans, folder)
        #  Return roles that are available to select.
        elif scope == 'available':
            if page is not None:
                page = int(page)
            else:
                page = 1
            if page_limit is not None:
                page_limit = int(page_limit)
            else:
                page_limit = 10
            roles, total_roles = trans.app.security_agent.get_valid_roles(trans, folder, query, page, page_limit)
            return_roles = []
            for role in roles:
                role_id = trans.security.encode_id(role.id)
                return_roles.append(dict(id=role_id, name=role.name, type=role.type))
            return dict(roles=return_roles, page=page, page_limit=page_limit, total=total_roles)
        else:
            raise RequestParameterInvalidException("The value of 'scope' parameter is invalid. Alllowed values: current, available")

    def set_permissions(self, trans, encoded_folder_id, payload: dict):
        """
        Set permissions of the given folder to the given role ids.

        :param  encoded_folder_id:      the encoded id of the folder to set the permissions of
        :type   encoded_folder_id:      an encoded id string
        :param   payload: dictionary structure containing:

            :param  action:            (required) describes what action should be performed
            :type   action:            string
            :param  add_ids[]:         list of Role.id defining roles that should have add item permission on the folder
            :type   add_ids[]:         string or list
            :param  manage_ids[]:      list of Role.id defining roles that should have manage permission on the folder
            :type   manage_ids[]:      string or list
            :param  modify_ids[]:      list of Role.id defining roles that should have modify permission on the folder
            :type   modify_ids[]:      string or list

        :type       dictionary
        :returns:   dict of current roles for all available permission types.
        :rtype:     dictionary
        :raises: RequestParameterInvalidException, InsufficientPermissionsException, RequestParameterMissingException
        """

        is_admin = trans.user_is_admin
        current_user_roles = trans.get_current_user_roles()
        decoded_folder_id = self.folder_manager.cut_and_decode(trans, encoded_folder_id)
        folder = self.folder_manager.get(trans, decoded_folder_id)
        if not (is_admin or trans.app.security_agent.can_manage_library_item(current_user_roles, folder)):
            raise InsufficientPermissionsException('You do not have proper permission to modify permissions of this folder.')

        new_add_roles_ids = util.listify(payload.get('add_ids[]', None))
        new_manage_roles_ids = util.listify(payload.get('manage_ids[]', None))
        new_modify_roles_ids = util.listify(payload.get('modify_ids[]', None))

        action = payload.get('action', None)
        if action is None:
            raise RequestParameterMissingException('The mandatory parameter "action" is missing.')
        elif action == 'set_permissions':

            # ADD TO LIBRARY ROLES
            valid_add_roles = []
            invalid_add_roles_names = []
            for role_id in new_add_roles_ids:
                role = self.role_manager.get(trans, self.__decode_id(trans, role_id, 'role'))
                #  Check whether role is in the set of allowed roles
                valid_roles, total_roles = trans.app.security_agent.get_valid_roles(trans, folder)
                if role in valid_roles:
                    valid_add_roles.append(role)
                else:
                    invalid_add_roles_names.append(role_id)
            if len(invalid_add_roles_names) > 0:
                log.warning("The following roles could not be added to the add library item permission: " + str(invalid_add_roles_names))

            # MANAGE FOLDER ROLES
            valid_manage_roles = []
            invalid_manage_roles_names = []
            for role_id in new_manage_roles_ids:
                role = self.role_manager.get(trans, self.__decode_id(trans, role_id, 'role'))
                #  Check whether role is in the set of allowed roles
                valid_roles, total_roles = trans.app.security_agent.get_valid_roles(trans, folder)
                if role in valid_roles:
                    valid_manage_roles.append(role)
                else:
                    invalid_manage_roles_names.append(role_id)
            if len(invalid_manage_roles_names) > 0:
                log.warning("The following roles could not be added to the manage folder permission: " + str(invalid_manage_roles_names))

            # MODIFY FOLDER ROLES
            valid_modify_roles = []
            invalid_modify_roles_names = []
            for role_id in new_modify_roles_ids:
                role = self.role_manager.get(trans, self.__decode_id(trans, role_id, 'role'))
                #  Check whether role is in the set of allowed roles
                valid_roles, total_roles = trans.app.security_agent.get_valid_roles(trans, folder)
                if role in valid_roles:
                    valid_modify_roles.append(role)
                else:
                    invalid_modify_roles_names.append(role_id)
            if len(invalid_modify_roles_names) > 0:
                log.warning("The following roles could not be added to the modify folder permission: " + str(invalid_modify_roles_names))

            permissions = {trans.app.security_agent.permitted_actions.LIBRARY_ADD: valid_add_roles}
            permissions.update({trans.app.security_agent.permitted_actions.LIBRARY_MANAGE: valid_manage_roles})
            permissions.update({trans.app.security_agent.permitted_actions.LIBRARY_MODIFY: valid_modify_roles})

            trans.app.security_agent.set_all_library_permissions(trans, folder, permissions)
        else:
            raise RequestParameterInvalidException('The mandatory parameter "action" has an invalid value.'
                                                   'Allowed values are: "set_permissions"')
        return self.folder_manager.get_current_roles(trans, folder)

    def delete(self, trans, encoded_folder_id, undelete: bool = False):
        """
        DELETE /api/folders/{encoded_folder_id}

        Mark the folder with the given ``encoded_folder_id`` as `deleted`
        (or remove the `deleted` mark if the `undelete` param is true).

        .. note:: Currently, only admin users can un/delete folders.

        :param  encoded_folder_id:     the encoded id of the folder to un/delete
        :type   encoded_folder_id:     an encoded id string

        :param  undelete:    (optional) flag specifying whether the item should be deleted or undeleted, defaults to false:
        :type   undelete:    bool

        :returns:   detailed folder information
        :rtype:     dictionary

        """
        folder = self.folder_manager.get(trans, self.folder_manager.cut_and_decode(trans, encoded_folder_id), True)
        folder = self.folder_manager.delete(trans, folder, undelete)
        folder_dict = self.folder_manager.get_folder_dict(trans, folder)
        return folder_dict

    def update(self, trans, encoded_folder_id, payload: dict):
        """
        Update the folder defined by an ``encoded_folder_id``
        with the data in the payload.

       .. note:: Currently, only admin users can update library folders. Also the folder must not be `deleted`.

        :param  id:      the encoded id of the folder
        :type   id:      an encoded id string

        :param  payload: (required) dictionary structure containing::
            'name':         new folder's name, cannot be empty
            'description':  new folder's description
        :type   payload: dict

        :returns:   detailed folder information
        :rtype:     dict

        :raises: RequestParameterMissingException
        """
        decoded_folder_id = self.folder_manager.cut_and_decode(trans, encoded_folder_id)
        folder = self.folder_manager.get(trans, decoded_folder_id)
        name = payload.get('name', None)
        if not name:
            raise RequestParameterMissingException("Parameter 'name' of library folder is required. You cannot remove it.")
        description = payload.get('description', None)
        updated_folder = self.folder_manager.update(trans, folder, name, description)
        folder_dict = self.folder_manager.get_folder_dict(trans, updated_folder)
        return folder_dict

    def __decode_id(self, trans, encoded_id, object_name=None):
        """
        Try to decode the id.

        :param  object_name:      Name of the object the id belongs to. (optional)
        :type   object_name:      str
        """
        try:
            return trans.security.decode_id(encoded_id)
        except TypeError:
            raise MalformedId('Malformed %s id specified, unable to decode.' % object_name if object_name is not None else '')
        except ValueError:
            raise MalformedId('Wrong %s id specified, unable to decode.' % object_name if object_name is not None else '')
