import { type components } from "@/api/schema";

export type BaseUserNotification = components["schemas"]["UserNotificationResponse"];
export type UserNotificationPreferences = components["schemas"]["UserNotificationPreferences"]["preferences"];
export type NotificationChannel = keyof components["schemas"]["NotificationChannelSettings"];
export type NotificationCategory = components["schemas"]["PersonalNotificationCategory"];

export interface MessageNotification extends BaseUserNotification {
    category: "message";
    content: components["schemas"]["MessageNotificationContent"];
}

export interface SharedItemNotification extends BaseUserNotification {
    category: "new_shared_item";
    content: components["schemas"]["NewSharedItemNotificationContent"];
}

type NotificationCreateData = components["schemas"]["NotificationCreateData"];

export interface MessageNotificationCreateData extends NotificationCreateData {
    category: "message";
    content: components["schemas"]["MessageNotificationContent"];
}

export type NotificationCreateRequest = components["schemas"]["NotificationCreateRequest"];

export interface MessageNotificationCreateRequest extends NotificationCreateRequest {
    notification: MessageNotificationCreateData;
}

export type UserNotification = MessageNotification | SharedItemNotification;

export type NotificationChanges = components["schemas"]["UserNotificationUpdateRequest"];

export type UserNotificationsBatchUpdateRequest = components["schemas"]["UserNotificationsBatchUpdateRequest"];

export type NotificationVariants = components["schemas"]["NotificationVariant"];

export type NewSharedItemNotificationContentItemType =
    components["schemas"]["NewSharedItemNotificationContent"]["item_type"];
