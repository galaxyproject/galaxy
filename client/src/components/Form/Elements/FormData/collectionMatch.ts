import { CollectionTypeDescription } from "@/components/Workflow/Editor/modules/collectionTypeDescription";

/** Map-over type the server assigns when a `paired_or_unpaired` input is fed a plain list */
const SINGLE_DATASETS = "single_datasets";

/**
 * How a collection feeds an input accepting `inputTypes`, mirroring `DataCollectionToolParameter.to_dict`: directly
 * (`mapOverType: null`), mapped over the deepest input type it nests, or not at all (`null`). A map-over the server
 * cannot split the collection into when running the tool (`_split_dataset_collection`) is refused.
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
    // deepest first, so each job gets as much data as possible; a split never yields a sample_sheet
    const mapOver = [...inputs]
        .sort((a, b) => b.rank - a.rank)
        .find((input) => !input.collectionType.startsWith("sample_sheet") && item.canMapOver(input));
    if (!mapOver) {
        return null;
    }
    const mapOverType = item.splitCollectionType(mapOver.collectionType);
    // the server splits a collection only into subcollections whose type is literally the map-over type
    if (mapOverType !== SINGLE_DATASETS && !collectionType.endsWith(`:${mapOverType}`)) {
        return null;
    }
    return { mapOverType };
}
