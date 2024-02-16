import { type components, fetcher } from "@/api/schema";

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

export type NotificationChanges = components["schemas"]["UserNotificationUpdateRequest"];

export type UserNotificationsBatchUpdateRequest = components["schemas"]["UserNotificationsBatchUpdateRequest"];

export type NotificationVariants = components["schemas"]["NotificationVariant"];

export type NewSharedItemNotificationContentItemType =
    components["schemas"]["NewSharedItemNotificationContent"]["item_type"];

type UserNotificationUpdateRequest = components["schemas"]["UserNotificationUpdateRequest"];

type NotificationCreateRequest = components["schemas"]["NotificationCreateRequest"];

type NotificationResponse = components["schemas"]["NotificationResponse"];

const getNotification = fetcher.path("/api/notifications/{notification_id}").method("get").create();

export async function loadNotification(id: string): Promise<NotificationResponse> {
    const { data } = await getNotification({ notification_id: id });
    return data;
}

const postNotification = fetcher.path("/api/notifications").method("post").create();

export async function sendNotification(notification: NotificationCreateRequest) {
    const { data } = await postNotification(notification);
    return data;
}

const putNotification = fetcher.path("/api/notifications/{notification_id}").method("put").create();

export async function updateNotification(id: string, notification: UserNotificationUpdateRequest) {
    const { data } = await putNotification({ notification_id: id, ...notification });
    return data;
}

const getNotifications = fetcher.path("/api/notifications").method("get").create();

export async function loadNotificationsFromServer(): Promise<UserNotification[]> {
    const { data } = await getNotifications({});
    return data as UserNotification[];
}

const putBatchNotifications = fetcher.path("/api/notifications").method("put").create();

export async function updateBatchNotificationsOnServer(request: UserNotificationsBatchUpdateRequest) {
    const { data } = await putBatchNotifications(request);
    return data;
}

const getNotificationStatus = fetcher.path("/api/notifications/status").method("get").create();

export async function loadNotificationsStatus(since: Date) {
    const { data } = await getNotificationStatus({ since: since.toISOString().replace("Z", "") });
    return data;
}
