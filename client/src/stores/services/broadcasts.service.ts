import { fetcher } from "@/schema";

const getBroadcastNotifications = fetcher.path("/api/notifications/broadcast").method("get").create();

export async function loadBroadcastsFromServer() {
    const { data } = await getBroadcastNotifications({});
    return data;
}
