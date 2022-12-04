import { DatatypesMapperModel } from "./model";
import { getDatatypes } from "./services";

export async function getDatatypesMapper(upload_only = true) {
    const typesAndMapping = await getDatatypes(upload_only);
    return new DatatypesMapperModel(typesAndMapping);
}
