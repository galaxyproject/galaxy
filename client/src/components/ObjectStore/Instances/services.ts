import { fetcher } from "@/api/schema/fetcher";

import type { UserConcreteObjectStore } from "./types";

export const create = fetcher.path("/api/object_store_instances").method("post").create();
export const test = fetcher.path("/api/object_store_instances/test").method("post").create();
export const testInstance = fetcher
    .path("/api/object_store_instances/{user_object_store_id}/test")
    .method("get")
    .create();
export const update = fetcher.path("/api/object_store_instances/{user_object_store_id}").method("put").create();
export const testUpdate = fetcher
    .path("/api/object_store_instances/{user_object_store_id}/test")
    .method("post")
    .create();

export async function hide(instance: UserConcreteObjectStore) {
    const payload = { hidden: true };
    const args = { user_object_store_id: String(instance?.uuid) };
    const { data: objectStore } = await update({ ...args, ...payload });
    return objectStore;
}
