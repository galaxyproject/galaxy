import { type components, fetcher } from "@/schema";

const getNotificationsPreferences = fetcher.path("/api/notifications/preferences").method("get").create();
export async function getNotificationsPreferencesFromServer() {
    const { data } = await getNotificationsPreferences({});
    return data;
}

type UpdateUserNotificationPreferencesRequest = components["schemas"]["UpdateUserNotificationPreferencesRequest"];
const updateNotificationsPreferences = fetcher.path("/api/notifications/preferences").method("put").create();
export async function updateNotificationsPreferencesOnServer(request: UpdateUserNotificationPreferencesRequest) {
    const { data } = await updateNotificationsPreferences(request);
    return data;
}
