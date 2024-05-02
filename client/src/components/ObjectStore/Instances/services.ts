import { fetcher } from "@/api/schema/fetcher";

export const create = fetcher.path("/api/object_store_instances").method("post").create();
export const update = fetcher.path("/api/object_store_instances/{user_object_store_id}").method("put").create();
