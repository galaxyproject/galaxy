export class DatatypesMapperModel {
    constructor(typesAndMapping) {
        this.datatypes = typesAndMapping.datatypes;
        this.datatypes.sort();
        this.datatypesMapping = typesAndMapping.datatypes_mapping;
    }

    isSubType(child, parent) {
        const mapping = this.datatypesMapping;
        child = mapping.ext_to_class_name[child];
        parent = mapping.ext_to_class_name[parent];
        return mapping.class_to_classes[child] && parent in mapping.class_to_classes[child];
    }

    isSubTypeOfAny(child, parents) {
        return parents.some((parent) => this.isSubType(child, parent));
    }
}
