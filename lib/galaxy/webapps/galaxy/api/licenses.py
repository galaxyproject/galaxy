from typing import List

from fastapi import (
    Depends,
    Path
)
from fastapi_utils.cbv import cbv
from fastapi_utils.inferring_router import InferringRouter as APIRouter

from galaxy.managers.licenses import (
    LicenseMetadataModel,
    LicensesManager
)
from galaxy.web import expose_api_anonymous_and_sessionless
from galaxy.webapps.base.controller import BaseAPIController

router = APIRouter(tags=['licenses'])

LicenseIdPath: str = Path(
    ...,  # Mark this Path parameter as required
    title="SPDX license short ID",
    description="The [SPDX license short identifier](https://spdx.github.io/spdx-spec/appendix-I-SPDX-license-list/)",
    example="Apache-2.0"
)


def get_licenses_manager() -> LicensesManager:
    return LicensesManager()


@cbv(router)
class FastAPILicenses:
    licenses_manager: LicensesManager = Depends(get_licenses_manager)

    @router.get('/api/licenses',
        summary="Lists all available SPDX licenses",
        response_description="List of SPDX licenses")
    async def index(self) -> List[LicenseMetadataModel]:
        """Returns an index with all the available [SPDX licenses](https://spdx.org/licenses/)."""
        return self.licenses_manager.get_licenses()

    @router.get('/api/licenses/{id}',
        summary="Gets the SPDX license metadata associated with the short identifier",
        response_description="SPDX license metadata")
    async def get(self, id=LicenseIdPath) -> LicenseMetadataModel:
        """Returns the license metadata associated with the given
        [SPDX license short ID](https://spdx.github.io/spdx-spec/appendix-I-SPDX-license-list/)."""
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
        return self.licenses_manager.get_license_by_id(license_id)
