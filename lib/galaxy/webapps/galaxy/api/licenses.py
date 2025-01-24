from typing import List

from fastapi import Path

from galaxy.managers.licenses import (
    LicenseMetadataModel,
    LicensesManager,
)
from . import (
    depends,
    Router,
)

router = Router(tags=["licenses"])

LicenseIdPath: str = Path(
    ...,  # Mark this Path parameter as required
    title="SPDX license short ID",
    description="The [SPDX license short identifier](https://spdx.github.io/spdx-spec/appendix-I-SPDX-license-list/)",
    examples=["Apache-2.0"],
)


@router.cbv
class FastAPILicenses:
    licenses_manager: LicensesManager = depends(LicensesManager)

    @router.get(
        "/api/licenses",
        public=True,
        summary="Lists all available SPDX licenses",
        response_description="List of SPDX licenses",
    )
    async def index(self) -> List[LicenseMetadataModel]:
        """Returns an index with all the available [SPDX licenses](https://spdx.org/licenses/)."""
        return self.licenses_manager.get_licenses()

    @router.get(
        "/api/licenses/{id}",
        public=True,
        summary="Gets the SPDX license metadata associated with the short identifier",
        response_description="SPDX license metadata",
    )
    async def get(self, id=LicenseIdPath) -> LicenseMetadataModel:
        """Returns the license metadata associated with the given
        [SPDX license short ID](https://spdx.github.io/spdx-spec/appendix-I-SPDX-license-list/)."""
        return self.licenses_manager.get_license_by_id(id)
