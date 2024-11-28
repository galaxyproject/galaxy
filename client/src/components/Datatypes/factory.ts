import { GalaxyApi } from "@/api";
import { rethrowSimple } from "@/utils/simple-error";

import { DatatypesMapperModel } from "./model";

export async function getDatatypesMapper(upload_only = true) {
    const { data, error } = await GalaxyApi().GET("/api/datatypes/types_and_mapping", {
        params: { query: { upload_only } },
    });
    if (error) {
        rethrowSimple(error);
    }
    return new DatatypesMapperModel(data);
}
