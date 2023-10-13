import { fetcher } from "@/api/schema";

const getTypesAndMappings = fetcher.path("/api/datatypes/types_and_mapping").method("get").create();

export async function getDatatypes(upload_only = true) {
    const { data } = await getTypesAndMappings({ upload_only });
    return data;
}
