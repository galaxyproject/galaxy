export const isSubPath = (originPath, destinationPath) => {
    return subPathCondition(ensureTrailingSlash(originPath), ensureTrailingSlash(destinationPath));
};
// we need "/" at the end to avoid a usecase, when folder_example starts with folder
function ensureTrailingSlash(path) {
    return path.endsWith("/") ? path : path + "/";
}
function subPathCondition(originPath, destinationPath) {
    return originPath !== destinationPath && destinationPath.startsWith(originPath);
}
