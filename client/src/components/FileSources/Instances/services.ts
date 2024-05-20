import { fetcher } from "@/api/schema/fetcher";

export const create = fetcher.path("/api/file_source_instances").method("post").create();
export const update = fetcher.path("/api/file_source_instances/{user_file_source_id}").method("put").create();
