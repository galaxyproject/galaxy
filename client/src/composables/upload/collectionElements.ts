import type { CollectionElementIdentifiers } from "@/api";
import {
    COMMON_FILTERS,
    DEFAULT_FILTER,
    guessInitialFilterType,
    guessNameForPair,
} from "@/components/Collections/pairing";

import type { SupportedCollectionType } from "./collectionTypes";

interface CollectionUploadItem {
    name: string;
}

/**
 * Builds collection element identifiers based on collection type.
 * Uses the shared pairing abstractions from @/components/Collections/pairing for
 * pair name extraction (synchronized with the backend via auto_pairing_spec.yml).
 *
 * @param items - Upload items with dataset IDs
 * @param datasetIds - Array of created dataset IDs (in upload order)
 * @param collectionType - Type of collection to create
 * @returns Collection element identifiers ready for API
 */
export function buildCollectionElements(
    items: CollectionUploadItem[],
    datasetIds: string[],
    collectionType: SupportedCollectionType,
): CollectionElementIdentifiers {
    if (collectionType === "list") {
        // Simple list: one element per dataset
        return items.map((item, index) => ({
            name: item.name || `element_${index + 1}`,
            src: "hda" as const,
            id: datasetIds[index],
        }));
    }
    // List of pairs: group consecutive files into pairs
    const pairs: CollectionElementIdentifiers = [];
    const usedNames = new Set<string>();

    // Use the shared filter detection to determine forward/reverse naming convention
    const filterType = guessInitialFilterType(items) ?? DEFAULT_FILTER;
    const [forwardFilter, reverseFilter] = COMMON_FILTERS[filterType];

    for (let i = 0; i < items.length; i += 2) {
        if (i + 1 >= items.length) {
            // Odd number of files - skip last one or handle as error
            console.warn(`Skipping unpaired file at index ${i}: ${items[i]?.name}`);
            break;
        }

        const item1 = items[i];
        const item2 = items[i + 1];

        if (!item1 || !item2) {
            continue;
        }

        const basePairName =
            guessNameForPair(item1, item2, forwardFilter, reverseFilter, true) || `pair_${Math.floor(i / 2) + 1}`;
        let pairName = basePairName;

        // Ensure unique pair names by adding suffix if needed
        let counter = 1;
        while (usedNames.has(pairName)) {
            pairName = `${basePairName}_${counter}`;
            counter++;
        }
        usedNames.add(pairName);

        pairs.push({
            collection_type: "paired",
            src: "new_collection" as const,
            name: pairName,
            element_identifiers: [
                {
                    name: "forward",
                    src: "hda" as const,
                    id: datasetIds[i],
                },
                {
                    name: "reverse",
                    src: "hda" as const,
                    id: datasetIds[i + 1],
                },
            ],
        });
    }

    return pairs;
}
