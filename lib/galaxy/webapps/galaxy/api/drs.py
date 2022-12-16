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
from galaxy.schema.drs import (
    DrsObject,
    Service,
    ServiceOrganization,
    ServiceType,
)
from galaxy.schema.fields import DecodedDatabaseIdField
from galaxy.version import VERSION
from galaxy.webapps.galaxy.services.datasets import DatasetsService
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

    @router.get("/ga4gh/drs/v1/service-info")
    def service_info(self, request: Request) -> Service:
        components = request.url.components
        hostname = components.hostname
        assert hostname
        default_organization_id = ".".join(reversed(hostname.split(".")))
        config = self.config
        organization_id = config.ga4gh_service_id or default_organization_id
        organization_name = config.ga4gh_service_organization_name or organization_id
        organization_url = config.ga4gh_service_organization_url or f"{components.scheme}://{components.netloc}"

        organization = ServiceOrganization(
            url=organization_url,
            name=organization_name,
        )
        service_type = ServiceType(
            group="org.ga4gh",
            artifact="drs",
            version="1.2.0",
        )
        environment = config.ga4gh_service_environment
        extra_kwds = {}
        if environment:
            extra_kwds["environment"] = environment
        return Service(
            id=organization_id + ".drs",
            name=DRS_SERVICE_NAME,
            description=DRS_SERVICE_DESCRIPTION,
            organization=organization,
            type=service_type,
            version=VERSION,
            **extra_kwds,
        )

    @router.get("/ga4gh/drs/v1/objects/{object_id}")
    @router.post("/ga4gh/drs/v1/objects/{object_id}")  # spec specifies both get and post should work.
    def get_object(
        self,
        request: Request,
        trans: ProvidesHistoryContext = DependsOnTrans,
        object_id: str = ObjectIDParam,
    ) -> DrsObject:
        return self.service.get_drs_object(trans, object_id, request_url=request.url)

    @router.get("/ga4gh/drs/v1/objects/{object_id}/access/{access_id}")
    @router.post("/ga4gh/drs/v1/objects/{object_id}/access/{access_id}")
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
        response_class=FileResponse,
    )
    def download(self, trans: ProvidesHistoryContext = DependsOnTrans, object_id: str = ObjectIDParam):
        decoded_object_id, hda_ldda = self.service.drs_dataset_instance(object_id)
        display_data, headers = self.service.display(
            trans, DecodedDatabaseIdField(decoded_object_id), hda_ldda=hda_ldda, filename=None, raw=True
        )
        data_io = cast(IOBase, display_data)
        return FileResponse(getattr(data_io, "name", "unnamed_file"), headers=headers)
