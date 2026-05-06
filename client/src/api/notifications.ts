import { GalaxyApi } from "@/api";
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

export interface ToolInstallationRequestNotificationContent {
    category: "tool_installation_request";
    tool_names: string[];
    tool_url?: string;
    description: string;
    scientific_domain?: string;
    requested_version?: string;
    requester_email?: string | null;
    workflow_id?: string;
    additional_remarks?: string;
}

export interface ToolInstallationRequestNotification extends BaseUserNotification {
    category: "tool_installation_request";
    content: ToolInstallationRequestNotificationContent;
}

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

export interface ToolInstallationRequestSubmitContent {
    tool_names: string[];
    tool_url?: string;
    description: string;
    scientific_domain?: string;
    requested_version?: string;
    workflow_id?: string;
    additional_remarks?: string;
}

/** Submit a tool installation request as the authenticated user.
 *  Returns the encoded notification ID so the caller can link to it.
 */
export async function submitToolInstallationRequest(content: ToolInstallationRequestSubmitContent): Promise<string> {
    const { data, error } = await GalaxyApi().POST("/api/notifications", {
        body: {
            recipients: { user_ids: [], group_ids: [], role_ids: [] },
            notification: {
                source: "tool_installation_request_form",
                category: "tool_installation_request",
                variant: "info",
                content: {
                    category: "tool_installation_request",
                    ...content,
                },
            },
        },
    });
    if (error) {
        const errorObject = error as { err_msg?: string; message?: string };
        const message = errorObject.err_msg || errorObject.message || "Failed to submit notification.";
        throw new Error(message);
    }
    return (data as { notification: { id: string } }).notification.id;
}
