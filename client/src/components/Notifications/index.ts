import { type components } from "@/schema";

export type BaseUserNotification = components["schemas"]["UserNotificationResponse"];

export interface MessageNotification extends BaseUserNotification {
    category: "message";
    content: components["schemas"]["MessageNotificationContent"];
}

export interface SharedItemNotification extends BaseUserNotification {
    category: "new_shared_item";
    content: components["schemas"]["NewSharedItemNotificationContent"];
}

export type UserNotification = MessageNotification | SharedItemNotification;
