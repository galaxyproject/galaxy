import { getDatatypes } from "@/api/datatypes";

import { DatatypesMapperModel } from "./model";

export async function getDatatypesMapper(upload_only = true) {
    const typesAndMapping = await getDatatypes(upload_only);
    return new DatatypesMapperModel(typesAndMapping);
}
