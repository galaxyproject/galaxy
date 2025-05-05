import logging
from datetime import datetime
from enum import Enum
from typing import (
    cast,
    Dict,
    List,
    NamedTuple,
    Optional,
    Set,
    Tuple,
    Type,
)
from urllib.parse import urlparse

from pydantic import (
    BaseModel,
    ValidationError,
)
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
from sqlalchemy.orm import InstrumentedAttribute
from sqlalchemy.sql import Select
from typing_extensions import Protocol

from galaxy import util
from galaxy.config import (
    GalaxyAppConfiguration,
    templates,
)
from galaxy.exceptions import (
    ConfigDoesNotAllowException,
    ObjectNotFound,
)
from galaxy.managers.markdown_util import to_html
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
    AnyNotificationContent,
    BroadcastNotificationCreateRequest,
    MandatoryNotificationCategory,
    MessageNotificationContent,
    NewSharedItemNotificationContent,
    NotificationBroadcastUpdateRequest,
    NotificationCategorySettings,
    NotificationChannelSettings,
    NotificationCreateData,
    NotificationCreateRequest,
    NotificationRecipients,
    NotificationVariant,
    PersonalNotificationCategory,
    UpdateUserNotificationPreferencesRequest,
    UserNotificationPreferences,
    UserNotificationUpdateRequest,
)

log = logging.getLogger(__name__)


NOTIFICATION_PREFERENCES_SECTION_NAME = "notifications"


class CleanupResultSummary(NamedTuple):
    deleted_notifications_count: int
    deleted_associations_count: int


class NotificationRecipientResolverStrategy(Protocol):
    def resolve_users(self, recipients: NotificationRecipients) -> List[User]:
        pass


class NotificationChannelPlugin(Protocol):
    config: GalaxyAppConfiguration

    def __init__(self, config: GalaxyAppConfiguration):
        self.config = config

    def send(self, notification: Notification, user: User):
        raise NotImplementedError


class NotificationManager:
    """Manager class to interact with the database models related with Notifications."""

    def __init__(self, sa_session: galaxy_scoped_session, config: GalaxyAppConfiguration):
        self.sa_session = sa_session
        self.config = config
        self.recipient_resolver = NotificationRecipientResolver(strategy=DefaultStrategy(sa_session))
        self.user_notification_columns: List[InstrumentedAttribute] = [
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
        self.broadcast_notification_columns: List[InstrumentedAttribute] = [
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
        self.channel_plugins = self._register_supported_channels()

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

    @property
    def can_send_notifications_async(self):
        return self.config.enable_celery_tasks

    def send_notification_to_recipients(self, request: NotificationCreateRequest) -> Tuple[Optional[Notification], int]:
        """
        Creates a new notification and associates it with all the recipient users.

        It takes into account the user's notification preferences to decide if the notification should be sent to them.
        No other notification channel is used here, only the internal database associations are created.
        """
        self.ensure_notifications_enabled()
        recipient_users = self.recipient_resolver.resolve(request.recipients)
        notification = self._create_notification_model(request.notification, request.galaxy_url)
        self.sa_session.add(notification)
        self.sa_session.commit()

        notifications_sent = self._create_associations(notification, recipient_users)
        self.sa_session.commit()

        return notification, notifications_sent

    def _create_associations(self, notification: Notification, users: List[User]) -> int:
        success_count = 0
        for user in users:
            try:
                if self._is_user_subscribed_to_notification(user, notification):
                    user_notification_association = UserNotificationAssociation(user, notification)
                    self.sa_session.add(user_notification_association)
                    success_count += 1
            except Exception as e:
                log.error(f"Error sending notification to user {user.id}. Reason: {util.unicodify(e)}")
                continue
        return success_count

    def dispatch_pending_notifications_via_channels(self) -> int:
        """
        Dispatches all pending notifications to the users depending on the configured channels.

        This is meant to be called periodically by a background task.
        """
        self.ensure_notifications_enabled()
        pending_notifications = self.get_pending_notifications()

        # Mark all pending notifications as dispatched
        for notification in pending_notifications:
            notification.dispatched = True

        self.sa_session.commit()

        # Do the actual dispatching
        for notification in pending_notifications:
            self._dispatch_notification_to_users(notification)

        return len(pending_notifications)

    def get_pending_notifications(self):
        """
        Returns all pending notifications that have not been dispatched yet
        but are due and ready to be sent to the users.
        """
        stmt = select(Notification).where(Notification.dispatched == false(), self._notification_is_active)
        return self.sa_session.execute(stmt).scalars().all()

    def _dispatch_notification_to_users(self, notification: Notification):
        users = self._get_associated_users(notification)
        for user in users:
            try:
                if self._is_user_subscribed_to_notification(user, notification):
                    settings = self._get_user_category_settings(user, notification.category)  # type:ignore[arg-type]
                    self._send_via_channels(notification, user, settings.channels)
            except Exception as e:
                log.error(f"Error sending notification to user {user.id}. Reason: {util.unicodify(e)}")
                continue

    def _get_associated_users(self, notification: Notification):
        stmt = (
            select(User)
            .join(
                UserNotificationAssociation,
                UserNotificationAssociation.user_id == User.id,
            )
            .where(
                UserNotificationAssociation.notification_id == notification.id,
            )
        )
        return self.sa_session.execute(stmt).scalars().all()

    def _is_user_subscribed_to_notification(self, user: User, notification: Notification) -> bool:
        if self._is_urgent(notification):
            # Urgent notifications are always sent
            return True
        category_settings = self._get_user_category_settings(user, notification.category)  # type:ignore[arg-type]
        return self._is_subscribed_to_category(category_settings)

    def _send_via_channels(self, notification: Notification, user: User, channel_settings: NotificationChannelSettings):
        channels = channel_settings.model_fields_set
        for channel in channels:
            if channel not in self.channel_plugins:
                continue  # Skip unsupported channels
            user_opted_out = getattr(channel_settings, channel, False) is False
            if user_opted_out and not self._is_urgent(notification):
                continue  # Skip sending to opted-out users unless it's an urgent notification
            try:
                plugin = self.channel_plugins[channel]
                plugin.send(notification, user)
            except Exception as e:
                log.error(
                    f"Error sending notification to user {user.id} via channel '{channel}'. Reason: {util.unicodify(e)}"
                )

    def _is_subscribed_to_category(self, category_settings: NotificationCategorySettings) -> bool:
        return category_settings.enabled

    def _is_urgent(self, notification: Notification) -> bool:
        return notification.variant == NotificationVariant.urgent.value

    def _get_user_category_settings(
        self, user: User, category: PersonalNotificationCategory
    ) -> NotificationCategorySettings:
        notification_preferences = self.get_user_notification_preferences(user)
        category_settings = notification_preferences.get(category)
        return category_settings

    def create_broadcast_notification(self, request: BroadcastNotificationCreateRequest):
        """Creates a broadcasted notification.

        This kind of notification is not explicitly associated with any specific user but it is accessible by all users.
        """
        self.ensure_notifications_enabled()
        notification = self._create_notification_model(request)
        self.sa_session.add(notification)
        self.sa_session.commit()
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
            select(func.count(UserNotificationAssociation.id))
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
        return self.sa_session.execute(stmt).scalar() or 0

    def get_broadcasted_notification(self, notification_id: int, active_only: Optional[bool] = True):
        stmt = (
            select(*self.broadcast_notification_columns)
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
        self.sa_session.commit()
        return updated_row_count

    def update_broadcasted_notification(self, notification_id: int, request: NotificationBroadcastUpdateRequest) -> int:
        """Updates a single broadcasted notification with the requested values."""
        updated_row_count = 0
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
        self.sa_session.commit()
        return updated_row_count

    def get_user_notification_preferences(self, user: User) -> UserNotificationPreferences:
        """Gets the user's current notification preferences or the default ones if no preferences are set."""
        current_notification_preferences = user.preferences.get(NOTIFICATION_PREFERENCES_SECTION_NAME)
        if current_notification_preferences:
            try:
                return UserNotificationPreferences.model_validate_json(current_notification_preferences)
            except ValidationError:
                pass
        # Gracefully return default preferences is they don't exist or get corrupted
        return UserNotificationPreferences.default()

    def update_user_notification_preferences(
        self, user: User, request: UpdateUserNotificationPreferencesRequest
    ) -> UserNotificationPreferences:
        """Updates the user's notification preferences with the requested changes."""
        preferences = self.get_user_notification_preferences(user)
        preferences.update(request.preferences)
        user.preferences[NOTIFICATION_PREFERENCES_SECTION_NAME] = preferences.model_dump_json()
        self.sa_session.commit()
        return preferences

    def _register_supported_channels(self) -> Dict[str, NotificationChannelPlugin]:
        """Registers the supported notification channels in this server."""
        supported_channels: Dict[str, NotificationChannelPlugin] = {
            # Push notifications are handled client-side so no real plugin is needed
            "push": NoOpNotificationChannelPlugin(self.config),
        }

        if self.can_send_notifications_async:
            # Most additional channels require asynchronous processing and will be
            # handled by Celery tasks. Add their plugins here.
            supported_channels["email"] = EmailNotificationChannelPlugin(self.config)

        return supported_channels

    def get_supported_channels(self) -> Set[str]:
        """Returns the set of supported notification channels in this server."""
        return set(self.channel_plugins.keys())

    def cleanup_expired_notifications(self) -> CleanupResultSummary:
        """
        Permanently removes from the database all notifications (and user associations) that have expired.
        """
        notification_has_expired = Notification.expiration_time <= self._now

        expired_notifications_stmt = select(Notification.id).where(notification_has_expired)
        delete_stmt = delete(UserNotificationAssociation).where(
            UserNotificationAssociation.notification_id.in_(expired_notifications_stmt)
        )
        result = self.sa_session.execute(delete_stmt, execution_options={"synchronize_session": False})
        deleted_associations_count = result.rowcount

        delete_stmt = delete(Notification).where(notification_has_expired)
        result = self.sa_session.execute(delete_stmt)
        deleted_notifications_count = result.rowcount

        self.sa_session.commit()

        return CleanupResultSummary(deleted_notifications_count, deleted_associations_count)

    def _create_notification_model(
        self, payload: NotificationCreateData, galaxy_url: Optional[str] = None
    ) -> Notification:
        notification = Notification(
            payload.source,
            payload.category,
            payload.variant,
            payload.content.model_dump(),
        )
        notification.publication_time = payload.publication_time
        notification.expiration_time = payload.expiration_time
        notification.galaxy_url = galaxy_url
        return notification

    def _user_notifications_query(
        self, user: User, since: Optional[datetime] = None, active_only: Optional[bool] = True
    ):
        stmt = (
            select(*self.user_notification_columns)
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
            select(*self.broadcast_notification_columns)
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


# --------------------------------------
# Notification Recipients Resolver Implementations


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
        user_ids_from_groups_and_roles = {id for id, in self.sa_session.execute(union_stmt)}
        unique_user_ids.update(user_ids_from_groups_and_roles)

        stmt = select(User).where(User.id.in_(unique_user_ids))
        return self.sa_session.scalars(stmt).all()  # type:ignore[return-value]

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
            group_ids_from_roles = {id for id, in self.sa_session.execute(stmt) if id is not None}
            new_group_ids = group_ids_from_roles - processed_group_ids

            # Get role IDs associated with any of the given group IDs
            stmt = (
                select(GroupRoleAssociation.role_id)
                .select_from(GroupRoleAssociation)
                .where(GroupRoleAssociation.group_id.in_(group_ids))
                .distinct()
            )
            role_ids_from_groups = {id for id, in self.sa_session.execute(stmt) if id is not None}
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


# --------------------------------------
# Notification Channel Plugins Implementations


class NoOpNotificationChannelPlugin(NotificationChannelPlugin):
    def send(self, notification: Notification, user: User):
        pass


class TemplateFormats(str, Enum):
    HTML = "html"
    TXT = "txt"


class NotificationContext(BaseModel):
    """Information passed to the email template to render the body."""

    name: str
    user_email: str
    date: str
    hostname: str
    contact_email: str
    variant: str
    notification_settings_url: str
    content: AnyNotificationContent
    galaxy_url: Optional[str] = None


class EmailNotificationTemplateBuilder(Protocol):
    config: GalaxyAppConfiguration
    notification: Notification
    user: User

    def __init__(self, config: GalaxyAppConfiguration, notification: Notification, user: User):
        self.config = config
        self.notification = notification
        self.user = user

    def get_content(self, template_format: TemplateFormats) -> AnyNotificationContent:
        """Processes the notification content to be rendered in the email body.

        This should be implemented by each concrete template builder.
        """
        raise NotImplementedError

    def get_subject(self) -> str:
        """Returns the subject of the email to be sent.

        This should be implemented by each concrete template builder.
        """
        raise NotImplementedError

    def build_context(self, template_format: TemplateFormats) -> NotificationContext:
        notification = self.notification
        user = self.user
        notification_date = notification.publication_time if notification.publication_time else notification.create_time
        hostname = (
            urlparse(self.notification.galaxy_url).hostname if self.notification.galaxy_url else self.config.server_name
        )
        notification_settings_url = (
            f"{self.notification.galaxy_url}/user/notifications?preferences=true"
            if self.notification.galaxy_url
            else None
        )
        contact_email = self.config.error_email_to or None
        return NotificationContext(
            name=user.username,
            user_email=user.email,
            date=notification_date.strftime("%B %d, %Y"),
            hostname=hostname,
            contact_email=contact_email,
            notification_settings_url=notification_settings_url,
            variant=notification.variant,
            content=self.get_content(template_format),
            galaxy_url=self.notification.galaxy_url,
        )

    def get_body(self, template_format: TemplateFormats) -> str:
        template_path = f"mail/notifications/{self.notification.category}-email.{template_format.value}"
        context = self.build_context(template_format)
        return templates.render(
            template_path,
            context.model_dump(),
            self.config.templates_dir,
        )


class MessageEmailNotificationTemplateBuilder(EmailNotificationTemplateBuilder):

    markdown_to = {
        TemplateFormats.HTML: to_html,
        TemplateFormats.TXT: lambda x: x,  # TODO: strip markdown?
    }

    def get_content(self, template_format: TemplateFormats) -> AnyNotificationContent:
        content = MessageNotificationContent.model_construct(**self.notification.content)  # type:ignore[arg-type]
        content.message = self.markdown_to[template_format](content.message)
        return content

    def get_subject(self) -> str:
        content = cast(MessageNotificationContent, self.get_content(TemplateFormats.TXT))
        return f"[Galaxy] New message: {content.subject}"


class NewSharedItemEmailNotificationTemplateBuilder(EmailNotificationTemplateBuilder):

    def get_content(self, template_format: TemplateFormats) -> AnyNotificationContent:
        content = NewSharedItemNotificationContent.model_construct(**self.notification.content)  # type:ignore[arg-type]
        return content

    def get_subject(self) -> str:
        content = cast(NewSharedItemNotificationContent, self.get_content(TemplateFormats.TXT))
        return f"[Galaxy] New {content.item_type} shared with you: {content.item_name}"


class EmailNotificationChannelPlugin(NotificationChannelPlugin):

    # Register the supported email templates here
    email_templates_by_category: Dict[PersonalNotificationCategory, Type[EmailNotificationTemplateBuilder]] = {
        PersonalNotificationCategory.message: MessageEmailNotificationTemplateBuilder,
        PersonalNotificationCategory.new_shared_item: NewSharedItemEmailNotificationTemplateBuilder,
    }

    def send(self, notification: Notification, user: User):
        try:
            category = cast(PersonalNotificationCategory, notification.category)
            email_template_builder = self.email_templates_by_category.get(category)
            if email_template_builder is None:
                log.warning(f"No email template found for notification category '{notification.category}'.")
                return
            template_builder = email_template_builder(self.config, notification, user)
            subject = template_builder.get_subject()
            text_body = template_builder.get_body(TemplateFormats.TXT)
            html_body = template_builder.get_body(TemplateFormats.HTML)
            util.send_mail(
                frm=self.config.email_from,
                to=user.email,
                subject=subject,
                body=text_body,
                config=self.config,
                html=html_body,
            )
        except Exception as e:
            log.error(f"Error sending email notification to user {user.id}. Reason: {util.unicodify(e)}")
            pass
