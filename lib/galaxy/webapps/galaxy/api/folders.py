"""
API operations on library folders.
"""
import logging
from typing import (
    Optional,
    Union,
)

from fastapi import (
    Body,
    Path,
    Query,
)

from galaxy import (
    exceptions,
    util
)
from galaxy.managers.context import ProvidesUserContext
from galaxy.schema.fields import EncodedDatabaseIdField
from galaxy.schema.schema import (
    CreateLibraryFolderPayload,
    LibraryAvailablePermissions,
    LibraryFolderCurrentPermissions,
    LibraryFolderDetails,
    LibraryFolderPermissionAction,
    LibraryFolderPermissionsPayload,
    LibraryPermissionScope,
    UpdateLibraryFolderPayload,
)
from galaxy.web import expose_api
from galaxy.webapps.galaxy.services.library_folders import LibraryFoldersService
from . import (
    BaseGalaxyAPIController,
    depends,
    DependsOnTrans,
    Router,
)

log = logging.getLogger(__name__)

router = Router(tags=['folders'])

FolderIdPathParam: EncodedDatabaseIdField = Path(
    ...,
    title="Folder ID",
    description="The encoded identifier of the library folder."
)

UndeleteQueryParam: Optional[bool] = Query(
    default=None,
    title="Undelete",
    description="Whether to restore a deleted library folder."
)


@router.cbv
class FastAPILibraryFolders:
    service: LibraryFoldersService = depends(LibraryFoldersService)

    @router.get(
        '/api/folders/{id}',
        summary="Displays information about a particular library folder.",
    )
    def show(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        id: EncodedDatabaseIdField = FolderIdPathParam,
    ) -> LibraryFolderDetails:
        """Returns detailed information about the library folder with the given ID."""
        return self.service.show(trans, id)

    @router.post(
        '/api/folders/{id}',
        summary="Create a new library folder underneath the one specified by the ID.",
    )
    def create(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        id: EncodedDatabaseIdField = FolderIdPathParam,
        payload: CreateLibraryFolderPayload = Body(...)

    ) -> LibraryFolderDetails:
        """Returns detailed information about the newly created library folder."""
        return self.service.create(trans, id, payload)

    @router.put(
        '/api/folders/{id}',
        summary="Updates the information of an existing library folder.",
    )
    @router.patch('/api/folders/{id}')
    def update(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        id: EncodedDatabaseIdField = FolderIdPathParam,
        payload: UpdateLibraryFolderPayload = Body(...),
    ) -> LibraryFolderDetails:
        """Updates the information of an existing library folder."""
        return self.service.update(trans, id, payload)

    @router.delete(
        '/api/folders/{id}',
        summary="Marks the specified library folder as deleted (or undeleted).",
    )
    def delete(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        id: EncodedDatabaseIdField = FolderIdPathParam,
        undelete: Optional[bool] = UndeleteQueryParam,
    ) -> LibraryFolderDetails:
        """Marks the specified library folder as deleted (or undeleted)."""
        return self.service.delete(trans, id, undelete)

    @router.get(
        '/api/folders/{id}/permissions',
        summary="Gets the current or available permissions of a particular library folder.",
    )
    def get_permissions(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        id: EncodedDatabaseIdField = FolderIdPathParam,
        scope: Optional[LibraryPermissionScope] = Query(
            None, title="Scope",
            description="The scope of the permissions to retrieve. Either the `current` permissions or the `available`."
        ),
        page: Optional[int] = Query(
            default=1,
            title="Page",
            description="The page number to retrieve when paginating the available roles."
        ),
        page_limit: Optional[int] = Query(
            default=10,
            title="Page Limit",
            description="The maximum number of permissions per page when paginating."
        ),
        q: Optional[str] = Query(
            None, title="Query",
            description="Optional search text to retrieve only the roles matching this query."
        ),
    ) -> Union[LibraryFolderCurrentPermissions, LibraryAvailablePermissions]:
        """Gets the current or available permissions of a particular library.
        The results can be paginated and additionally filtered by a query."""
        return self.service.get_permissions(
            trans,
            id,
            scope,
            page,
            page_limit,
            q,
        )

    @router.post(
        '/api/folders/{id}/permissions',
        summary="Sets the permissions to manage a library folder.",
    )
    def set_permissions(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        id: EncodedDatabaseIdField = FolderIdPathParam,
        action: Optional[LibraryFolderPermissionAction] = Query(
            default=None,
            title="Action",
            description=(
                "Indicates what action should be performed on the Library. "
                f"Currently only `{LibraryFolderPermissionAction.set_permissions}` is supported."
            ),
        ),
        payload: LibraryFolderPermissionsPayload = Body(...),
    ) -> LibraryFolderCurrentPermissions:
        """Sets the permissions to manage a library folder."""
        payload_dict = payload.dict(by_alias=True)
        if isinstance(payload, LibraryFolderPermissionsPayload) and action is not None:
            payload_dict["action"] = action
        return self.service.set_permissions(trans, id, payload_dict)


class FoldersController(BaseGalaxyAPIController):

    service: LibraryFoldersService = depends(LibraryFoldersService)

    @expose_api
    def index(self, trans, **kwd):
        """
        GET /api/folders/

        This would normally display a list of folders. However, that would
        be across multiple libraries, so it's not implemented.
        """
        raise exceptions.NotImplemented('Listing all accessible library folders is not implemented.')

    @expose_api
    def show(self, trans, id, **kwd):
        """
        GET /api/folders/{encoded_folder_id}

        Displays information about a folder.

        :param  id:      the folder's encoded id (required)
        :type   id:      an encoded id string (has to be prefixed by 'F')

        :returns:   dictionary including details of the folder
        :rtype:     dict
        """
        return self.service.show(trans, id)

    @expose_api
    def create(self, trans, encoded_parent_folder_id, payload, **kwd):
        """
        POST /api/folders/{encoded_parent_folder_id}

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
        create_payload = CreateLibraryFolderPayload(**payload)
        return self.service.create(trans, encoded_parent_folder_id, create_payload)

    @expose_api
    def get_permissions(self, trans, encoded_folder_id, **kwd):
        """
        GET /api/folders/{id}/permissions

        Load all permissions for the given folder id and return it.

        :param  encoded_folder_id:     the encoded id of the folder
        :type   encoded_folder_id:     an encoded id string

        :param  scope:      either 'current' or 'available'
        :type   scope:      string

        :returns:   dictionary with all applicable permissions' values
        :rtype:     dictionary

        :raises: InsufficientPermissionsException
        """
        scope = kwd.get('scope')
        page = kwd.get('page')
        if isinstance(page, str):
            page = int(page)
        page_limit = kwd.get('page_limit')
        if isinstance(page_limit, str):
            page_limit = int(page_limit)
        query = kwd.get('q')
        return self.service.get_permissions(trans, encoded_folder_id, scope, page, page_limit, query)

    @expose_api
    def set_permissions(self, trans, encoded_folder_id, payload: dict, **kwd):
        """
        POST /api/folders/{encoded_folder_id}/permissions

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
        if payload:
            payload.update(kwd)
        return self.service.set_permissions(trans, encoded_folder_id, payload)

    @expose_api
    def delete(self, trans, encoded_folder_id, **kwd):
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
        undelete = util.string_as_bool(kwd.get('undelete', False))
        return self.service.delete(trans, encoded_folder_id, undelete)

    @expose_api
    def update(self, trans, encoded_folder_id, payload, **kwd):
        """
        PATCH /api/folders/{encoded_folder_id}

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
        update_payload = UpdateLibraryFolderPayload(**payload)
        return self.service.update(trans, encoded_folder_id, update_payload)
