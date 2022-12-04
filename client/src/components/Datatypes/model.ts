import { components } from "schema";

export type DatatypesCombinedMap = components["schemas"]["DatatypesCombinedMap"];

export class DatatypesMapperModel {
    datatypes: DatatypesCombinedMap["datatypes"];
    datatypesMapping: DatatypesCombinedMap["datatypes_mapping"];

    constructor(typesAndMapping: DatatypesCombinedMap) {
        // create a shallow copy of the datatypes, otherwise sort mutates in place
        // and causes a possible infinite render update loop.
        this.datatypes = [...typesAndMapping.datatypes];
        this.datatypes.sort();
        this.datatypesMapping = typesAndMapping.datatypes_mapping;
    }

    isSubType(child: string, parent: string): boolean {
        const mapping = this.datatypesMapping;
        child = mapping.ext_to_class_name[child];
        parent = mapping.ext_to_class_name[parent];
        return mapping.class_to_classes[child] && parent in mapping.class_to_classes[child];
    }

    isSubTypeOfAny(child: string, parents: DatatypesCombinedMap["datatypes"]): boolean {
        return parents.some((parent) => this.isSubType(child, parent));
    }
}
