"""
API operations on Quota objects.
"""
import logging

from fastapi import Path
from fastapi.param_functions import Body

from galaxy.managers.context import ProvidesUserContext
from galaxy.quota._schema import (
    CreateQuotaParams,
    CreateQuotaResult,
    DeleteQuotaPayload,
    QuotaDetails,
    QuotaSummaryList,
    UpdateQuotaParams,
)
from galaxy.schema.fields import DecodedDatabaseIdField
from galaxy.webapps.galaxy.api import (
    depends,
    DependsOnTrans,
    Router,
)
from galaxy.webapps.galaxy.services.quotas import QuotasService

log = logging.getLogger(__name__)


router = Router(tags=["quotas"])


QuotaIdPathParam: DecodedDatabaseIdField = Path(
    ..., title="Quota ID", description="The encoded identifier of the Quota."  # Required
)


class FastAPIQuota:
    @router.get(
        "/api/quotas",
        summary="Displays a list with information of quotas that are currently active.",
        require_admin=True,
    )
    def index(
        trans: ProvidesUserContext = DependsOnTrans,
        service: QuotasService = depends(QuotasService),
    ) -> QuotaSummaryList:
        """Displays a list with information of quotas that are currently active."""
        return service.index(trans)

    @router.get(
        "/api/quotas/deleted",
        summary="Displays a list with information of quotas that have been deleted.",
        require_admin=True,
    )
    def index_deleted(
        trans: ProvidesUserContext = DependsOnTrans,
        service: QuotasService = depends(QuotasService),
    ) -> QuotaSummaryList:
        """Displays a list with information of quotas that have been deleted."""
        return service.index(trans, deleted=True)

    @router.get(
        "/api/quotas/{id}",
        name="quota",
        summary="Displays details on a particular active quota.",
        require_admin=True,
    )
    def show(
        trans: ProvidesUserContext = DependsOnTrans,
        id: DecodedDatabaseIdField = QuotaIdPathParam,
        service: QuotasService = depends(QuotasService),
    ) -> QuotaDetails:
        """Displays details on a particular active quota."""
        return service.show(trans, id)

    @router.get(
        "/api/quotas/deleted/{id}",
        name="deleted_quota",
        summary="Displays details on a particular quota that has been deleted.",
        require_admin=True,
    )
    def show_deleted(
        trans: ProvidesUserContext = DependsOnTrans,
        id: DecodedDatabaseIdField = QuotaIdPathParam,
        service: QuotasService = depends(QuotasService),
    ) -> QuotaDetails:
        """Displays details on a particular quota that has been deleted."""
        return service.show(trans, id, deleted=True)

    @router.post(
        "/api/quotas",
        summary="Creates a new quota.",
        require_admin=True,
    )
    def create(
        payload: CreateQuotaParams,
        trans: ProvidesUserContext = DependsOnTrans,
        service: QuotasService = depends(QuotasService),
    ) -> CreateQuotaResult:
        """Creates a new quota."""
        return service.create(trans, payload)

    @router.put(
        "/api/quotas/{id}",
        summary="Updates an existing quota.",
        require_admin=True,
    )
    def update(
        payload: UpdateQuotaParams,
        id: DecodedDatabaseIdField = QuotaIdPathParam,
        trans: ProvidesUserContext = DependsOnTrans,
        service: QuotasService = depends(QuotasService),
    ) -> str:
        """Updates an existing quota."""
        return service.update(trans, id, payload)

    @router.delete(
        "/api/quotas/{id}",
        summary="Deletes an existing quota.",
        require_admin=True,
    )
    def delete(
        id: DecodedDatabaseIdField = QuotaIdPathParam,
        trans: ProvidesUserContext = DependsOnTrans,
        payload: DeleteQuotaPayload = Body(None),  # Optional
        service: QuotasService = depends(QuotasService),
    ) -> str:
        """Deletes an existing quota."""
        return service.delete(trans, id, payload)

    @router.post(
        "/api/quotas/{id}/purge",
        summary="Purges a previously deleted quota.",
        require_admin=True,
    )
    def purge(
        id: DecodedDatabaseIdField = QuotaIdPathParam,
        trans: ProvidesUserContext = DependsOnTrans,
        service: QuotasService = depends(QuotasService),
    ) -> str:
        return service.purge(trans, id)

    @router.post(
        "/api/quotas/deleted/{id}/undelete",
        summary="Restores a previously deleted quota.",
        require_admin=True,
    )
    def undelete(
        id: DecodedDatabaseIdField = QuotaIdPathParam,
        trans: ProvidesUserContext = DependsOnTrans,
        service: QuotasService = depends(QuotasService),
    ) -> str:
        """Restores a previously deleted quota."""
        return service.undelete(trans, id)
