// TODO: Swap these awful relative paths to an alias
import DatatypesJson from "@tests/test-data/json/datatypes.json";
import DatatypesMappingJson from "@tests/test-data/json/datatypes.mapping.json";

import { http } from "@/api/client/__mocks__/http";

import { type DatatypesCombinedMap, DatatypesMapperModel } from "./model";

export const typesAndMappingResponse: DatatypesCombinedMap = {
    datatypes: DatatypesJson,
    datatypes_mapping: DatatypesMappingJson,
};

export const testDatatypesMapper = new DatatypesMapperModel(typesAndMappingResponse);

/** Answers the datatypes mapper's request with `typesAndMappingResponse`. */
export const typesAndMappingHandler = http.get("/api/datatypes/types_and_mapping", ({ response }) =>
    response(200).json(typesAndMappingResponse),
);
