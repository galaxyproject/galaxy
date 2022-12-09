"""
API operations on a history.

.. seealso:: :class:`galaxy.model.History`
"""
import logging
from typing import (
    Any,
    List,
    Optional,
    Union,
)

from fastapi import (
    Body,
    Depends,
    Header,
    Path,
    Query,
    Response,
    status,
)
from pydantic.fields import Field
from pydantic.main import BaseModel

from galaxy.managers.context import (
    ProvidesHistoryContext,
    ProvidesUserContext,
)
from galaxy.schema import (
    FilterQueryParams,
    SerializationParams,
)
from galaxy.schema.fields import DecodedDatabaseIdField
from galaxy.schema.schema import (
    AnyHistoryView,
    AsyncFile,
    AsyncTaskResultSummary,
    CreateHistoryFromStore,
    CreateHistoryPayload,
    CustomBuildsMetadataResponse,
    ExportHistoryArchivePayload,
    ExportTaskListResponse,
    HistoryArchiveExportResult,
    JobExportHistoryArchiveListResponse,
    JobImportHistoryResponse,
    SetSlugPayload,
    ShareWithPayload,
    ShareWithStatus,
    SharingStatus,
    StoreExportPayload,
    WriteStoreToPayload,
)
from galaxy.schema.types import LatestLiteral
from galaxy.webapps.base.api import GalaxyFileResponse
from galaxy.webapps.galaxy.api import (
    as_form,
    depends,
    DependsOnTrans,
    Router,
    try_get_request_body_as_json,
)
from galaxy.webapps.galaxy.api.common import (
    get_filter_query_params,
    LimitQueryParam,
    OffsetQueryParam,
    query_serialization_params,
)
from galaxy.webapps.galaxy.services.histories import HistoriesService

log = logging.getLogger(__name__)

router = Router(tags=["histories"])

HistoryIDPathParam: DecodedDatabaseIdField = Path(
    ..., title="History ID", description="The encoded database identifier of the History."
)

JehaIDPathParam: Union[DecodedDatabaseIdField, LatestLiteral] = Path(
    default="latest",
    title="Job Export History ID",
    description=(
        "The ID of the specific Job Export History Association or "
        "`latest` (default) to download the last generated archive."
    ),
    example="latest",
)

AllHistoriesQueryParam = Query(
    default=False,
    title="All Histories",
    description=(
        "Whether all histories from other users in this Galaxy should be included. "
        "Only admins are allowed to query all histories."
    ),
)


class DeleteHistoryPayload(BaseModel):
    purge: bool = Field(
        default=False, title="Purge", description="Whether to definitely remove this history from disk."
    )


@as_form
class CreateHistoryFormData(CreateHistoryPayload):
    """Uses Form data instead of JSON"""


@router.cbv
class FastAPIHistories:
    service: HistoriesService = depends(HistoriesService)

    @router.get(
        "/api/histories",
        summary="Returns histories for the current user.",
    )
    def index(
        self,
        trans: ProvidesHistoryContext = DependsOnTrans,
        filter_query_params: FilterQueryParams = Depends(get_filter_query_params),
        serialization_params: SerializationParams = Depends(query_serialization_params),
        all: Optional[bool] = AllHistoriesQueryParam,
        deleted: Optional[bool] = Query(  # This is for backward compatibility but looks redundant
            default=False,
            title="Deleted Only",
            description="Whether to return only deleted items.",
            deprecated=True,  # Marked as deprecated as it seems just like '/api/histories/deleted'
        ),
    ) -> List[AnyHistoryView]:
        return self.service.index(
            trans, serialization_params, filter_query_params, deleted_only=deleted, all_histories=all
        )

    @router.get(
        "/api/histories/deleted",
        summary="Returns deleted histories for the current user.",
    )
    def index_deleted(
        self,
        trans: ProvidesHistoryContext = DependsOnTrans,
        filter_query_params: FilterQueryParams = Depends(get_filter_query_params),
        serialization_params: SerializationParams = Depends(query_serialization_params),
        all: Optional[bool] = AllHistoriesQueryParam,
    ) -> List[AnyHistoryView]:
        return self.service.index(
            trans, serialization_params, filter_query_params, deleted_only=True, all_histories=all
        )

    @router.get(
        "/api/histories/published",
        summary="Return all histories that are published.",
    )
    def published(
        self,
        trans: ProvidesHistoryContext = DependsOnTrans,
        filter_query_params: FilterQueryParams = Depends(get_filter_query_params),
        serialization_params: SerializationParams = Depends(query_serialization_params),
    ) -> List[AnyHistoryView]:
        return self.service.published(trans, serialization_params, filter_query_params)

    @router.get(
        "/api/histories/shared_with_me",
        summary="Return all histories that are shared with the current user.",
    )
    def shared_with_me(
        self,
        trans: ProvidesHistoryContext = DependsOnTrans,
        filter_query_params: FilterQueryParams = Depends(get_filter_query_params),
        serialization_params: SerializationParams = Depends(query_serialization_params),
    ) -> List[AnyHistoryView]:
        return self.service.shared_with_me(trans, serialization_params, filter_query_params)

    @router.get(
        "/api/histories/most_recently_used",
        summary="Returns the most recently used history of the user.",
    )
    def show_recent(
        self,
        trans: ProvidesHistoryContext = DependsOnTrans,
        serialization_params: SerializationParams = Depends(query_serialization_params),
    ) -> AnyHistoryView:
        return self.service.show(trans, serialization_params)

    @router.get(
        "/api/histories/{history_id}",
        name="history",
        summary="Returns the history with the given ID.",
    )
    def show(
        self,
        trans: ProvidesHistoryContext = DependsOnTrans,
        history_id: DecodedDatabaseIdField = HistoryIDPathParam,
        serialization_params: SerializationParams = Depends(query_serialization_params),
    ) -> AnyHistoryView:
        return self.service.show(trans, serialization_params, history_id)

    @router.post(
        "/api/histories/{history_id}/prepare_store_download",
        summary="Return a short term storage token to monitor download of the history.",
    )
    def prepare_store_download(
        self,
        trans: ProvidesHistoryContext = DependsOnTrans,
        history_id: DecodedDatabaseIdField = HistoryIDPathParam,
        payload: StoreExportPayload = Body(...),
    ) -> AsyncFile:
        return self.service.prepare_download(
            trans,
            history_id,
            payload=payload,
        )

    @router.post(
        "/api/histories/{history_id}/write_store",
        summary="Prepare history for export-style download and write to supplied URI.",
    )
    def write_store(
        self,
        trans: ProvidesHistoryContext = DependsOnTrans,
        history_id: DecodedDatabaseIdField = HistoryIDPathParam,
        payload: WriteStoreToPayload = Body(...),
    ) -> AsyncTaskResultSummary:
        return self.service.write_store(
            trans,
            history_id,
            payload=payload,
        )

    @router.get(
        "/api/histories/{history_id}/citations",
        summary="Return all the citations for the tools used to produce the datasets in the history.",
    )
    def citations(
        self,
        trans: ProvidesHistoryContext = DependsOnTrans,
        history_id: DecodedDatabaseIdField = HistoryIDPathParam,
    ) -> List[Any]:
        return self.service.citations(trans, history_id)

    @router.post(
        "/api/histories",
        summary="Creates a new history.",
    )
    def create(
        self,
        trans: ProvidesHistoryContext = DependsOnTrans,
        payload: CreateHistoryPayload = Depends(CreateHistoryFormData.as_form),  # type: ignore[attr-defined]
        payload_as_json: Optional[Any] = Depends(try_get_request_body_as_json),
        serialization_params: SerializationParams = Depends(query_serialization_params),
    ) -> Union[JobImportHistoryResponse, AnyHistoryView]:
        """The new history can also be copied form a existing history or imported from an archive or URL."""
        # This action needs to work both with json and x-www-form-urlencoded payloads.
        # The way to support different content types on the same path operation is reading
        # the request directly and parse it depending on the content type.
        # We will assume x-www-form-urlencoded (payload) by default to deal with possible file uploads
        # and if the content type is explicitly JSON, we will use payload_as_json instead.
        # See https://github.com/tiangolo/fastapi/issues/990#issuecomment-639615888
        if payload_as_json:
            payload = CreateHistoryPayload.parse_obj(payload_as_json)
        return self.service.create(trans, payload, serialization_params)

    @router.delete(
        "/api/histories/{history_id}",
        summary="Marks the history with the given ID as deleted.",
    )
    def delete(
        self,
        trans: ProvidesHistoryContext = DependsOnTrans,
        history_id: DecodedDatabaseIdField = HistoryIDPathParam,
        serialization_params: SerializationParams = Depends(query_serialization_params),
        purge: bool = Query(default=False),
        payload: Optional[DeleteHistoryPayload] = Body(default=None),
    ) -> AnyHistoryView:
        if payload:
            purge = payload.purge
        return self.service.delete(trans, history_id, serialization_params, purge)

    @router.post(
        "/api/histories/deleted/{history_id}/undelete",
        summary="Restores a deleted history with the given ID (that hasn't been purged).",
    )
    def undelete(
        self,
        trans: ProvidesHistoryContext = DependsOnTrans,
        history_id: DecodedDatabaseIdField = HistoryIDPathParam,
        serialization_params: SerializationParams = Depends(query_serialization_params),
    ) -> AnyHistoryView:
        return self.service.undelete(trans, history_id, serialization_params)

    @router.put(
        "/api/histories/{history_id}",
        summary="Updates the values for the history with the given ID.",
    )
    def update(
        self,
        trans: ProvidesHistoryContext = DependsOnTrans,
        history_id: DecodedDatabaseIdField = HistoryIDPathParam,
        payload: Any = Body(
            ...,
            description="Object containing any of the editable fields of the history.",
        ),
        serialization_params: SerializationParams = Depends(query_serialization_params),
    ) -> AnyHistoryView:
        return self.service.update(trans, history_id, payload, serialization_params)

    @router.post(
        "/api/histories/from_store",
        summary="Create histories from a model store.",
    )
    def create_from_store(
        self,
        trans: ProvidesHistoryContext = DependsOnTrans,
        serialization_params: SerializationParams = Depends(query_serialization_params),
        payload: CreateHistoryFromStore = Body(...),
    ) -> AnyHistoryView:
        return self.service.create_from_store(trans, payload, serialization_params)

    @router.post(
        "/api/histories/from_store_async",
        summary="Launch a task to create histories from a model store.",
    )
    def create_from_store_async(
        self,
        trans: ProvidesHistoryContext = DependsOnTrans,
        payload: CreateHistoryFromStore = Body(...),
    ) -> AsyncTaskResultSummary:
        return self.service.create_from_store_async(trans, payload)

    @router.get(
        "/api/histories/{history_id}/exports",
        name="get_history_exports",
        summary=("Get previous history exports."),
        responses={
            200: {
                "description": "A list of history exports",
                "content": {
                    "application/json": {
                        "schema": {"ref": "#/components/schemas/JobExportHistoryArchiveListResponse"},
                    },
                    ExportTaskListResponse.__accept_type__: {
                        "schema": {"ref": "#/components/schemas/ExportTaskListResponse"},
                    },
                },
            },
        },
    )
    def index_exports(
        self,
        trans: ProvidesHistoryContext = DependsOnTrans,
        history_id: DecodedDatabaseIdField = HistoryIDPathParam,
        limit: Optional[int] = LimitQueryParam,
        offset: Optional[int] = OffsetQueryParam,
        accept: str = Header(default="application/json", include_in_schema=False),
    ) -> Union[JobExportHistoryArchiveListResponse, ExportTaskListResponse]:
        """
        By default the legacy job-based history exports (jeha) are returned.

        Change the `accept` content type header to return the new task-based history exports.
        """
        use_tasks = accept == ExportTaskListResponse.__accept_type__
        exports = self.service.index_exports(trans, history_id, use_tasks, limit, offset)
        if use_tasks:
            return ExportTaskListResponse(__root__=exports)
        return JobExportHistoryArchiveListResponse(__root__=exports)

    @router.put(  # PUT instead of POST because multiple requests should just result in one object being created.
        "/api/histories/{history_id}/exports",
        summary=("Start job (if needed) to create history export for corresponding history."),
        responses={
            200: {
                "description": "Object containing url to fetch export from.",
            },
            202: {
                "description": "The exported archive file is not ready yet.",
            },
        },
        deprecated=True,
    )
    def archive_export(
        self,
        response: Response,
        trans=DependsOnTrans,
        history_id: DecodedDatabaseIdField = HistoryIDPathParam,
        payload: Optional[ExportHistoryArchivePayload] = Body(None),
    ) -> HistoryArchiveExportResult:
        """This will start a job to create a history export archive.

        Calling this endpoint multiple times will return the 202 status code until the archive
        has been completely generated and is ready to download. When ready, it will return
        the 200 status code along with the download link information.

        If the history will be exported to a `directory_uri`, instead of returning the download
        link information, the Job ID will be returned so it can be queried to determine when
        the file has been written.

        **Deprecation notice**: Please use `/api/histories/{id}/prepare_store_download` or
        `/api/histories/{id}/write_store` instead.
        """
        export_result, ready = self.service.archive_export(trans, history_id, payload)
        if not ready:
            response.status_code = status.HTTP_202_ACCEPTED
        return export_result

    @router.get(
        "/api/histories/{history_id}/exports/{jeha_id}",
        name="history_archive_download",
        summary=("If ready and available, return raw contents of exported history as a downloadable archive."),
        response_class=GalaxyFileResponse,
        responses={
            200: {
                "description": "The archive file containing the History.",
            }
        },
        deprecated=True,
    )
    def archive_download(
        self,
        trans: ProvidesHistoryContext = DependsOnTrans,
        history_id: DecodedDatabaseIdField = HistoryIDPathParam,
        jeha_id: Union[DecodedDatabaseIdField, LatestLiteral] = JehaIDPathParam,
    ):
        """
        See ``PUT /api/histories/{id}/exports`` to initiate the creation
        of the history export - when ready, that route will return 200 status
        code (instead of 202) and this route can be used to download the archive.

        **Deprecation notice**: Please use `/api/histories/{id}/prepare_store_download` or
        `/api/histories/{id}/write_store` instead.
        """
        jeha = self.service.get_ready_history_export(trans, history_id, jeha_id)
        media_type = self.service.get_archive_media_type(jeha)
        file_path = self.service.get_archive_download_path(trans, jeha)
        return GalaxyFileResponse(
            path=file_path,
            media_type=media_type,
            filename=jeha.export_name,
        )

    @router.get(
        "/api/histories/{history_id}/custom_builds_metadata",
        summary="Returns meta data for custom builds.",
    )
    def get_custom_builds_metadata(
        self,
        trans: ProvidesHistoryContext = DependsOnTrans,
        history_id: DecodedDatabaseIdField = HistoryIDPathParam,
    ) -> CustomBuildsMetadataResponse:
        return self.service.get_custom_builds_metadata(trans, history_id)

    @router.get(
        "/api/histories/{history_id}/sharing",
        summary="Get the current sharing status of the given item.",
    )
    def sharing(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        history_id: DecodedDatabaseIdField = HistoryIDPathParam,
    ) -> SharingStatus:
        """Return the sharing status of the item."""
        return self.service.shareable_service.sharing(trans, history_id)

    @router.put(
        "/api/histories/{history_id}/enable_link_access",
        summary="Makes this item accessible by a URL link.",
    )
    def enable_link_access(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        history_id: DecodedDatabaseIdField = HistoryIDPathParam,
    ) -> SharingStatus:
        """Makes this item accessible by a URL link and return the current sharing status."""
        return self.service.shareable_service.enable_link_access(trans, history_id)

    @router.put(
        "/api/histories/{history_id}/disable_link_access",
        summary="Makes this item inaccessible by a URL link.",
    )
    def disable_link_access(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        history_id: DecodedDatabaseIdField = HistoryIDPathParam,
    ) -> SharingStatus:
        """Makes this item inaccessible by a URL link and return the current sharing status."""
        return self.service.shareable_service.disable_link_access(trans, history_id)

    @router.put(
        "/api/histories/{history_id}/publish",
        summary="Makes this item public and accessible by a URL link.",
    )
    def publish(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        history_id: DecodedDatabaseIdField = HistoryIDPathParam,
    ) -> SharingStatus:
        """Makes this item publicly available by a URL link and return the current sharing status."""
        return self.service.shareable_service.publish(trans, history_id)

    @router.put(
        "/api/histories/{history_id}/unpublish",
        summary="Removes this item from the published list.",
    )
    def unpublish(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        history_id: DecodedDatabaseIdField = HistoryIDPathParam,
    ) -> SharingStatus:
        """Removes this item from the published list and return the current sharing status."""
        return self.service.shareable_service.unpublish(trans, history_id)

    @router.put(
        "/api/histories/{history_id}/share_with_users",
        summary="Share this item with specific users.",
    )
    def share_with_users(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        history_id: DecodedDatabaseIdField = HistoryIDPathParam,
        payload: ShareWithPayload = Body(...),
    ) -> ShareWithStatus:
        """Shares this item with specific users and return the current sharing status."""
        return self.service.shareable_service.share_with_users(trans, history_id, payload)

    @router.put(
        "/api/histories/{history_id}/slug",
        summary="Set a new slug for this shared item.",
        status_code=status.HTTP_204_NO_CONTENT,
    )
    def set_slug(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        history_id: DecodedDatabaseIdField = HistoryIDPathParam,
        payload: SetSlugPayload = Body(...),
    ):
        """Sets a new slug to access this item by URL. The new slug must be unique."""
        self.service.shareable_service.set_slug(trans, history_id, payload)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
