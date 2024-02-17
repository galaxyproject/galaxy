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
