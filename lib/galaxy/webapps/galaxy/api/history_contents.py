"""
API operations on the contents of a history.
"""
import logging
from datetime import datetime
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Set,
    Union,
)

from fastapi import (
    Body,
    Depends,
    Header,
    Path,
    Query,
    Request,
)
from pydantic.error_wrappers import ValidationError
from starlette import status
from starlette.responses import (
    Response,
    StreamingResponse,
)

from galaxy import util
from galaxy.managers.context import ProvidesHistoryContext
from galaxy.schema import (
    FilterQueryParams,
    SerializationParams,
    ValueFilterQueryParams,
)
from galaxy.schema.fields import EncodedDatabaseIdField
from galaxy.schema.schema import (
    AnyHistoryContentItem,
    AnyJobStateSummary,
    AsyncFile,
    AsyncTaskResultSummary,
    DatasetAssociationRoles,
    DatasetSourceType,
    DeleteHistoryContentPayload,
    DeleteHistoryContentResult,
    HistoryContentBulkOperationPayload,
    HistoryContentBulkOperationResult,
    HistoryContentsArchiveDryRunResult,
    HistoryContentsResult,
    HistoryContentsWithStatsResult,
    HistoryContentType,
    MaterializeDatasetInstanceAPIRequest,
    MaterializeDatasetInstanceRequest,
    StoreExportPayload,
    UpdateDatasetPermissionsPayload,
    UpdateHistoryContentsBatchPayload,
    UpdateHistoryContentsPayload,
    WriteStoreToPayload,
)
from galaxy.web.framework.decorators import validation_error_to_message_exception
from galaxy.webapps.galaxy.api.common import (
    get_filter_query_params,
    get_update_permission_payload,
    get_value_filter_query_params,
    query_serialization_params,
)
from galaxy.webapps.galaxy.services.history_contents import (
    CreateHistoryContentFromStore,
    CreateHistoryContentPayload,
    DatasetDetailsType,
    DirectionOptions,
    HistoriesContentsService,
    HistoryContentsFilterList,
    HistoryContentsIndexJobsSummaryParams,
    HistoryContentsIndexParams,
    LegacyHistoryContentsIndexParams,
)
from . import (
    depends,
    DependsOnTrans,
    Router,
)

log = logging.getLogger(__name__)


router = Router(tags=["histories"])

HistoryIDPathParam: EncodedDatabaseIdField = Path(..., title="History ID", description="The ID of the History.")

HistoryItemIDPathParam: EncodedDatabaseIdField = Path(
    ..., title="History Item ID", description="The ID of the item (`HDA`/`HDCA`) contained in the history."
)

HistoryHDCAIDPathParam: EncodedDatabaseIdField = Path(
    ..., title="History Dataset Collection ID", description="The ID of the `HDCA` contained in the history."
)

ContentTypeQueryParam = Query(
    default=HistoryContentType.dataset,
    title="Content Type",
    description="The type of the history element to show.",
    example=HistoryContentType.dataset,
)

CONTENT_DELETE_RESPONSES = {
    200: {
        "description": "Request has been executed.",
        "model": DeleteHistoryContentResult,
    },
    202: {
        "description": "Request accepted, processing will finish later.",
        "model": DeleteHistoryContentResult,
    },
}


def get_index_query_params(
    v: Optional[str] = Query(  # Should this be deprecated at some point and directly use the latest version by default?
        default=None,
        title="Version",
        description=(
            "Only `dev` value is allowed. Set it to use the latest version of this endpoint. "
            "**All parameters marked as `deprecated` will be ignored when this parameter is set.**"
        ),
        example="dev",
    ),
    dataset_details: Optional[str] = Query(
        default=None,
        alias="details",
        title="Dataset Details",
        description=(
            "A comma-separated list of encoded dataset IDs that will return additional (full) details "
            "instead of the *summary* default information."
        ),
        deprecated=True,  # TODO: remove 'dataset_details' when the UI doesn't need it
    ),
) -> HistoryContentsIndexParams:
    """This function is meant to be used as a dependency to render the OpenAPI documentation
    correctly"""
    return parse_index_query_params(
        v=v,
        dataset_details=dataset_details,
    )


def parse_index_query_params(
    v: Optional[str] = None,
    dataset_details: Optional[str] = None,
    **_,  # Additional params are ignored
) -> HistoryContentsIndexParams:
    """Parses query parameters for the history contents `index` operation
    and returns a model containing the values in the correct type."""
    try:
        return HistoryContentsIndexParams(
            v=v,
            dataset_details=parse_dataset_details(dataset_details),
        )
    except ValidationError as e:
        raise validation_error_to_message_exception(e)


def get_legacy_index_query_params(
    ids: Optional[str] = Query(
        default=None,
        title="IDs",
        description=(
            "A comma-separated list of encoded `HDA/HDCA` IDs. If this list is provided, only information about the "
            "specific datasets will be returned. Also, setting this value will return `all` details of the content item."
        ),
        deprecated=True,
    ),
    types: Optional[List[str]] = Query(
        default=None,
        title="Types",
        description=(
            "A list or comma-separated list of kinds of contents to return "
            "(currently just `dataset` and `dataset_collection` are available). "
            "If unset, all types will be returned."
        ),
        deprecated=True,
    ),
    type: Optional[str] = Query(
        default=None,
        include_in_schema=False,
        deprecated=True,
    ),
    details: Optional[str] = Query(
        default=None,
        title="Details",
        description=("Legacy name for the `dataset_details` parameter."),
        deprecated=True,
    ),
    deleted: Optional[bool] = Query(
        default=None,
        title="Deleted",
        description="Whether to return deleted or undeleted datasets only. Leave unset for both.",
        deprecated=True,
    ),
    visible: Optional[bool] = Query(
        default=None,
        title="Visible",
        description="Whether to return visible or hidden datasets only. Leave unset for both.",
        deprecated=True,
    ),
) -> LegacyHistoryContentsIndexParams:
    """This function is meant to be used as a dependency to render the OpenAPI documentation
    correctly"""
    return parse_legacy_index_query_params(
        ids=ids,
        types=types or type,
        details=details,
        deleted=deleted,
        visible=visible,
    )


def parse_legacy_index_query_params(
    ids: Optional[str] = None,
    types: Optional[Union[List[str], str]] = None,
    details: Optional[str] = None,
    deleted: Optional[bool] = None,
    visible: Optional[bool] = None,
    **_,  # Additional params are ignored
) -> LegacyHistoryContentsIndexParams:
    """Parses (legacy) query parameters for the history contents `index` operation
    and returns a model containing the values in the correct type."""
    if types:
        if isinstance(types, list) and len(types) == 1:  # Support ?types=dataset,dataset_collection
            content_types = util.listify(types[0])
        else:  # Support ?types=dataset&types=dataset_collection
            content_types = util.listify(types)
    else:
        content_types = [e.value for e in HistoryContentType]

    id_list: Optional[List[EncodedDatabaseIdField]] = None
    if ids:
        id_list = util.listify(ids)
        # If explicit ids given, always used detailed result.
        dataset_details = "all"
    else:
        dataset_details = parse_dataset_details(details)

    try:
        return LegacyHistoryContentsIndexParams(
            types=content_types,
            ids=id_list,
            deleted=deleted,
            visible=visible,
            dataset_details=dataset_details,
        )
    except ValidationError as e:
        raise validation_error_to_message_exception(e)


def parse_dataset_details(details: Optional[str]):
    """Parses the different values that the `dataset_details` parameter
    can have from a string."""
    dataset_details: Optional[DatasetDetailsType] = None
    if details is not None and details != "all":
        dataset_details = set(util.listify(details))
    else:  # either None or 'all'
        dataset_details = details  # type: ignore
    return dataset_details


def get_index_jobs_summary_params(
    ids: Optional[str] = Query(
        default=None,
        title="IDs",
        description=(
            "A comma-separated list of encoded ids of job summary objects to return - if `ids` "
            "is specified types must also be specified and have same length."
        ),
    ),
    types: Optional[str] = Query(
        default=None,
        title="Types",
        description=(
            "A comma-separated list of type of object represented by elements in the `ids` array - any of "
            "`Job`, `ImplicitCollectionJob`, or `WorkflowInvocation`."
        ),
    ),
) -> HistoryContentsIndexJobsSummaryParams:
    """This function is meant to be used as a dependency to render the OpenAPI documentation
    correctly"""
    return parse_index_jobs_summary_params(
        ids=ids,
        types=types,
    )


def parse_index_jobs_summary_params(
    ids: Optional[str] = None,
    types: Optional[str] = None,
    **_,  # Additional params are ignored
) -> HistoryContentsIndexJobsSummaryParams:
    """Parses query parameters for the history contents `index_jobs_summary` operation
    and returns a model containing the values in the correct type."""
    return HistoryContentsIndexJobsSummaryParams(ids=util.listify(ids), types=util.listify(types))


def parse_content_filter_params(
    params: Dict[str, Any],
    exclude: Optional[Set[str]] = None,
) -> HistoryContentsFilterList:
    """Alternative way of parsing query parameter for filtering history contents.

    Parses parameters like: ?[field]-[operator]=[value]
        Example: ?update_time-gt=2015-01-29

    Currently used by the `contents_near` endpoint. The `exclude` set can contain
    names of parameters that will be ignored and not added to the filters.
    """
    DEFAULT_OP = "eq"
    splitchar = "-"

    exclude = exclude or set()
    result = []
    for key, val in params.items():
        if key in exclude:
            continue
        attr = key
        op = DEFAULT_OP
        if splitchar in key:
            attr, op = key.rsplit(splitchar, 1)
        result.append([attr, op, val])

    return result


@router.cbv
class FastAPIHistoryContents:
    service: HistoriesContentsService = depends(HistoriesContentsService)

    @router.get(
        "/api/histories/{history_id}/contents/{type}s",
        summary="Returns the contents of the given history filtered by type.",
    )
    @router.get(
        "/api/histories/{history_id}/contents",
        name="history_contents",
        summary="Returns the contents of the given history.",
        responses={
            200: {
                "description": ("The contents of the history that match the query."),
                "content": {
                    "application/json": {
                        "schema": {  # HistoryContentsResult.schema(),
                            "ref": "#/components/schemas/HistoryContentsResult"
                        },
                    },
                    HistoryContentsWithStatsResult.__accept_type__: {
                        "schema": {  # HistoryContentsWithStatsResult.schema(),
                            "ref": "#/components/schemas/HistoryContentsWithStatsResult"
                        },
                    },
                },
            },
        },
    )
    def index(
        self,
        trans: ProvidesHistoryContext = DependsOnTrans,
        history_id: EncodedDatabaseIdField = HistoryIDPathParam,
        index_params: HistoryContentsIndexParams = Depends(get_index_query_params),
        legacy_params: LegacyHistoryContentsIndexParams = Depends(get_legacy_index_query_params),
        serialization_params: SerializationParams = Depends(query_serialization_params),
        filter_query_params: FilterQueryParams = Depends(get_filter_query_params),
        accept: str = Header(default="application/json", include_in_schema=False),
    ) -> Union[HistoryContentsResult, HistoryContentsWithStatsResult]:
        """
        Return a list of `HDA`/`HDCA` data for the history with the given ``ID``.

        - The contents can be filtered and queried using the appropriate parameters.
        - The amount of information returned for each item can be customized.

        **Note**: Anonymous users are allowed to get their current history contents.
        """
        items = self.service.index(
            trans,
            history_id,
            index_params,
            legacy_params,
            serialization_params,
            filter_query_params,
            accept,
        )
        return items

    @router.get(
        "/api/histories/{history_id}/contents/{type}s/{id}/jobs_summary",
        summary="Return detailed information about an `HDA` or `HDCAs` jobs.",
    )
    def show_jobs_summary(
        self,
        trans: ProvidesHistoryContext = DependsOnTrans,
        history_id: EncodedDatabaseIdField = HistoryIDPathParam,
        id: EncodedDatabaseIdField = HistoryItemIDPathParam,
        type: HistoryContentType = ContentTypeQueryParam,
    ) -> AnyJobStateSummary:
        """Return detailed information about an `HDA` or `HDCAs` jobs.

        **Warning**: We allow anyone to fetch job state information about any object they
        can guess an encoded ID for - it isn't considered protected data. This keeps
        polling IDs as part of state calculation for large histories and collections as
        efficient as possible.
        """
        return self.service.show_jobs_summary(trans, id, contents_type=type)

    @router.get(
        "/api/histories/{history_id}/contents/{type}s/{id}",
        name="history_content_typed",
        summary="Return detailed information about a specific HDA or HDCA with the given `ID` within a history.",
        response_model_exclude_unset=True,
    )
    @router.get(
        "/api/histories/{history_id}/contents/{id}",
        name="history_content",
        summary="Return detailed information about an HDA within a history. ``/api/histories/{history_id}/contents/{type}s/{id}`` should be used instead.",
        response_model_exclude_unset=True,
        deprecated=True,
    )
    def show(
        self,
        trans: ProvidesHistoryContext = DependsOnTrans,
        history_id: EncodedDatabaseIdField = HistoryIDPathParam,
        id: EncodedDatabaseIdField = HistoryItemIDPathParam,
        type: HistoryContentType = ContentTypeQueryParam,
        fuzzy_count: Optional[int] = Query(
            default=None,
            title="Fuzzy Count",
            description=(
                "This value can be used to broadly restrict the magnitude "
                "of the number of elements returned via the API for large "
                "collections. The number of actual elements returned may "
                'be "a bit" more than this number or "a lot" less - varying '
                "on the depth of nesting, balance of nesting at each level, "
                "and size of target collection. The consumer of this API should "
                "not expect a stable number or pre-calculable number of "
                "elements to be produced given this parameter - the only "
                "promise is that this API will not respond with an order "
                "of magnitude more elements estimated with this value. "
                'The UI uses this parameter to fetch a "balanced" concept of '
                'the "start" of large collections at every depth of the '
                "collection."
            ),
        ),
        serialization_params: SerializationParams = Depends(query_serialization_params),
    ) -> AnyHistoryContentItem:
        """
        Return detailed information about an `HDA` or `HDCA` within a history.

        **Note**: Anonymous users are allowed to get their current history contents.
        """
        return self.service.show(
            trans,
            id=id,
            serialization_params=serialization_params,
            contents_type=type,
            fuzzy_count=fuzzy_count,
        )

    @router.post(
        "/api/histories/{history_id}/contents/{type}s/{id}/prepare_store_download",
        summary="Prepare a dataset or dataset collection for export-style download.",
    )
    def prepare_store_download(
        self,
        trans: ProvidesHistoryContext = DependsOnTrans,
        history_id: EncodedDatabaseIdField = HistoryIDPathParam,
        id: EncodedDatabaseIdField = HistoryItemIDPathParam,
        type: HistoryContentType = ContentTypeQueryParam,
        payload: StoreExportPayload = Body(...),
    ) -> AsyncFile:
        return self.service.prepare_store_download(
            trans,
            id,
            contents_type=type,
            payload=payload,
        )

    @router.post(
        "/api/histories/{history_id}/contents/{type}s/{id}/write_store",
        summary="Prepare a dataset or dataset collection for export-style download and write to supplied URI.",
    )
    def write_store(
        self,
        trans: ProvidesHistoryContext = DependsOnTrans,
        history_id: EncodedDatabaseIdField = HistoryIDPathParam,
        id: EncodedDatabaseIdField = HistoryItemIDPathParam,
        type: HistoryContentType = ContentTypeQueryParam,
        payload: WriteStoreToPayload = Body(...),
    ) -> AsyncTaskResultSummary:
        return self.service.write_store(
            trans,
            id,
            contents_type=type,
            payload=payload,
        )

    @router.get(
        "/api/histories/{history_id}/jobs_summary",
        summary="Return job state summary info for jobs, implicit groups jobs for collections or workflow invocations.",
    )
    def index_jobs_summary(
        self,
        trans: ProvidesHistoryContext = DependsOnTrans,
        history_id: EncodedDatabaseIdField = HistoryIDPathParam,
        params: HistoryContentsIndexJobsSummaryParams = Depends(get_index_jobs_summary_params),
    ) -> List[AnyJobStateSummary]:
        """Return job state summary info for jobs, implicit groups jobs for collections or workflow invocations.

        **Warning**: We allow anyone to fetch job state information about any object they
        can guess an encoded ID for - it isn't considered protected data. This keeps
        polling IDs as part of state calculation for large histories and collections as
        efficient as possible.
        """
        return self.service.index_jobs_summary(trans, params)

    @router.get(
        "/api/histories/{history_id}/contents/dataset_collections/{id}/download",
        summary="Download the content of a dataset collection as a `zip` archive.",
        response_class=StreamingResponse,
    )
    @router.get(
        "/api/dataset_collections/{id}/download",
        summary="Download the content of a dataset collection as a `zip` archive.",
        response_class=StreamingResponse,
        tags=["dataset collections"],
    )
    def download_dataset_collection(
        self,
        trans: ProvidesHistoryContext = DependsOnTrans,
        history_id: Optional[EncodedDatabaseIdField] = Query(
            default=None,
            description="The encoded database identifier of the History.",
        ),
        id: EncodedDatabaseIdField = HistoryHDCAIDPathParam,
    ):
        """Download the content of a history dataset collection as a `zip` archive
        while maintaining approximate collection structure.
        """
        archive = self.service.get_dataset_collection_archive_for_download(trans, id)
        return StreamingResponse(archive.response(), headers=archive.get_headers())

    @router.post(
        "/api/histories/{history_id}/contents/dataset_collections/{id}/prepare_download",
        summary="Prepare an short term storage object that the collection will be downloaded to.",
        responses={
            200: {
                "description": "Short term storage reference for async monitoring of this download.",
            },
            501: {"description": "Required asynchronous tasks required for this operation not available."},
        },
    )
    @router.post(
        "/api/dataset_collections/{id}/prepare_download",
        summary="Prepare an short term storage object that the collection will be downloaded to.",
        tags=["dataset collections"],
    )
    def prepare_collection_download(
        self,
        trans: ProvidesHistoryContext = DependsOnTrans,
        history_id: EncodedDatabaseIdField = HistoryIDPathParam,
        id: EncodedDatabaseIdField = HistoryHDCAIDPathParam,
    ) -> AsyncFile:
        """The history dataset collection will be written as a `zip` archive to the
        returned short term storage object. Progress tracking this file's creation
        can be tracked with the short_term_storage API.
        """
        return self.service.prepare_collection_download(trans, id)

    @router.post(
        "/api/histories/{history_id}/contents/{type}s",
        summary="Create a new `HDA` or `HDCA` in the given History.",
        response_model_exclude_unset=True,
    )
    @router.post(
        "/api/histories/{history_id}/contents",
        summary="Create a new `HDA` or `HDCA` in the given History.",
        response_model_exclude_unset=True,
        deprecated=True,
    )
    def create(
        self,
        trans: ProvidesHistoryContext = DependsOnTrans,
        history_id: EncodedDatabaseIdField = HistoryIDPathParam,
        type: Optional[HistoryContentType] = Query(
            default=None,
            title="Content Type",
            description="The type of the history element to create.",
            example=HistoryContentType.dataset,
        ),
        serialization_params: SerializationParams = Depends(query_serialization_params),
        payload: CreateHistoryContentPayload = Body(...),
    ) -> Union[AnyHistoryContentItem, List[AnyHistoryContentItem]]:
        """Create a new `HDA` or `HDCA` in the given History."""
        payload.type = type or payload.type
        return self.service.create(trans, history_id, payload, serialization_params)

    @router.put(
        "/api/histories/{history_id}/contents/{dataset_id}/permissions",
        summary="Set permissions of the given history dataset to the given role ids.",
    )
    def update_permissions(
        self,
        trans: ProvidesHistoryContext = DependsOnTrans,
        history_id: EncodedDatabaseIdField = HistoryIDPathParam,
        dataset_id: EncodedDatabaseIdField = HistoryItemIDPathParam,
        # Using a generic Dict here as an attempt on supporting multiple aliases for the permissions params.
        payload: Dict[str, Any] = Body(
            default=...,
            example=UpdateDatasetPermissionsPayload(),
        ),
    ) -> DatasetAssociationRoles:
        """Set permissions of the given history dataset to the given role ids."""
        update_payload = get_update_permission_payload(payload)
        return self.service.update_permissions(trans, dataset_id, update_payload)

    @router.put(
        "/api/histories/{history_id}/contents",
        summary="Batch update specific properties of a set items contained in the given History.",
    )
    def update_batch(
        self,
        trans: ProvidesHistoryContext = DependsOnTrans,
        history_id: EncodedDatabaseIdField = HistoryIDPathParam,
        serialization_params: SerializationParams = Depends(query_serialization_params),
        payload: UpdateHistoryContentsBatchPayload = Body(...),
    ) -> HistoryContentsResult:
        """Batch update specific properties of a set items contained in the given History.

        If you provide an invalid/unknown property key the request will not fail, but no changes
        will be made to the items.
        """
        result = self.service.update_batch(trans, history_id, payload, serialization_params)
        return HistoryContentsResult.parse_obj(result)

    @router.put(
        "/api/histories/{history_id}/contents/bulk",
        summary="Executes an operation on a set of items contained in the given History.",
    )
    def bulk_operation(
        self,
        trans: ProvidesHistoryContext = DependsOnTrans,
        history_id: EncodedDatabaseIdField = HistoryIDPathParam,
        filter_query_params: ValueFilterQueryParams = Depends(get_value_filter_query_params),
        payload: HistoryContentBulkOperationPayload = Body(...),
    ) -> HistoryContentBulkOperationResult:
        """Executes an operation on a set of items contained in the given History.

        The items to be processed can be explicitly set or determined by a dynamic query.
        """
        return self.service.bulk_operation(trans, history_id, filter_query_params, payload)

    @router.put(
        "/api/histories/{history_id}/contents/{id}/validate",
        summary="Validates the metadata associated with a dataset within a History.",
    )
    def validate(
        self,
        trans: ProvidesHistoryContext = DependsOnTrans,
        history_id: EncodedDatabaseIdField = HistoryIDPathParam,
        id: EncodedDatabaseIdField = HistoryItemIDPathParam,
    ) -> dict:  # TODO: define a response?
        """Validates the metadata associated with a dataset within a History."""
        return self.service.validate(trans, history_id, id)

    @router.put(
        "/api/histories/{history_id}/contents/{type}s/{id}",
        summary="Updates the values for the history content item with the given ``ID``.",
        response_model_exclude_unset=True,
    )
    @router.put(
        "/api/histories/{history_id}/contents/{id}",
        summary="Updates the values for the history content item with the given ``ID``. ``/api/histories/{history_id}/contents/{type}s/{id}`` should be used instead.",
        response_model_exclude_unset=True,
        deprecated=True,
    )
    def update(
        self,
        trans: ProvidesHistoryContext = DependsOnTrans,
        history_id: EncodedDatabaseIdField = HistoryIDPathParam,
        id: EncodedDatabaseIdField = HistoryItemIDPathParam,
        type: HistoryContentType = ContentTypeQueryParam,
        serialization_params: SerializationParams = Depends(query_serialization_params),
        payload: UpdateHistoryContentsPayload = Body(...),
    ) -> AnyHistoryContentItem:
        """Updates the values for the history content item with the given ``ID``."""
        return self.service.update(trans, history_id, id, payload.dict(), serialization_params, contents_type=type)

    @router.delete(
        "/api/histories/{history_id}/contents/{type}s/{id}",
        summary="Delete the history content with the given ``ID`` and specified type.",
        responses=CONTENT_DELETE_RESPONSES,
    )
    @router.delete(
        "/api/histories/{history_id}/contents/{id}",
        summary="Delete the history dataset with the given ``ID``.",
        responses=CONTENT_DELETE_RESPONSES,
    )
    def delete(
        self,
        response: Response,
        trans: ProvidesHistoryContext = DependsOnTrans,
        history_id: EncodedDatabaseIdField = HistoryIDPathParam,
        id: EncodedDatabaseIdField = HistoryItemIDPathParam,
        type: HistoryContentType = ContentTypeQueryParam,
        serialization_params: SerializationParams = Depends(query_serialization_params),
        purge: Optional[bool] = Query(
            default=False,
            title="Purge",
            description="Whether to remove from disk the target HDA or child HDAs of the target HDCA.",
            deprecated=True,
        ),
        recursive: Optional[bool] = Query(
            default=False,
            title="Recursive",
            description="When deleting a dataset collection, whether to also delete containing datasets.",
            deprecated=True,
        ),
        stop_job: Optional[bool] = Query(
            default=False,
            title="Stop Job",
            description="Whether to stop the creating job if all outputs of the job have been deleted.",
            deprecated=True,
        ),
        payload: DeleteHistoryContentPayload = Body(None),
    ):
        """
        Delete the history content with the given ``ID`` and specified type (defaults to dataset).

        **Note**: Currently does not stop any active jobs for which this dataset is an output.
        """
        # TODO: should we just use the default payload and deprecate the query params?
        if payload is None:
            payload = DeleteHistoryContentPayload()
        payload.purge = payload.purge or purge is True
        payload.recursive = payload.recursive or recursive is True
        payload.stop_job = payload.stop_job or stop_job is True
        rval = self.service.delete(
            trans,
            id=id,
            serialization_params=serialization_params,
            contents_type=type,
            payload=payload,
        )
        async_result = rval.pop("async_result", None)
        if async_result:
            response.status_code = status.HTTP_202_ACCEPTED
        return rval

    @router.get(
        "/api/histories/{history_id}/contents/archive/{filename}.{format}",
        summary="Build and return a compressed archive of the selected history contents.",
    )
    @router.get(
        "/api/histories/{history_id}/contents/archive/{id}",
        summary="Build and return a compressed archive of the selected history contents.",
    )
    def archive(
        self,
        trans: ProvidesHistoryContext = DependsOnTrans,
        history_id: EncodedDatabaseIdField = HistoryIDPathParam,
        filename: Optional[str] = Query(
            default=None,
            description="The name that the Archive will have (defaults to history name).",
        ),
        format: Optional[str] = Query(
            default="zip",
            description="Output format of the archive.",
            deprecated=True,  # Looks like is not really used?
        ),
        dry_run: Optional[bool] = Query(
            default=True,
            description="Whether to return the archive and file paths only (as JSON) and not an actual archive file.",
        ),
        filter_query_params: FilterQueryParams = Depends(get_filter_query_params),
    ):
        """Build and return a compressed archive of the selected history contents.

        **Note**: this is a volatile endpoint and settings and behavior may change."""
        archive = self.service.archive(trans, history_id, filter_query_params, filename, dry_run)
        if isinstance(archive, HistoryContentsArchiveDryRunResult):
            return archive
        return StreamingResponse(archive.response(), headers=archive.get_headers())

    @router.post("/api/histories/{history_id}/contents_from_store", summary="Create contents from store.")
    def create_from_store(
        self,
        trans: ProvidesHistoryContext = DependsOnTrans,
        history_id: EncodedDatabaseIdField = HistoryIDPathParam,
        serialization_params: SerializationParams = Depends(query_serialization_params),
        create_payload: CreateHistoryContentFromStore = Body(...),
    ) -> List[AnyHistoryContentItem]:
        """
        Create history contents from model store.
        Input can be a tarfile created with build_objects script distributed
        with galaxy-data, from an exported history with files stripped out,
        or hand-crafted JSON dictionary.
        """
        return self.service.create_from_store(trans, history_id, create_payload, serialization_params)

    @router.get(
        "/api/histories/{history_id}/contents/{direction}/{hid}/{limit}",
        summary="Get content items around a particular `HID`.",
    )
    def contents_near(
        self,
        request: Request,
        response: Response,
        trans: ProvidesHistoryContext = DependsOnTrans,
        history_id: EncodedDatabaseIdField = HistoryIDPathParam,
        hid: int = Path(
            ...,
            title="Target HID",
            description="The target `HID` to get content around it.",
        ),
        direction: DirectionOptions = Path(
            ...,
            description="Determines what items are selected before, after or near the target `hid`.",
        ),
        limit: int = Path(
            ...,
            description="The maximum number of content items to return above and below the target `HID`.",
        ),
        since: Optional[datetime] = Query(
            default=None,
            description=(
                "A timestamp in ISO format to check if the history has changed since this particular date/time. "
                "If it hasn't changed, no additional processing will be done and 204 status code will be returned."
            ),
        ),
        serialization_params: SerializationParams = Depends(query_serialization_params),
    ) -> HistoryContentsResult:
        """
        .. warning:: For internal use to support the scroller functionality.

        This endpoint provides random access to a large history without having
        to know exactly how many pages are in the final query. Pick a target HID
        and filters, and the endpoint will get a maximum of `limit` history items "around" the `hid`.

        Additional counts are provided in the HTTP headers.

        The `direction` determines what items are selected:

        a) item counts:

           - total matches-up:   hid < {hid}
           - total matches-down: hid > {hid}
           - total matches:      total matches-up + total matches-down + 1 (+1 for hid == {hid})
           - displayed matches-up:   hid <= {hid} (hid == {hid} is included)
           - displayed matches-down: hid > {hid}
           - displayed matches:      displayed matches-up + displayed matches-down

        b) {limit} history items:

           - if direction == "before": hid <= {hid}
           - if direction == "after":  hid > {hid}
           - if direction == "near":   "near" {hid}, so that
             n. items before <= limit // 2,
             n. items after <= limit // 2 + 1.

        .. note:: This endpoint uses slightly different filter params syntax. Instead of using `q`/`qv` parameters,
            it uses the following syntax for query parameters::

                ?[field]-[operator]=[value]

            Example::

                ?update_time-gt=2015-01-29
        """

        # Needed to parse arbitrary query parameter names for the filters.
        # Since we are directly accessing the request's query_params we also need to exclude the
        # known params that are already parsed by FastAPI or they may be treated as filter params too.
        # This looks a bit hacky...
        exclude_params = {"since"}
        exclude_params.update(SerializationParams.__fields__.keys())
        filter_params = parse_content_filter_params(request.query_params._dict, exclude=exclude_params)

        result = self.service.contents_near(
            trans,
            history_id,
            serialization_params,
            filter_params,
            direction,
            hid,
            limit,
            since,
        )
        if result is None:
            return Response(status_code=status.HTTP_204_NO_CONTENT)
        response.headers.update(result.stats.to_headers())
        return result.contents

    @router.post(
        "/api/histories/{history_id}/contents/datasets/{id}/materialize",
        summary="Materialize a deferred dataset into real, usable dataset.",
    )
    def materialize_dataset(
        self,
        trans: ProvidesHistoryContext = DependsOnTrans,
        history_id: EncodedDatabaseIdField = HistoryIDPathParam,
        id: EncodedDatabaseIdField = HistoryItemIDPathParam,
    ) -> AsyncTaskResultSummary:
        materializae_request = MaterializeDatasetInstanceRequest(
            history_id=history_id,
            source=DatasetSourceType.hda,
            content=id,
        )
        rval = self.service.materialize(trans, materializae_request)
        return rval

    @router.post(
        "/api/histories/{history_id}/materialize",
        summary="Materialize a deferred library or HDA dataset into real, usable dataset in specified history.",
    )
    def materialize_to_history(
        self,
        trans: ProvidesHistoryContext = DependsOnTrans,
        history_id: EncodedDatabaseIdField = HistoryIDPathParam,
        materialize_api_payload: MaterializeDatasetInstanceAPIRequest = Body(...),
    ) -> AsyncTaskResultSummary:
        materializae_request: MaterializeDatasetInstanceRequest = MaterializeDatasetInstanceRequest(
            history_id=history_id, **materialize_api_payload.dict()
        )
        rval = self.service.materialize(trans, materializae_request)
        return rval
