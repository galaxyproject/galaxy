import logging
from typing import (
    List,
    Optional,
    Set,
    Tuple,
)

from sqlalchemy import false

from galaxy import exceptions
from galaxy.managers import base
from galaxy.managers.sharable import (
    SharableModelManager,
    SharableModelSerializer,
)
from galaxy.model import User
from galaxy.schema.fields import EncodedDatabaseIdField
from galaxy.schema.schema import (
    SetSlugPayload,
    ShareWithPayload,
    ShareWithStatus,
    SharingOptions,
    SharingStatus,
)

log = logging.getLogger(__name__)


class ShareableService:
    """
    Provides the common logic used by the API to share *any* kind of
    resource with other users.

    The Manager class of the particular resource must implement the SharableModelManager
    and have a compatible SharableModelSerializer implementation.
    """

    def __init__(self, manager: SharableModelManager, serializer: SharableModelSerializer) -> None:
        self.manager = manager
        self.serializer = serializer

    def set_slug(self, trans, id: EncodedDatabaseIdField, payload: SetSlugPayload):
        item = self._get_item_by_id(trans, id)
        self.manager.set_slug(item, payload.new_slug, trans.user)

    def sharing(self, trans, id: EncodedDatabaseIdField) -> SharingStatus:
        """Gets the current sharing status of the item with the given id."""
        item = self._get_item_by_id(trans, id)
        return self._get_sharing_status(trans, item)

    def enable_link_access(self, trans, id: EncodedDatabaseIdField) -> SharingStatus:
        """Makes this item accessible by link.
        If this item contains other elements they will be publicly accessible too.
        """
        item = self._get_item_by_id(trans, id)
        self.manager.make_members_public(trans, item)
        self.manager.make_importable(item)
        return self._get_sharing_status(trans, item)

    def disable_link_access(self, trans, id: EncodedDatabaseIdField) -> SharingStatus:
        item = self._get_item_by_id(trans, id)
        self.manager.make_non_importable(item)
        return self._get_sharing_status(trans, item)

    def publish(self, trans, id: EncodedDatabaseIdField) -> SharingStatus:
        """Makes this item publicly accessible.
        If this item contains other elements they will be publicly accessible too.
        """
        item = self._get_item_by_id(trans, id)
        self.manager.make_members_public(trans, item)
        self.manager.publish(item)
        return self._get_sharing_status(trans, item)

    def unpublish(self, trans, id: EncodedDatabaseIdField) -> SharingStatus:
        item = self._get_item_by_id(trans, id)
        self.manager.unpublish(item)
        return self._get_sharing_status(trans, item)

    def share_with_users(self, trans, id: EncodedDatabaseIdField, payload: ShareWithPayload) -> ShareWithStatus:
        item = self._get_item_by_id(trans, id)
        users, errors = self._get_users(trans, payload.user_ids)
        extra = self._share_with_options(trans, item, users, errors, payload.share_option)
        base_status = self._get_sharing_status(trans, item)
        status = ShareWithStatus.parse_obj(base_status)
        status.extra = extra
        status.errors.extend(errors)
        return status

    def _share_with_options(
        self,
        trans,
        item,
        users: Set[User],
        errors: Set[str],
        share_option: Optional[SharingOptions] = None,
    ):
        extra = self.manager.get_sharing_extra_information(trans, item, users, errors, share_option)
        if not extra or extra.can_share:
            self.manager.update_current_sharing_with_users(item, users)
            extra = None
        return extra

    def _get_item_by_id(self, trans, id: EncodedDatabaseIdField):
        class_name = self.manager.model_class.__name__
        item = base.get_object(trans, id, class_name, check_ownership=True, check_accessible=True, deleted=False)
        return item

    def _get_sharing_status(self, trans, item):
        status = self.serializer.serialize_to_view(item, user=trans.user, trans=trans, default_view="sharing")
        status["users_shared_with"] = [
            {"id": self.manager.app.security.encode_id(a.user.id), "email": a.user.email}
            for a in item.users_shared_with
        ]
        return SharingStatus.parse_obj(status)

    def _get_users(self, trans, emails_or_ids: Optional[List] = None) -> Tuple[Set[User], Set[str]]:
        if emails_or_ids is None:
            raise exceptions.MessageException("Missing required user IDs or emails")
        send_to_users: Set[User] = set()
        send_to_err: Set[str] = set()
        for email_or_id in set(emails_or_ids):
            email_or_id = email_or_id.strip()
            if not email_or_id:
                continue

            send_to_user = None
            if "@" in email_or_id:
                email_address = email_or_id
                send_to_user = self.manager.user_manager.by_email(
                    email_address, filters=[User.table.c.deleted == false()]
                )
            else:
                try:
                    decoded_user_id = trans.security.decode_id(email_or_id)
                    send_to_user = self.manager.user_manager.by_id(decoded_user_id)
                    if send_to_user.deleted:
                        send_to_user = None
                except exceptions.MalformedId:
                    send_to_user = None

            if not send_to_user:
                send_to_err.add(f"{email_or_id} is not a valid Galaxy user.")
            elif send_to_user == trans.user:
                send_to_err.add("You cannot share resources with yourself.")
            else:
                send_to_users.add(send_to_user)

        return send_to_users, send_to_err
