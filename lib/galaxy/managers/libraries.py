"""
Manager and Serializer for libraries.
"""
import logging
from datetime import datetime
from enum import Enum
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Tuple,
    Union,
)

from pydantic import (
    BaseModel,
    Field,
)
from sqlalchemy import and_, false, not_, or_, true
from sqlalchemy.orm.exc import MultipleResultsFound
from sqlalchemy.orm.exc import NoResultFound

from galaxy import (
    exceptions,
    util,
)
from galaxy.managers import (
    folders,
)
from galaxy.managers.context import ProvidesAppContext
from galaxy.managers.roles import (
    BasicRoleModel,
    RoleManager,
)
from galaxy.schema.fields import EncodedDatabaseIdField
from galaxy.util import (
    pretty_print_time_interval,
    unicodify,
)

log = logging.getLogger(__name__)


# =============================================================================
class LibraryManager:
    """
    Interface/service object for interacting with libraries.
    """

    def get(self, trans, decoded_library_id, check_accessible=True):
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
            library = trans.sa_session.query(trans.app.model.Library).filter(trans.app.model.Library.table.c.id == decoded_library_id).one()
        except MultipleResultsFound:
            raise exceptions.InconsistentDatabase('Multiple libraries found with the same id.')
        except NoResultFound:
            raise exceptions.RequestParameterInvalidException('No library found with the id provided.')
        except Exception as e:
            raise exceptions.InternalServerError(f"Error loading from the database.{unicodify(e)}")
        library = self.secure(trans, library, check_accessible)
        return library

    def create(self, trans, name, description='', synopsis=''):
        """
        Create a new library.
        """
        if not trans.user_is_admin:
            raise exceptions.ItemAccessibilityException('Only administrators can create libraries.')
        else:
            library = trans.app.model.Library(name=name, description=description, synopsis=synopsis)
            root_folder = trans.app.model.LibraryFolder(name=name, description='')
            library.root_folder = root_folder
            trans.sa_session.add_all((library, root_folder))
            trans.sa_session.flush()
            return library

    def update(self, trans, library, name=None, description=None, synopsis=None):
        """
        Update the given library
        """
        changed = False
        if not trans.user_is_admin:
            raise exceptions.ItemAccessibilityException('Only administrators can update libraries.')
        if library.deleted:
            raise exceptions.RequestParameterInvalidException('You cannot modify a deleted library. Undelete it first.')
        if name is not None:
            library.name = name
            changed = True
            #  When library is renamed the root folder has to be renamed too.
            folder_manager = folders.FolderManager()
            folder_manager.update(trans, library.root_folder, name=name)
        if description is not None:
            library.description = description
            changed = True
        if synopsis is not None:
            library.synopsis = synopsis
            changed = True
        if changed:
            trans.sa_session.add(library)
            trans.sa_session.flush()
        return library

    def delete(self, trans, library, undelete=False):
        """
        Mark given library deleted/undeleted based on the flag.
        """
        if not trans.user_is_admin:
            raise exceptions.ItemAccessibilityException('Only administrators can delete and undelete libraries.')
        if undelete:
            library.deleted = False
        else:
            library.deleted = True
        trans.sa_session.add(library)
        trans.sa_session.flush()
        return library

    def list(self, trans, deleted: Optional[bool] = False):
        """
        Return a list of libraries from the DB.

        :param  deleted: if True, show only ``deleted`` libraries, if False show only ``non-deleted``
        :type   deleted: boolean (optional)

        :returns: query that will emit all accessible libraries
        :rtype:   sqlalchemy query
        :returns: dict of 3 sets with available actions for user's accessible
                  libraries and a set of ids of all public libraries. These are
                  used for limiting the number of queries when dictifying the
                  libraries later on.
        :rtype:   dict
        """
        is_admin = trans.user_is_admin
        query = trans.sa_session.query(trans.app.model.Library)
        library_access_action = trans.app.security_agent.permitted_actions.LIBRARY_ACCESS.action
        restricted_library_ids = {lp.library_id for lp in (
            trans.sa_session.query(trans.model.LibraryPermissions).filter(
                trans.model.LibraryPermissions.table.c.action == library_access_action
            ).distinct())}
        prefetched_ids = {'restricted_library_ids': restricted_library_ids}
        if is_admin:
            if deleted is None:
                #  Flag is not specified, do not filter on it.
                pass
            elif deleted:
                query = query.filter(trans.app.model.Library.table.c.deleted == true())
            else:
                query = query.filter(trans.app.model.Library.table.c.deleted == false())
        else:
            #  Nonadmins can't see deleted libraries
            query = query.filter(trans.app.model.Library.table.c.deleted == false())
            current_user_role_ids = [role.id for role in trans.get_current_user_roles()]
            all_actions = trans.sa_session.query(trans.model.LibraryPermissions).filter(trans.model.LibraryPermissions.table.c.role_id.in_(current_user_role_ids))
            library_add_action = trans.app.security_agent.permitted_actions.LIBRARY_ADD.action
            library_modify_action = trans.app.security_agent.permitted_actions.LIBRARY_MODIFY.action
            library_manage_action = trans.app.security_agent.permitted_actions.LIBRARY_MANAGE.action
            accessible_restricted_library_ids = set()
            allowed_library_add_ids = set()
            allowed_library_modify_ids = set()
            allowed_library_manage_ids = set()
            for action in all_actions:
                if action.action == library_access_action:
                    accessible_restricted_library_ids.add(action.library_id)
                if action.action == library_add_action:
                    allowed_library_add_ids.add(action.library_id)
                if action.action == library_modify_action:
                    allowed_library_modify_ids.add(action.library_id)
                if action.action == library_manage_action:
                    allowed_library_manage_ids.add(action.library_id)
            query = query.filter(or_(
                not_(trans.model.Library.table.c.id.in_(restricted_library_ids)),
                trans.model.Library.table.c.id.in_(accessible_restricted_library_ids)
            ))
            prefetched_ids['allowed_library_add_ids'] = allowed_library_add_ids
            prefetched_ids['allowed_library_modify_ids'] = allowed_library_modify_ids
            prefetched_ids['allowed_library_manage_ids'] = allowed_library_manage_ids
        return query, prefetched_ids

    def secure(self, trans, library, check_accessible=True):
        """
        Check if library is accessible to user.

        :param  library:                 library
        :type   library:                 galaxy.model.Library
        :param  check_accessible:        flag whether to check that user can access library
        :type   check_accessible:        bool

        :returns:   the original library
        :rtype:     galaxy.model.Library
        """
        # all libraries are accessible to an admin
        if trans.user_is_admin:
            return library
        if check_accessible:
            library = self.check_accessible(trans, library)
        return library

    def check_accessible(self, trans, library):
        """
        Check whether the library is accessible to current user.
        """
        if not trans.app.security_agent.can_access_library(trans.get_current_user_roles(), library):
            raise exceptions.ObjectNotFound('Library with the id provided was not found.')
        elif library.deleted:
            raise exceptions.ObjectNotFound('Library with the id provided is deleted.')
        else:
            return library

    def get_library_dict(self, trans, library, prefetched_ids=None):
        """
        Return library data in the form of a dictionary.

        :param  library:         library
        :type   library:         galaxy.model.Library
        :param  prefetched_ids:  dict of 3 sets with available actions for user's accessible
                                 libraries and a set of ids of all public libraries. These are
                                 used for limiting the number of queries when dictifying a
                                 set of libraries.
        :type   prefetched_ids:  dict

        :returns:   dict with data about the library
        :rtype:     dictionary
        """
        restricted_library_ids = prefetched_ids.get('restricted_library_ids', None) if prefetched_ids else None
        allowed_library_add_ids = prefetched_ids.get('allowed_library_add_ids', None) if prefetched_ids else None
        allowed_library_modify_ids = prefetched_ids.get('allowed_library_modify_ids', None) if prefetched_ids else None
        allowed_library_manage_ids = prefetched_ids.get('allowed_library_manage_ids', None) if prefetched_ids else None
        library_dict = library.to_dict(view='element', value_mapper={'id': trans.security.encode_id, 'root_folder_id': trans.security.encode_id})
        library_dict['public'] = False if (restricted_library_ids and library.id in restricted_library_ids) else True
        library_dict['create_time_pretty'] = pretty_print_time_interval(library.create_time, precise=True)
        if not trans.user_is_admin:
            if prefetched_ids:
                library_dict['can_user_add'] = True if (allowed_library_add_ids and library.id in allowed_library_add_ids) else False
                library_dict['can_user_modify'] = True if (allowed_library_modify_ids and library.id in allowed_library_modify_ids) else False
                library_dict['can_user_manage'] = True if (allowed_library_manage_ids and library.id in allowed_library_manage_ids) else False
            else:
                current_user_roles = trans.get_current_user_roles()
                library_dict['can_user_add'] = trans.app.security_agent.can_add_library_item(current_user_roles, library)
                library_dict['can_user_modify'] = trans.app.security_agent.can_modify_library_item(current_user_roles, library)
                library_dict['can_user_manage'] = trans.app.security_agent.can_manage_library_item(current_user_roles, library)
        else:
            library_dict['can_user_add'] = True
            library_dict['can_user_modify'] = True
            library_dict['can_user_manage'] = True
        return library_dict

    def get_current_roles(self, trans, library):
        """
        Load all permissions currently related to the given library.

        :param  library:      the model object
        :type   library:      galaxy.model.Library

        :rtype:     dictionary
        :returns:   dict of current roles for all available permission types
        """
        access_library_role_list = [(access_role.name, trans.security.encode_id(access_role.id)) for access_role in self.get_access_roles(trans, library)]
        modify_library_role_list = [(modify_role.name, trans.security.encode_id(modify_role.id)) for modify_role in self.get_modify_roles(trans, library)]
        manage_library_role_list = [(manage_role.name, trans.security.encode_id(manage_role.id)) for manage_role in self.get_manage_roles(trans, library)]
        add_library_item_role_list = [(add_role.name, trans.security.encode_id(add_role.id)) for add_role in self.get_add_roles(trans, library)]
        return dict(access_library_role_list=access_library_role_list,
                    modify_library_role_list=modify_library_role_list,
                    manage_library_role_list=manage_library_role_list,
                    add_library_item_role_list=add_library_item_role_list)

    def get_access_roles(self, trans, library):
        """
        Load access roles for all library permissions
        """
        return set(library.get_access_roles(trans.app.security_agent))

    def get_modify_roles(self, trans, library):
        """
        Load modify roles for all library permissions
        """
        return set(trans.app.security_agent.get_roles_for_action(library, trans.app.security_agent.permitted_actions.LIBRARY_MODIFY))

    def get_manage_roles(self, trans, library):
        """
        Load manage roles for all library permissions
        """
        return set(trans.app.security_agent.get_roles_for_action(library, trans.app.security_agent.permitted_actions.LIBRARY_MANAGE))

    def get_add_roles(self, trans, library):
        """
        Load add roles for all library permissions
        """
        return set(trans.app.security_agent.get_roles_for_action(library, trans.app.security_agent.permitted_actions.LIBRARY_ADD))

    def set_permission_roles(self, trans, library, access_roles, modify_roles, manage_roles, add_roles):
        """
        Set permissions on the given library.
        """

    def make_public(self, trans, library):
        """
        Makes the given library public (removes all access roles)
        """
        trans.app.security_agent.make_library_public(library)
        return self.is_public(trans, library)

    def is_public(self, trans, library):
        """
        Return true if lib is public.
        """
        return trans.app.security_agent.library_is_public(library)


def get_containing_library_from_library_dataset(trans, library_dataset):
    """Given a library_dataset, get the containing library"""
    folder = library_dataset.folder
    while folder.parent:
        folder = folder.parent
    # We have folder set to the library's root folder, which has the same name as the library
    for library in trans.sa_session.query(trans.model.Library).filter(
        and_(trans.model.Library.table.c.deleted == false(),
            trans.model.Library.table.c.name == folder.name)):
        # Just to double-check
        if library.root_folder == folder:
            return library
    return None


class LibraryLegacySummary(BaseModel):
    model_class: str = Field(
        "Library", const=True,
        title="Model class",
        description="The name of the database model class.",
    )
    id: EncodedDatabaseIdField = Field(
        ...,
        title="ID",
        description="Encoded ID of the Library.",
    )
    name: str = Field(
        ...,
        title="Name",
        description="The name of the Library.",
    )
    description: Optional[str] = Field(
        "",
        title="Description",
        description="A detailed description of the Library.",
    )
    synopsis: Optional[str] = Field(
        None,
        title="Description",
        description="A short text describing the contents of the Library.",
    )
    root_folder_id: EncodedDatabaseIdField = Field(
        ...,
        title="Root Folder ID",
        description="Encoded ID of the Library's base folder.",
    )
    create_time: datetime = Field(
        ...,
        title="Create Time",
        description="The time and date this item was created.",
    )
    deleted: bool = Field(
        ...,
        title="Deleted",
        description="Whether this Library has been deleted.",
    )


class LibrarySummary(LibraryLegacySummary):
    create_time_pretty: str = Field(  # This is somewhat redundant, maybe the client can do this with `create_time`?
        ...,
        title="Create Time Pretty",
        description="Nice time representation of the creation date.",
        example="2 months ago",
    )
    public: bool = Field(
        ...,
        title="Public",
        description="Whether this Library has been deleted.",
    )
    can_user_add: bool = Field(
        ...,
        title="Can User Add",
        description="Whether the current user can add contents to this Library.",
    )
    can_user_modify: bool = Field(
        ...,
        title="Can User Modify",
        description="Whether the current user can modify this Library.",
    )
    can_user_manage: bool = Field(
        ...,
        title="Can User Manage",
        description="Whether the current user can manage the Library and its contents.",
    )


class LibrarySummaryList(BaseModel):
    __root__: List[LibrarySummary] = Field(
        default=[],
        title='List with summary information of Libraries.',
    )


class CreateLibraryPayload(BaseModel):
    name: str = Field(
        ...,
        title="Name",
        description="The name of the Library.",
    )
    description: Optional[str] = Field(
        "",
        title="Description",
        description="A detailed description of the Library.",
    )
    synopsis: Optional[str] = Field(
        "",
        title="Synopsis",
        description="A short text describing the contents of the Library.",
    )


class UpdateLibraryPayload(BaseModel):
    name: Optional[str] = Field(
        None,
        title="Name",
        description="The new name of the Library. Leave unset to keep the existing.",
    )
    description: Optional[str] = Field(
        None,
        title="Description",
        description="A detailed description of the Library. Leave unset to keep the existing.",
    )
    synopsis: Optional[str] = Field(
        None,
        title="Synopsis",
        description="A short text describing the contents of the Library. Leave unset to keep the existing.",
    )


class DeleteLibraryPayload(BaseModel):
    undelete: bool = Field(
        ...,
        title="Undelete",
        description="Whether to restore this previously deleted library.",
    )


class LibraryPermissionScope(str, Enum):
    current = "current"
    available = "available"


# The tuple should probably be another proper model instead?
# Keeping it as a Tuple for now for backward compatibility
RoleNameIdTuple = Tuple[str, EncodedDatabaseIdField]


class LibraryCurrentPermissions(BaseModel):
    access_library_role_list: List[RoleNameIdTuple] = Field(
        ...,
        title="Access Role List",
        description="A list containing pairs of role names and corresponding encoded IDs which have access to the Library.",
    )
    modify_library_role_list: List[RoleNameIdTuple] = Field(
        ...,
        title="Modify Role List",
        description="A list containing pairs of role names and corresponding encoded IDs which can modify the Library.",
    )
    manage_library_role_list: List[RoleNameIdTuple] = Field(
        ...,
        title="Manage Role List",
        description="A list containing pairs of role names and corresponding encoded IDs which can manage the Library.",
    )
    add_library_item_role_list: List[RoleNameIdTuple] = Field(
        ...,
        title="Add Role List",
        description="A list containing pairs of role names and corresponding encoded IDs which can add items to the Library.",
    )


class LibraryAvailablePermissions(BaseModel):
    roles: List[BasicRoleModel] = Field(
        ...,
        title="Roles",
        description="A list available roles that can be assigned to a particular permission.",
    )
    page: int = Field(
        ...,
        title="Page",
        description="Current page .",
    )
    page_limit: int = Field(
        ...,
        title="Page Limit",
        description="Maximum number of items per page.",
    )
    total: int = Field(
        ...,
        title="Total",
        description="Total number of items",
    )


RoleIdList = Union[List[EncodedDatabaseIdField], EncodedDatabaseIdField]  # Should we support just List[EncodedDatabaseIdField] in the future?


class LegacyLibraryPermissionsPayload(BaseModel):
    LIBRARY_ACCESS_in: Optional[RoleIdList] = Field(
        [],
        title="Access IDs",
        description="A list of role encoded IDs defining roles that should have access permission on the library.",
    )
    LIBRARY_MODIFY_in: Optional[RoleIdList] = Field(
        [],
        title="Add IDs",
        description="A list of role encoded IDs defining roles that should be able to add items to the library.",
    )
    LIBRARY_ADD_in: Optional[RoleIdList] = Field(
        [],
        title="Manage IDs",
        description="A list of role encoded IDs defining roles that should have manage permission on the library.",
    )
    LIBRARY_MANAGE_in: Optional[RoleIdList] = Field(
        [],
        title="Modify IDs",
        description="A list of role encoded IDs defining roles that should have modify permission on the library.",
    )


class LibraryPermissionAction(str, Enum):
    set_permissions = "set_permissions"
    remove_restrictions = "remove_restrictions"  # name inconsistency? should be `make_public`?


class LibraryPermissionsPayload(BaseModel):
    class Config:
        use_enum_values = True  # When using .dict()
        allow_population_by_alias = True

    action: LibraryPermissionAction = Field(
        ...,
        title="Action",
        description="Indicates what action should be performed on the Library.",
    )
    access_ids: Optional[RoleIdList] = Field(
        [],
        alias="access_ids[]",  # Added for backward compatibility but it looks really ugly...
        title="Access IDs",
        description="A list of role encoded IDs defining roles that should have access permission on the library.",
    )
    add_ids: Optional[RoleIdList] = Field(
        [],
        alias="add_ids[]",
        title="Add IDs",
        description="A list of role encoded IDs defining roles that should be able to add items to the library.",
    )
    manage_ids: Optional[RoleIdList] = Field(
        [],
        alias="manage_ids[]",
        title="Manage IDs",
        description="A list of role encoded IDs defining roles that should have manage permission on the library.",
    )
    modify_ids: Optional[RoleIdList] = Field(
        [],
        alias="modify_ids[]",
        title="Modify IDs",
        description="A list of role encoded IDs defining roles that should have modify permission on the library.",
    )


class LibrariesService:
    """
    Interface/service object for sharing logic between controllers.
    """

    def __init__(
        self,
        folder_manager: folders.FolderManager,
        library_manager: LibraryManager,
        role_manager: RoleManager,
    ):
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
        """ Returns detailed information about a library.

        :param  id:      the encoded id of the library
        :type   id:      an encoded id string
        :param  deleted: if True, allow information on a ``deleted`` library
        :type   deleted: boolean

        :returns:   detailed library information
        :rtype:     dict

        .. seealso:: :attr:`galaxy.model.Library.dict_element_visible_keys`

        :raises: MalformedId, ObjectNotFound
        """
        library = self.library_manager.get(trans, trans.security.decode_id(id, object_name='library'))
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

       .. note:: Currently, only admin users can update libraries. Also the library must not be `deleted`.

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
        library = self.library_manager.get(trans, trans.security.decode_id(id, object_name='library'))
        name = payload.name
        if name == '':
            raise exceptions.RequestParameterMissingException("Parameter 'name' of library is required. You cannot remove it.")
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
        library = self.library_manager.get(trans, trans.security.decode_id(id, object_name='library'))
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
        library = self.library_manager.get(trans, trans.security.decode_id(id, object_name='library'))
        if not (is_admin or trans.app.security_agent.can_manage_library_item(current_user_roles, library)):
            raise exceptions.InsufficientPermissionsException('You do not have proper permission to access permissions of this library.')

        if scope == LibraryPermissionScope.current or scope is None:
            roles = self.library_manager.get_current_roles(trans, library)
            return LibraryCurrentPermissions.parse_obj(roles)

        #  Return roles that are available to select.
        elif scope == LibraryPermissionScope.available:
            roles, total_roles = trans.app.security_agent.get_valid_roles(trans, library, query, page, page_limit, is_library_access)

            return_roles = []
            for role in roles:
                role_id = trans.security.encode_id(role.id)
                return_roles.append(dict(id=role_id, name=role.name, type=role.type))
            return LibraryAvailablePermissions(roles=return_roles, page=page, page_limit=page_limit, total=total_roles)
        else:
            raise exceptions.RequestParameterInvalidException("The value of 'scope' parameter is invalid. Alllowed values: current, available")

    def set_permissions(
        self, trans, id: EncodedDatabaseIdField, payload: Dict[str, Any]
    ) -> Union[
        LibraryLegacySummary,  # Old legacy response
        LibraryCurrentPermissions,
    ]:
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
        library = self.library_manager.get(trans, trans.security.decode_id(id, object_name='library'))

        if not (is_admin or trans.app.security_agent.can_manage_library_item(current_user_roles, library)):
            raise exceptions.InsufficientPermissionsException('You do not have proper permission to modify permissions of this library.')

        new_access_roles_ids = util.listify(payload.get('access_ids[]', None))
        new_add_roles_ids = util.listify(payload.get('add_ids[]', None))
        new_manage_roles_ids = util.listify(payload.get('manage_ids[]', None))
        new_modify_roles_ids = util.listify(payload.get('modify_ids[]', None))

        action = payload.get('action', None)
        if action is None:
            if payload is not None:
                return self.set_permissions_old(trans, library, payload)
            else:
                raise exceptions.RequestParameterMissingException('The mandatory parameter "action" is missing.')
        elif action == 'remove_restrictions':
            is_public = self.library_manager.make_public(trans, library)
            if not is_public:
                raise exceptions.InternalServerError('An error occurred while making library public.')
        elif action == 'set_permissions':

            # ACCESS LIBRARY ROLES
            valid_access_roles = []
            invalid_access_roles_names = []
            for role_id in new_access_roles_ids:
                role = self.role_manager.get(trans, trans.security.decode_id(role_id, object_name='role'))
                valid_roles, total_roles = trans.app.security_agent.get_valid_roles(trans, library, is_library_access=True)
                if role in valid_roles:
                    valid_access_roles.append(role)
                else:
                    invalid_access_roles_names.append(role_id)
            if len(invalid_access_roles_names) > 0:
                log.warning(f"The following roles could not be added to the library access permission: {str(invalid_access_roles_names)}")

            # ADD TO LIBRARY ROLES
            valid_add_roles = []
            invalid_add_roles_names = []
            for role_id in new_add_roles_ids:
                role = self.role_manager.get(trans, trans.security.decode_id(role_id, object_name='role'))
                valid_roles, total_roles = trans.app.security_agent.get_valid_roles(trans, library)
                if role in valid_roles:
                    valid_add_roles.append(role)
                else:
                    invalid_add_roles_names.append(role_id)
            if len(invalid_add_roles_names) > 0:
                log.warning(f"The following roles could not be added to the add library item permission: {str(invalid_add_roles_names)}")

            # MANAGE LIBRARY ROLES
            valid_manage_roles = []
            invalid_manage_roles_names = []
            for role_id in new_manage_roles_ids:
                role = self.role_manager.get(trans, trans.security.decode_id(role_id, object_name='role'))
                valid_roles, total_roles = trans.app.security_agent.get_valid_roles(trans, library)
                if role in valid_roles:
                    valid_manage_roles.append(role)
                else:
                    invalid_manage_roles_names.append(role_id)
            if len(invalid_manage_roles_names) > 0:
                log.warning(f"The following roles could not be added to the manage library permission: {str(invalid_manage_roles_names)}")

            # MODIFY LIBRARY ROLES
            valid_modify_roles = []
            invalid_modify_roles_names = []
            for role_id in new_modify_roles_ids:
                role = self.role_manager.get(trans, trans.security.decode_id(role_id, object_name='role'))
                valid_roles, total_roles = trans.app.security_agent.get_valid_roles(trans, library)
                if role in valid_roles:
                    valid_modify_roles.append(role)
                else:
                    invalid_modify_roles_names.append(role_id)
            if len(invalid_modify_roles_names) > 0:
                log.warning(f"The following roles could not be added to the modify library permission: {str(invalid_modify_roles_names)}")

            permissions = {trans.app.security_agent.permitted_actions.LIBRARY_ACCESS: valid_access_roles}
            permissions.update({trans.app.security_agent.permitted_actions.LIBRARY_ADD: valid_add_roles})
            permissions.update({trans.app.security_agent.permitted_actions.LIBRARY_MANAGE: valid_manage_roles})
            permissions.update({trans.app.security_agent.permitted_actions.LIBRARY_MODIFY: valid_modify_roles})

            trans.app.security_agent.set_all_library_permissions(trans, library, permissions)
            trans.sa_session.refresh(library)
            # Copy the permissions to the root folder
            trans.app.security_agent.copy_library_permissions(trans, library, library.root_folder)
        else:
            raise exceptions.RequestParameterInvalidException('The mandatory parameter "action" has an invalid value.'
                                                              'Allowed values are: "remove_restrictions", set_permissions"')
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
            in_roles = [trans.sa_session.query(trans.app.model.Role).get(trans.security.decode_id(x)) for x in util.listify(role_params)]
            permissions[trans.app.security_agent.get_action(v.action)] = in_roles
        trans.app.security_agent.set_all_library_permissions(trans, library, permissions)
        trans.sa_session.refresh(library)
        # Copy the permissions to the root folder
        trans.app.security_agent.copy_library_permissions(trans, library, library.root_folder)
        item = library.to_dict(view='element', value_mapper={'id': trans.security.encode_id, 'root_folder_id': trans.security.encode_id})
        return LibraryLegacySummary.parse_obj(item)
