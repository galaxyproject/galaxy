import { client } from "@/api";
import { type UserFileSourceModel } from "@/api/fileSources";
import { rethrowSimple } from "@/utils/simple-error";

export async function hide(instance: UserFileSourceModel) {
    const { data: fileSource, error } = await client.PUT("/api/file_source_instances/{user_file_source_id}", {
        params: { path: { user_file_source_id: instance.uuid } },
        body: {
            hidden: true,
        },
    });
    if (error) {
        rethrowSimple(error);
    }
    return fileSource;
}
