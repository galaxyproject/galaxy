"""
API operations on the contents of a library folder.
"""
import logging
from typing import Optional

from fastapi import (
    Body,
    Path,
    Query,
)

from galaxy.managers.context import ProvidesUserContext
from galaxy.schema.fields import LibraryFolderDatabaseIdField
from galaxy.schema.schema import (
    CreateLibraryFilePayload,
    LibraryFolderContentsIndexQueryPayload,
    LibraryFolderContentsIndexResult,
    LibraryFolderContentsIndexSortByEnum,
)
from galaxy.webapps.galaxy.api import (
    depends,
    DependsOnTrans,
    Router,
)
from galaxy.webapps.galaxy.services.library_folder_contents import LibraryFolderContentsService

log = logging.getLogger(__name__)

router = Router(tags=["data libraries folders"])

FolderIdPathParam: LibraryFolderDatabaseIdField = Path(
    ..., title="Folder ID", description="The encoded identifier of the library folder."
)

LimitQueryParam: int = Query(default=10, title="Limit", description="Maximum number of contents to return.")

OffsetQueryParam: int = Query(
    default=0,
    title="Offset",
    description="Return contents from this specified position. For example, if ``limit`` is set to 100 and ``offset`` to 200, contents between position 200-299 will be returned.",
)

SearchQueryParam: Optional[str] = Query(
    default=None,
    title="Search Text",
    description="Used to filter the contents. Only the folders and files which name contains this text will be returned.",
)

IncludeDeletedQueryParam: Optional[bool] = Query(
    default=False,
    title="Include Deleted",
    description="Returns also deleted contents. Deleted contents can only be retrieved by Administrators or users with",
)

SortByQueryParam: LibraryFolderContentsIndexSortByEnum = Query(
    default="name",
    title="Sort By",
    description="Sort results by specified field.",
)

SortDescQueryParam: Optional[bool] = Query(
    default=False,
    title="Sort Descending",
    description="Sort results in descending order.",
)


@router.cbv
class FastAPILibraryFoldersContents:
    service: LibraryFolderContentsService = depends(LibraryFolderContentsService)

    @router.get(
        "/api/folders/{folder_id}/contents",
        summary="Returns a list of a folder's contents (files and sub-folders) with additional metadata about the folder.",
        responses={
            200: {
                "description": "The contents of the folder that match the query parameters.",
                "model": LibraryFolderContentsIndexResult,
            },
        },
    )
    def index(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        folder_id: LibraryFolderDatabaseIdField = FolderIdPathParam,
        limit: int = LimitQueryParam,
        offset: int = OffsetQueryParam,
        search_text: Optional[str] = SearchQueryParam,
        include_deleted: Optional[bool] = IncludeDeletedQueryParam,
        order_by: LibraryFolderContentsIndexSortByEnum = SortByQueryParam,
        sort_desc: Optional[bool] = SortDescQueryParam,
    ):
        """Returns a list of a folder's contents (files and sub-folders).

        Additional metadata for the folder is provided in the response as a separate object containing data
        for breadcrumb path building, permissions and other folder's details.

        *Note*: When sorting, folders always have priority (they show-up before any dataset regardless of the sorting).

        **Security note**:
        - Accessing a library folder or sub-folder requires only access to the parent library.
        - Deleted folders can only be accessed by admins or users with `MODIFY` permission.
        - Datasets may be public, private or restricted (to a group of users). Listing deleted datasets has the same requirements as folders.
        """
        payload = LibraryFolderContentsIndexQueryPayload(
            limit=limit,
            offset=offset,
            search_text=search_text,
            include_deleted=include_deleted,
            order_by=order_by,
            sort_desc=sort_desc,
        )
        return self.service.index(trans, folder_id, payload)

    @router.post(
        "/api/folders/{folder_id}/contents",
        name="add_history_datasets_to_library",
        summary="Creates a new library file from an existing HDA/HDCA.",
    )
    def create(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        folder_id: LibraryFolderDatabaseIdField = FolderIdPathParam,
        payload: CreateLibraryFilePayload = Body(...),
    ):
        return self.service.create(trans, folder_id, payload)
