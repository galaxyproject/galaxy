import { fetcher } from "@/schema/fetcher";

const getTypesAndMappings = fetcher.path("/api/datatypes/types_and_mapping").method("get").create();

export async function getDatatypes(upload_only = true) {
    const response = await getTypesAndMappings({ upload_only });
    return response.data;
}
