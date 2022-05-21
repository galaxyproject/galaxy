import logging
from typing import Optional

from sqlalchemy import (
    false,
    true,
)

from galaxy import (
    model,
    util,
)
from galaxy.managers.context import ProvidesUserContext
from galaxy.managers.quotas import QuotaManager
from galaxy.quota._schema import (
    CreateQuotaParams,
    CreateQuotaResult,
    DefaultQuotaValues,
    DeleteQuotaPayload,
    QuotaDetails,
    QuotaSummaryList,
    UpdateQuotaParams,
)
from galaxy.schema.fields import EncodedDatabaseIdField
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
        """Displays a collection (list) of quotas."""
        rval = []
        query = trans.sa_session.query(model.Quota)
        if deleted:
            route = "deleted_quota"
            query = query.filter(model.Quota.deleted == true())
        else:
            route = "quota"
            query = query.filter(model.Quota.deleted == false())
        for quota in query:
            item = quota.to_dict(value_mapper={"id": trans.security.encode_id})
            encoded_id = trans.security.encode_id(quota.id)
            item["url"] = self._url_for(route, id=encoded_id)
            rval.append(item)
        return QuotaSummaryList.parse_obj(rval)

    def show(self, trans: ProvidesUserContext, id: EncodedDatabaseIdField, deleted: bool = False) -> QuotaDetails:
        """Displays information about a quota."""
        quota = self.quota_manager.get_quota(trans, id, deleted=deleted)
        rval = quota.to_dict(view="element", value_mapper={"id": trans.security.encode_id, "total_disk_usage": float})
        return QuotaDetails.parse_obj(rval)

    def create(self, trans: ProvidesUserContext, params: CreateQuotaParams) -> CreateQuotaResult:
        """Creates a new quota."""
        payload = params.dict()
        self.validate_in_users_and_groups(trans, payload)
        quota, message = self.quota_manager.create_quota(payload)
        item = quota.to_dict(value_mapper={"id": trans.security.encode_id})
        item["url"] = self._url_for("quota", id=trans.security.encode_id(quota.id))
        item["message"] = message
        return CreateQuotaResult.parse_obj(item)

    def update(self, trans: ProvidesUserContext, id: EncodedDatabaseIdField, params: UpdateQuotaParams) -> str:
        """Modifies a quota."""
        payload = params.dict()
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
            messages.append(message)
        return "; ".join(messages)

    def delete(
        self, trans: ProvidesUserContext, id: EncodedDatabaseIdField, payload: Optional[DeleteQuotaPayload] = None
    ) -> str:
        """Marks a quota as deleted."""
        quota = self.quota_manager.get_quota(
            trans, id, deleted=False
        )  # deleted quotas are not technically members of this collection
        message = self.quota_manager.delete_quota(quota)
        if payload and payload.purge:
            message += self.quota_manager.purge_quota(quota)
        return message

    def undelete(self, trans: ProvidesUserContext, id: EncodedDatabaseIdField) -> str:
        """Restores a previously deleted quota."""
        quota = self.quota_manager.get_quota(trans, id, deleted=True)
        return self.quota_manager.undelete_quota(quota)

    def validate_in_users_and_groups(self, trans, payload):
        """
        For convenience, in_users and in_groups can be encoded IDs or emails/group names in the API.
        """

        def get_id(item, model_class, column):
            try:
                return trans.security.decode_id(item)
            except Exception:
                pass  # maybe an email/group name
            # this will raise if the item is invalid
            return trans.sa_session.query(model_class).filter(column == item).first().id

        new_in_users = []
        new_in_groups = []
        invalid = []
        for item in util.listify(payload.get("in_users", [])):
            try:
                new_in_users.append(get_id(item, model.User, model.User.email))
            except Exception:
                invalid.append(item)
        for item in util.listify(payload.get("in_groups", [])):
            try:
                new_in_groups.append(get_id(item, model.Group, model.Group.name))
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

    def _url_for(self, *args, **kargs):
        try:
            return url_for(*args, **kargs)
        except AttributeError:
            return "*deprecated attribute not filled in by FastAPI server*"
