// TODO: Swap these awful relative paths to an alias
import DatatypesMappingJson from "../../../tests/qunit/test-data/json/datatypes.mapping.json";
import DatatypesJson from "../../../tests/qunit/test-data/json/datatypes.json";
import { DatatypesMapperModel } from "./model.js";

export const typesAndMappingResponse = {
    datatypes: DatatypesJson,
    datatypes_mapping: DatatypesMappingJson,
};

export const testDatatypesMapper = new DatatypesMapperModel(typesAndMappingResponse);
