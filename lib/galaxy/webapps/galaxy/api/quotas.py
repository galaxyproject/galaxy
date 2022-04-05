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
from galaxy.schema.fields import EncodedDatabaseIdField
from galaxy.webapps.galaxy.services.quotas import QuotasService
from . import (
    depends,
    DependsOnTrans,
    Router,
)

log = logging.getLogger(__name__)


router = Router(tags=["quotas"])


QuotaIdPathParam: EncodedDatabaseIdField = Path(
    ..., title="Quota ID", description="The encoded identifier of the Quota."  # Required
)


@router.cbv
class FastAPIQuota:
    service: QuotasService = depends(QuotasService)

    @router.get(
        "/api/quotas",
        summary="Displays a list with information of quotas that are currently active.",
        require_admin=True,
    )
    def index(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
    ) -> QuotaSummaryList:
        """Displays a list with information of quotas that are currently active."""
        return self.service.index(trans)

    @router.get(
        "/api/quotas/deleted",
        summary="Displays a list with information of quotas that have been deleted.",
        require_admin=True,
    )
    def index_deleted(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
    ) -> QuotaSummaryList:
        """Displays a list with information of quotas that have been deleted."""
        return self.service.index(trans, deleted=True)

    @router.get(
        "/api/quotas/{id}",
        summary="Displays details on a particular active quota.",
        require_admin=True,
    )
    def show(
        self, trans: ProvidesUserContext = DependsOnTrans, id: EncodedDatabaseIdField = QuotaIdPathParam
    ) -> QuotaDetails:
        """Displays details on a particular active quota."""
        return self.service.show(trans, id)

    @router.get(
        "/api/quotas/deleted/{id}",
        summary="Displays details on a particular quota that has been deleted.",
        require_admin=True,
    )
    def show_deleted(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        id: EncodedDatabaseIdField = QuotaIdPathParam,
    ) -> QuotaDetails:
        """Displays details on a particular quota that has been deleted."""
        return self.service.show(trans, id, deleted=True)

    @router.post(
        "/api/quotas",
        summary="Creates a new quota.",
        require_admin=True,
    )
    def create(
        self,
        payload: CreateQuotaParams,
        trans: ProvidesUserContext = DependsOnTrans,
    ) -> CreateQuotaResult:
        """Creates a new quota."""
        return self.service.create(trans, payload)

    @router.put(
        "/api/quotas/{id}",
        summary="Updates an existing quota.",
        require_admin=True,
    )
    def update(
        self,
        payload: UpdateQuotaParams,
        id: EncodedDatabaseIdField = QuotaIdPathParam,
        trans: ProvidesUserContext = DependsOnTrans,
    ) -> str:
        """Updates an existing quota."""
        return self.service.update(trans, id, payload)

    @router.delete(
        "/api/quotas/{id}",
        summary="Deletes an existing quota.",
        require_admin=True,
    )
    def delete(
        self,
        id: EncodedDatabaseIdField = QuotaIdPathParam,
        trans: ProvidesUserContext = DependsOnTrans,
        payload: DeleteQuotaPayload = Body(None),  # Optional
    ) -> str:
        """Deletes an existing quota."""
        return self.service.delete(trans, id, payload)

    @router.post(
        "/api/quotas/deleted/{id}/undelete",
        summary="Restores a previously deleted quota.",
        require_admin=True,
    )
    def undelete(
        self,
        id: EncodedDatabaseIdField = QuotaIdPathParam,
        trans: ProvidesUserContext = DependsOnTrans,
    ) -> str:
        """Restores a previously deleted quota."""
        return self.service.undelete(trans, id)
