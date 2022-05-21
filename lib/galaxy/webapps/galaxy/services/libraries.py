import logging
from typing import (
    Any,
    Dict,
    Optional,
    Union,
)

from galaxy import (
    exceptions,
    util,
)
from galaxy.managers.context import ProvidesAppContext
from galaxy.managers.folders import FolderManager
from galaxy.managers.libraries import LibraryManager
from galaxy.managers.roles import RoleManager
from galaxy.schema.fields import EncodedDatabaseIdField
from galaxy.schema.schema import (
    CreateLibraryPayload,
    LibraryAvailablePermissions,
    LibraryCurrentPermissions,
    LibraryLegacySummary,
    LibraryPermissionScope,
    LibrarySummary,
    LibrarySummaryList,
    UpdateLibraryPayload,
)
from galaxy.security.idencoding import IdEncodingHelper
from galaxy.webapps.galaxy.services.base import ServiceBase

log = logging.getLogger(__name__)


class LibrariesService(ServiceBase):
    """
    Common interface/service logic for interactions with libraries (top level) in the context of the API.

    Provides the logic of the actions invoked by API controllers and uses type definitions
    and pydantic models to declare its parameters and return types.
    """

    def __init__(
        self,
        security: IdEncodingHelper,
        folder_manager: FolderManager,
        library_manager: LibraryManager,
        role_manager: RoleManager,
    ):
        super().__init__(security)
        self.folder_manager = folder_manager
        self.library_manager = library_manager
        self.role_manager = role_manager

    def index(self, trans: ProvidesAppContext, deleted: Optional[bool] = False) -> LibrarySummaryList:
        """Returns a list of summary data for all libraries.

        :param  deleted: if True, show only ``deleted`` libraries, if False show only ``non-deleted``
        :type   deleted: boolean (optional)

        :returns:   list of dictionaries containing library information
        :rtype:     list

        .. seealso:: :attr:`galaxy.model.Library.dict_collection_visible_keys`

        """
        query, prefetched_ids = self.library_manager.list(trans, deleted)
        libraries = []
        for library in query:
            libraries.append(self.library_manager.get_library_dict(trans, library, prefetched_ids))
        return LibrarySummaryList.parse_obj(libraries)

    def show(self, trans, id: EncodedDatabaseIdField) -> LibrarySummary:
        """Returns detailed information about a library.

        :param  id:      the encoded id of the library
        :type   id:      an encoded id string
        :param  deleted: if True, allow information on a ``deleted`` library
        :type   deleted: boolean

        :returns:   detailed library information
        :rtype:     dict

        .. seealso:: :attr:`galaxy.model.Library.dict_element_visible_keys`

        :raises: MalformedId, ObjectNotFound
        """
        library = self.library_manager.get(trans, trans.security.decode_id(id, object_name="library"))
        library_dict = self.library_manager.get_library_dict(trans, library)
        return LibrarySummary.parse_obj(library_dict)

    def create(self, trans, payload: CreateLibraryPayload) -> LibrarySummary:
        """Creates a new library.

        .. note:: Currently, only admin users can create libraries.

        :param  payload: dictionary structure containing::
            :param name:         (required) the new library's name
            :type  name:         str
            :param description:  the new library's description
            :type  description:  str
            :param synopsis:     the new library's synopsis
            :type  synopsis:     str
        :type   payload: dict
        :returns:   detailed library information
        :rtype:     dict
        :raises: RequestParameterMissingException
        """
        library = self.library_manager.create(trans, payload.name, payload.description, payload.synopsis)
        library_dict = self.library_manager.get_library_dict(trans, library)
        return LibrarySummary.parse_obj(library_dict)

    def update(self, trans, id: EncodedDatabaseIdField, payload: UpdateLibraryPayload) -> LibrarySummary:
        """Updates the library defined by an ``encoded_id`` with the data in the payload.

        :param  id:      the encoded id of the library
        :type   id:      an encoded id string
        :param  payload: dictionary structure containing::
            :param name:         new library's name, cannot be empty
            :type  name:         str
            :param description:  new library's description
            :type  description:  str
            :param synopsis:     new library's synopsis
            :type  synopsis:     str
        :type   payload: dict
        :returns:   detailed library information
        :rtype:     dict
        :raises: RequestParameterMissingException
        """
        library = self.library_manager.get(trans, trans.security.decode_id(id, object_name="library"))
        name = payload.name
        if name == "":
            raise exceptions.RequestParameterMissingException(
                "Parameter 'name' of library is required. You cannot remove it."
            )
        updated_library = self.library_manager.update(trans, library, name, payload.description, payload.synopsis)
        library_dict = self.library_manager.get_library_dict(trans, updated_library)
        return LibrarySummary.parse_obj(library_dict)

    def delete(self, trans, id: EncodedDatabaseIdField, undelete: Optional[bool] = False) -> LibrarySummary:
        """Marks the library with the given ``id`` as `deleted` (or removes the `deleted` mark if the `undelete` param is true)

        .. note:: Currently, only admin users can un/delete libraries.

        :param  id:     the encoded id of the library to un/delete
        :type   id:     an encoded id string

        :param  undelete:    (optional) flag specifying whether the item should be deleted or undeleted, defaults to false:
        :type   undelete:    bool

        :returns:   detailed library information
        :rtype:     dictionary

        .. seealso:: :attr:`galaxy.model.Library.dict_element_visible_keys`
        """
        library = self.library_manager.get(trans, trans.security.decode_id(id, object_name="library"))
        library = self.library_manager.delete(trans, library, undelete)
        library_dict = self.library_manager.get_library_dict(trans, library)
        return LibrarySummary.parse_obj(library_dict)

    def get_permissions(
        self,
        trans,
        id: EncodedDatabaseIdField,
        scope: Optional[LibraryPermissionScope] = LibraryPermissionScope.current,
        is_library_access: Optional[bool] = False,
        page: Optional[int] = 1,
        page_limit: Optional[int] = 10,
        query: Optional[str] = None,
    ) -> Union[LibraryCurrentPermissions, LibraryAvailablePermissions]:
        """Load all permissions for the given library id and return it.

        :param  id:     the encoded id of the library
        :type   id:     an encoded id string

        :param  scope:      either 'current' or 'available'
        :type   scope:      string

        :param  is_library_access:      indicates whether the roles available for the library access are requested
        :type   is_library_access:      bool

        :returns:   dictionary with all applicable permissions' values
        :rtype:     dictionary

        :raises: InsufficientPermissionsException
        """
        current_user_roles = trans.get_current_user_roles()
        is_admin = trans.user_is_admin
        library = self.library_manager.get(trans, trans.security.decode_id(id, object_name="library"))
        if not (is_admin or trans.app.security_agent.can_manage_library_item(current_user_roles, library)):
            raise exceptions.InsufficientPermissionsException(
                "You do not have proper permission to access permissions of this library."
            )

        if scope == LibraryPermissionScope.current or scope is None:
            roles = self.library_manager.get_current_roles(trans, library)
            return LibraryCurrentPermissions.parse_obj(roles)

        #  Return roles that are available to select.
        elif scope == LibraryPermissionScope.available:
            roles, total_roles = trans.app.security_agent.get_valid_roles(
                trans, library, query, page, page_limit, is_library_access
            )

            return_roles = []
            for role in roles:
                role_id = trans.security.encode_id(role.id)
                return_roles.append(dict(id=role_id, name=role.name, type=role.type))
            return LibraryAvailablePermissions(roles=return_roles, page=page, page_limit=page_limit, total=total_roles)
        else:
            raise exceptions.RequestParameterInvalidException(
                "The value of 'scope' parameter is invalid. Alllowed values: current, available"
            )

    def set_permissions(
        self, trans, id: EncodedDatabaseIdField, payload: Dict[str, Any]
    ) -> Union[LibraryLegacySummary, LibraryCurrentPermissions]:  # Old legacy response
        """Set permissions of the given library to the given role ids.

        :param  id:      the encoded id of the library to set the permissions of
        :type   id:      an encoded id string
        :param   payload: dictionary structure containing:

            :param  action:            (required) describes what action should be performed
                                       available actions: remove_restrictions, set_permissions
            :type   action:            str
            :param  access_ids[]:      list of Role.id defining roles that should have access permission on the library
            :type   access_ids[]:      string or list
            :param  add_ids[]:         list of Role.id defining roles that should have add item permission on the library
            :type   add_ids[]:         string or list
            :param  manage_ids[]:      list of Role.id defining roles that should have manage permission on the library
            :type   manage_ids[]:      string or list
            :param  modify_ids[]:      list of Role.id defining roles that should have modify permission on the library
            :type   modify_ids[]:      string or list

        :type:      dictionary
        :returns:   dict of current roles for all available permission types
        :rtype:     dictionary
        :raises: RequestParameterInvalidException, InsufficientPermissionsException, InternalServerError
                    RequestParameterMissingException
        """
        is_admin = trans.user_is_admin
        current_user_roles = trans.get_current_user_roles()
        library = self.library_manager.get(trans, trans.security.decode_id(id, object_name="library"))

        if not (is_admin or trans.app.security_agent.can_manage_library_item(current_user_roles, library)):
            raise exceptions.InsufficientPermissionsException(
                "You do not have proper permission to modify permissions of this library."
            )

        new_access_roles_ids = util.listify(payload.get("access_ids[]", None))
        new_add_roles_ids = util.listify(payload.get("add_ids[]", None))
        new_manage_roles_ids = util.listify(payload.get("manage_ids[]", None))
        new_modify_roles_ids = util.listify(payload.get("modify_ids[]", None))

        action = payload.get("action", None)
        if action is None:
            if payload is not None:
                return self.set_permissions_old(trans, library, payload)
            else:
                raise exceptions.RequestParameterMissingException('The mandatory parameter "action" is missing.')
        elif action == "remove_restrictions":
            is_public = self.library_manager.make_public(trans, library)
            if not is_public:
                raise exceptions.InternalServerError("An error occurred while making library public.")
        elif action == "set_permissions":

            # ACCESS LIBRARY ROLES
            valid_access_roles = []
            invalid_access_roles_names = []
            for role_id in new_access_roles_ids:
                role = self.role_manager.get(trans, trans.security.decode_id(role_id, object_name="role"))
                valid_roles, total_roles = trans.app.security_agent.get_valid_roles(
                    trans, library, is_library_access=True
                )
                if role in valid_roles:
                    valid_access_roles.append(role)
                else:
                    invalid_access_roles_names.append(role_id)
            if len(invalid_access_roles_names) > 0:
                log.warning(
                    f"The following roles could not be added to the library access permission: {str(invalid_access_roles_names)}"
                )

            # ADD TO LIBRARY ROLES
            valid_add_roles = []
            invalid_add_roles_names = []
            for role_id in new_add_roles_ids:
                role = self.role_manager.get(trans, trans.security.decode_id(role_id, object_name="role"))
                valid_roles, total_roles = trans.app.security_agent.get_valid_roles(trans, library)
                if role in valid_roles:
                    valid_add_roles.append(role)
                else:
                    invalid_add_roles_names.append(role_id)
            if len(invalid_add_roles_names) > 0:
                log.warning(
                    f"The following roles could not be added to the add library item permission: {str(invalid_add_roles_names)}"
                )

            # MANAGE LIBRARY ROLES
            valid_manage_roles = []
            invalid_manage_roles_names = []
            for role_id in new_manage_roles_ids:
                role = self.role_manager.get(trans, trans.security.decode_id(role_id, object_name="role"))
                valid_roles, total_roles = trans.app.security_agent.get_valid_roles(trans, library)
                if role in valid_roles:
                    valid_manage_roles.append(role)
                else:
                    invalid_manage_roles_names.append(role_id)
            if len(invalid_manage_roles_names) > 0:
                log.warning(
                    f"The following roles could not be added to the manage library permission: {str(invalid_manage_roles_names)}"
                )

            # MODIFY LIBRARY ROLES
            valid_modify_roles = []
            invalid_modify_roles_names = []
            for role_id in new_modify_roles_ids:
                role = self.role_manager.get(trans, trans.security.decode_id(role_id, object_name="role"))
                valid_roles, total_roles = trans.app.security_agent.get_valid_roles(trans, library)
                if role in valid_roles:
                    valid_modify_roles.append(role)
                else:
                    invalid_modify_roles_names.append(role_id)
            if len(invalid_modify_roles_names) > 0:
                log.warning(
                    f"The following roles could not be added to the modify library permission: {str(invalid_modify_roles_names)}"
                )

            permissions = {trans.app.security_agent.permitted_actions.LIBRARY_ACCESS: valid_access_roles}
            permissions.update({trans.app.security_agent.permitted_actions.LIBRARY_ADD: valid_add_roles})
            permissions.update({trans.app.security_agent.permitted_actions.LIBRARY_MANAGE: valid_manage_roles})
            permissions.update({trans.app.security_agent.permitted_actions.LIBRARY_MODIFY: valid_modify_roles})

            trans.app.security_agent.set_all_library_permissions(trans, library, permissions)
            trans.sa_session.refresh(library)
            # Copy the permissions to the root folder
            trans.app.security_agent.copy_library_permissions(trans, library, library.root_folder)
        else:
            raise exceptions.RequestParameterInvalidException(
                'The mandatory parameter "action" has an invalid value.'
                'Allowed values are: "remove_restrictions", set_permissions"'
            )
        roles = self.library_manager.get_current_roles(trans, library)
        return LibraryCurrentPermissions.parse_obj(roles)

    def set_permissions_old(self, trans, library, payload) -> LibraryLegacySummary:
        """
        *** old implementation for backward compatibility ***

        Updates the library permissions.
        """
        params = util.Params(payload)
        permissions = {}
        for k, v in trans.app.model.Library.permitted_actions.items():
            role_params = params.get(f"{k}_in", [])
            in_roles = [
                trans.sa_session.query(trans.app.model.Role).get(trans.security.decode_id(x))
                for x in util.listify(role_params)
            ]
            permissions[trans.app.security_agent.get_action(v.action)] = in_roles
        trans.app.security_agent.set_all_library_permissions(trans, library, permissions)
        trans.sa_session.refresh(library)
        # Copy the permissions to the root folder
        trans.app.security_agent.copy_library_permissions(trans, library, library.root_folder)
        item = library.to_dict(
            view="element", value_mapper={"id": trans.security.encode_id, "root_folder_id": trans.security.encode_id}
        )
        return LibraryLegacySummary.parse_obj(item)
