import { type components, fetcher } from "@/schema";

type BroadcastNotificationResponse = components["schemas"]["BroadcastNotificationResponse"];

const getBroadcast = fetcher.path("/api/notifications/broadcast/{notification_id}").method("get").create();
export async function loadBroadcast(id: string): Promise<BroadcastNotificationResponse> {
    const { data } = await getBroadcast({ notification_id: id });
    return data;
}

const getBroadcasts = fetcher.path("/api/notifications/broadcast").method("get").create();
export async function loadBroadcasts(): Promise<BroadcastNotificationResponse[]> {
    const { data } = await getBroadcasts({});
    return data;
}

const postBroadcast = fetcher.path("/api/notifications/broadcast").method("post").create();
type BroadcastNotificationCreateRequest = components["schemas"]["BroadcastNotificationCreateRequest"];
export async function createBroadcast(broadcast: BroadcastNotificationCreateRequest) {
    const { data } = await postBroadcast(broadcast);
    return data;
}

const putBroadcast = fetcher.path("/api/notifications/broadcast/{notification_id}").method("put").create();
type NotificationBroadcastUpdateRequest = components["schemas"]["NotificationBroadcastUpdateRequest"];
export async function updateBroadcast(id: string, broadcast: NotificationBroadcastUpdateRequest) {
    const { data } = await putBroadcast({ notification_id: id, ...broadcast });
    return data;
}
