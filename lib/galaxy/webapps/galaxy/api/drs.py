"""Implement a DRS server for Galaxy dataset objects (experimental)."""

import logging
from io import IOBase
from typing import cast

from fastapi import (
    Path,
    Request,
)
from starlette.responses import FileResponse

from galaxy.config import GalaxyAppConfiguration
from galaxy.exceptions import ObjectNotFound
from galaxy.managers.context import ProvidesHistoryContext
from galaxy.schema.drs import DrsObject
from galaxy.webapps.galaxy.services.datasets import DatasetsService
from galaxy.webapps.galaxy.services.ga4gh import build_service_info
from . import (
    depends,
    DependsOnTrans,
    Router,
)

log = logging.getLogger(__name__)
router = Router(tags=["drs"])
ObjectIDParam: str = Path(..., title="Object ID", description="The ID of the group")
AccessIDParam: str = Path(
    ..., title="Access ID", description="The access ID of the access method for objects, unused in Galaxy."
)

DRS_SERVICE_NAME = "Galaxy DRS API"
DRS_SERVICE_DESCRIPTION = "Serves Galaxy datasets according to the GA4GH DRS specification"


@router.cbv
class DrsApi:
    service: DatasetsService = depends(DatasetsService)
    config: GalaxyAppConfiguration = depends(GalaxyAppConfiguration)

    @router.get("/ga4gh/drs/v1/service-info", public=True)
    def service_info(self, request: Request):
        return build_service_info(
            config=self.config,
            request_url=str(request.url),
            artifact="drs",
            service_name=DRS_SERVICE_NAME,
            service_description=DRS_SERVICE_DESCRIPTION,
            artifact_version="1.2.0",
        )

    @router.get("/ga4gh/drs/v1/objects/{object_id}", public=True)
    @router.post("/ga4gh/drs/v1/objects/{object_id}", public=True)  # spec specifies both get and post should work.
    def get_object(
        self,
        request: Request,
        trans: ProvidesHistoryContext = DependsOnTrans,
        object_id: str = ObjectIDParam,
    ) -> DrsObject:
        return self.service.get_drs_object(trans, object_id, request_url=request.url)

    @router.get("/ga4gh/drs/v1/objects/{object_id}/access/{access_id}", public=True)
    @router.post("/ga4gh/drs/v1/objects/{object_id}/access/{access_id}", public=True)
    def get_access_url(
        self,
        request: Request,
        trans: ProvidesHistoryContext = DependsOnTrans,
        object_id: str = ObjectIDParam,
        access_id: str = AccessIDParam,
    ):
        raise ObjectNotFound("Access IDs are not implemented for this DRS server")

    @router.get(
        "/api/drs_download/{object_id}",
        public=True,
        response_class=FileResponse,
    )
    def download(self, trans: ProvidesHistoryContext = DependsOnTrans, object_id: str = ObjectIDParam):
        decoded_object_id, hda_ldda = self.service.drs_dataset_instance(object_id)
        display_data, headers = self.service.display(
            trans, decoded_object_id, hda_ldda=hda_ldda, filename=None, raw=True
        )
        data_io = cast(IOBase, display_data)
        return FileResponse(getattr(data_io, "name", "unnamed_file"), headers=headers)
