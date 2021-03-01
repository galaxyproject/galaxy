"""
Manager and Serializers for Quotas.

For more information about quotas: https://galaxyproject.org/admin/disk-quotas/
"""
import logging
from typing import List, Tuple

from galaxy import model, util
from galaxy.app import StructuredApp
from galaxy.exceptions import ActionInputError
from galaxy.managers import base
from galaxy.managers.context import ProvidesUserContext
from galaxy.quota._schema import (
    CreateQuotaPayload,
    CreateQuotaResult,
    QuotaDetails,
    QuotaSummaryList,
    UpdateQuotaPayload,
)
from galaxy.schema.fields import EncodedDatabaseIdField

log = logging.getLogger(__name__)


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
    """Interface/service object to interact with Quotas."""

    def __init__(self, app: StructuredApp):
        self.app = app

    @property
    def sa_session(self):
        return self.app.model.context

    @property
    def quota_agent(self):
        return self.app.quota_agent

    def create_quota(self, params, decode_id=None) -> Tuple[model.Quota, str]:
        if params.amount.lower() in ('unlimited', 'none', 'no limit'):
            create_amount = None
        else:
            try:
                create_amount = util.size_to_bytes(params.amount)
            except AssertionError:
                create_amount = False
        if not params.name or not params.description:
            raise ActionInputError("Enter a valid name and a description.")
        elif self.sa_session.query(model.Quota).filter(model.Quota.name == params.name).first():
            raise ActionInputError("Quota names must be unique and a quota with that name already exists, so choose another name.")
        elif not params.get('amount', None):
            raise ActionInputError("Enter a valid quota amount.")
        elif create_amount is False:
            raise ActionInputError("Unable to parse the provided amount.")
        elif params.operation not in model.Quota.valid_operations:
            raise ActionInputError("Enter a valid operation.")
        elif params.default != 'no' and params.default not in model.DefaultQuotaAssociation.types.__members__.values():
            raise ActionInputError("Enter a valid default type.")
        elif params.default != 'no' and params.operation != '=':
            raise ActionInputError("Operation for a default quota must be '='.")
        elif create_amount is None and params.operation != '=':
            raise ActionInputError("Operation for an unlimited quota must be '='.")
        else:
            # Create the quota
            quota = model.Quota(name=params.name, description=params.description, amount=create_amount, operation=params.operation)
            self.sa_session.add(quota)
            # If this is a default quota, create the DefaultQuotaAssociation
            if params.default != 'no':
                self.quota_agent.set_default_quota(params.default, quota)
                message = f"Default quota '{quota.name}' has been created."
            else:
                # Create the UserQuotaAssociations
                in_users = [self.sa_session.query(model.User).get(decode_id(x) if decode_id else x) for x in util.listify(params.in_users)]
                in_groups = [self.sa_session.query(model.Group).get(decode_id(x) if decode_id else x) for x in util.listify(params.in_groups)]
                if None in in_users:
                    raise ActionInputError("One or more invalid user id has been provided.")
                for user in in_users:
                    uqa = model.UserQuotaAssociation(user, quota)
                    self.sa_session.add(uqa)
                # Create the GroupQuotaAssociations
                if None in in_groups:
                    raise ActionInputError("One or more invalid group id has been provided.")
                for group in in_groups:
                    gqa = model.GroupQuotaAssociation(group, quota)
                    self.sa_session.add(gqa)
                message = f"Quota '{quota.name}' has been created with {len(in_users)} associated users and {len(in_groups)} associated groups."
            self.sa_session.flush()
            return quota, message

    def rename_quota(self, quota, params) -> str:
        if not params.name:
            raise ActionInputError('Enter a valid name.')
        elif params.name != quota.name and self.sa_session.query(model.Quota).filter(model.Quota.name == params.name).first():
            raise ActionInputError('A quota with that name already exists.')
        else:
            old_name = quota.name
            quota.name = params.name
            quota.description = params.description
            self.sa_session.add(quota)
            self.sa_session.flush()
            message = f"Quota '{old_name}' has been renamed to '{params.name}'."
            return message

    def manage_users_and_groups_for_quota(self, quota, params, decode_id=None) -> str:
        if quota.default:
            raise ActionInputError('Default quotas cannot be associated with specific users and groups.')
        else:
            in_users = [self.sa_session.query(model.User).get(decode_id(x) if decode_id else x) for x in util.listify(params.in_users)]
            if None in in_users:
                raise ActionInputError("One or more invalid user id has been provided.")
            in_groups = [self.sa_session.query(model.Group).get(decode_id(x) if decode_id else x) for x in util.listify(params.in_groups)]
            if None in in_groups:
                raise ActionInputError("One or more invalid group id has been provided.")
            self.quota_agent.set_entity_quota_associations(quotas=[quota], users=in_users, groups=in_groups)
            self.sa_session.refresh(quota)
            message = f"Quota '{quota.name}' has been updated with {len(in_users)} associated users and {len(in_groups)} associated groups."
            return message

    def edit_quota(self, quota, params) -> str:
        if params.amount.lower() in ('unlimited', 'none', 'no limit'):
            new_amount = None
        else:
            try:
                new_amount = util.size_to_bytes(params.amount)
            except (AssertionError, ValueError):
                new_amount = False
        if not params.amount:
            raise ActionInputError('Enter a valid amount.')
        elif new_amount is False:
            raise ActionInputError('Unable to parse the provided amount.')
        elif params.operation not in model.Quota.valid_operations:
            raise ActionInputError('Enter a valid operation.')
        else:
            quota.amount = new_amount
            quota.operation = params.operation
            self.sa_session.add(quota)
            self.sa_session.flush()
            message = f"Quota '{quota.name}' is now '{quota.operation}{quota.display_amount}'."
            return message

    def set_quota_default(self, quota, params) -> str:
        if params.default != 'no' and params.default not in model.DefaultQuotaAssociation.types.__members__.values():
            raise ActionInputError('Enter a valid default type.')
        else:
            if params.default != 'no':
                self.quota_agent.set_default_quota(params.default, quota)
                message = f"Quota '{quota.name}' is now the default for {params.default} users."
            else:
                if quota.default:
                    message = f"Quota '{quota.name}' is no longer the default for {quota.default[0].type} users."
                    for dqa in quota.default:
                        self.sa_session.delete(dqa)
                    self.sa_session.flush()
                else:
                    message = f"Quota '{quota.name}' is not a default."
            return message

    def unset_quota_default(self, quota, params=None) -> str:
        if not quota.default:
            raise ActionInputError(f"Quota '{quota.name}' is not a default.")
        else:
            message = f"Quota '{quota.name}' is no longer the default for {quota.default[0].type} users."
            for dqa in quota.default:
                self.sa_session.delete(dqa)
            self.sa_session.flush()
            return message

    def delete_quota(self, quota, params=None) -> str:
        quotas = util.listify(quota)
        names = []
        for q in quotas:
            if q.default:
                names.append(q.name)
        if len(names) == 1:
            raise ActionInputError(f"Quota '{names[0]}' is a default, please unset it as a default before deleting it.")
        elif len(names) > 1:
            raise ActionInputError(f"Quotas are defaults, please unset them as defaults before deleting them: {', '.join(names)}")
        message = f"Deleted {len(quotas)} quotas: "
        for q in quotas:
            q.deleted = True
            self.sa_session.add(q)
            names.append(q.name)
        self.sa_session.flush()
        message += ', '.join(names)
        return message

    def undelete_quota(self, quota, params=None) -> str:
        quotas = util.listify(quota)
        names = []
        for q in quotas:
            if not q.deleted:
                names.append(q.name)
        if len(names) == 1:
            raise ActionInputError(f"Quota '{names[0]}' has not been deleted, so it cannot be undeleted.")
        elif len(names) > 1:
            raise ActionInputError(f"Quotas have not been deleted so they cannot be undeleted: {', '.join(names)}")
        message = f"Undeleted {len(quotas)} quotas: "
        for q in quotas:
            q.deleted = False
            self.sa_session.add(q)
            names.append(q.name)
        self.sa_session.flush()
        message += ', '.join(names)
        return message

    def purge_quota(self, quota, params=None):
        """
        This method should only be called for a Quota that has previously been deleted.
        Purging a deleted Quota deletes all of the following from the database:
        - UserQuotaAssociations where quota_id == Quota.id
        - GroupQuotaAssociations where quota_id == Quota.id
        """
        quotas = util.listify(quota)
        names = []
        for q in quotas:
            if not q.deleted:
                names.append(q.name)
        if len(names) == 1:
            raise ActionInputError(f"Quota '{names[0]}' has not been deleted, so it cannot be purged.")
        elif len(names) > 1:
            raise ActionInputError(f"Quotas have not been deleted so they cannot be undeleted: {', '.join(names)}")
        message = f"Purged {len(quotas)} quotas: "
        for q in quotas:
            # Delete UserQuotaAssociations
            for uqa in q.users:
                self.sa_session.delete(uqa)
            # Delete GroupQuotaAssociations
            for gqa in q.groups:
                self.sa_session.delete(gqa)
            names.append(q.name)
        self.sa_session.flush()
        message += ', '.join(names)
        return message

    def get_quota(self, trans, id, deleted=None) -> model.Quota:
        return base.get_object(trans, id, 'Quota', check_ownership=False, check_accessible=False, deleted=deleted)

    def get_params(self, kwargs) -> util.Params:
        params = util.Params(kwargs)
        # set defaults if unset
        updates = dict(webapp=params.get('webapp', 'galaxy'),
                       message=util.restore_text(params.get('message', '')),
                       status=util.restore_text(params.get('status', 'done')))
        params.update(updates)
        return params

    def get_quota_params(self, kwargs) -> util.Params:
        params = self.get_params(kwargs)
        updates = dict(name=util.restore_text(params.get('name', '')),
                       description=util.restore_text(params.get('description', '')),
                       amount=util.restore_text(params.get('amount', '').strip()),
                       operation=params.get('operation', ''),
                       default=params.get('default', ''),
                       in_users=util.listify(params.get('in_users', [])),
                       out_users=util.listify(params.get('out_users', [])),
                       in_groups=util.listify(params.get('in_groups', [])),
                       out_groups=util.listify(params.get('out_groups', [])))
        params.update(updates)
        return params
