import { DatatypesMapperModel } from "./model.js";
import { getDatatypes } from "./services";

export async function getDatatypesMapper() {
    const typesAndMapping = await getDatatypes();
    return new DatatypesMapperModel(typesAndMapping);
}
