import type { CollectionType } from "@/api/datasetCollections";
import type { CollectionBuilderType } from "@/components/Collections/common/buildCollectionModal";

export const unconstrainedCollectionTypeBuilders: CollectionBuilderType[] = ["list", "list:paired", "paired"];

export function buildersForCollectionType(collectionType: CollectionType): CollectionBuilderType[] {
    if (collectionType === "list") {
        return ["list"];
    } else if (collectionType == "paired") {
        // generally prefer list:paired over paired, most people operate on these as lists
        // according to analysts.
        return ["list:paired", "paired"];
    } else if (collectionType == "list:paired") {
        return ["list:paired"];
    } else if (collectionType == "list:paired_or_unpaired") {
        return ["list", "list:paired", "list:paired_or_unpaired"];
    } else if (collectionType == "sample_sheet") {
        return ["sample_sheet"];
    } else if (collectionType == "sample_sheet:paired") {
        return ["sample_sheet:paired"];
    } else if (collectionType == "sample_sheet:paired_or_unpaired") {
        return ["sample_sheet:paired_or_unpaired"];
    } else if (collectionType == "sample_sheet:record") {
        return ["sample_sheet:record"];
    } else {
        return [];
    }
}

export function buildersForCollectionTypes(collectionTypes: CollectionType[]): CollectionBuilderType[] {
    const uniqueBuilders = new Set<CollectionBuilderType>();
    for (const collectionType of collectionTypes) {
        const builders = buildersForCollectionType(collectionType);
        builders.forEach((builder) => uniqueBuilders.add(builder));
    }
    return Array.from(uniqueBuilders);
}
