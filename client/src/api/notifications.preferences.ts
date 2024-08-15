import { type components, fetcher } from "@/api/schema";

type UserNotificationPreferences = components["schemas"]["UserNotificationPreferences"];

export interface UserNotificationPreferencesExtended extends UserNotificationPreferences {
    supportedChannels: string[];
}

const getNotificationsPreferences = fetcher.path("/api/notifications/preferences").method("get").create();
export async function getNotificationsPreferencesFromServer(): Promise<UserNotificationPreferencesExtended> {
    const { data, headers } = await getNotificationsPreferences({});
    return {
        ...data,
        supportedChannels: headers.get("supported-channels")?.split(",") ?? [],
    };
}

type UpdateUserNotificationPreferencesRequest = components["schemas"]["UpdateUserNotificationPreferencesRequest"];
const updateNotificationsPreferences = fetcher.path("/api/notifications/preferences").method("put").create();
export async function updateNotificationsPreferencesOnServer(request: UpdateUserNotificationPreferencesRequest) {
    const { data } = await updateNotificationsPreferences(request);
    return data;
}
