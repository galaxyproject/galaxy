import { rethrowSimple } from "utils/simple-error";
import { fetcher } from "schema/fetcher";

const getTypesAndMappings = fetcher.path("/api/datatypes/types_and_mapping").method("get").create();

export async function getDatatypes(upload_only = true) {
    try {
        const response = await getTypesAndMappings({ upload_only });
        return response.data;
    } catch (e) {
        rethrowSimple(e);
    }
}
