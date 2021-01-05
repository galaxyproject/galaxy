from typing import List

from fastapi import Depends, Path
from fastapi.routing import APIRouter
from fastapi_utils.cbv import cbv


from galaxy.managers.licenses import (
    LicenseModel,
    LicensesManager
)
from galaxy.web import expose_api_anonymous_and_sessionless
from galaxy.webapps.base.controller import BaseAPIController

router = APIRouter(tags=['licenses'])

LicenseIdPath = Path(..., title="The SPDX identifier of the license", description="SPDX identifier", example="MIT")


def get_licenses_manager() -> LicensesManager:
    return LicensesManager()


@cbv(router)
class FastAPILicenses:
    licenses_manager: LicensesManager = Depends(get_licenses_manager)

    @router.get('/api/licenses',
        summary="Lists all available SPDX licenses",
        response_model=List[LicenseModel])
    async def index(self) -> List[LicenseModel]:
        """Returns the list with all the available SPDX licenses."""
        return self.licenses_manager.get_licenses()

    @router.get('/api/licenses/{id}',
        summary="Gets the SPDX license with the matching short identifier",
        response_model=LicenseModel)
    async def get(self, id: str = LicenseIdPath) -> LicenseModel:
        """Returns the license with the matching SPDX short identifier."""
        return self.licenses_manager.get_license_by_id(id)


class LicensesController(BaseAPIController):

    def __init__(self, app):
        self.licenses_manager = LicensesManager()

    @expose_api_anonymous_and_sessionless
    def index(self, trans, **kwd):
        """
        GET /api/licenses

        Return an index of known licenses.
        """
        return self.licenses_manager.index()

    @expose_api_anonymous_and_sessionless
    def get(self, trans, id, **kwd):
        """
        GET /api/licenses/<license_id>

        Return license metadata by URI or SPDX id.
        """
        license_id = id
        return self.licenses_manager.get(license_id)
