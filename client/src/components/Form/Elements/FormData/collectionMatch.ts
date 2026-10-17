import { CollectionTypeDescription } from "@/components/Workflow/Editor/modules/collectionTypeDescription";

/** Map-over type the server assigns when a `paired_or_unpaired` input is fed a plain list */
const SINGLE_DATASETS = "single_datasets";

/**
 * How a collection feeds an input accepting `inputTypes`, mirroring `DataCollectionToolParameter.to_dict`: directly
 * (`mapOverType: null`), mapped over the deepest input type it nests, or not at all (`null`).
 */
export function matchCollectionType(
    collectionType: string,
    inputTypes: string[],
): { mapOverType: string | null } | null {
    const item = new CollectionTypeDescription(collectionType);
    const inputs = inputTypes.map((inputType) => new CollectionTypeDescription(inputType));
    if (inputs.some((input) => input.canMatch(item))) {
        return { mapOverType: null };
    }
    // deepest first, so each job gets as much data as possible
    const mapOver = [...inputs].sort((a, b) => b.rank - a.rank).find((input) => item.canMapOver(input));
    if (!mapOver) {
        return null;
    }
    if (mapOver.collectionType === "paired_or_unpaired" && !collectionType.endsWith("paired_or_unpaired")) {
        return { mapOverType: collectionType.endsWith("paired") ? "paired" : SINGLE_DATASETS };
    }
    return { mapOverType: mapOver.collectionType };
}
