from logging import getLogger
from typing import Optional

from fastapi import (
    Body,
    Path,
    Query,
    Response,
    status,
)
from typing_extensions import Annotated

from galaxy.managers.context import ProvidesHistoryContext
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
)
from galaxy.webapps.galaxy.services.dataset_collections import (
    DatasetCollectionAttributesResult,
    DatasetCollectionContentElements,
    DatasetCollectionsService,
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
