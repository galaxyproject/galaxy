"""
API operations on the contents of a data library.
"""

import logging
from typing import (
    cast,
    List,
    Optional,
)

from fastapi import (
    Body,
    Depends,
    Request,
    UploadFile,
)
from starlette.datastructures import UploadFile as StarletteUploadFile

from galaxy.managers.context import (
    ProvidesHistoryContext,
    ProvidesUserContext,
)
from galaxy.schema.fields import DecodedDatabaseIdField
from galaxy.schema.library_contents import (
    AnyLibraryContentsCreatePayload,
    AnyLibraryContentsCreateResponse,
    AnyLibraryContentsShowResponse,
    LibraryContentsDeletePayload,
    LibraryContentsDeleteResponse,
    LibraryContentsFileCreatePayload,
    LibraryContentsIndexListResponse,
)
from galaxy.webapps.galaxy.api import (
    depends,
    DependsOnTrans,
    Router,
)
from galaxy.webapps.galaxy.services.library_contents import (
    LibraryContentsService,
    MaybeLibraryFolderOrDatasetID,
)
from . import (
    APIContentTypeRoute,
    as_form,
)

log = logging.getLogger(__name__)

router = Router(tags=["libraries"])


class FormDataApiRoute(APIContentTypeRoute):
    match_content_type = "multipart/form-data"


class JsonApiRoute(APIContentTypeRoute):
    match_content_type = "application/json"


LibraryContentsCreateForm = as_form(LibraryContentsFileCreatePayload)


async def get_files(request: Request, files: Optional[List[UploadFile]] = None):
    # FastAPI's UploadFile is a very light wrapper around starlette's UploadFile
    files2: List[StarletteUploadFile] = cast(List[StarletteUploadFile], files or [])
    if not files2:
        data = await request.form()
        for value in data.values():
            if isinstance(value, StarletteUploadFile):
                files2.append(value)
    return files2


@router.cbv
class FastAPILibraryContents:
    service: LibraryContentsService = depends(LibraryContentsService)

    @router.get(
        "/api/libraries/{library_id}/contents",
        summary="Return a list of library files and folders.",
        deprecated=True,
    )
    def index(
        self,
        library_id: DecodedDatabaseIdField,
        trans: ProvidesUserContext = DependsOnTrans,
    ) -> LibraryContentsIndexListResponse:
        """This endpoint is deprecated. Please use GET /api/folders/{folder_id}/contents instead."""
        return self.service.index(trans, library_id)

    @router.get(
        "/api/libraries/{library_id}/contents/{id}",
        name="library_content",
        summary="Return a library file or folder.",
        deprecated=True,
    )
    def show(
        self,
        library_id: DecodedDatabaseIdField,
        id: MaybeLibraryFolderOrDatasetID,
        trans: ProvidesUserContext = DependsOnTrans,
    ) -> AnyLibraryContentsShowResponse:
        """This endpoint is deprecated. Please use GET /api/libraries/datasets/{library_id} instead."""
        return self.service.show(trans, id)

    @router.post(
        "/api/libraries/{library_id}/contents",
        summary="Create a new library file or folder.",
        deprecated=True,
        route_class_override=JsonApiRoute,
    )
    def create_json(
        self,
        library_id: DecodedDatabaseIdField,
        payload: AnyLibraryContentsCreatePayload,
        trans: ProvidesHistoryContext = DependsOnTrans,
    ) -> AnyLibraryContentsCreateResponse:
        """This endpoint is deprecated. Please use POST /api/folders/{folder_id} or POST /api/folders/{folder_id}/contents instead."""
        return self.service.create(trans, library_id, payload)

    @router.post(
        "/api/libraries/{library_id}/contents",
        summary="Create a new library file or folder.",
        deprecated=True,
        route_class_override=FormDataApiRoute,
    )
    def create_form(
        self,
        library_id: DecodedDatabaseIdField,
        payload: LibraryContentsFileCreatePayload = Depends(LibraryContentsCreateForm.as_form),
        files: List[StarletteUploadFile] = Depends(get_files),
        trans: ProvidesHistoryContext = DependsOnTrans,
    ) -> AnyLibraryContentsCreateResponse:
        """This endpoint is deprecated. Please use POST /api/folders/{folder_id} or POST /api/folders/{folder_id}/contents instead."""
        return self.service.create(trans, library_id, payload, files)

    @router.put(
        "/api/libraries/{library_id}/contents/{id}",
        summary="Update a library file or folder.",
        deprecated=True,
    )
    def update(
        self,
        library_id: DecodedDatabaseIdField,
        id: DecodedDatabaseIdField,
        payload,
        trans: ProvidesUserContext = DependsOnTrans,
    ) -> None:
        """This endpoint is deprecated. Please use PATCH /api/libraries/datasets/{library_id} instead."""
        return self.service.update(trans, id, payload)

    @router.delete(
        "/api/libraries/{library_id}/contents/{id}",
        summary="Delete a library file or folder.",
        deprecated=True,
    )
    def delete(
        self,
        library_id: DecodedDatabaseIdField,
        id: DecodedDatabaseIdField,
        payload: Optional[LibraryContentsDeletePayload] = Body(None),
        trans: ProvidesHistoryContext = DependsOnTrans,
    ) -> LibraryContentsDeleteResponse:
        """This endpoint is deprecated. Please use DELETE /api/libraries/datasets/{library_id} instead."""
        return self.service.delete(trans, id, payload or LibraryContentsDeletePayload())
