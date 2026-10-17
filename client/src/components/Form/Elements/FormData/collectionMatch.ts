/**
 * How a collection feeds an input accepting `inputTypes`: directly (`mapOverType: null`), mapped over an input
 * type it ends with, or not at all (`null`).
 */
export function matchCollectionType(
    collectionType: string,
    inputTypes: string[],
): { mapOverType: string | null } | null {
    if (inputTypes.includes(collectionType)) {
        return { mapOverType: null };
    }
    const mapOverType = inputTypes.find((inputType) => collectionType.endsWith(inputType));
    if (!mapOverType) {
        return null;
    }
    return { mapOverType };
}
