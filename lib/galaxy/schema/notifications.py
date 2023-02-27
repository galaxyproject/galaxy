import json
from datetime import datetime
from enum import Enum
from typing import (
    Any,
    List,
    Optional,
    Union,
)

from pydantic import (
    AnyUrl,
    Field,
)
from pydantic.utils import GetterDict
from typing_extensions import (
    Annotated,
    Literal,
)

from galaxy.schema.fields import (
    DecodedDatabaseIdField,
    EncodedDatabaseIdField,
)
from galaxy.schema.schema import (
    CreateTimeField,
    Model,
    UpdateTimeField,
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


class OptionalNotificationCategory(str, Enum):
    """These notification categories can be opt-out by the user and will be
    displayed in the notification preferences.
    """

    message = "message"
    near_quota_limit = "near_quota_limit"
    new_history_shared = "new_history_shared"
    new_workflow_shared = "new_workflow_shared"
    new_page_shared = "new_page_shared"
    new_visualization_shared = "new_page_shared"
    workflow_execution_completed = "workflow_execution_completed"


NotificationCategory = Union[MandatoryNotificationCategory, OptionalNotificationCategory]


class NotificationContentBase(Model):
    subject: str
    message: str  # markdown?


class ActionLink(Model):
    action_name: str
    link: AnyUrl


# Create the corresponding model for the registered category below and
# add it to AnyNotificationContent Union.


class BroadcastNotificationContent(NotificationContentBase):
    category: Literal[MandatoryNotificationCategory.broadcast] = MandatoryNotificationCategory.broadcast
    action_links: List[ActionLink]


class NotificationMessageContent(NotificationContentBase):
    category: Literal[OptionalNotificationCategory.message] = OptionalNotificationCategory.message


class NearQuotaLimitNotificationContent(Model):
    category: Literal[OptionalNotificationCategory.near_quota_limit] = OptionalNotificationCategory.near_quota_limit


class NewSharedItemNotificationContent(Model):
    share_link: AnyUrl


class NewHistorySharedNotificationContent(NewSharedItemNotificationContent):
    category: Literal[OptionalNotificationCategory.new_history_shared] = OptionalNotificationCategory.new_history_shared


class NewWorkflowSharedNotificationContent(NewSharedItemNotificationContent):
    category: Literal[
        OptionalNotificationCategory.new_workflow_shared
    ] = OptionalNotificationCategory.new_workflow_shared


class NewPageSharedNotificationContent(NewSharedItemNotificationContent):
    category: Literal[OptionalNotificationCategory.new_page_shared] = OptionalNotificationCategory.new_page_shared


class NewVisualizationSharedNotificationContent(NewSharedItemNotificationContent):
    category: Literal[
        OptionalNotificationCategory.new_visualization_shared
    ] = OptionalNotificationCategory.new_visualization_shared


class WorkflowExecutionCompletedNotificationContent(Model):
    category: Literal[
        OptionalNotificationCategory.workflow_execution_completed
    ] = OptionalNotificationCategory.workflow_execution_completed
    workflow_id: EncodedDatabaseIdField
    invocation_id: EncodedDatabaseIdField


AnyNotificationContent = Annotated[
    Union[
        BroadcastNotificationContent,
        NotificationMessageContent,
        NearQuotaLimitNotificationContent,
    ],
    Field(discriminator="category"),
]


class NotificationGetter(GetterDict):
    """Helper to convert a Notification ORM model into a NotificationResponse.
    For more information: https://docs.pydantic.dev/usage/models/#data-binding
    """

    def get(self, key: Any, default: Any = None) -> Any:
        # The `content` column of the ORM model is a JSON string that needs to be passed
        # as a dictionary to the `from_orm` constructor to build the correct `AnyNotificationContent`.
        if key in {"content"} and isinstance(self._obj.content, str):
            return json.loads(self._obj.content)

        return super().get(key, default)


class NotificationResponse(Model):
    id: EncodedDatabaseIdField
    source: str
    category: NotificationCategory
    variant: NotificationVariant
    create_time: datetime = CreateTimeField
    update_time: datetime = UpdateTimeField
    publication_time: datetime
    expiration_time: Optional[datetime]
    content: AnyNotificationContent

    class Config:
        orm_mode = True
        getter_dict = NotificationGetter


class UserNotificationResponse(NotificationResponse):
    seen_time: Optional[datetime]
    favorite: bool
    deleted: bool


class NotificationListResponse(Model):
    __root__: List[UserNotificationResponse]


class NotificationStatusSummary(Model):
    unread_count: int
    updated_notifications: List[UserNotificationResponse]


class NotificationCreateData(Model):
    source: str
    category: NotificationCategory
    variant: NotificationVariant
    content: AnyNotificationContent
    publication_time: Optional[datetime]
    expiration_time: Optional[datetime]


class NotificationRecipients(Model):
    user_ids: List[DecodedDatabaseIdField] = Field(default=[])
    group_ids: List[DecodedDatabaseIdField] = Field(default=[])
    role_ids: List[DecodedDatabaseIdField] = Field(default=[])


class NotificationCreateRequest(Model):
    recipients: NotificationRecipients
    notification: NotificationCreateData


class NotificationBroadcastCreateRequest(NotificationCreateData):
    category: Literal[MandatoryNotificationCategory.broadcast]


class NotificationCreateResponse(Model):
    total_notifications_sent: int
    notification: NotificationResponse


class NotificationUpdateRequest(Model):
    seen: Optional[bool]
    favorite: Optional[bool]
    deleted: Optional[bool]
    # Admin only
    publication_time: Optional[datetime]
    expiration_time: Optional[datetime]


class NotificationsBatchRequest(Model):
    notification_ids: List[DecodedDatabaseIdField]


class NotificationsBatchUpdateRequest(NotificationsBatchRequest):
    changes: NotificationUpdateRequest


class NotificationChannels(Model):
    galaxy: bool
    popup: bool
    # email: bool # Not supported for now
    # matrix: bool # Possible future Matrix.org integration?


class NotificationChannelSettings(Model):
    category: OptionalNotificationCategory
    channels: NotificationChannels


class NotificationUserPreferences(Model):
    __root__: List[NotificationChannelSettings]
