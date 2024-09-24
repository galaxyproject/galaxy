"""
API operations on the contents of a history dataset.
"""

import logging
from io import (
    BytesIO,
    IOBase,
    StringIO,
)
from typing import (
    Any,
    cast,
    Dict,
    List,
    Optional,
)

from fastapi import (
    Body,
    Depends,
    Path,
    Query,
    Request,
)
from starlette.responses import (
    Response,
    StreamingResponse,
)
from typing_extensions import Annotated

from galaxy.datatypes.dataproviders.base import MAX_LIMIT
from galaxy.schema import (
    FilterQueryParams,
    SerializationParams,
)
from galaxy.schema.fields import DecodedDatabaseIdField
from galaxy.schema.schema import (
    AnyHDA,
    AnyHistoryContentItem,
    AsyncTaskResultSummary,
    DatasetAssociationRoles,
    DatasetSourceType,
    UpdateDatasetPermissionsPayload,
)
from galaxy.util.zipstream import ZipstreamWrapper
from galaxy.webapps.base.api import GalaxyFileResponse
from galaxy.webapps.galaxy.api import (
    depends,
    DependsOnTrans,
    Router,
)
from galaxy.webapps.galaxy.api.common import (
    get_filter_query_params,
    get_query_parameters_from_request_excluding,
    get_update_permission_payload,
    HistoryDatasetIDPathParam,
    HistoryIDPathParam,
    query_serialization_params,
)
from galaxy.webapps.galaxy.services.datasets import (
    ComputeDatasetHashPayload,
    ConvertedDatasetsMap,
    DatasetContentType,
    DatasetExtraFiles,
    DatasetInheritanceChain,
    DatasetsService,
    DatasetStorageDetails,
    DatasetTextContentDetails,
    DeleteDatasetBatchPayload,
    DeleteDatasetBatchResult,
    RequestDataType,
    UpdateObjectStoreIdPayload,
)

log = logging.getLogger(__name__)

router = Router(tags=["datasets"])

DatasetIDPathParam = Annotated[
    DecodedDatabaseIdField, Path(..., description="The encoded database identifier of the dataset.")
]

DatasetSourceQueryParam: DatasetSourceType = Query(
    default=DatasetSourceType.hda,
    description="Whether this dataset belongs to a history (HDA) or a library (LDDA).",
)

PreviewQueryParam = Query(
    default=False,
    description=(
        "Whether to get preview contents to be directly displayed on the web. "
        "If preview is False (default) the contents will be downloaded instead."
    ),
)

FilenameQueryParam = Query(
    default=None,
    description="If non-null, get the specified filename from the extra files for this dataset.",
)

ToExtQueryParam = Query(
    default=None,
    description=(
        "The file extension when downloading the display data. Use the value `data` to "
        "let the server infer it from the data type."
    ),
)

RawQueryParam = Query(
    default=False,
    description=(
        "The query parameter 'raw' should be considered experimental and may be dropped at "
        "some point in the future without warning. Generally, data should be processed by its "
        "datatype prior to display."
    ),
)

DisplayOffsetQueryParam = Query(
    default=None,
    description=(
        "Set this for datatypes that allow chunked display through the display_data method to enable "
        "chunking. This specifies a byte offset into the target dataset's display."
    ),
)

DisplayChunkSizeQueryParam = Query(
    default=None,
    description=(
        "If offset is set, this recommends 'how large' the next chunk should be. "
        "This is not respected or interpreted uniformly and should be interpreted as a very loose recommendation. "
        "Different datatypes interpret 'largeness' differently - for bam datasets this is a number of lines whereas "
        "for tabular datatypes this is interpreted as a number of bytes. "
    ),
)


@router.cbv
class FastAPIDatasets:
    service: DatasetsService = depends(DatasetsService)

    @router.get(
        "/api/datasets",
        summary="Search datasets or collections using a query system.",
        response_model_exclude_unset=True,
    )
    def index(
        self,
        trans=DependsOnTrans,
        history_id: Optional[DecodedDatabaseIdField] = Query(
            default=None,
            description="Optional identifier of a History. Use it to restrict the search within a particular History.",
        ),
        serialization_params: SerializationParams = Depends(query_serialization_params),
        filter_query_params: FilterQueryParams = Depends(get_filter_query_params),
    ) -> List[AnyHistoryContentItem]:
        return self.service.index(trans, history_id, serialization_params, filter_query_params)

    @router.get(
        "/api/datasets/{dataset_id}/storage",
        summary="Display user-facing storage details related to the objectstore a dataset resides in.",
    )
    def show_storage(
        self,
        dataset_id: HistoryDatasetIDPathParam,
        trans=DependsOnTrans,
        hda_ldda: DatasetSourceType = DatasetSourceQueryParam,
    ) -> DatasetStorageDetails:
        return self.service.show_storage(trans, dataset_id, hda_ldda)

    @router.get(
        "/api/datasets/{dataset_id}/inheritance_chain",
        summary="For internal use, this endpoint may change without warning.",
        include_in_schema=True,  # Can be changed to False if we don't really want to expose this
    )
    def show_inheritance_chain(
        self,
        dataset_id: HistoryDatasetIDPathParam,
        trans=DependsOnTrans,
        hda_ldda: DatasetSourceType = DatasetSourceQueryParam,
    ) -> DatasetInheritanceChain:
        return self.service.show_inheritance_chain(trans, dataset_id, hda_ldda)

    @router.get(
        "/api/datasets/{dataset_id}/get_content_as_text",
        summary="Returns dataset content as Text.",
    )
    def get_content_as_text(
        self,
        dataset_id: HistoryDatasetIDPathParam,
        trans=DependsOnTrans,
    ) -> DatasetTextContentDetails:
        return self.service.get_content_as_text(trans, dataset_id)

    @router.get(
        "/api/datasets/{dataset_id}/converted/{ext}",
        summary="Return information about datasets made by converting this dataset to a new format.",
    )
    def converted_ext(
        self,
        dataset_id: HistoryDatasetIDPathParam,
        trans=DependsOnTrans,
        ext: str = Path(
            ...,
            description="File extension of the new format to convert this dataset to.",
        ),
        serialization_params: SerializationParams = Depends(query_serialization_params),
    ) -> AnyHDA:
        """
        Return information about datasets made by converting this dataset to a new format.

        If there is no existing converted dataset for the format in `ext`, one will be created.

        **Note**: `view` and `keys` are also available to control the serialization of the dataset.
        """
        return self.service.converted_ext(trans, dataset_id, ext, serialization_params)

    @router.get(
        "/api/datasets/{dataset_id}/converted",
        summary=("Return a a map with all the existing converted datasets associated with this instance."),
    )
    def converted(
        self,
        dataset_id: HistoryDatasetIDPathParam,
        trans=DependsOnTrans,
    ) -> ConvertedDatasetsMap:
        """
        Return a map of `<converted extension> : <converted id>` containing all the *existing* converted datasets.
        """
        return self.service.converted(trans, dataset_id)

    @router.put(
        "/api/datasets/{dataset_id}/permissions",
        summary="Set permissions of the given history dataset to the given role ids.",
    )
    def update_permissions(
        self,
        dataset_id: HistoryDatasetIDPathParam,
        trans=DependsOnTrans,
        # Using a generic Dict here as an attempt on supporting multiple aliases for the permissions params.
        payload: Dict[str, Any] = Body(
            default=...,
            examples=[UpdateDatasetPermissionsPayload()],
        ),
    ) -> DatasetAssociationRoles:
        """Set permissions of the given history dataset to the given role ids."""
        update_payload = get_update_permission_payload(payload)
        return self.service.update_permissions(trans, dataset_id, update_payload)

    @router.get(
        "/api/histories/{history_id}/contents/{history_content_id}/extra_files",
        summary="Get the list of extra files/directories associated with a dataset.",
        tags=["histories"],
    )
    def extra_files_history(
        self,
        history_id: HistoryIDPathParam,
        history_content_id: HistoryDatasetIDPathParam,
        trans=DependsOnTrans,
    ) -> DatasetExtraFiles:
        return self.service.extra_files(trans, history_content_id)

    @router.get(
        "/api/datasets/{dataset_id}/extra_files",
        summary="Get the list of extra files/directories associated with a dataset.",
    )
    def extra_files(
        self,
        dataset_id: DatasetIDPathParam,
        trans=DependsOnTrans,
    ) -> DatasetExtraFiles:
        return self.service.extra_files(trans, dataset_id)

    @router.get(
        "/api/histories/{history_id}/contents/{history_content_id}/display",
        name="history_contents_display",
        summary="Displays (preview) or downloads dataset content.",
        tags=["histories"],
        response_class=StreamingResponse,
    )
    @router.head(
        "/api/histories/{history_id}/contents/{history_content_id}/display",
        name="history_contents_display",
        summary="Check if dataset content can be previewed or downloaded.",
        tags=["histories"],
    )
    def display_history_content(
        self,
        request: Request,
        history_content_id: HistoryDatasetIDPathParam,
        history_id: Optional[HistoryIDPathParam] = None,
        trans=DependsOnTrans,
        preview: bool = PreviewQueryParam,
        filename: Optional[str] = FilenameQueryParam,
        to_ext: Optional[str] = ToExtQueryParam,
        raw: bool = RawQueryParam,
        offset: Optional[int] = DisplayOffsetQueryParam,
        ck_size: Optional[int] = DisplayChunkSizeQueryParam,
    ):
        """Streams the dataset for download or the contents preview to be displayed in a browser."""
        return self._display(request, trans, history_content_id, preview, filename, to_ext, raw, offset, ck_size)

    @router.get(
        "/api/datasets/{history_content_id}/display",
        summary="Displays (preview) or downloads dataset content.",
        response_class=StreamingResponse,
    )
    @router.head(
        "/api/datasets/{history_content_id}/display",
        summary="Check if dataset content can be previewed or downloaded.",
    )
    def display(
        self,
        request: Request,
        history_content_id: HistoryDatasetIDPathParam,
        trans=DependsOnTrans,
        preview: bool = PreviewQueryParam,
        filename: Optional[str] = FilenameQueryParam,
        to_ext: Optional[str] = ToExtQueryParam,
        raw: bool = RawQueryParam,
        offset: Optional[int] = DisplayOffsetQueryParam,
        ck_size: Optional[int] = DisplayChunkSizeQueryParam,
    ):
        """Streams the dataset for download or the contents preview to be displayed in a browser."""
        return self._display(request, trans, history_content_id, preview, filename, to_ext, raw, offset, ck_size)

    def _display(
        self,
        request: Request,
        trans,
        history_content_id: DecodedDatabaseIdField,
        preview: bool,
        filename: Optional[str],
        to_ext: Optional[str],
        raw: bool,
        offset: Optional[int] = None,
        ck_size: Optional[int] = None,
    ):
        extra_params = get_query_parameters_from_request_excluding(
            request, {"preview", "filename", "to_ext", "raw", "dataset", "ck_size", "offset"}
        )
        display_data, headers = self.service.display(
            trans,
            history_content_id,
            preview=preview,
            filename=filename,
            to_ext=to_ext,
            raw=raw,
            offset=offset,
            ck_size=ck_size,
            **extra_params,
        )
        if isinstance(display_data, IOBase):
            file_name = getattr(display_data, "name", None)
            if file_name:
                return GalaxyFileResponse(file_name, headers=headers, method=request.method)
        elif isinstance(display_data, ZipstreamWrapper):
            return StreamingResponse(display_data.response(), headers=headers)
        elif isinstance(display_data, bytes):
            return StreamingResponse(BytesIO(display_data), headers=headers)
        elif isinstance(display_data, str):
            return StreamingResponse(content=StringIO(display_data), headers=headers)
        return StreamingResponse(display_data, headers=headers)

    @router.get(
        "/api/histories/{history_id}/contents/{history_content_id}/metadata_file",
        summary="Returns the metadata file associated with this history item.",
        name="get_metadata_file",
        tags=["histories"],
        operation_id="history_contents__get_metadata_file",
        response_class=GalaxyFileResponse,
    )
    def get_metadata_file_history_content(
        self,
        history_id: HistoryIDPathParam,
        history_content_id: HistoryDatasetIDPathParam,
        trans=DependsOnTrans,
        metadata_file: str = Query(
            ...,
            description="The name of the metadata file to retrieve.",
        ),
    ):
        return self._get_metadata_file(trans, history_content_id, metadata_file)

    @router.get(
        "/api/datasets/{history_content_id}/metadata_file",
        summary="Returns the metadata file associated with this history item.",
        response_class=GalaxyFileResponse,
        operation_id="datasets__get_metadata_file",
    )
    @router.head(
        "/api/datasets/{history_content_id}/metadata_file",
        summary="Check if metadata file can be downloaded.",
    )
    def get_metadata_file_datasets(
        self,
        history_content_id: HistoryDatasetIDPathParam,
        trans=DependsOnTrans,
        metadata_file: str = Query(
            ...,
            description="The name of the metadata file to retrieve.",
        ),
    ):
        return self._get_metadata_file(trans, history_content_id, metadata_file)

    def _get_metadata_file(
        self,
        trans,
        history_content_id: DecodedDatabaseIdField,
        metadata_file: str,
    ) -> GalaxyFileResponse:
        metadata_file_path, headers = self.service.get_metadata_file(trans, history_content_id, metadata_file)
        return GalaxyFileResponse(path=cast(str, metadata_file_path), headers=headers)

    @router.get(
        "/api/datasets/{dataset_id}",
        summary="Displays information about and/or content of a dataset.",
    )
    def show(
        self,
        request: Request,
        dataset_id: HistoryDatasetIDPathParam,
        trans=DependsOnTrans,
        hda_ldda: DatasetSourceType = Query(
            default=DatasetSourceType.hda,
            description=("The type of information about the dataset to be requested."),
        ),
        data_type: Optional[RequestDataType] = Query(
            default=None,
            description=(
                "The type of information about the dataset to be requested. "
                "Each of these values may require additional parameters in the request and "
                "may return different responses."
            ),
        ),
        limit: Annotated[
            Optional[int],
            Query(
                ge=1,
                le=MAX_LIMIT,
                description="Maximum number of items to return. Currently only applies to `data_type=raw_data` requests",
            ),
        ] = MAX_LIMIT,
        offset: Annotated[
            Optional[int],
            Query(
                ge=0,
                description="Starts at the beginning skip the first ( offset - 1 ) items and begin returning at the Nth item. Currently only applies to `data_type=raw_data` requests",
            ),
        ] = 0,
        serialization_params: SerializationParams = Depends(query_serialization_params),
    ):
        """
        **Note**: Due to the multipurpose nature of this endpoint, which can receive a wide variety of parameters
        and return different kinds of responses, the documentation here will be limited.
        To get more information please check the source code.
        """
        exclude_params = {"hda_ldda", "data_type", "limit", "offset"}
        exclude_params.update(SerializationParams.model_fields.keys())
        extra_params = get_query_parameters_from_request_excluding(request, exclude_params)

        return self.service.show(
            trans, dataset_id, hda_ldda, serialization_params, data_type, limit=limit, offset=offset, **extra_params
        )

    @router.get(
        "/api/datasets/{dataset_id}/content/{content_type}",
        summary="Retrieve information about the content of a dataset.",
    )
    def get_structured_content(
        self,
        request: Request,
        dataset_id: HistoryDatasetIDPathParam,
        trans=DependsOnTrans,
        content_type: DatasetContentType = DatasetContentType.data,
    ):
        content, headers = self.service.get_structured_content(trans, dataset_id, content_type, **request.query_params)
        return Response(content=content, headers=headers)

    @router.delete(
        "/api/datasets",
        summary="Deletes or purges a batch of datasets.",
    )
    def delete_batch(
        self,
        trans=DependsOnTrans,
        payload: DeleteDatasetBatchPayload = Body(...),
    ) -> DeleteDatasetBatchResult:
        """
        Deletes or purges a batch of datasets.
        **Warning**: only the ownership of the datasets (and upload state for HDAs) is checked,
        no other checks or restrictions are made.
        """
        return self.service.delete_batch(trans, payload)

    @router.put(
        "/api/datasets/{dataset_id}/hash",
        summary="Compute dataset hash for dataset and update model",
    )
    def compute_hash(
        self,
        dataset_id: HistoryDatasetIDPathParam,
        trans=DependsOnTrans,
        hda_ldda: DatasetSourceType = DatasetSourceQueryParam,
        payload: ComputeDatasetHashPayload = Body(...),
    ) -> AsyncTaskResultSummary:
        return self.service.compute_hash(trans, dataset_id, payload, hda_ldda=hda_ldda)

    @router.put(
        "/api/datasets/{dataset_id}/object_store_id",
        summary="Update an object store ID for a dataset you own.",
        operation_id="datasets__update_object_store_id",
    )
    def update_object_store_id(
        self,
        dataset_id: HistoryDatasetIDPathParam,
        trans=DependsOnTrans,
        payload: UpdateObjectStoreIdPayload = Body(...),
    ) -> None:
        self.service.update_object_store_id(trans, dataset_id, payload)
