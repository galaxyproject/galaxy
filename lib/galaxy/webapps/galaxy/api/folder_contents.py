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
from galaxy.schema.fields import DecodedDatabaseIdField
from galaxy.schema.schema import (
    CreateLibraryFilePayload,
    LibraryFolderContentsIndexQueryPayload,
    LibraryFolderContentsIndexResult,
)
from galaxy.webapps.galaxy.services.library_folder_contents import LibraryFolderContentsService
from . import (
    depends,
    DependsOnTrans,
    Router,
)

log = logging.getLogger(__name__)

router = Router(tags=["data libraries folders"])

FolderIdPathParam: DecodedDatabaseIdField = Path(
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
        folder_id: DecodedDatabaseIdField = FolderIdPathParam,
        limit: int = LimitQueryParam,
        offset: int = OffsetQueryParam,
        search_text: Optional[str] = SearchQueryParam,
        include_deleted: Optional[bool] = IncludeDeletedQueryParam,
    ):
        """Returns a list of a folder's contents (files and sub-folders).

        Additional metadata for the folder is provided in the response as a separate object containing data
        for breadcrumb path building, permissions and other folder's details.
        """
        payload = LibraryFolderContentsIndexQueryPayload(
            limit=limit, offset=offset, search_text=search_text, include_deleted=include_deleted
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
        folder_id: DecodedDatabaseIdField = FolderIdPathParam,
        payload: CreateLibraryFilePayload = Body(...),
    ):
        return self.service.create(trans, folder_id, payload)
