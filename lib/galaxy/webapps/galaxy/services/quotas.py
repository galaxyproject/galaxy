import logging
from typing import Optional

from sqlalchemy import (
    false,
    select,
    true,
)

from galaxy import util
from galaxy.managers.context import ProvidesUserContext
from galaxy.managers.groups import get_group_by_name
from galaxy.managers.quotas import QuotaManager
from galaxy.model import Quota
from galaxy.model.db.user import get_user_by_email
from galaxy.model.scoped_session import galaxy_scoped_session
from galaxy.quota._schema import (
    CreateQuotaParams,
    CreateQuotaResult,
    DefaultQuotaValues,
    DeleteQuotaPayload,
    QuotaDetails,
    QuotaSummaryList,
    UpdateQuotaParams,
)
from galaxy.schema.fields import (
    DecodedDatabaseIdField,
    Security,
)
from galaxy.security.idencoding import IdEncodingHelper
from galaxy.web import url_for
from galaxy.webapps.galaxy.services.base import ServiceBase

log = logging.getLogger(__name__)


class QuotasService(ServiceBase):
    """Interface/service object shared by controllers for interacting with quotas."""

    def __init__(self, security: IdEncodingHelper, quota_manager: QuotaManager):
        super().__init__(security)
        self.quota_manager = quota_manager

    def index(self, trans: ProvidesUserContext, deleted: bool = False) -> QuotaSummaryList:
        """Displays a list of quotas."""
        rval = []
        if deleted:
            route = "deleted_quota"
            quotas = get_quotas(trans.sa_session, deleted=True)
        else:
            route = "quota"
            quotas = get_quotas(trans.sa_session, deleted=False)
        for quota in quotas:
            item = quota.to_dict()
            encoded_id = Security.security.encode_id(quota.id)
            item["url"] = url_for(route, id=encoded_id)
            rval.append(item)
        return QuotaSummaryList(root=rval)

    def show(self, trans: ProvidesUserContext, id: DecodedDatabaseIdField, deleted: bool = False) -> QuotaDetails:
        """Displays information about a quota."""
        quota = self.quota_manager.get_quota(trans, id, deleted=deleted)
        rval = quota.to_dict(view="element", value_mapper={"total_disk_usage": float})
        return QuotaDetails(**rval)

    def create(self, trans: ProvidesUserContext, params: CreateQuotaParams) -> CreateQuotaResult:
        """Creates a new quota."""
        payload = params.model_dump()
        self.validate_in_users_and_groups(trans, payload)
        quota, message = self.quota_manager.create_quota(payload)
        item = quota.to_dict()
        item["url"] = url_for("quota", id=Security.security.encode_id(quota.id))
        item["message"] = message
        return CreateQuotaResult(**item)

    def update(self, trans: ProvidesUserContext, id: DecodedDatabaseIdField, params: UpdateQuotaParams) -> str:
        """Modifies a quota."""
        payload = params.model_dump()
        self.validate_in_users_and_groups(trans, payload)
        quota = self.quota_manager.get_quota(trans, id, deleted=False)

        params = UpdateQuotaParams(**payload)
        # FIXME: Doing it this way makes the update non-atomic if a method fails after an earlier one has succeeded.
        methods = []
        if params.name or params.description:
            methods.append(self.quota_manager.rename_quota)
        if params.amount:
            methods.append(self.quota_manager.edit_quota)
        if params.default == DefaultQuotaValues.NO:
            methods.append(self.quota_manager.unset_quota_default)
        elif params.default:
            methods.append(self.quota_manager.set_quota_default)
        if params.in_users or params.in_groups:
            methods.append(self.quota_manager.manage_users_and_groups_for_quota)

        messages = []
        for method in methods:
            message = method(quota, params)
            if message:
                messages.append(message)
        return "; ".join(messages)

    def delete(
        self, trans: ProvidesUserContext, id: DecodedDatabaseIdField, payload: Optional[DeleteQuotaPayload] = None
    ) -> str:
        """Marks a quota as deleted."""
        quota = self.quota_manager.get_quota(
            trans, id, deleted=False
        )  # deleted quotas are not technically members of this collection
        message = self.quota_manager.delete_quota(quota)
        if payload and payload.purge:
            message += self.quota_manager.purge_quota(quota)
        return message

    def purge(self, trans: ProvidesUserContext, id: DecodedDatabaseIdField) -> str:
        """Purges a previously deleted quota."""
        quota = self.quota_manager.get_quota(trans, id, deleted=True)
        return self.quota_manager.purge_quota(quota)

    def undelete(self, trans: ProvidesUserContext, id: DecodedDatabaseIdField) -> str:
        """Restores a previously deleted quota."""
        quota = self.quota_manager.get_quota(trans, id, deleted=True)
        return self.quota_manager.undelete_quota(quota)

    def validate_in_users_and_groups(self, trans, payload):
        """
        For convenience, in_users and in_groups can be encoded IDs or emails/group names in the API.
        """

        def get_user_id(item):
            try:
                return trans.security.decode_id(item)
            except Exception:
                return get_user_by_email(trans.sa_session, item).id

        def get_group_id(item):
            try:
                return trans.security.decode_id(item)
            except Exception:
                return get_group_by_name(trans.sa_session, item).id

        new_in_users = []
        new_in_groups = []
        invalid = []
        for item in util.listify(payload.get("in_users", [])):
            try:
                new_in_users.append(get_user_id(item))
            except Exception:
                invalid.append(item)
        for item in util.listify(payload.get("in_groups", [])):
            try:
                new_in_groups.append(get_group_id(item))
            except Exception:
                invalid.append(item)
        if invalid:
            msg = (
                f"The following value(s) for associated users and/or groups could not be parsed: {', '.join(invalid)}."
            )
            msg += "  Valid values are email addresses of users, names of groups, or IDs of both."
            raise Exception(msg)
        payload["in_users"] = list(map(str, new_in_users))
        payload["in_groups"] = list(map(str, new_in_groups))


def get_quotas(session: galaxy_scoped_session, deleted: bool = False):
    is_deleted = true() if deleted else false()
    stmt = select(Quota).where(Quota.deleted == is_deleted)
    return session.scalars(stmt)
