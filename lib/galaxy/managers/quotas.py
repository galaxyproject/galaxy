"""
Manager and Serializers for Quotas.

For more information about quotas: https://galaxyproject.org/admin/disk-quotas/
"""

from typing import List

from galaxy.managers.context import ProvidesUserContext
from galaxy.quota._schema import (
    CreateQuotaPayload,
    CreateQuotaResult,
    QuotaDetails,
    QuotaSummaryList,
    UpdateQuotaPayload,
)
from galaxy.schema.fields import EncodedDatabaseIdField


class QuotasManager:
    """Interface/service object shared by controllers for interacting with quotas."""

    def index(self, trans: ProvidesUserContext, deleted: bool = False) -> QuotaSummaryList:
        """Displays a collection (list) of quotas."""
        pass

    def show(self, trans: ProvidesUserContext, id: EncodedDatabaseIdField, deleted: bool = False) -> QuotaDetails:
        """Displays information about a quota."""
        pass

    def create(self, trans: ProvidesUserContext, payload: CreateQuotaPayload) -> CreateQuotaResult:
        """Creates a new quota."""
        pass

    def update(self, trans: ProvidesUserContext, id: EncodedDatabaseIdField, payload: UpdateQuotaPayload) -> List[str]:
        """Modifies a quota."""
        pass

    def delete(self, trans: ProvidesUserContext, id: EncodedDatabaseIdField) -> List[str]:
        """Marks a quota as deleted."""
        pass

    def undelete(self, trans: ProvidesUserContext, id: EncodedDatabaseIdField) -> List[str]:
        """Restores a previously deleted quota."""
        pass
