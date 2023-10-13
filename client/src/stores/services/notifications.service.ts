import { type components, fetcher } from "@/api/schema";
import type { UserNotification } from "@/components/Notifications";

const getNotifications = fetcher.path("/api/notifications").method("get").create();

export async function loadNotificationsFromServer() {
    const { data } = await getNotifications({});
    return data as UserNotification[];
}

type UserNotificationsBatchUpdateRequest = components["schemas"]["UserNotificationsBatchUpdateRequest"];

const putBatchNotifications = fetcher.path("/api/notifications").method("put").create();
export async function updateBatchNotificationsOnServer(request: UserNotificationsBatchUpdateRequest) {
    const { data } = await putBatchNotifications({
        notification_ids: request.notification_ids,
        changes: request.changes,
    });
    return data;
}

const getNotificationStatus = fetcher.path("/api/notifications/status").method("get").create();
export async function loadNotificationsStatus(since: Date) {
    const { data } = await getNotificationStatus({ since: since.toISOString().replace("Z", "") });
    return data;
}
