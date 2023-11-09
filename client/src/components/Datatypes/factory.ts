import { fetchDatatypesAndMappings } from "@/api/datatypes";

import { DatatypesMapperModel } from "./model";

export async function getDatatypesMapper(upload_only = true) {
    const typesAndMapping = await fetchDatatypesAndMappings(upload_only);
    return new DatatypesMapperModel(typesAndMapping);
}
