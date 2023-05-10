import { fetcher } from "@/schema";

const _loadBroadcastsFromServer = fetcher.path("/api/notifications/broadcast").method("get").create();

export async function loadBroadcastsFromServer() {
    const { data } = await _loadBroadcastsFromServer({});
    return data;
}
