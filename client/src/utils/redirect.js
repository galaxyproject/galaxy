import { getAppRoot } from "onload/loadConfig";

// Simple redirect, only here to make testing easier
export function redirectToUrl(url) {
    window.location = url;
}

// separated purely to make testing easier
export function reloadPage() {
    window.location.reload();
}

// Prepends configured appRoot to given url
const slashCleanup = /(\/)+/g;
export function prependPath(path) {
    const root = getAppRoot();
    return `${root}/${path}`.replace(slashCleanup, "/");
}

export function absPath(path) {
    const relativePath = prependPath(path);
    const server = window.location.origin;
    return `${server}/${relativePath}`.replace(slashCleanup, "/");
}
