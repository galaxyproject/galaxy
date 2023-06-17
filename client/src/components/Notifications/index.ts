import type { components } from "@/schema";

export type UserNotification = components["schemas"]["UserNotificationResponse"];

export interface MessageNotification extends UserNotification {
    category: "message";
    content: components["schemas"]["MessageNotificationContent"];
}

export interface SharedItemNotification extends UserNotification {
    category: "new_shared_item";
    content: components["schemas"]["NewSharedItemNotificationContent"];
}
