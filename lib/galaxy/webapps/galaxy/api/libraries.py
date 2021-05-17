"""
API operations on a data library.
"""
import logging
from typing import (
    Any,
    Dict,
    Optional,
    Union,
)

from fastapi import (
    Body,
    Path,
    Query,
)

from galaxy import util
from galaxy.managers.context import ProvidesUserContext
from galaxy.managers.libraries import (
    CreateLibraryPayload,
    DeleteLibraryPayload,
    LegacyLibraryPermissionsPayload,
    LibrariesService,
    LibraryAvailablePermissions,
    LibraryCurrentPermissions,
    LibraryLegacySummary,
    LibraryPermissionScope,
    LibraryPermissionsPayload,
    LibrarySummary,
    LibrarySummaryList,
    UpdateLibraryPayload,
)
from galaxy.schema.fields import EncodedDatabaseIdField
from galaxy.web import (
    expose_api,
    expose_api_anonymous,
)
from . import (
    BaseGalaxyAPIController,
    depends,
    DependsOnTrans,
    Router,
)

log = logging.getLogger(__name__)

router = Router(tags=['libraries'])

DeletedQueryParam: Optional[bool] = Query(
    default=None,
    title="Display deleted",
    description="Whether to include deleted libraries in the result."
)

LibraryIdPathParam: EncodedDatabaseIdField = Path(
    ...,
    title="Library ID",
    description="The encoded identifier of the Library."
)

UndeleteQueryParam: Optional[bool] = Query(
    default=None,
    title="Undelete",
    description="Whether to restore a deleted library."
)


@router.cbv
class FastAPILibraries:
    service: LibrariesService = depends(LibrariesService)

    @router.get(
        '/api/libraries',
        summary="Returns a list of summary data for all libraries.",
    )
    def index(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        deleted: Optional[bool] = DeletedQueryParam,
    ) -> LibrarySummaryList:
        """Returns a list of summary data for all libraries."""
        return self.service.index(trans, deleted)

    @router.get(
        '/api/libraries/deleted',
        summary="Returns a list of summary data for all libraries marked as deleted.",
    )
    def index_deleted(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
    ) -> LibrarySummaryList:
        """Returns a list of summary data for all libraries marked as deleted."""
        return self.service.index(trans, True)

    @router.get(
        '/api/libraries/{id}',
        summary="Returns summary information about a particular library.",
    )
    def show(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        id: EncodedDatabaseIdField = LibraryIdPathParam,
    ) -> LibrarySummary:
        """Returns summary information about a particular library."""
        return self.service.show(trans, id)

    @router.post(
        '/api/libraries',
        summary="Creates a new library and returns its summary information.",
        require_admin=True,
    )
    def create(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        payload: CreateLibraryPayload = Body(...),
    ) -> LibrarySummary:
        """Creates a new library and returns its summary information. Currently, only admin users can create libraries."""
        return self.service.create(trans, payload)

    @router.put(
        '/api/libraries/{id}',
        summary="Updates the information of an existing library.",
        require_admin=True,
    )
    def update(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        id: EncodedDatabaseIdField = LibraryIdPathParam,
        payload: UpdateLibraryPayload = Body(...),
    ) -> LibrarySummary:
        """Updates the information of an existing library.
        Currently, only admin users can update libraries."""
        return self.service.update(trans, id, payload)

    @router.delete(
        '/api/libraries/{id}',
        summary="Marks the specified library as deleted (or undeleted).",
        require_admin=True,
    )
    def delete(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        id: EncodedDatabaseIdField = LibraryIdPathParam,
        undelete: Optional[bool] = UndeleteQueryParam,
        payload: Optional[DeleteLibraryPayload] = Body(default=None),
    ) -> LibrarySummary:
        """Marks the specified library as deleted (or undeleted).
        Currently, only admin users can delete or restore libraries."""
        if payload:
            undelete = payload.undelete
        return self.service.delete(trans, id, undelete)

    @router.get(
        '/api/libraries/{id}/permissions',
        summary="Gets the current or available permissions of a particular library.",
    )
    def get_permissions(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        id: EncodedDatabaseIdField = LibraryIdPathParam,
        scope: Optional[LibraryPermissionScope] = Query(
            None, title="Scope",
            description="The scope of the permissions to retrieve. Either the `current` permissions or the `available`."
        ),
        is_library_access: Optional[bool] = Query(
            None, title="Is Library Access",
            description="Indicates whether the roles available for the library access are requested."
        ),
        page: Optional[int] = Query(
            default=1,
            title="Page",
            description="The page number to retrieve when paginating the permissions."
        ),
        page_limit: Optional[int] = Query(
            default=10,
            title="Page Limit",
            description="The maximum number of permissions per page when paginating."
        ),
        query: Optional[str] = Query(
            None, title="Query",
            description="Optional search query to retrieve the permissions."
        ),
    ) -> Union[LibraryCurrentPermissions, LibraryAvailablePermissions]:
        """Gets the current or available permissions of a particular library.
        The results can be paginated and additionally filtered by a query."""
        return self.service.get_permissions(
            trans,
            id,
            scope,
            is_library_access,
            page,
            page_limit,
            query,
        )

    @router.post(
        '/api/libraries/{id}/permissions',
        summary="Sets the permissions to access and manipulate a library.",
    )
    def set_permissions(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        id: EncodedDatabaseIdField = LibraryIdPathParam,
        payload: Union[
            LibraryPermissionsPayload,
            LegacyLibraryPermissionsPayload,
        ] = Body(...),
    ) -> Union[
        LibraryLegacySummary,  # Old legacy response
        LibraryCurrentPermissions,
    ]:
        """Sets the permissions to access and manipulate a library."""
        return self.service.set_permissions(trans, id, payload.dict(by_alias=True))


class LibrariesController(BaseGalaxyAPIController):
    service: LibrariesService = depends(LibrariesService)

    @expose_api_anonymous
    def index(self, trans: ProvidesUserContext, **kwd):
        """
        index( self, trans, **kwd )
        * GET /api/libraries:
            Returns a list of summary data for all libraries.

        :param  deleted: if True, show only ``deleted`` libraries, if False show only ``non-deleted``
        :type   deleted: boolean (optional)

        :returns:   list of dictionaries containing library information
        :rtype:     list

        .. seealso:: :attr:`galaxy.model.Library.dict_collection_visible_keys`

        """
        deleted = util.string_as_bool_or_none(kwd.get('deleted', None))
        return self.service.index(trans, deleted)

    @expose_api_anonymous
    def show(self, trans: ProvidesUserContext, id: EncodedDatabaseIdField, **kwd):
        """
        show( self, trans, id, deleted='False', **kwd )
        * GET /api/libraries/{encoded_id}:
            returns detailed information about a library
        * GET /api/libraries/deleted/{encoded_id}:
            returns detailed information about a ``deleted`` library

        :param  id:      the encoded id of the library
        :type   id:      an encoded id string

        :returns:   detailed library information
        :rtype:     dictionary

        .. seealso:: :attr:`galaxy.model.Library.dict_element_visible_keys`

        :raises: MalformedId, ObjectNotFound
        """
        return self.service.show(trans, id)

    @expose_api
    def create(self, trans: ProvidesUserContext, payload: Dict[str, str], **kwd):
        """
        * POST /api/libraries:
            Creates a new library.

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
        create_payload = CreateLibraryPayload(**payload)
        return self.service.create(trans, create_payload)

    @expose_api
    def update(self, trans: ProvidesUserContext, id: EncodedDatabaseIdField, payload: Dict[str, str], **kwd):
        """
        * PATCH /api/libraries/{encoded_id}
           Updates the library defined by an ``encoded_id`` with the data in the payload.

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
        update_payload = UpdateLibraryPayload(**payload)
        return self.service.update(trans, id, update_payload)

    @expose_api
    def delete(self, trans: ProvidesUserContext, id: EncodedDatabaseIdField, payload: Dict[str, Any] = None, **kwd):
        """
        * DELETE /api/libraries/{id}
            marks the library with the given ``id`` as `deleted` (or removes the `deleted` mark if the `undelete` param is true)

        .. note:: Currently, only admin users can un/delete libraries.

        :param  id:     the encoded id of the library to un/delete
        :type   id:     an encoded id string

        :param   payload: dictionary structure containing:
            :param  undelete:    (optional) flag specifying whether the item should be deleted or undeleted, defaults to false:
            :type   undelete:    bool
        :type:     dictionary
        :returns:   detailed library information
        :rtype:     dictionary

        .. seealso:: :attr:`galaxy.model.Library.dict_element_visible_keys`
        """
        if payload:
            kwd.update(payload)
        undelete = util.string_as_bool(kwd.get('undelete', False))
        return self.service.delete(trans, id, undelete)

    @expose_api
    def get_permissions(self, trans: ProvidesUserContext, encoded_library_id: EncodedDatabaseIdField, **kwd):
        """
        * GET /api/libraries/{encoded_library_id}/permissions

        Load all permissions for the given library id and return it.

        :param  encoded_library_id:     the encoded id of the library
        :type   encoded_library_id:     an encoded id string

        :param  scope:      either 'current' or 'available'
        :type   scope:      string

        :param  is_library_access:      indicates whether the roles available for the library access are requested
        :type   is_library_access:      bool

        :returns:   dictionary with all applicable permissions' values
        :rtype:     dictionary

        :raises: InsufficientPermissionsException
        """
        scope = kwd.get('scope', None)
        is_library_access = util.string_as_bool(kwd.get('is_library_access', False))
        page = kwd.get('page', None)
        if page is not None:
            page = int(page)
        else:
            page = 1

        page_limit = kwd.get('page_limit', None)
        if page_limit is not None:
            page_limit = int(page_limit)
        else:
            page_limit = 10

        query = kwd.get('q', None)

        return self.service.get_permissions(trans, encoded_library_id, scope, is_library_access, page, page_limit, query)

    @expose_api
    def set_permissions(self, trans: ProvidesUserContext, encoded_library_id: EncodedDatabaseIdField, payload: Dict[str, Any], **kwd):
        """
        POST /api/libraries/{encoded_library_id}/permissions

        Set permissions of the given library to the given role ids.

        :param  encoded_library_id:      the encoded id of the library to set the permissions of
        :type   encoded_library_id:      an encoded id string
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
        return self.service.set_permissions(trans, encoded_library_id, payload)
