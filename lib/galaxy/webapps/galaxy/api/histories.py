"""
API operations on a history.

.. seealso:: :class:`galaxy.model.History`
"""

import logging
from typing import (
    Any,
    List,
    Literal,
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
from typing_extensions import Annotated

from galaxy.managers.context import (
    ProvidesHistoryContext,
    ProvidesUserContext,
)
from galaxy.schema import (
    FilterQueryParams,
    SerializationParams,
)
from galaxy.schema.fields import (
    AcceptHeaderValidator,
    DecodedDatabaseIdField,
)
from galaxy.schema.history import (
    HistoryIndexQueryPayload,
    HistorySortByEnum,
)
from galaxy.schema.schema import (
    AnyArchivedHistoryView,
    AnyHistoryView,
    ArchiveHistoryRequestPayload,
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
    ShareHistoryWithStatus,
    ShareWithPayload,
    SharingStatus,
    StoreExportPayload,
    ToolRequestModel,
    UpdateHistoryPayload,
    WriteStoreToPayload,
)
from galaxy.schema.types import LatestLiteral
from galaxy.webapps.base.api import GalaxyFileResponse
from galaxy.webapps.galaxy.api import (
    as_form,
    depends,
    DependsOnTrans,
    IndexQueryTag,
    Router,
    search_query_param,
    try_get_request_body_as_json,
)
from galaxy.webapps.galaxy.api.common import (
    get_filter_query_params,
    LimitQueryParam,
    OffsetQueryParam,
    query_serialization_params,
)
from galaxy.webapps.galaxy.services.histories import HistoriesService
from .common import HistoryIDPathParam

log = logging.getLogger(__name__)

router = Router(tags=["histories"])

query_tags = [
    IndexQueryTag("name", "The history's name."),
    IndexQueryTag("annotation", "The history's annotation.", "a"),
    IndexQueryTag("tag", "The history's tags.", "t"),
]

AllHistoriesQueryParam = Query(
    default=False,
    title="All Histories",
    description=(
        "Whether all histories from other users in this Galaxy should be included. "
        "Only admins are allowed to query all histories."
    ),
)

JehaIDPathParam: Union[DecodedDatabaseIdField, LatestLiteral] = Path(
    title="Job Export History ID",
    description=(
        "The ID of the specific Job Export History Association or "
        "`latest` (default) to download the last generated archive."
    ),
    examples=["latest"],
)

SearchQueryParam: Optional[str] = search_query_param(
    model_name="History",
    tags=query_tags,
    free_text_fields=["title", "description", "slug", "tag"],
)

ShowOwnQueryParam: bool = Query(default=True, title="Show histories owned by user.", description="")

ShowPublishedQueryParam: bool = Query(default=True, title="Include published histories.", description="")

ShowSharedQueryParam: bool = Query(
    default=False, title="Include histories shared with authenticated user.", description=""
)

ShowArchivedQueryParam: Optional[bool] = Query(
    default=None,
    title="Show Archived",
    description="Whether to include archived histories.",
)

SortByQueryParam: HistorySortByEnum = Query(
    default="update_time",
    title="Sort attribute",
    description="Sort index by this specified attribute",
)

SortDescQueryParam: bool = Query(
    default=True,
    title="Sort Descending",
    description="Sort in descending order?",
)


class DeleteHistoryPayload(BaseModel):
    purge: bool = Field(
        default=False, title="Purge", description="Whether to definitely remove this history from disk."
    )


class DeleteHistoriesPayload(BaseModel):
    ids: Annotated[List[DecodedDatabaseIdField], Field(title="IDs", description="List of history IDs to be deleted.")]
    purge: Annotated[
        bool, Field(default=False, title="Purge", description="Whether to definitely remove this history from disk.")
    ]


class UndeleteHistoriesPayload(BaseModel):
    ids: Annotated[List[DecodedDatabaseIdField], Field(title="IDs", description="List of history IDs to be undeleted.")]


@as_form
class CreateHistoryFormData(CreateHistoryPayload):
    """Uses Form data instead of JSON"""


IndexExportsAcceptHeader = Annotated[
    Literal[
        "application/json",
        "application/vnd.galaxy.task.export+json",
    ],
    AcceptHeaderValidator,
    Header(description="Accept header to determine the response format. Default is 'application/json'."),
]


@router.cbv
class FastAPIHistories:
    service: HistoriesService = depends(HistoriesService)

    @router.get(
        "/api/histories",
        summary="Returns histories available to the current user.",
        response_model_exclude_unset=True,
    )
    def index(
        self,
        response: Response,
        trans: ProvidesHistoryContext = DependsOnTrans,
        limit: Optional[int] = LimitQueryParam,
        offset: Optional[int] = OffsetQueryParam,
        show_own: bool = ShowOwnQueryParam,
        show_published: bool = ShowPublishedQueryParam,
        show_shared: bool = ShowSharedQueryParam,
        show_archived: Optional[bool] = ShowArchivedQueryParam,
        sort_by: HistorySortByEnum = SortByQueryParam,
        sort_desc: bool = SortDescQueryParam,
        search: Optional[str] = SearchQueryParam,
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
        if search is None:
            return self.service.index(
                trans, serialization_params, filter_query_params, deleted_only=deleted, all_histories=all
            )
        else:
            payload = HistoryIndexQueryPayload.model_construct(
                show_own=show_own,
                show_published=show_published,
                show_shared=show_shared,
                show_archived=show_archived,
                sort_by=sort_by,
                sort_desc=sort_desc,
                limit=limit,
                offset=offset,
                search=search,
            )
            entries, total_matches = self.service.index_query(
                trans, payload, serialization_params, include_total_count=True
            )
            response.headers["total_matches"] = str(total_matches)
            return entries

    @router.get(
        "/api/histories/count",
        summary="Returns number of histories for the current user.",
    )
    def count(
        self,
        trans: ProvidesHistoryContext = DependsOnTrans,
    ) -> int:
        return self.service.count(trans)

    @router.get(
        "/api/histories/deleted",
        summary="Returns deleted histories for the current user.",
        response_model_exclude_unset=True,
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
        response_model_exclude_unset=True,
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
        response_model_exclude_unset=True,
    )
    def shared_with_me(
        self,
        trans: ProvidesHistoryContext = DependsOnTrans,
        filter_query_params: FilterQueryParams = Depends(get_filter_query_params),
        serialization_params: SerializationParams = Depends(query_serialization_params),
    ) -> List[AnyHistoryView]:
        return self.service.shared_with_me(trans, serialization_params, filter_query_params)

    @router.get(
        "/api/histories/archived",
        summary="Get a list of all archived histories for the current user.",
        response_model_exclude_unset=True,
    )
    def get_archived_histories(
        self,
        response: Response,
        trans: ProvidesHistoryContext = DependsOnTrans,
        serialization_params: SerializationParams = Depends(query_serialization_params),
        filter_query_params: FilterQueryParams = Depends(get_filter_query_params),
    ) -> List[AnyArchivedHistoryView]:
        """Get a list of all archived histories for the current user.

        Archived histories are histories are not part of the active histories of the user but they can be accessed using this endpoint.
        """
        archived_histories, total_matches = self.service.get_archived_histories(
            trans, serialization_params, filter_query_params, include_total_matches=True
        )
        response.headers["total_matches"] = str(total_matches)
        return archived_histories

    @router.get(
        "/api/histories/most_recently_used",
        summary="Returns the most recently used history of the user.",
        response_model_exclude_unset=True,
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
        response_model_exclude_unset=True,
    )
    def show(
        self,
        history_id: HistoryIDPathParam,
        trans: ProvidesHistoryContext = DependsOnTrans,
        serialization_params: SerializationParams = Depends(query_serialization_params),
    ) -> AnyHistoryView:
        return self.service.show(trans, serialization_params, history_id)

    @router.post(
        "/api/histories/{history_id}/prepare_store_download",
        summary="Return a short term storage token to monitor download of the history.",
    )
    def prepare_store_download(
        self,
        history_id: HistoryIDPathParam,
        trans: ProvidesHistoryContext = DependsOnTrans,
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
        history_id: HistoryIDPathParam,
        trans: ProvidesHistoryContext = DependsOnTrans,
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
        history_id: HistoryIDPathParam,
        trans: ProvidesHistoryContext = DependsOnTrans,
    ) -> List[Any]:
        return self.service.citations(trans, history_id)

    @router.get(
        "/api/histories/{history_id}/tool_requests",
        summary="Return all the tool requests for the tools submitted to this history.",
    )
    def tool_requests(
        self,
        history_id: HistoryIDPathParam,
        trans: ProvidesHistoryContext = DependsOnTrans,
    ) -> List[ToolRequestModel]:
        return self.service.tool_requests(trans, history_id)

    @router.post(
        "/api/histories",
        summary="Creates a new history.",
        response_model_exclude_unset=True,
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
            payload = CreateHistoryPayload.model_validate(payload_as_json)
        return self.service.create(trans, payload, serialization_params)

    @router.delete(
        "/api/histories/{history_id}",
        summary="Marks the history with the given ID as deleted.",
        response_model_exclude_unset=True,
    )
    def delete(
        self,
        history_id: HistoryIDPathParam,
        trans: ProvidesHistoryContext = DependsOnTrans,
        serialization_params: SerializationParams = Depends(query_serialization_params),
        purge: bool = Query(default=False),
        payload: Optional[DeleteHistoryPayload] = Body(default=None),
    ) -> AnyHistoryView:
        if payload:
            purge = payload.purge
        return self.service.delete(trans, history_id, serialization_params, purge)

    @router.put(
        "/api/histories/batch/delete",
        summary="Marks several histories with the given IDs as deleted.",
        response_model_exclude_unset=True,
    )
    def batch_delete(
        self,
        trans: ProvidesHistoryContext = DependsOnTrans,
        serialization_params: SerializationParams = Depends(query_serialization_params),
        purge: bool = Query(default=False),
        payload: DeleteHistoriesPayload = Body(...),
    ) -> List[AnyHistoryView]:
        if payload:
            purge = payload.purge
        results = []
        for history_id in payload.ids:
            result = self.service.delete(trans, history_id, serialization_params, purge)
            results.append(result)
        return results

    @router.post(
        "/api/histories/deleted/{history_id}/undelete",
        summary="Restores a deleted history with the given ID (that hasn't been purged).",
        response_model_exclude_unset=True,
    )
    def undelete(
        self,
        history_id: HistoryIDPathParam,
        trans: ProvidesHistoryContext = DependsOnTrans,
        serialization_params: SerializationParams = Depends(query_serialization_params),
    ) -> AnyHistoryView:
        return self.service.undelete(trans, history_id, serialization_params)

    @router.put(
        "/api/histories/batch/undelete",
        summary="Marks several histories with the given IDs as undeleted.",
        response_model_exclude_unset=True,
    )
    def batch_undelete(
        self,
        trans: ProvidesHistoryContext = DependsOnTrans,
        serialization_params: SerializationParams = Depends(query_serialization_params),
        payload: UndeleteHistoriesPayload = Body(...),
    ) -> List[AnyHistoryView]:
        results = []
        for history_id in payload.ids:
            result = self.service.undelete(trans, history_id, serialization_params)
            results.append(result)
        return results

    @router.put(
        "/api/histories/{history_id}",
        summary="Updates the values for the history with the given ID.",
        response_model_exclude_unset=True,
    )
    def update(
        self,
        history_id: HistoryIDPathParam,
        trans: ProvidesHistoryContext = DependsOnTrans,
        payload: UpdateHistoryPayload = Body(
            ...,
            description="Object containing any of the editable fields of the history.",
        ),
        serialization_params: SerializationParams = Depends(query_serialization_params),
    ) -> AnyHistoryView:
        data = payload.model_dump(exclude_unset=True)
        return self.service.update(trans, history_id, data, serialization_params)

    @router.post(
        "/api/histories/from_store",
        summary="Create histories from a model store.",
        response_model_exclude_unset=True,
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
                        "schema": {"$ref": "#/components/schemas/JobExportHistoryArchiveListResponse"},
                    },
                    ExportTaskListResponse.__accept_type__: {
                        "schema": {"$ref": "#/components/schemas/ExportTaskListResponse"},
                    },
                },
            },
        },
    )
    def index_exports(
        self,
        history_id: HistoryIDPathParam,
        trans: ProvidesHistoryContext = DependsOnTrans,
        limit: Optional[int] = LimitQueryParam,
        offset: Optional[int] = OffsetQueryParam,
        accept: IndexExportsAcceptHeader = "application/json",
    ) -> Union[JobExportHistoryArchiveListResponse, ExportTaskListResponse]:
        """
        By default the legacy job-based history exports (jeha) are returned.

        Change the `accept` content type header to return the new task-based history exports.
        """
        use_tasks = accept == ExportTaskListResponse.__accept_type__
        exports = self.service.index_exports(trans, history_id, use_tasks, limit, offset)
        if use_tasks:
            return ExportTaskListResponse(root=exports)
        return JobExportHistoryArchiveListResponse(root=exports)

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
        history_id: HistoryIDPathParam,
        trans=DependsOnTrans,
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
        history_id: HistoryIDPathParam,
        trans: ProvidesHistoryContext = DependsOnTrans,
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
        history_id: HistoryIDPathParam,
        trans: ProvidesHistoryContext = DependsOnTrans,
    ) -> CustomBuildsMetadataResponse:
        return self.service.get_custom_builds_metadata(trans, history_id)

    @router.post(
        "/api/histories/{history_id}/archive",
        summary="Archive a history.",
        response_model_exclude_unset=True,
    )
    def archive_history(
        self,
        history_id: HistoryIDPathParam,
        trans: ProvidesHistoryContext = DependsOnTrans,
        payload: Optional[ArchiveHistoryRequestPayload] = Body(default=None),
    ) -> AnyArchivedHistoryView:
        """Marks the given history as 'archived' and returns the history.

        Archiving a history will remove it from the list of active histories of the user but it will still be
        accessible via the `/api/histories/{id}` or the `/api/histories/archived` endpoints.

        Associating an export record:

        - Optionally, an export record (containing information about a recent snapshot of the history) can be associated with the
        archived history by providing an `archive_export_id` in the payload. The export record must belong to the history and
        must be in the ready state.
        - When associating an export record, the history can be purged after it has been archived using the `purge_history` flag.

        If the history is already archived, this endpoint will return a 409 Conflict error, indicating that the history is already archived.
        If the history was not purged after it was archived, you can restore it using the `/api/histories/{id}/archive/restore` endpoint.
        """
        return self.service.archive_history(trans, history_id, payload)

    @router.put(
        "/api/histories/{history_id}/archive/restore",
        summary="Restore an archived history.",
        response_model_exclude_unset=True,
    )
    def restore_archived_history(
        self,
        history_id: HistoryIDPathParam,
        trans: ProvidesHistoryContext = DependsOnTrans,
        force: Optional[bool] = Query(
            default=None,
            description="If true, the history will be un-archived even if it has an associated archive export record and was purged.",
        ),
    ) -> AnyHistoryView:
        """Restores an archived history and returns it.

        Restoring an archived history will add it back to the list of active histories of the user (unless it was purged).

        **Warning**: Please note that histories that are associated with an archive export might be purged after export, so un-archiving them
        will not restore the datasets that were in the history before it was archived. You will need to import back the archive export
        record to restore the history and its datasets as a new copy. See `/api/histories/from_store_async` for more information.
        """
        return self.service.restore_archived_history(trans, history_id, force)

    @router.get(
        "/api/histories/{history_id}/sharing",
        summary="Get the current sharing status of the given item.",
    )
    def sharing(
        self,
        history_id: HistoryIDPathParam,
        trans: ProvidesUserContext = DependsOnTrans,
    ) -> SharingStatus:
        """Return the sharing status of the item."""
        return self.service.shareable_service.sharing(trans, history_id)

    @router.put(
        "/api/histories/{history_id}/enable_link_access",
        summary="Makes this item accessible by a URL link.",
    )
    def enable_link_access(
        self,
        history_id: HistoryIDPathParam,
        trans: ProvidesUserContext = DependsOnTrans,
    ) -> SharingStatus:
        """Makes this item accessible by a URL link and return the current sharing status."""
        return self.service.shareable_service.enable_link_access(trans, history_id)

    @router.put(
        "/api/histories/{history_id}/disable_link_access",
        summary="Makes this item inaccessible by a URL link.",
    )
    def disable_link_access(
        self,
        history_id: HistoryIDPathParam,
        trans: ProvidesUserContext = DependsOnTrans,
    ) -> SharingStatus:
        """Makes this item inaccessible by a URL link and return the current sharing status."""
        return self.service.shareable_service.disable_link_access(trans, history_id)

    @router.put(
        "/api/histories/{history_id}/publish",
        summary="Makes this item public and accessible by a URL link.",
    )
    def publish(
        self,
        history_id: HistoryIDPathParam,
        trans: ProvidesUserContext = DependsOnTrans,
    ) -> SharingStatus:
        """Makes this item publicly available by a URL link and return the current sharing status."""
        return self.service.shareable_service.publish(trans, history_id)

    @router.put(
        "/api/histories/{history_id}/unpublish",
        summary="Removes this item from the published list.",
    )
    def unpublish(
        self,
        history_id: HistoryIDPathParam,
        trans: ProvidesUserContext = DependsOnTrans,
    ) -> SharingStatus:
        """Removes this item from the published list and return the current sharing status."""
        return self.service.shareable_service.unpublish(trans, history_id)

    @router.put(
        "/api/histories/{history_id}/share_with_users",
        summary="Share this item with specific users.",
    )
    def share_with_users(
        self,
        history_id: HistoryIDPathParam,
        trans: ProvidesUserContext = DependsOnTrans,
        payload: ShareWithPayload = Body(...),
    ) -> ShareHistoryWithStatus:
        """Shares this item with specific users and return the current sharing status."""
        return self.service.shareable_service.share_with_users(trans, history_id, payload)

    @router.put(
        "/api/histories/{history_id}/slug",
        summary="Set a new slug for this shared item.",
        status_code=status.HTTP_204_NO_CONTENT,
    )
    def set_slug(
        self,
        history_id: HistoryIDPathParam,
        trans: ProvidesUserContext = DependsOnTrans,
        payload: SetSlugPayload = Body(...),
    ):
        """Sets a new slug to access this item by URL. The new slug must be unique."""
        self.service.shareable_service.set_slug(trans, history_id, payload)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
