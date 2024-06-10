import type { UserFileSourceModel } from "@/api/fileSources";
import { fetcher } from "@/api/schema/fetcher";

export const create = fetcher.path("/api/file_source_instances").method("post").create();
export const test = fetcher.path("/api/file_source_instances/test").method("post").create();
export const update = fetcher.path("/api/file_source_instances/{user_file_source_id}").method("put").create();

export async function hide(instance: UserFileSourceModel) {
    const payload = { hidden: true };
    const args = { user_file_source_id: String(instance?.uuid) };
    const { data: fileSource } = await update({ ...args, ...payload });
    return fileSource;
}
