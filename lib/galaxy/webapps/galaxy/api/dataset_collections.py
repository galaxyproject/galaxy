from logging import getLogger
from typing import Optional

from fastapi import (
    Body,
    Path,
    Query,
)

from galaxy.managers.context import ProvidesHistoryContext
from galaxy.schema.fields import DecodedDatabaseIdField
from galaxy.schema.schema import (
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
from galaxy.webapps.galaxy.services.dataset_collections import (
    DatasetCollectionAttributesResult,
    DatasetCollectionContentElements,
    DatasetCollectionsService,
    SuitableConverters,
    UpdateCollectionAttributePayload,
)

log = getLogger(__name__)

router = Router(tags=["dataset collections"])

DatasetCollectionIdPathParam: DecodedDatabaseIdField = Path(
    ..., description="The encoded identifier of the dataset collection."
)


DatasetCollectionElementIdPathParam: DecodedDatabaseIdField = Path(
    ..., description="The encoded identifier of the dataset collection element."
)

InstanceTypeQueryParam: DatasetCollectionInstanceType = Query(
    default="history",
    description="The type of collection instance. Either `history` (default) or `library`.",
)


class FastAPIDatasetCollections:
    @router.post(
        "/api/dataset_collections",
        summary="Create a new dataset collection instance.",
    )
    def create(
        trans: ProvidesHistoryContext = DependsOnTrans,
        payload: CreateNewCollectionPayload = Body(...),
        service: DatasetCollectionsService = depends(DatasetCollectionsService),
    ) -> HDCADetailed:
        return service.create(trans, payload)

    @router.post(
        "/api/dataset_collections/{id}/copy",
        summary="Copy the given collection datasets to a new collection using a new `dbkey` attribute.",
    )
    def copy(
        trans: ProvidesHistoryContext = DependsOnTrans,
        id: DecodedDatabaseIdField = Path(..., description="The ID of the dataset collection to copy."),
        payload: UpdateCollectionAttributePayload = Body(...),
        service: DatasetCollectionsService = depends(DatasetCollectionsService),
    ):
        service.copy(trans, id, payload)

    @router.get(
        "/api/dataset_collections/{id}/attributes",
        summary="Returns `dbkey`/`extension` attributes for all the collection elements.",
    )
    def attributes(
        trans: ProvidesHistoryContext = DependsOnTrans,
        id: DecodedDatabaseIdField = DatasetCollectionIdPathParam,
        instance_type: DatasetCollectionInstanceType = InstanceTypeQueryParam,
        service: DatasetCollectionsService = depends(DatasetCollectionsService),
    ) -> DatasetCollectionAttributesResult:
        return service.attributes(trans, id, instance_type)

    @router.get(
        "/api/dataset_collections/{id}/suitable_converters",
        summary="Returns a list of applicable converters for all datatypes in the given collection.",
    )
    def suitable_converters(
        trans: ProvidesHistoryContext = DependsOnTrans,
        id: DecodedDatabaseIdField = DatasetCollectionIdPathParam,
        instance_type: DatasetCollectionInstanceType = InstanceTypeQueryParam,
        service: DatasetCollectionsService = depends(DatasetCollectionsService),
    ) -> SuitableConverters:
        return service.suitable_converters(trans, id, instance_type)

    @router.get(
        "/api/dataset_collections/{id}",
        summary="Returns detailed information about the given collection.",
    )
    def show(
        trans: ProvidesHistoryContext = DependsOnTrans,
        id: DecodedDatabaseIdField = DatasetCollectionIdPathParam,
        instance_type: DatasetCollectionInstanceType = InstanceTypeQueryParam,
        service: DatasetCollectionsService = depends(DatasetCollectionsService),
    ) -> HDCADetailed:
        return service.show(trans, id, instance_type)

    @router.get(
        "/api/dataset_collections/{hdca_id}/contents/{parent_id}",
        name="contents_dataset_collection",
        summary="Returns direct child contents of indicated dataset collection parent ID.",
    )
    def contents(
        trans: ProvidesHistoryContext = DependsOnTrans,
        hdca_id: DecodedDatabaseIdField = DatasetCollectionIdPathParam,
        parent_id: DecodedDatabaseIdField = Path(
            ...,
            description="Parent collection ID describing what collection the contents belongs to.",
        ),
        instance_type: DatasetCollectionInstanceType = InstanceTypeQueryParam,
        limit: Optional[int] = Query(
            default=None,
            description="The maximum number of content elements to return.",
        ),
        offset: Optional[int] = Query(
            default=None,
            description="The number of content elements that will be skipped before returning.",
        ),
        service: DatasetCollectionsService = depends(DatasetCollectionsService),
    ) -> DatasetCollectionContentElements:
        return service.contents(trans, hdca_id, parent_id, instance_type, limit, offset)

    @router.get("/api/dataset_collection_element/{dce_id}")
    def content(
        trans: ProvidesHistoryContext = DependsOnTrans,
        dce_id: DecodedDatabaseIdField = DatasetCollectionElementIdPathParam,
        service: DatasetCollectionsService = depends(DatasetCollectionsService),
    ) -> DCESummary:
        return service.dce_content(trans, dce_id)
