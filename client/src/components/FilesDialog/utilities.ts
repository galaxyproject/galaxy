import { USER_FILE_PREFIX } from "@/utils/url";

import type { SelectionItem } from "../SelectionDialog/selectionTypes";

export { entryToSelectionItem, fileSourcePluginToItem } from "../SelectionDialog/selectionAdapters";

export const isSubPath = (originPath: string, destinationPath: string) => {
    return subPathCondition(ensureTrailingSlash(originPath), ensureTrailingSlash(destinationPath));
};

export const isSamePath = (path: string, otherPath: string) => {
    return ensureTrailingSlash(path) === ensureTrailingSlash(otherPath);
};

// we need "/" at the end to avoid a use case, when we have 2 folders with similar name
// namely, "folder_example" starts with "folder"
function ensureTrailingSlash(path: string) {
    return path.endsWith("/") ? path : path + "/";
}
function subPathCondition(originPath: string, destinationPath: string) {
    return originPath !== destinationPath && destinationPath.startsWith(originPath);
}

/**
 * Comparator for sorting file sources.
 * User-created sources come first, then alphabetical by label.
 */
export function sortFileSources(a: SelectionItem, b: SelectionItem): number {
    const aIsUser = a.url.startsWith(USER_FILE_PREFIX);
    const bIsUser = b.url.startsWith(USER_FILE_PREFIX);

    if (aIsUser && !bIsUser) {
        return -1;
    }
    if (!aIsUser && bIsUser) {
        return 1;
    }
    return a.label.localeCompare(b.label);
}

/**
 * Normalize SelectionDialog's Model.finalize() return value (single item or array) into an array.
 */
export function selectionToArray(selection: SelectionItem | SelectionItem[]): SelectionItem[] {
    return Array.isArray(selection) ? selection : selection ? [selection] : [];
}
