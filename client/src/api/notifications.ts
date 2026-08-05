import { GalaxyApi } from "@/api";
import type { components } from "@/api/schema";
import { rethrowSimple } from "@/utils/simple-error";

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

export interface StorageOperationNotification extends BaseUserNotification {
    category: "storage_operation";
    content: components["schemas"]["StorageOperationNotificationContent"];
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

export type ToolInstallationRequestNotificationContent =
    components["schemas"]["ToolInstallationRequestNotificationContent"];

export type RequestedTool = components["schemas"]["RequestedTool"];

export interface ToolInstallationRequestNotification extends BaseUserNotification {
    category: "tool_installation_request";
    content: ToolInstallationRequestNotificationContent;
}

/**
 * Caller-supplied fields for a tool installation request. The server-stamped
 * `category`/`requester_email`/`is_confirmation` fields are excluded; the
 * service always derives them server-side.
 */
export type ToolInstallationRequestInput = Omit<
    ToolInstallationRequestNotificationContent,
    "category" | "requester_email" | "is_confirmation"
>;

export type UserNotification =
    | MessageNotification
    | SharedItemNotification
    | StorageOperationNotification
    | ToolInstallationRequestNotification;

export type NotificationChanges = components["schemas"]["UserNotificationUpdateRequest"];

export type UserNotificationsBatchUpdateRequest = components["schemas"]["UserNotificationsBatchUpdateRequest"];

export type NotificationVariants = components["schemas"]["NotificationVariant"];

export type NewSharedItemNotificationContentItemType =
    components["schemas"]["NewSharedItemNotificationContent"]["item_type"];

/** Submit a tool installation request as the authenticated user. */
export async function submitToolInstallationRequest(content: ToolInstallationRequestInput) {
    const { error } = await GalaxyApi().POST("/api/notifications", {
        body: {
            recipients: { user_ids: [], group_ids: [], role_ids: [] },
            notification: {
                source: "tool_installation_request_form",
                category: "tool_installation_request",
                variant: "info",
                content: {
                    ...content,
                    category: "tool_installation_request",
                },
            },
        },
    });
    if (error) {
        rethrowSimple(error);
    }
}
