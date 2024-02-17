import { fetcher } from "@/api/schema";

export const datatypesFetcher = fetcher.path("/api/datatypes").method("get").create();

export const edamFormatsFetcher = fetcher.path("/api/datatypes/edam_formats/detailed").method("get").create();
export const edamDataFetcher = fetcher.path("/api/datatypes/edam_data/detailed").method("get").create();

const typesAndMappingsFetcher = fetcher.path("/api/datatypes/types_and_mapping").method("get").create();

export async function fetchDatatypesAndMappings(upload_only = true) {
    const { data } = await typesAndMappingsFetcher({ upload_only });
    return data;
}
