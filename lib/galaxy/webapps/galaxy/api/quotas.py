"""
API operations on Quota objects.
"""
import logging

from fastapi import Path

from galaxy import (
    util,
    web,
)
from galaxy.managers.context import ProvidesUserContext
from galaxy.managers.quotas import QuotasManager
from galaxy.quota._schema import (
    CreateQuotaParams,
    DeleteQuotaPayload,
    UpdateQuotaParams,
)
from galaxy.schema.fields import EncodedDatabaseIdField
from . import (
    AdminUserRequired,
    BaseGalaxyAPIController,
    depends,
    DependsOnTrans,
    Router,
)

log = logging.getLogger(__name__)


# TODO: This FastAPI router is disabled.
_router = Router(tags=['quotas'])


QuotaIdPathParam: EncodedDatabaseIdField = Path(
    ...,  # Required
    title="Quota ID",
    description="The encoded indentifier of the Quota."
)


@_router.cbv
class FastAPITags:
    manager: QuotasManager = depends(QuotasManager)

    @_router.get(
        '/api/quotas',
        summary="Displays a list with information of quotas that are currently active.",
        dependencies=[AdminUserRequired],
    )
    def index(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
    ):
        """Displays a list with information of quotas that are currently active."""
        self.manager.index(trans)

    @_router.get(
        '/api/quotas/deleted',
        summary="Displays a list with information of quotas that have been deleted.",
        dependencies=[AdminUserRequired],
    )
    def index_deleted(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
    ):
        """Displays a list with information of quotas that have been deleted."""
        self.manager.index(trans, deleted=True)

    @_router.get(
        '/api/quotas/{id}',
        summary="Displays details on a particular active quota.",
        dependencies=[AdminUserRequired],
    )
    def show(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        id: EncodedDatabaseIdField = QuotaIdPathParam
    ):
        """Displays details on a particular active quota."""
        self.manager.show(trans, id)

    @_router.get(
        '/api/quotas/deleted/{id}',
        summary="Displays details on a particular quota that has been deleted.",
        dependencies=[AdminUserRequired],
    )
    def show_deleted(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        id: EncodedDatabaseIdField = QuotaIdPathParam,
    ):
        """Displays details on a particular quota that has been deleted."""
        self.manager.show(trans, id, deleted=True)

    @_router.post(
        '/api/quotas',
        summary="Creates a new quota.",
        dependencies=[AdminUserRequired],
    )
    def create(
        self,
        payload: CreateQuotaParams,
        trans: ProvidesUserContext = DependsOnTrans,
    ):
        """Creates a new quota."""
        self.manager.create(trans, payload)

    @_router.put(
        '/api/quotas/{id}',
        summary="Updates an existing quota.",
        dependencies=[AdminUserRequired],
    )
    def update(
        self,
        payload: UpdateQuotaParams,
        id: EncodedDatabaseIdField = QuotaIdPathParam,
        trans: ProvidesUserContext = DependsOnTrans,
    ):
        """Updates an existing quota."""
        self.manager.update(trans, id, payload)

    @_router.delete(
        '/api/quotas/{id}',
        summary="Deletes an existing quota.",
        dependencies=[AdminUserRequired],
    )
    def delete(
        self,
        payload: DeleteQuotaPayload,
        id: EncodedDatabaseIdField = QuotaIdPathParam,
        trans: ProvidesUserContext = DependsOnTrans,
    ):
        """Deletes an existing quota."""
        self.manager.delete(trans, id, payload)

    @_router.post(
        '/api/quotas/deleted/{id}/undelete',
        summary="Restores a previously deleted quota.",
        dependencies=[AdminUserRequired],
    )
    def undelete(
        self,
        id: EncodedDatabaseIdField = QuotaIdPathParam,
        trans: ProvidesUserContext = DependsOnTrans,
    ):
        """Restores a previously deleted quota."""
        self.manager.undelete(trans, id)


class QuotaAPIController(BaseGalaxyAPIController):

    manager: QuotasManager = depends(QuotasManager)

    @web.require_admin
    @web.expose_api
    def index(self, trans, deleted='False', **kwd):
        """
        GET /api/quotas
        GET /api/quotas/deleted
        Displays a collection (list) of quotas.
        """
        deleted = util.string_as_bool(deleted)
        return self.manager.index(trans, deleted)

    @web.require_admin
    @web.expose_api
    def show(self, trans, id, deleted='False', **kwd):
        """
        GET /api/quotas/{encoded_quota_id}
        GET /api/quotas/deleted/{encoded_quota_id}
        Displays information about a quota.
        """
        deleted = util.string_as_bool(deleted)
        return self.manager.show(trans, id, deleted)

    @web.require_admin
    @web.expose_api
    def create(self, trans, payload, **kwd):
        """
        POST /api/quotas
        Creates a new quota.
        """
        return self.manager.create(trans, payload)

    @web.require_admin
    @web.expose_api
    def update(self, trans, id, payload, **kwd):
        """
        PUT /api/quotas/{encoded_quota_id}
        Modifies a quota.
        """
        return self.manager.update(trans, id, payload)

    @web.require_admin
    @web.expose_api
    def delete(self, trans, id, **kwd):
        """
        DELETE /api/quotas/{encoded_quota_id}
        Deletes a quota
        """
        # a request body is optional here
        payload = DeleteQuotaPayload(**kwd.get('payload', {}))
        return self.manager.delete(trans, id, payload)

    @web.require_admin
    @web.expose_api
    def undelete(self, trans, id, **kwd):
        """
        POST /api/quotas/deleted/{encoded_quota_id}/undelete
        Undeletes a quota
        """
        return self.manager.undelete(trans, id)
