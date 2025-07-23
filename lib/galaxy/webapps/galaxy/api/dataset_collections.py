from logging import getLogger
from typing import Optional

from fastapi import (
    Body,
    Path,
    Query,
    Response,
    status,
)
from starlette.responses import StreamingResponse
from typing_extensions import Annotated

from galaxy.managers.context import ProvidesHistoryContext
from galaxy.model.dataset_collections.types.sample_sheet_workbook import (
    CreateWorkbookRequest,
    ParsedWorkbook,
    ParseWorkbook,
)
from galaxy.schema.fields import DecodedDatabaseIdField
from galaxy.schema.schema import (
    AnyHDCA,
    CreateNewCollectionPayload,
    DatasetCollectionInstanceType,
    DCESummary,
    HDCADetailed,
)
from galaxy.webapps.galaxy.api import (
    depends,
    DependsOnTrans,
    Router,
)
from galaxy.webapps.galaxy.api.common import (
    DatasetCollectionElementIdPathParam,
    HistoryHDCAIDPathParam,
    serve_workbook,
)
from galaxy.webapps.galaxy.services.dataset_collections import (
    CreateWorkbookForCollectionApi,
    DatasetCollectionAttributesResult,
    DatasetCollectionContentElements,
    DatasetCollectionsService,
    ParsedWorkbookForCollection,
    ParseWorkbookForCollectionApi,
    SuitableConverters,
    UpdateCollectionAttributePayload,
)

log = getLogger(__name__)

router = Router(tags=["dataset collections"])


InstanceTypeQueryParam: DatasetCollectionInstanceType = Query(
    default="history",
    description="The type of collection instance. Either `history` (default) or `library`.",
)

ViewTypeQueryParam: str = Query(
    default="element",
    description="The view of collection instance to return.",
)

Base64ColumnDefinitionsQueryParam: str = Query(
    ...,
    description="Base64 encoding of column definitions.",
)
Base64PrefixValuesQueryParam: str = Query(
    None,
    description="Prefix values for the seeding the workbook, base64 encoded.",
)
WorkbookFilenameQueryParam: Optional[str] = Query(
    None,
    description="Filename of the workbook download to generate",
)


@router.cbv
class FastAPIDatasetCollections:
    service: DatasetCollectionsService = depends(DatasetCollectionsService)

    @router.post(
        "/api/dataset_collections",
        summary="Create a new dataset collection instance.",
    )
    def create(
        self,
        trans: ProvidesHistoryContext = DependsOnTrans,
        payload: CreateNewCollectionPayload = Body(...),
    ) -> HDCADetailed:
        return self.service.create(trans, payload)

    @router.post(
        "/api/sample_sheet_workbook",
        summary="Create an XLSX workbook for a sample sheet definition.",
        response_class=StreamingResponse,
        operation_id="dataset_collections__workbook_download",
    )
    def create_workbook(
        self,
        trans: ProvidesHistoryContext = DependsOnTrans,
        filename: Optional[str] = WorkbookFilenameQueryParam,
        payload: CreateWorkbookRequest = Body(...),
    ):
        output = self.service.create_workbook(payload)
        return serve_workbook(output, filename)

    @router.post(
        "/api/sample_sheet_workbook/parse",
        summary="Parse an XLSX workbook for a sample sheet definition and supplied file contents.",
        operation_id="dataset_collections__workbook_parse",
    )
    def parse_workbook(
        self,
        trans: ProvidesHistoryContext = DependsOnTrans,
        payload: ParseWorkbook = Body(...),
    ) -> ParsedWorkbook:
        return self.service.parse_workbook(payload)

    @router.post(
        "/api/dataset_collections/{hdca_id}/sample_sheet_workbook",
        summary="Create an XLSX workbook for a sample sheet definition targeting an existing collection.",
        response_class=StreamingResponse,
        operation_id="dataset_collections__workbook_download_for_collection",
    )
    def create_workbook_for_collection(
        self,
        hdca_id: HistoryHDCAIDPathParam,
        trans: ProvidesHistoryContext = DependsOnTrans,
        filename: Optional[str] = WorkbookFilenameQueryParam,
        payload: CreateWorkbookForCollectionApi = Body(...),
    ):
        output = self.service.create_workbook_for_collection(trans, hdca_id, payload)
        return serve_workbook(output, filename)

    @router.post(
        "/api/dataset_collections/{hdca_id}/sample_sheet_workbook/parse",
        summary="Parse an XLSX workbook for a sample sheet definition and supplied file contents.",
        operation_id="dataset_collections__workbook_parse_for_collection",
    )
    def parse_workbook_for_collection(
        self,
        hdca_id: HistoryHDCAIDPathParam,
        trans: ProvidesHistoryContext = DependsOnTrans,
        payload: ParseWorkbookForCollectionApi = Body(...),
    ) -> ParsedWorkbookForCollection:
        return self.service.parse_workbook_for_collection(trans, hdca_id, payload)

    @router.post(
        "/api/dataset_collections/{hdca_id}/copy",
        summary="Copy the given collection datasets to a new collection using a new `dbkey` attribute.",
        status_code=status.HTTP_204_NO_CONTENT,
    )
    def copy(
        self,
        hdca_id: HistoryHDCAIDPathParam,
        trans: ProvidesHistoryContext = DependsOnTrans,
        payload: UpdateCollectionAttributePayload = Body(...),
    ):
        self.service.copy(trans, hdca_id, payload)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @router.get(
        "/api/dataset_collections/{hdca_id}/attributes",
        summary="Returns `dbkey`/`extension` attributes for all the collection elements.",
    )
    def attributes(
        self,
        hdca_id: HistoryHDCAIDPathParam,
        trans: ProvidesHistoryContext = DependsOnTrans,
        instance_type: DatasetCollectionInstanceType = InstanceTypeQueryParam,
    ) -> DatasetCollectionAttributesResult:
        return self.service.attributes(trans, hdca_id, instance_type)

    @router.get(
        "/api/dataset_collections/{hdca_id}/suitable_converters",
        summary="Returns a list of applicable converters for all datatypes in the given collection.",
    )
    def suitable_converters(
        self,
        hdca_id: HistoryHDCAIDPathParam,
        trans: ProvidesHistoryContext = DependsOnTrans,
        instance_type: DatasetCollectionInstanceType = InstanceTypeQueryParam,
    ) -> SuitableConverters:
        return self.service.suitable_converters(trans, hdca_id, instance_type)

    @router.get(
        "/api/dataset_collections/{hdca_id}",
        summary="Returns detailed information about the given collection.",
    )
    def show(
        self,
        hdca_id: HistoryHDCAIDPathParam,
        trans: ProvidesHistoryContext = DependsOnTrans,
        instance_type: DatasetCollectionInstanceType = InstanceTypeQueryParam,
        view: str = ViewTypeQueryParam,
    ) -> AnyHDCA:
        return self.service.show(trans, hdca_id, instance_type, view=view)

    @router.get(
        "/api/dataset_collections/{hdca_id}/contents/{parent_id}",
        name="contents_dataset_collection",
        summary="Returns direct child contents of indicated dataset collection parent ID.",
    )
    def contents(
        self,
        hdca_id: HistoryHDCAIDPathParam,
        parent_id: Annotated[
            DecodedDatabaseIdField,
            Path(
                ...,
                description="Parent collection ID describing what collection the contents belongs to.",
            ),
        ],
        trans: ProvidesHistoryContext = DependsOnTrans,
        instance_type: DatasetCollectionInstanceType = InstanceTypeQueryParam,
        limit: Optional[int] = Query(
            default=None,
            description="The maximum number of content elements to return.",
        ),
        offset: Optional[int] = Query(
            default=None,
            description="The number of content elements that will be skipped before returning.",
        ),
    ) -> DatasetCollectionContentElements:
        return self.service.contents(trans, hdca_id, parent_id, instance_type, limit, offset)

    @router.get("/api/dataset_collection_element/{dce_id}")
    def content(
        self,
        dce_id: DatasetCollectionElementIdPathParam,
        trans: ProvidesHistoryContext = DependsOnTrans,
    ) -> DCESummary:
        return self.service.dce_content(trans, dce_id)
