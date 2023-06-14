from datetime import datetime
from typing import (
    List,
    NamedTuple,
    Optional,
    Set,
    Tuple,
)

from pydantic import ValidationError
from sqlalchemy import (
    and_,
    delete,
    false,
    func,
    or_,
    select,
    union,
    update,
)
from sqlalchemy.sql import Select
from typing_extensions import Protocol

from galaxy.config import GalaxyAppConfiguration
from galaxy.exceptions import (
    ConfigDoesNotAllowException,
    ObjectNotFound,
)
from galaxy.model import (
    GroupRoleAssociation,
    Notification,
    User,
    UserGroupAssociation,
    UserNotificationAssociation,
    UserRoleAssociation,
)
from galaxy.model.scoped_session import galaxy_scoped_session
from galaxy.schema.notifications import (
    BroadcastNotificationCreateRequest,
    MandatoryNotificationCategory,
    NotificationBroadcastUpdateRequest,
    NotificationCreateData,
    NotificationCreateRequest,
    NotificationRecipients,
    PersonalNotificationCategory,
    UpdateUserNotificationPreferencesRequest,
    UserNotificationPreferences,
    UserNotificationUpdateRequest,
)

NOTIFICATION_PREFERENCES_SECTION_NAME = "notifications"


class CleanupResultSummary(NamedTuple):
    deleted_notifications_count: int
    deleted_associations_count: int


class NotificationManager:
    """Manager class to interact with the database models related with Notifications."""

    def __init__(self, sa_session: galaxy_scoped_session, config: GalaxyAppConfiguration):
        self.sa_session = sa_session
        self.config = config
        self.recipient_resolver = NotificationRecipientResolver(strategy=DefaultStrategy(sa_session))
        self.user_notification_columns = [
            Notification.id,
            Notification.source,
            Notification.category,
            Notification.variant,
            Notification.create_time,
            UserNotificationAssociation.update_time,
            Notification.publication_time,
            Notification.expiration_time,
            Notification.content,
            UserNotificationAssociation.seen_time,
            UserNotificationAssociation.deleted,
        ]
        self.broadcast_notification_columns = [
            Notification.id,
            Notification.source,
            Notification.category,
            Notification.variant,
            Notification.create_time,
            Notification.update_time,
            Notification.publication_time,
            Notification.expiration_time,
            Notification.content,
        ]

    @property
    def notifications_enabled(self):
        return self.config.enable_notification_system

    @property
    def _now(self):
        return datetime.utcnow()

    @property
    def _notification_is_active(self):
        """Condition to filter active (published and not expired) notifications only."""
        return and_(
            Notification.publication_time <= self._now,
            Notification.expiration_time > self._now,
        )

    def ensure_notifications_enabled(self):
        if not self.notifications_enabled:
            raise ConfigDoesNotAllowException("Notifications are disabled in this Galaxy.")

    def send_notification_to_recipients(self, request: NotificationCreateRequest) -> Tuple[Optional[Notification], int]:
        """
        Creates a new notification and associates it with all the recipient users.
        """
        self.ensure_notifications_enabled()
        recipient_users = self.recipient_resolver.resolve(request.recipients)
        notifications_sent = len(recipient_users)
        with self.sa_session.begin():
            notification = self._create_notification_model(request.notification)
            self.sa_session.add(notification)
            self._send_to_users(notification, recipient_users)

        return notification, notifications_sent

    def _send_to_users(self, notification: Notification, users: List[User]):
        # TODO: Move this potentially expensive operation to a task?
        for user in users:
            if self._user_is_subscribed_to_notification(user, notification.category):
                user_notification_association = UserNotificationAssociation(user, notification)
                self.sa_session.add(user_notification_association)

    def _user_is_subscribed_to_notification(self, user: User, category: PersonalNotificationCategory) -> bool:
        notification_preferences = self.get_user_notification_preferences(user)
        category_settings = notification_preferences.get(category)
        return category_settings.enabled

    def create_broadcast_notification(self, request: BroadcastNotificationCreateRequest):
        """Creates a broadcasted notification.

        This kind of notification is not explicitly associated with any specific user but it is accessible by all users.
        """
        self.ensure_notifications_enabled()
        with self.sa_session.begin():
            notification = self._create_notification_model(request)
            self.sa_session.add(notification)
        return notification

    def get_user_notification(self, user: User, notification_id: int, active_only: Optional[bool] = True):
        """
        Displays a notification belonging to the user.
        """
        stmt = self._user_notifications_query(user, active_only=active_only)
        stmt = stmt.where(Notification.id == notification_id)

        result = self.sa_session.execute(stmt).fetchone()
        if result is None:
            raise ObjectNotFound
        return result

    def get_user_notifications(
        self,
        user: User,
        limit: Optional[int] = 50,
        offset: Optional[int] = None,
        since: Optional[datetime] = None,
    ):
        """
        Displays the list of notifications belonging to the user.
        """
        stmt = self._user_notifications_query(user, since)
        if offset:
            stmt = stmt.offset(offset)
        if limit:
            stmt = stmt.limit(limit)

        result = self.sa_session.execute(stmt).fetchall()
        return result

    def get_user_total_unread_notification_count(self, user: User) -> int:
        """
        Returns the total number of unread notifications of the user.
        Only published and not expired notifications are accounted.
        """
        stmt = (
            select([func.count(UserNotificationAssociation.id)])
            .select_from(UserNotificationAssociation)
            .join(
                Notification,
                Notification.id == UserNotificationAssociation.notification_id,
            )
            .where(self._notification_is_active)
            .where(
                and_(
                    UserNotificationAssociation.user_id == user.id,
                    UserNotificationAssociation.deleted == false(),
                    UserNotificationAssociation.seen_time.is_(None),
                )
            )
        )
        result = self.sa_session.execute(stmt).scalar()
        return result

    def get_broadcasted_notification(self, notification_id: int, active_only: Optional[bool] = True):
        stmt = (
            select(self.broadcast_notification_columns)
            .select_from(Notification)
            .where(
                and_(
                    Notification.id == notification_id,
                    Notification.category == MandatoryNotificationCategory.broadcast,
                )
            )
        )
        if active_only:
            stmt = stmt.where(self._notification_is_active)
        result = self.sa_session.execute(stmt).fetchone()
        if result is None:
            raise ObjectNotFound
        return result

    def get_all_broadcasted_notifications(self, since: Optional[datetime] = None, active_only: Optional[bool] = True):
        stmt = self._broadcasted_notifications_query(since, active_only)
        result = self.sa_session.execute(stmt).fetchall()
        return result

    def update_user_notifications(
        self, user: User, notification_ids: Set[int], request: UserNotificationUpdateRequest
    ) -> int:
        """Updates a batch of notifications associated with the user using the requested values."""
        updated_row_count = 0
        with self.sa_session.begin():
            stmt = update(UserNotificationAssociation).where(
                and_(
                    UserNotificationAssociation.user_id == user.id,
                    UserNotificationAssociation.notification_id.in_(notification_ids),
                )
            )
            if request.seen is not None:
                seen_time = self._now if request.seen else None
                stmt = stmt.values(seen_time=seen_time)
            if request.deleted is not None:
                stmt = stmt.values(deleted=request.deleted)
            result = self.sa_session.execute(stmt)
            updated_row_count = result.rowcount
        return updated_row_count

    def update_broadcasted_notification(self, notification_id: int, request: NotificationBroadcastUpdateRequest) -> int:
        """Updates a single broadcasted notification with the requested values."""
        updated_row_count = 0
        with self.sa_session.begin():
            stmt = update(Notification).where(
                and_(
                    Notification.id == notification_id,
                    Notification.category == MandatoryNotificationCategory.broadcast,
                )
            )
            if request.source is not None:
                stmt = stmt.values(source=request.source)
            if request.variant is not None:
                stmt = stmt.values(variant=request.variant)
            if request.publication_time is not None:
                stmt = stmt.values(publication_time=request.publication_time)
            if request.expiration_time is not None:
                stmt = stmt.values(expiration_time=request.expiration_time)
            if request.content is not None:
                stmt = stmt.values(content=request.content.json())
            result = self.sa_session.execute(stmt)
            updated_row_count = result.rowcount
        return updated_row_count

    def get_user_notification_preferences(self, user: User) -> UserNotificationPreferences:
        """Gets the user's current notification preferences or the default ones if no preferences are set."""
        current_notification_preferences = (
            user.preferences[NOTIFICATION_PREFERENCES_SECTION_NAME]
            if NOTIFICATION_PREFERENCES_SECTION_NAME in user.preferences
            else None
        )
        try:
            return UserNotificationPreferences.parse_raw(current_notification_preferences)
        except ValidationError:
            # Gracefully return default preferences is they don't exist or get corrupted
            return UserNotificationPreferences.default()

    def update_user_notification_preferences(
        self, user: User, request: UpdateUserNotificationPreferencesRequest
    ) -> UserNotificationPreferences:
        """Updates the user's notification preferences with the requested changes."""
        notification_preferences = self.get_user_notification_preferences(user)
        notification_preferences.update(request.preferences)
        with self.sa_session.begin():
            user.preferences[NOTIFICATION_PREFERENCES_SECTION_NAME] = notification_preferences.json()
        return notification_preferences

    def cleanup_expired_notifications(self) -> CleanupResultSummary:
        """
        Permanently removes from the database all notifications (and user associations) that have expired.
        """
        deleted_notifications_count = 0
        deleted_associations_count = 0
        execution_options_for_delete = {"synchronize_session": "fetch"}
        with self.sa_session.begin():
            is_favorite_and_not_deleted = and_(
                UserNotificationAssociation.favorite.is_(True),
                UserNotificationAssociation.deleted.is_(False),
            )
            has_expired = Notification.expiration_time <= self._now

            # Find those notification ids that have expired excluding those that somebody has marked as favorite
            non_favorite_expired_notifications_query = (
                select(Notification.id)
                .where(has_expired)
                .where(~Notification.user_notification_associations.any(is_favorite_and_not_deleted))
            )
            non_favorite_expired_notification_ids = (
                self.sa_session.execute(non_favorite_expired_notifications_query).scalars().fetchall()
            )

            # Delete all notifications and associations that have expired and nobody has marked as favorite
            delete_expired_non_favorite_associations_query = delete(UserNotificationAssociation).where(
                UserNotificationAssociation.notification_id.in_(non_favorite_expired_notification_ids)
            )
            result = self.sa_session.execute(
                delete_expired_non_favorite_associations_query, execution_options=execution_options_for_delete
            )
            deleted_associations_count += result.rowcount

            delete_expired_non_favorite_notifications_query = delete(Notification).where(
                Notification.id.in_(non_favorite_expired_notification_ids)
            )
            result = self.sa_session.execute(
                delete_expired_non_favorite_notifications_query, execution_options=execution_options_for_delete
            )
            deleted_notifications_count += result.rowcount

            # Find those notification ids that have expired but somebody has marked as favorite
            favorite_expired_notifications_query = (
                select(Notification.id)
                .where(has_expired)
                .where(Notification.user_notification_associations.any(is_favorite_and_not_deleted))
            )
            favorite_expired_notification_ids = self.sa_session.execute(favorite_expired_notifications_query).scalars()

            # Delete those associations that did expire and are not marked as favorite
            non_favorite_expired_associations_query = (
                select(UserNotificationAssociation)
                .where(UserNotificationAssociation.favorite.is_(False))
                .where(UserNotificationAssociation.notification_id.in_(favorite_expired_notification_ids))
            )
            delete_non_favorite_expired_associations_query = delete(UserNotificationAssociation).where(
                UserNotificationAssociation.id.in_(
                    select(UserNotificationAssociation.id).select_from(
                        non_favorite_expired_associations_query.subquery()
                    )
                )
            )
            result = self.sa_session.execute(
                delete_non_favorite_expired_associations_query, execution_options=execution_options_for_delete
            )
            deleted_associations_count += result.rowcount

            # Delete broadcasted
            delete_expired_broadcasted_notifications_query = (
                delete(Notification)
                .where(has_expired)
                .where(Notification.category == MandatoryNotificationCategory.broadcast)
            )
            result = self.sa_session.execute(
                delete_expired_broadcasted_notifications_query, execution_options=execution_options_for_delete
            )
            deleted_notifications_count += result.rowcount
        return CleanupResultSummary(deleted_notifications_count, deleted_associations_count)

    def _create_notification_model(self, payload: NotificationCreateData):
        notification = Notification(
            payload.source,
            payload.category,
            payload.variant,
            payload.content.json(),
        )
        notification.publication_time = payload.publication_time
        notification.expiration_time = payload.expiration_time
        return notification

    def _user_notifications_query(
        self, user: User, since: Optional[datetime] = None, active_only: Optional[bool] = True
    ):
        stmt = (
            select(self.user_notification_columns)
            .select_from(Notification)
            .join(
                UserNotificationAssociation,
                UserNotificationAssociation.notification_id == Notification.id,
            )
            .where(UserNotificationAssociation.user_id == user.id)
        )
        if since is not None:
            stmt = stmt.where(
                or_(
                    UserNotificationAssociation.update_time >= since,
                    Notification.publication_time >= since,
                )
            )
        if active_only:
            stmt = stmt.where(self._notification_is_active)
            stmt = stmt.where(UserNotificationAssociation.deleted == false())

        return stmt

    def _broadcasted_notifications_query(self, since: Optional[datetime] = None, active_only: Optional[bool] = True):
        stmt = (
            select(self.broadcast_notification_columns)
            .select_from(Notification)
            .where(Notification.category == MandatoryNotificationCategory.broadcast)
        )
        if since is not None:
            stmt = stmt.where(
                or_(
                    Notification.update_time >= since,
                    Notification.publication_time >= since,
                )
            )
        if active_only:
            stmt = stmt.where(self._notification_is_active)
        return stmt


class NotificationRecipientResolverStrategy(Protocol):
    def resolve_users(self, recipients: NotificationRecipients) -> List[User]:
        pass


class NotificationRecipientResolver:
    """Resolves a set of NotificationRecipients to a list of unique users using a specific strategy."""

    def __init__(self, strategy: NotificationRecipientResolverStrategy):
        self.strategy = strategy

    def resolve(self, recipients: NotificationRecipients) -> List[User]:
        """Given individual user, group and roles ids as recipients, obtains the unique list of users.

        The resulting list will contain only unique users even if the same user id might have been provided more
        than once as `user_ids` input or implicitly in groups or roles.
        """
        return self.strategy.resolve_users(recipients)


class DefaultStrategy(NotificationRecipientResolverStrategy):
    """Resolves the recipient users using an iterative approach."""

    def __init__(self, sa_session: galaxy_scoped_session):
        self.sa_session = sa_session

    def resolve_users(self, recipients: NotificationRecipients) -> List[User]:
        unique_user_ids: Set[int] = set(recipients.user_ids)

        all_group_ids, all_role_ids = self._expand_group_and_roles_ids(
            set(recipients.group_ids), set(recipients.role_ids)
        )

        user_ids_from_groups_stmt = self._get_all_user_ids_from_groups_query(all_group_ids)
        user_ids_from_roles_stmt = self._get_all_user_ids_from_roles_query(all_role_ids)

        union_stmt = union(user_ids_from_groups_stmt, user_ids_from_roles_stmt)
        user_ids_from_groups_and_roles = set([id for id, in self.sa_session.execute(union_stmt)])
        unique_user_ids.update(user_ids_from_groups_and_roles)

        unique_recipient_users = self.sa_session.query(User).filter(User.id.in_(unique_user_ids)).all()
        return unique_recipient_users

    def _get_all_user_ids_from_roles_query(self, role_ids: Set[int]) -> Select:
        stmt = (
            select(UserRoleAssociation.user_id)
            .select_from(UserRoleAssociation)
            .where(UserRoleAssociation.role_id.in_(role_ids))
            .distinct()
        )
        return stmt

    def _get_all_user_ids_from_groups_query(self, group_ids: Set[int]) -> Select:
        stmt = (
            select(UserGroupAssociation.user_id)
            .select_from(UserGroupAssociation)
            .where(UserGroupAssociation.group_id.in_(group_ids))
            .distinct()
        )
        return stmt

    def _expand_group_and_roles_ids(self, group_ids: Set[int], role_ids: Set[int]) -> Tuple[Set[int], Set[int]]:
        """Given a set of group and roles IDs, it expands those sets (non-recursively) by including sub-groups or sub-roles
        indirectly associated with them.
        """
        processed_group_ids: Set[int] = set()
        processed_role_ids: Set[int] = set()

        while True:
            # Get group IDs associated with any of the given role IDs
            stmt = (
                select(GroupRoleAssociation.group_id)
                .select_from(GroupRoleAssociation)
                .where(GroupRoleAssociation.role_id.in_(role_ids))
                .distinct()
            )
            group_ids_from_roles = set([id for id, in self.sa_session.execute(stmt) if id is not None])
            new_group_ids = group_ids_from_roles - processed_group_ids

            # Get role IDs associated with any of the given group IDs
            stmt = (
                select(GroupRoleAssociation.role_id)
                .select_from(GroupRoleAssociation)
                .where(GroupRoleAssociation.group_id.in_(group_ids))
                .distinct()
            )
            role_ids_from_groups = set([id for id, in self.sa_session.execute(stmt) if id is not None])
            new_role_ids = role_ids_from_groups - processed_role_ids

            # Stop if there are no new group or role IDs to process
            if not new_group_ids and not new_role_ids:
                break

            # Add new group and role IDs to the respective sets
            group_ids.update(new_group_ids)
            role_ids.update(new_role_ids)

            # Add new group and role IDs to the processed sets
            processed_group_ids.update(new_group_ids)
            processed_role_ids.update(new_role_ids)

        return group_ids, role_ids


class RecursiveCTEStrategy(NotificationRecipientResolverStrategy):
    def resolve_users(self, recipients: NotificationRecipients) -> List[User]:
        # TODO Implement resolver using recursive CTEs?
        return []
