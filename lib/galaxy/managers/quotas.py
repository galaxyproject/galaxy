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

    # TODO refactor move here code from lib/galaxy/webapps/galaxy/api/quotas.py::QuotaAPIController
    def index(self, trans: ProvidesUserContext, deleted: bool = False) -> QuotaSummaryList:
        """Displays a collection (list) of quotas."""
        raise NotImplementedError

    def show(self, trans: ProvidesUserContext, id: EncodedDatabaseIdField, deleted: bool = False) -> QuotaDetails:
        """Displays information about a quota."""
        raise NotImplementedError

    def create(self, trans: ProvidesUserContext, payload: CreateQuotaPayload) -> CreateQuotaResult:
        """Creates a new quota."""
        raise NotImplementedError

    def update(self, trans: ProvidesUserContext, id: EncodedDatabaseIdField, payload: UpdateQuotaPayload) -> List[str]:
        """Modifies a quota."""
        raise NotImplementedError

    def delete(self, trans: ProvidesUserContext, id: EncodedDatabaseIdField) -> List[str]:
        """Marks a quota as deleted."""
        raise NotImplementedError

    def undelete(self, trans: ProvidesUserContext, id: EncodedDatabaseIdField) -> List[str]:
        """Restores a previously deleted quota."""
        raise NotImplementedError


class QuotaManager:

    # TODO: refactor move here code from lib/galaxy/actions/admin.py::AdminActions
    def create_quota(self, params, decode_id=None):
        raise NotImplementedError

    def rename_quota(self, quota, params):
        raise NotImplementedError

    def manage_users_and_groups_for_quota(self, quota, params, decode_id=None):
        raise NotImplementedError

    def edit_quota(self, quota, params):
        raise NotImplementedError

    def set_quota_default(self, quota, params):
        raise NotImplementedError

    def unset_quota_default(self, quota, params=None):
        raise NotImplementedError

    def delete_quota(self, quota, params=None):
        raise NotImplementedError

    def undelete_quota(self, quota, params=None):
        raise NotImplementedError

    def purge_quota(self, quota, params=None):
        raise NotImplementedError

    # TODO: refactor move here code from lib/galaxy/webapps/base/controller.py::UsesQuotaMixin
    def get_quota(self, trans, id, check_ownership=False, check_accessible=False, deleted=None):
        raise NotImplementedError
