import { GalaxyApi, type GalaxyApiPaths } from "@/api";
import { rethrowSimple } from "@/utils/simple-error";

// TODO: Move these functions to broadcastStore and refactor other calls to go through the store

export async function fetchAllBroadcasts() {
    const { data, error } = await GalaxyApi().GET("/api/notifications/broadcast");
    if (error) {
        rethrowSimple(error);
    }
    return data;
}

type CreateBroadcastNotificationRequestBody =
    GalaxyApiPaths["/api/notifications/broadcast"]["post"]["requestBody"]["content"]["application/json"];
export async function createBroadcast(broadcast: CreateBroadcastNotificationRequestBody) {
    const { data, error } = await GalaxyApi().POST("/api/notifications/broadcast", {
        body: broadcast,
    });

    if (error) {
        rethrowSimple(error);
    }

    return data;
}

type UpdateBroadcastNotificationRequestBody =
    GalaxyApiPaths["/api/notifications/broadcast/{notification_id}"]["put"]["requestBody"]["content"]["application/json"];
export async function updateBroadcast(id: string, broadcast: UpdateBroadcastNotificationRequestBody) {
    const { data, error } = await GalaxyApi().PUT("/api/notifications/broadcast/{notification_id}", {
        params: {
            path: { notification_id: id },
        },
        body: broadcast,
    });

    if (error) {
        rethrowSimple(error);
    }

    return data;
}
