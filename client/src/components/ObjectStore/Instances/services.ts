import { GalaxyApi } from "@/api";

import type { UserConcreteObjectStore } from "./types";

const updateUrl = "/api/object_store_instances/{uuid}";

export async function hide(instance: UserConcreteObjectStore) {
    const payload = { hidden: true };
    const { data: objectStore } = await GalaxyApi().PUT(updateUrl, {
        params: {
            path: { uuid: String(instance?.uuid) },
        },
        body: payload,
    });
    return objectStore;
}
