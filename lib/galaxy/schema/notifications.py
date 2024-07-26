from datetime import datetime
from enum import Enum
from typing import (
    Any,
    Dict,
    Generic,
    List,
    Optional,
    Union,
)

from pydantic import (
    ConfigDict,
    Field,
    RootModel,
)
from typing_extensions import (
    Annotated,
    Literal,
)

from galaxy.schema.fields import (
    DecodedDatabaseIdField,
    EncodedDatabaseIdField,
)
from galaxy.schema.generics import (
    DatabaseIdT,
    GenericModel,
)
from galaxy.schema.schema import Model
from galaxy.schema.types import (
    AbsoluteOrRelativeUrl,
    OffsetNaiveDatetime,
)


class NotificationVariant(str, Enum):
    """The notification variant communicates the intent or relevance of the notification."""

    info = "info"
    warning = "warning"
    urgent = "urgent"


# Register a new category by adding it to the corresponding Enum:
# - NotificationCategory: these notification categories will be always received by the user.
# - OptionalNotificationCategory: these notifications can be opt-out by the user.
# Then register the content model further down below.


class MandatoryNotificationCategory(str, Enum):
    """These notification categories cannot be opt-out by the user.

    The user will always receive notifications from these categories.
    """

    broadcast = "broadcast"


class PersonalNotificationCategory(str, Enum):
    """These notification categories can be opt-out by the user and will be
    displayed in the notification preferences.
    """

    message = "message"
    new_shared_item = "new_shared_item"
    # TODO: enable this and create content model when we have a hook for completed workflows
    # workflow_execution_completed = "workflow_execution_completed"


NotificationCategory = Union[MandatoryNotificationCategory, PersonalNotificationCategory]


class MessageNotificationContentBase(Model):
    subject: str = Field(..., title="Subject", description="The subject of the notification.")
    message: str = Field(..., title="Message", description="The message of the notification (supports Markdown).")


class ActionLink(Model):
    """An action link to be displayed in the notification as a button."""

    action_name: str = Field(..., title="Action name", description="The name of the action, will be the button title.")
    link: AbsoluteOrRelativeUrl = Field(
        ..., title="Link", description="The link to be opened when the button is clicked."
    )


# Create the corresponding model for the registered category below and
# add it to AnyNotificationContent Union.


class BroadcastNotificationContent(MessageNotificationContentBase):
    category: Literal[MandatoryNotificationCategory.broadcast] = MandatoryNotificationCategory.broadcast
    action_links: Optional[List[ActionLink]] = Field(
        None,
        title="Action links",
        description="The optional action links (buttons) to be displayed in the notification.",
    )


class MessageNotificationContent(MessageNotificationContentBase):
    category: Literal[PersonalNotificationCategory.message] = PersonalNotificationCategory.message


SharableItemType = Literal[
    "history",
    "workflow",
    "visualization",
    "page",
]


class NewSharedItemNotificationContent(Model):
    category: Literal[PersonalNotificationCategory.new_shared_item] = PersonalNotificationCategory.new_shared_item
    item_type: SharableItemType = Field(..., title="Item type", description="The type of the shared item.")
    item_name: str = Field(..., title="Item name", description="The name of the shared item.")
    owner_name: str = Field(..., title="Owner name", description="The name of the owner of the shared item.")
    slug: str = Field(..., title="Slug", description="The slug of the shared item. Used for the link to the item.")


NotificationContentField = Field(
    default=...,
    discriminator="category",
    title="Content",
    description="The content of the notification. The structure depends on the category.",
)

AnyUserNotificationContent = Annotated[
    Union[
        MessageNotificationContent,
        NewSharedItemNotificationContent,
    ],
    NotificationContentField,
]

AnyNotificationContent = Annotated[
    Union[
        AnyUserNotificationContent,
        BroadcastNotificationContent,
    ],
    NotificationContentField,
]


NotificationIdField = Field(
    ...,
    title="ID",
    description="The encoded ID of the notification.",
)

NotificationSourceField = Field(
    ...,
    title="Source",
    description="The source of the notification. Represents the agent that created the notification. E.g. 'galaxy' or 'admin'.",
)

NotificationCategoryField = Field(
    ...,
    title="Category",
    description="The category of the notification. Represents the type of the notification. E.g. 'message' or 'new_shared_item'.",
)

NotificationVariantField = Field(
    ...,
    title="Variant",
    description="The variant of the notification. Represents the intent or relevance of the notification. E.g. 'info' or 'urgent'.",
)

NotificationCreateTimeField = Field(
    ...,
    title="Create time",
    description="The time when the notification was created.",
)

NotificationUpdateTimeField = Field(
    ...,
    title="Update time",
    description="The time when the notification was last updated.",
)

NotificationPublicationTimeField = Field(
    ...,
    title="Publication time",
    description="The time when the notification was published. Notifications can be created and then published at a later time.",
)

NotificationExpirationTimeField = Field(
    None,
    title="Expiration time",
    description="The time when the notification will expire. If not set, the notification will never expire. Expired notifications will be permanently deleted.",
)


class NotificationResponse(Model):
    """Basic common fields for all notification responses."""

    id: EncodedDatabaseIdField = NotificationIdField
    source: str = NotificationSourceField
    category: NotificationCategory = NotificationCategoryField
    variant: NotificationVariant = NotificationVariantField
    create_time: datetime = NotificationCreateTimeField
    update_time: datetime = NotificationUpdateTimeField
    publication_time: datetime = NotificationPublicationTimeField
    expiration_time: Optional[datetime] = NotificationExpirationTimeField
    content: AnyNotificationContent
    model_config = ConfigDict(from_attributes=True)


class UserNotificationResponse(NotificationResponse):
    """A notification response specific to the user."""

    category: PersonalNotificationCategory = NotificationCategoryField
    content: AnyUserNotificationContent
    seen_time: Optional[datetime] = Field(
        None,
        title="Seen time",
        description="The time when the notification was seen by the user. If not set, the notification was not seen yet.",
    )
    deleted: bool = Field(
        ...,
        title="Deleted",
        description="Whether the notification is marked as deleted by the user. Deleted notifications don't show up in the notification list.",
    )


class BroadcastNotificationResponse(NotificationResponse):
    """A notification response specific for broadcasting."""

    category: Literal[MandatoryNotificationCategory.broadcast] = MandatoryNotificationCategory.broadcast
    content: BroadcastNotificationContent


class UserNotificationListResponse(RootModel):
    """A list of user notifications."""

    root: List[UserNotificationResponse]


class BroadcastNotificationListResponse(RootModel):
    """A list of broadcast notifications."""

    root: List[BroadcastNotificationResponse]


class NotificationStatusSummary(Model):
    """A summary of the notification status for a user. Contains only updates since a particular timestamp."""

    total_unread_count: int = Field(
        ..., title="Total unread count", description="The total number of unread notifications for the user."
    )
    notifications: List[UserNotificationResponse] = Field(
        ..., title="Notifications", description="The list of updated notifications for the user."
    )
    broadcasts: List[BroadcastNotificationResponse] = Field(
        ..., title="Broadcasts", description="The list of updated broadcasts."
    )


class NotificationCreateData(Model):
    """Basic common fields for all notification create requests."""

    source: str = NotificationSourceField
    category: NotificationCategory = NotificationCategoryField
    variant: NotificationVariant = NotificationVariantField
    content: AnyNotificationContent
    publication_time: Optional[OffsetNaiveDatetime] = Field(
        None,
        title="Publication time",
        description="The time when the notification should be published. Notifications can be created and then scheduled to be published at a later time.",
    )
    expiration_time: Optional[OffsetNaiveDatetime] = Field(
        None,
        title="Expiration time",
        description="The time when the notification should expire. By default it will expire after 6 months. Expired notifications will be permanently deleted.",
    )


class GenericNotificationRecipients(GenericModel, Generic[DatabaseIdT]):
    """The recipients of a notification. Can be a combination of users, groups and roles."""

    user_ids: List[DatabaseIdT] = Field(
        default=[],
        title="User IDs",
        description="The list of encoded user IDs of the users that should receive the notification.",
    )
    group_ids: List[DatabaseIdT] = Field(
        default=[],
        title="Group IDs",
        description="The list of encoded group IDs of the groups that should receive the notification.",
    )
    role_ids: List[DatabaseIdT] = Field(
        default=[],
        title="Role IDs",
        description="The list of encoded role IDs of the roles that should receive the notification.",
    )


class GenericNotificationCreate(GenericModel, Generic[DatabaseIdT]):
    """Contains the recipients and the notification to create."""

    recipients: GenericNotificationRecipients[DatabaseIdT] = Field(
        ...,
        title="Recipients",
        description="The recipients of the notification. Can be a combination of users, groups and roles.",
    )
    notification: NotificationCreateData = Field(
        ...,
        title="Notification",
        description="The notification to create. The structure depends on the category.",
    )


class NotificationCreateRequest(GenericNotificationCreate[int]):
    galaxy_url: Optional[str] = Field(
        None,
        title="Galaxy URL",
        description="The URL of the Galaxy instance. Used to generate links in the notification content.",
    )


NotificationRecipients = GenericNotificationRecipients[int]


NotificationCreateRequestBody = GenericNotificationCreate[DecodedDatabaseIdField]


class BroadcastNotificationCreateRequest(NotificationCreateData):
    """A notification create request specific for broadcasting."""

    category: Literal[MandatoryNotificationCategory.broadcast] = MandatoryNotificationCategory.broadcast
    content: BroadcastNotificationContent = Field(
        ...,
        title="Content",
        description="The content of the broadcast notification. Broadcast notifications are displayed prominently to all users and can contain action links to redirect the user to a specific page.",
    )


class NotificationCreatedResponse(Model):
    total_notifications_sent: int = Field(
        ...,
        title="Total notifications sent",
        description="The total number of notifications that were sent to the recipients.",
    )
    notification: NotificationResponse = Field(
        ...,
        title="Notification",
        description="The notification that was created. The structure depends on the category.",
    )


class NotificationUpdateRequest(Model):
    def has_changes(self) -> bool:
        """Whether the notification update request contains at least one change."""
        return any(getattr(self, field) is not None for field in self.__fields__.keys())


class UserNotificationUpdateRequest(NotificationUpdateRequest):
    """A notification update request specific to the user."""

    seen: Optional[bool] = Field(
        None,
        title="Seen",
        description="Whether the notification should be marked as seen by the user. If not set, the notification will not be changed.",
    )
    deleted: Optional[bool] = Field(
        None,
        title="Deleted",
        description="Whether the notification should be marked as deleted by the user. If not set, the notification will not be changed.",
    )


class NotificationBroadcastUpdateRequest(NotificationUpdateRequest):
    """A notification update request specific for broadcasting."""

    source: Optional[str] = Field(
        None,
        title="Source",
        description="The source of the notification. Represents the agent that created the notification.",
    )
    variant: Optional[NotificationVariant] = Field(
        None,
        title="Variant",
        description="The variant of the notification. Used to express the importance of the notification.",
    )
    publication_time: Optional[OffsetNaiveDatetime] = Field(
        None,
        title="Publication time",
        description="The time when the notification should be published. Notifications can be created and then scheduled to be published at a later time.",
    )
    expiration_time: Optional[OffsetNaiveDatetime] = Field(
        None,
        title="Expiration time",
        description="The time when the notification should expire. By default it will expire after 6 months. Expired notifications will be permanently deleted.",
    )
    content: Optional[BroadcastNotificationContent] = Field(
        None,
        title="Content",
        description="The content of the broadcast notification. Broadcast notifications are displayed prominently to all users and can contain action links to redirect the user to a specific page.",
    )


class NotificationsBatchRequest(Model):
    notification_ids: List[DecodedDatabaseIdField] = Field(
        ...,
        title="Notification IDs",
        description="The list of encoded notification IDs of the notifications that should be updated.",
    )


class UserNotificationsBatchUpdateRequest(NotificationsBatchRequest):
    """A batch update request specific for user notifications."""

    changes: UserNotificationUpdateRequest = Field(
        ...,
        title="Changes",
        description="The changes that should be applied to the notifications. Only the fields that are set will be changed.",
    )


class NotificationsBatchUpdateResponse(Model):
    """The response of a batch update request."""

    updated_count: int = Field(
        ...,
        title="Updated count",
        description="The number of notifications that were updated.",
    )


class NotificationChannelSettings(Model):
    """The settings for each channel of a notification category."""

    push: bool = Field(
        default=True,
        title="Push",
        description="Whether the user wants to receive push notifications in the browser for this category.",
    )
    email: bool = Field(
        default=True,
        title="Email",
        description=(
            "Whether the user wants to receive email notifications for this category. "
            "This setting will be ignored unless the server supports asynchronous tasks."
        ),
    )
    # TODO: Add more channels here and implement the corresponding plugin in lib/galaxy/managers/notification.py
    # matrix: bool # Possible future Matrix.org integration?


class NotificationCategorySettings(Model):
    """The settings for a notification category."""

    enabled: bool = Field(
        default=True, title="Enabled", description="Whether the user wants to receive notifications for this category."
    )
    channels: NotificationChannelSettings = Field(
        default=NotificationChannelSettings(),
        title="Channels",
        description="The channels that the user wants to receive notifications from for this category.",
    )


PersonalNotificationPreferences = Dict[PersonalNotificationCategory, NotificationCategorySettings]


def get_default_personal_notification_preferences() -> PersonalNotificationPreferences:
    """Get the default personal notification preferences."""
    return {category: NotificationCategorySettings() for category in PersonalNotificationCategory.__members__.values()}


def get_default_personal_notification_preferences_example() -> Dict[str, Any]:
    return {
        category: NotificationCategorySettings().model_dump()
        for category in PersonalNotificationCategory.__members__.values()
    }


class UserNotificationPreferences(Model):
    """Contains the full notification preferences of a user."""

    preferences: PersonalNotificationPreferences = Field(
        ...,
        title="Preferences",
        description="The notification preferences of the user.",
    )

    def update(
        self,
        other: Union["UserNotificationPreferences", PersonalNotificationPreferences],
    ):
        """Convenience method to update the preferences with the preferences of another object."""
        if isinstance(other, UserNotificationPreferences):
            self.preferences.update(other.preferences)
        else:
            self.preferences.update(other)

    def get(self, category: PersonalNotificationCategory) -> NotificationCategorySettings:
        """Get the notification preferences for a specific category."""
        return self.preferences[category]

    @classmethod
    def default(cls):
        """Create a new instance with default preferences."""
        return cls(preferences=get_default_personal_notification_preferences())

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "preferences": get_default_personal_notification_preferences_example(),
                }
            ]
        }
    )


class UpdateUserNotificationPreferencesRequest(Model):
    """Contains the new notification preferences of a user."""

    preferences: PersonalNotificationPreferences = Field(
        ...,
        title="Preferences",
        description="The new notification preferences of the user.",
    )
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "preferences": get_default_personal_notification_preferences_example(),
                }
            ]
        }
    )
