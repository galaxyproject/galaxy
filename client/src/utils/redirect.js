import { getAppRoot } from "onload/loadConfig";

// Simple redirect, only here to make testing easier
export function redirectToUrl(url) {
    window.location = url;
}

// separated purely to make testing easier
export function reloadPage() {
    window.location.reload();
}

const slashCleanup = /(\/)+/g;
/**
 * Prepends the configured app root to given url
 * @param {String} path
 * @returns The relative URL path with the configured appRoot.
 */
export function prependPath(path) {
    const root = getAppRoot();
    return `${root}/${path}`.replace(slashCleanup, "/");
}

/**
 * Returns the absolute URL path for this server given a relative path.
 * @param {String} path
 * @returns The absolute URL path.
 */
export function absPath(path) {
    // Root path here may be '/' or '/galaxy' for example.  we always append the
    // base '/' and then clean up duplicates.
    const relativePath = `/${hasRoot(path) ? path : prependPath(path)}`.replace(slashCleanup, "/");
    const server = window.location.origin;
    return `${server}${relativePath}`;
}

/**
 * Checks if the path already has the app root.
 * @param {String} path
 * @returns true if the given path starts with the app root.
 */
function hasRoot(path) {
    return path.startsWith(getAppRoot());
}
