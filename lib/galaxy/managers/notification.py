from datetime import datetime
from typing import (
    List,
    Optional,
    Set,
    Tuple,
)

from sqlalchemy import (
    and_,
    bindparam,
    func,
    select,
    union,
    union_all,
    update,
)
from sqlalchemy.orm import aliased
from sqlalchemy.sql import Select

from galaxy.exceptions import ObjectNotFound
from galaxy.model import (
    GroupRoleAssociation,
    Notification,
    User,
    UserGroupAssociation,
    UserNotificationAssociation,
    UserRoleAssociation,
)
from galaxy.model.scoped_session import galaxy_scoped_session
from galaxy.schema.fields import DecodedDatabaseIdField
from galaxy.schema.notifications import (
    BroadcastNotificationCreateRequest,
    MandatoryNotificationCategory,
    NotificationBroadcastUpdateRequest,
    NotificationCreateData,
    NotificationCreateRequest,
    NotificationRecipients,
    UpdateUserNotificationPreferencesRequest,
    UserNotificationPreferences,
    UserNotificationUpdateRequest,
)

NOTIFICATION_PREFERENCES_SECTION_NAME = "notifications"


class NotificationManager:
    """Manager class to interact with the database models related with Notifications."""

    def __init__(self, sa_session: galaxy_scoped_session):
        self.sa_session = sa_session
        self.notification_columns = [
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
        self.user_notification_columns = self.notification_columns + [
            UserNotificationAssociation.seen_time,
            UserNotificationAssociation.favorite,
            UserNotificationAssociation.deleted,
        ]
        self.broadcast_notification_columns = self.notification_columns

    @property
    def now(self):
        return datetime.utcnow()

    def create_notification_for_users(self, request: NotificationCreateRequest) -> Tuple[Notification, int]:
        """
        Creates a new notification and associates it with all the recipient users.
        """
        recipient_users = self._get_all_recipient_users(request.recipients)
        with self.sa_session.begin():
            notification = self._create_notification_model(request.notification)
            self.sa_session.add(notification)
            for user in recipient_users:
                # TODO: check user notification settings before?
                user_notification_association = UserNotificationAssociation(user, notification)
                self.sa_session.add(user_notification_association)

        return notification, len(recipient_users)

    def create_broadcast_notification(self, request: BroadcastNotificationCreateRequest):
        """Creates a broadcasted notification.

        This kind of notification is not explicitly associated with any specific user but it is accessible by all users.
        """
        with self.sa_session.begin():
            notification = self._create_notification_model(request)
            self.sa_session.add(notification)
        return notification

    def get_user_notification(self, user: User, notification_id: int):
        """
        Displays a notification belonging to the user.
        """
        stmt = (
            select(self.user_notification_columns)
            .select_from(Notification)
            .join(
                UserNotificationAssociation,
                UserNotificationAssociation.notification_id == notification_id,
            )
            .where(
                and_(
                    UserNotificationAssociation.user_id == user.id,
                    Notification.publication_time < self.now,
                    Notification.expiration_time > self.now,
                )
            )
        )
        result = self.sa_session.execute(stmt).fetchone()
        if result is None:
            self._raise_notification_not_found(notification_id)
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
        stmt = self._all_user_notifications_query(user, since)
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
            .where(
                and_(
                    UserNotificationAssociation.user_id == user.id,
                    UserNotificationAssociation.seen_time.is_(None),
                    Notification.publication_time < self.now,
                    Notification.expiration_time > self.now,
                )
            )
        )

        result = self.sa_session.execute(stmt).scalar()
        return result

    def get_all_broadcasted_notifications(self, since: Optional[datetime] = None):
        stmt = self._all_broadcasted_notifications_query(since)
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
                seen_time = self.now if request.seen else None
                stmt = stmt.values(seen_time=seen_time)
            if request.favorite is not None:
                stmt = stmt.values(favorite=request.favorite)
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
        if current_notification_preferences is None:
            return UserNotificationPreferences.default()
        return UserNotificationPreferences.parse_raw(current_notification_preferences)

    def update_user_notification_preferences(
        self, user: User, request: UpdateUserNotificationPreferencesRequest
    ) -> UserNotificationPreferences:
        """Updates the user's notification preferences with the requested changes."""
        notification_preferences = UserNotificationPreferences.default()
        notification_preferences.update(request.preferences)
        with self.sa_session.begin():
            user.preferences[NOTIFICATION_PREFERENCES_SECTION_NAME] = notification_preferences.json()
        return notification_preferences

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

    def _all_user_notifications_query(self, user: User, since: Optional[datetime] = None):
        stmt = (
            select(self.user_notification_columns)
            .select_from(Notification)
            .join(
                UserNotificationAssociation,
                UserNotificationAssociation.notification_id == Notification.id,
            )
            .where(
                and_(
                    UserNotificationAssociation.user_id == user.id,
                    Notification.publication_time < self.now,
                    Notification.expiration_time > self.now,
                )
            )
        )
        if since is not None:
            stmt = stmt.where(Notification.publication_time > since)

        return stmt

    def _all_broadcasted_notifications_query(self, since: Optional[datetime] = None):
        stmt = (
            select(self.broadcast_notification_columns)
            .select_from(Notification)
            .where(
                and_(
                    Notification.category == MandatoryNotificationCategory.broadcast,
                    Notification.publication_time < self.now,
                    Notification.expiration_time > self.now,
                )
            )
        )
        if since is not None:
            stmt = stmt.where(Notification.publication_time > since)
        return stmt

    def _get_all_recipient_users(self, recipients: NotificationRecipients) -> List[User]:
        """Gets all the users from all the individual user ids, group ids and roles ids
        provided as recipients.
        The resulting list will contain only unique users even if the same user id might have been provided more
        than once as `user_ids` input or implicitly in groups or roles.
        """
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
            group_ids_from_roles = set([id for id, in self.sa_session.execute(stmt)])
            new_group_ids = group_ids_from_roles - processed_group_ids

            # Get role IDs associated with any of the given group IDs
            stmt = (
                select(GroupRoleAssociation.role_id)
                .select_from(GroupRoleAssociation)
                .where(GroupRoleAssociation.group_id.in_(group_ids))
                .distinct()
            )
            role_ids_from_groups = set([id for id, in self.sa_session.execute(stmt)])
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

    def _get_all_recipient_users_using_recursive_CTE(self, recipients: NotificationRecipients) -> List[User]:
        # Get all the user IDs from individual users
        user_ids = set(recipients.user_ids)

        # Get all the user IDs from groups and roles using recursive CTEs
        group_users = (
            select(UserGroupAssociation.user_id)
            .where(UserGroupAssociation.group_id.in_(bindparam("group_ids")))
            .cte("group_users", recursive=True)
        )

        group_users_alias = aliased(group_users, name="g")
        group_users_query = select(group_users_alias.c.user_id).select_from(group_users_alias)

        group_users = group_users.union_all(
            select(UserGroupAssociation.user_id).where(UserGroupAssociation.group_id == group_users_alias.c.user_id)
        )

        role_users = (
            select(UserRoleAssociation.user_id)
            .where(UserRoleAssociation.role_id.in_(bindparam("role_ids")))
            .cte("role_users", recursive=True)
        )

        role_users_alias = aliased(role_users, name="r")
        role_users_query = select(role_users_alias.c.user_id).select_from(role_users_alias)

        role_users = role_users.union_all(
            select(UserRoleAssociation.user_id).where(UserRoleAssociation.role_id == role_users_alias.c.user_id)
        )

        # Build the final query to get all unique user IDs
        query = (
            select(union_all(group_users_query, role_users_query).alias("all_users"))
            .select_from(union_all(group_users, role_users))
            .distinct("all_users.user_id")
        )

        # Execute the query and retrieve user IDs
        params = {"group_ids": list(recipients.group_ids), "role_ids": list(recipients.role_ids)}
        result = self.sa_session.execute(query, params).fetchall()
        group_and_role_user_ids = set([id for id, in result])

        # Get all the unique recipient users by ID
        unique_user_ids = user_ids.union(group_and_role_user_ids)
        unique_recipient_users = self.sa_session.query(User).filter(User.id.in_(unique_user_ids)).all()
        return unique_recipient_users

    def _raise_notification_not_found(self, notification_id: int):
        raise ObjectNotFound(
            f"The requested notification with id '{DecodedDatabaseIdField.encode(notification_id)}' was not found."
        )
