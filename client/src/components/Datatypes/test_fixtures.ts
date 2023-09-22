// TODO: Swap these awful relative paths to an alias
import DatatypesMappingJson from "@tests/test-data/json/datatypes.mapping.json";
import DatatypesJson from "@tests/test-data/json/datatypes.json";
import { DatatypesMapperModel } from "./model";
import type { DatatypesCombinedMap } from "./model";

export const typesAndMappingResponse: DatatypesCombinedMap = {
    datatypes: DatatypesJson,
    datatypes_mapping: DatatypesMappingJson,
};

export const testDatatypesMapper = new DatatypesMapperModel(typesAndMappingResponse);
