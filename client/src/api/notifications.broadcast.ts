import { type components, fetcher } from "@/api/schema";

type BroadcastNotificationResponse = components["schemas"]["BroadcastNotificationResponse"];

const broadcastFetcher = fetcher.path("/api/notifications/broadcast/{notification_id}").method("get").create();
export async function fetchBroadcast(id: string): Promise<BroadcastNotificationResponse> {
    const { data } = await broadcastFetcher({ notification_id: id });
    return data;
}

const broadcastsFetcher = fetcher.path("/api/notifications/broadcast").method("get").create();
export async function fetchAllBroadcasts(): Promise<BroadcastNotificationResponse[]> {
    const { data } = await broadcastsFetcher({});
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
