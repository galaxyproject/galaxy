import { type BrowsableFilesSourcePlugin } from "@/api/remoteFiles";

import { type SelectionItem } from "../SelectionDialog/selectionTypes";

export const isSubPath = (originPath: string, destinationPath: string) => {
    return subPathCondition(ensureTrailingSlash(originPath), ensureTrailingSlash(destinationPath));
};
// we need "/" at the end to avoid a use case, when we have 2 folders with similar name
// namely, "folder_example" starts with "folder"
function ensureTrailingSlash(path: string) {
    return path.endsWith("/") ? path : path + "/";
}
function subPathCondition(originPath: string, destinationPath: string) {
    return originPath !== destinationPath && destinationPath.startsWith(originPath);
}

export function fileSourcePluginToItem(plugin: BrowsableFilesSourcePlugin): SelectionItem {
    const result = {
        id: plugin.id,
        label: plugin.label,
        details: plugin.doc || "",
        isLeaf: false,
        url: plugin.uri_root,
    };
    return result;
}
