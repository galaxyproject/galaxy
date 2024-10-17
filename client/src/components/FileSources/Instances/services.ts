import { GalaxyApi } from "@/api";
import type { UserFileSourceModel } from "@/api/fileSources";

const updateUrl = "/api/file_source_instances/{uuid}";

export async function hide(instance: UserFileSourceModel) {
    const payload = { hidden: true };
    const { data: fileSource } = await GalaxyApi().PUT(updateUrl, {
        params: {
            path: { uuid: String(instance?.uuid) },
        },
        body: payload,
    });
    return fileSource;
}
