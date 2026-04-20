import type { components } from "@/api/schema";

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

export interface ToolRequestNotificationContent {
    category: "tool_request";
    tool_name: string;
    tool_url?: string;
    description: string;
    scientific_domain?: string;
    requested_version?: string;
    conda_available?: boolean;
    test_data_available?: boolean;
    requester_name?: string;
    requester_email: string;
    requester_affiliation?: string;
}

export interface ToolRequestNotification extends BaseUserNotification {
    category: "tool_request";
    content: ToolRequestNotificationContent;
}

export type UserNotification = MessageNotification | SharedItemNotification | ToolRequestNotification;

export type NotificationChanges = components["schemas"]["UserNotificationUpdateRequest"];

export type UserNotificationsBatchUpdateRequest = components["schemas"]["UserNotificationsBatchUpdateRequest"];

export type NotificationVariants = components["schemas"]["NotificationVariant"];

export type NewSharedItemNotificationContentItemType =
    components["schemas"]["NewSharedItemNotificationContent"]["item_type"];
