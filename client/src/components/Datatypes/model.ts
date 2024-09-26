import { type components } from "@/api/schema";

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

    /**
     * Checks if a given child datatype is a subtype of a parent datatype.
     * @param child - The child datatype extension as registered in the datatypes registry.
     * @param parent - The parent datatype, which can be an extension or explicit class name
     *                 Can also be used with extensionless abstract datatypes (e.g. "galaxy.datatypes.images.Image")
     * @returns A boolean indicating whether the child is a subtype of the parent.
     */
    isSubType(child: string, parent: string): boolean {
        const mapping = this.datatypesMapping;
        const childClassName = mapping.ext_to_class_name[child];
        const parentClassName = mapping.ext_to_class_name[parent] || parent;

        if (!childClassName || !parentClassName) {
            return false;
        }
        const childClassMappings = mapping.class_to_classes[childClassName];
        if (!childClassMappings) {
            return false;
        }
        return parentClassName in childClassMappings;
    }

    isSubTypeOfAny(child: string, parents: DatatypesCombinedMap["datatypes"]): boolean {
        return parents.some((parent) => this.isSubType(child, parent));
    }

    /** For classes like `galaxy.datatypes.{parent}.{extension}`, get the extension's parent */
    getParentDatatype(extension: string) {
        const fullClassName = this.datatypesMapping.ext_to_class_name[extension];
        return fullClassName?.split(".")[2];
    }

    isSubClassOfAny(child: string, parents: DatatypesCombinedMap["datatypes"]): boolean {
        return parents.every((parent) => this.getParentDatatype(parent) === this.getParentDatatype(child));
    }
}
