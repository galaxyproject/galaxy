import logging
from typing import (
    Optional,
    Union,
)

from galaxy import util
from galaxy.exceptions import (
    InsufficientPermissionsException,
    RequestParameterInvalidException,
    RequestParameterMissingException,
)
from galaxy.managers.folders import FolderManager
from galaxy.managers.roles import RoleManager
from galaxy.schema.fields import LibraryFolderDatabaseIdField
from galaxy.schema.schema import (
    BasicRoleModel,
    CreateLibraryFolderPayload,
    LibraryAvailablePermissions,
    LibraryFolderCurrentPermissions,
    LibraryFolderDetails,
    LibraryPermissionScope,
    UpdateLibraryFolderPayload,
)
from galaxy.security.idencoding import IdEncodingHelper
from galaxy.webapps.galaxy.services.base import ServiceBase

log = logging.getLogger(__name__)


class LibraryFoldersService(ServiceBase):
    """Common interface/service logic for interactions with library folders in the context of the API.
    Provides the logic of the actions invoked by API controllers and uses type definitions
    and pydantic models to declare its parameters and return types.
    """

    def __init__(self, security: IdEncodingHelper, folder_manager: FolderManager, role_manager: RoleManager):
        super().__init__(security)
        self.folder_manager = folder_manager
        self.role_manager = role_manager

    def show(self, trans, folder_id: LibraryFolderDatabaseIdField) -> LibraryFolderDetails:
        """
        Displays information about a folder.

        :param  id:      the folder's encoded id (required)
        :type   id:      an encoded id string (has to be prefixed by 'F')

        :returns:   dictionary including details of the folder
        :rtype:     dict
        """
        folder = self.folder_manager.get(trans, folder_id, check_manageable=False, check_accessible=True)
        return_dict = self.folder_manager.get_folder_dict(trans, folder)
        return LibraryFolderDetails(**return_dict)

    def create(
        self, trans, parent_folder_id: LibraryFolderDatabaseIdField, payload: CreateLibraryFolderPayload
    ) -> LibraryFolderDetails:
        """
        Create a new folder object underneath the one specified in the parameters.

        :param  parent_folder_id:      (required) the parent folder's id
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
        parent_folder = self.folder_manager.get(trans, parent_folder_id)
        new_folder = self.folder_manager.create(trans, parent_folder.id, payload.name, payload.description)
        return_dict = self.folder_manager.get_folder_dict(trans, new_folder)
        return LibraryFolderDetails(**return_dict)

    def get_permissions(
        self,
        trans,
        folder_id: LibraryFolderDatabaseIdField,
        scope: Optional[LibraryPermissionScope] = LibraryPermissionScope.current,
        page: int = 1,
        page_limit: int = 10,
        query: Optional[str] = None,
    ) -> Union[LibraryFolderCurrentPermissions, LibraryAvailablePermissions]:
        """
        Load all permissions for the given folder id and return it.

        :param  folder_id:     the encoded id of the folder

        :param  scope:      either 'current' or 'available'
        :type   scope:      string

        :returns:   dictionary with all applicable permissions' values
        :rtype:     dictionary

        :raises: InsufficientPermissionsException
        """
        current_user_roles = trans.get_current_user_roles()
        is_admin = trans.user_is_admin
        folder = self.folder_manager.get(trans, folder_id)

        if not (is_admin or trans.app.security_agent.can_manage_library_item(current_user_roles, folder)):
            raise InsufficientPermissionsException(
                "You do not have proper permission to access permissions of this folder."
            )

        if scope is None or scope == LibraryPermissionScope.current:
            current_permissions = self.folder_manager.get_current_roles(trans, folder)
            return LibraryFolderCurrentPermissions.model_construct(**current_permissions)
        #  Return roles that are available to select.
        elif scope == LibraryPermissionScope.available:
            roles, total_roles = trans.app.security_agent.get_valid_roles(trans, folder, query, page, page_limit)
            return_roles = []
            for role in roles:
                return_roles.append(BasicRoleModel(id=role.id, name=role.name, type=role.type))
            return LibraryAvailablePermissions(roles=return_roles, page=page, page_limit=page_limit, total=total_roles)
        else:
            raise RequestParameterInvalidException(
                "The value of 'scope' parameter is invalid. Allowed values: current, available"
            )

    def set_permissions(
        self, trans, folder_id: LibraryFolderDatabaseIdField, payload: dict
    ) -> LibraryFolderCurrentPermissions:
        """
        Set permissions of the given folder to the given role ids.

        :param  folder_id:      the encoded id of the folder to set the permissions of
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
        folder = self.folder_manager.get(trans, folder_id)
        if not (is_admin or trans.app.security_agent.can_manage_library_item(current_user_roles, folder)):
            raise InsufficientPermissionsException(
                "You do not have proper permission to modify permissions of this folder."
            )

        new_add_roles_ids = util.listify(payload.get("add_ids[]", None))
        new_manage_roles_ids = util.listify(payload.get("manage_ids[]", None))
        new_modify_roles_ids = util.listify(payload.get("modify_ids[]", None))

        action = payload.get("action", None)
        if action is None:
            raise RequestParameterMissingException('The mandatory parameter "action" is missing.')
        elif action == "set_permissions":
            # ADD TO LIBRARY ROLES
            valid_add_roles = []
            invalid_add_roles_names = []
            for role_id in new_add_roles_ids:
                role = self.role_manager.get(trans, role_id)
                #  Check whether role is in the set of allowed roles
                valid_roles, total_roles = trans.app.security_agent.get_valid_roles(trans, folder)
                if role in valid_roles:
                    valid_add_roles.append(role)
                else:
                    invalid_add_roles_names.append(role_id)
            if len(invalid_add_roles_names) > 0:
                log.warning(
                    f"The following roles could not be added to the add library item permission: {str(invalid_add_roles_names)}"
                )

            # MANAGE FOLDER ROLES
            valid_manage_roles = []
            invalid_manage_roles_names = []
            for role_id in new_manage_roles_ids:
                role = self.role_manager.get(trans, role_id)
                #  Check whether role is in the set of allowed roles
                valid_roles, total_roles = trans.app.security_agent.get_valid_roles(trans, folder)
                if role in valid_roles:
                    valid_manage_roles.append(role)
                else:
                    invalid_manage_roles_names.append(role_id)
            if len(invalid_manage_roles_names) > 0:
                log.warning(
                    f"The following roles could not be added to the manage folder permission: {str(invalid_manage_roles_names)}"
                )

            # MODIFY FOLDER ROLES
            valid_modify_roles = []
            invalid_modify_roles_names = []
            for role_id in new_modify_roles_ids:
                role = self.role_manager.get(trans, role_id)
                #  Check whether role is in the set of allowed roles
                valid_roles, total_roles = trans.app.security_agent.get_valid_roles(trans, folder)
                if role in valid_roles:
                    valid_modify_roles.append(role)
                else:
                    invalid_modify_roles_names.append(role_id)
            if len(invalid_modify_roles_names) > 0:
                log.warning(
                    f"The following roles could not be added to the modify folder permission: {str(invalid_modify_roles_names)}"
                )

            permissions = {trans.app.security_agent.permitted_actions.LIBRARY_ADD: valid_add_roles}
            permissions.update({trans.app.security_agent.permitted_actions.LIBRARY_MANAGE: valid_manage_roles})
            permissions.update({trans.app.security_agent.permitted_actions.LIBRARY_MODIFY: valid_modify_roles})

            trans.app.security_agent.set_all_library_permissions(trans, folder, permissions)
        else:
            raise RequestParameterInvalidException(
                'The mandatory parameter "action" has an invalid value. Allowed values are: "set_permissions"'
            )
        current_permissions = self.folder_manager.get_current_roles(trans, folder)
        return LibraryFolderCurrentPermissions(**current_permissions)

    def delete(
        self, trans, folder_id: LibraryFolderDatabaseIdField, undelete: Optional[bool] = False
    ) -> LibraryFolderDetails:
        """
        Mark the folder with the given ``encoded_folder_id`` as `deleted`
        (or remove the `deleted` mark if the `undelete` param is true).

        .. note:: Currently, only admin users can un/delete folders.

        :param  folder_id:     the encoded id of the folder to un/delete

        :param  undelete:    (optional) flag specifying whether the item should be deleted or undeleted, defaults to false:
        :type   undelete:    bool

        :returns:   detailed folder information
        :rtype:     dictionary

        """
        folder = self.folder_manager.get(trans, folder_id, True)
        folder = self.folder_manager.delete(trans, folder, undelete)
        folder_dict = self.folder_manager.get_folder_dict(trans, folder)
        return LibraryFolderDetails(**folder_dict)

    def update(
        self, trans, folder_id: LibraryFolderDatabaseIdField, payload: UpdateLibraryFolderPayload
    ) -> LibraryFolderDetails:
        """
         Update the folder with id ``folder_id`` with the data in the payload.

        .. note:: Currently, only administrators can update library folders. Also the folder must not be `deleted`.

         :param  folder_id:      the encoded id of the folder

         :param  payload: (required) dictionary structure containing::
             'name':         new folder's name, cannot be empty
             'description':  new folder's description
         :type   payload: dict

         :returns:   detailed folder information
         :rtype:     dict

         :raises: RequestParameterMissingException
        """
        folder = self.folder_manager.get(trans, folder_id)
        updated_folder = self.folder_manager.update(trans, folder, payload.name, payload.description)
        folder_dict = self.folder_manager.get_folder_dict(trans, updated_folder)
        return LibraryFolderDetails(**folder_dict)
