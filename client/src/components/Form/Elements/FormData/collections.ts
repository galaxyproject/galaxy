import { type CollectionType } from "@/api/datasetCollections";
import { type CollectionBuilderType } from "@/components/History/adapters/buildCollectionModal";

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
