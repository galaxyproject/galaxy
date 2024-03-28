/**
 * Converts a long tool ID to a short tool id.
 * If the passed in ID is short already, returns it.
 * @param longId long tool-id
 * @returns short tool-id
 */
export function getShortToolId(longId: string): string {
    const toolIdSlash = longId.split("/");
    const shortId = toolIdSlash[toolIdSlash.length - 2];

    return shortId ?? longId;
}
