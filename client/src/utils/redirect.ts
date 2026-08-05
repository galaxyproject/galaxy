import { getAppRoot } from "@/onload/loadConfig";

// Simple redirect, only here to make testing easier
export function redirectToUrl(url: string) {
    window.location.assign(url);
}

// separated purely to make testing easier
export function reloadPage() {
    window.location.reload();
}

const slashCleanup = /(?<!:)(\/)+/g;
/**
 * Prepends the configured app root to given url
 * @param path
 * @returns The relative URL path with the configured appRoot.
 */
export function prependPath(path: string) {
    const root = getAppRoot();
    return `${root}/${path}`.replace(slashCleanup, "/");
}

/**
 * Returns the absolute URL path for this server given a relative path.
 * @param path
 * @returns The absolute URL path.
 */
export function absPath(path: string) {
    // Root path here may be '/' or '/galaxy' for example.  we always append the
    // base '/' and then clean up duplicates.
    const relativePath = `/${hasRoot(path) ? path : prependPath(path)}`.replace(slashCleanup, "/");
    const server = window.location.origin;
    return `${server}${relativePath}`;
}

/**
 * (Safely) Prepends the configured app root to given url
 * @param path
 * @returns The relative URL or original path.
 */
export function withPrefix(path: string) {
    if (path && path.startsWith("/")) {
        return prependPath(path);
    }
    return path;
}

/**
 * Checks if the path already has the app root.
 * @param path
 * @returns true if the given path starts with the app root.
 */
function hasRoot(path: string) {
    return path.startsWith(getAppRoot());
}

// Browsers drop tabs and newlines from a URL before resolving it, so "/<TAB>/host"
// reaches the network as the protocol-relative "//host".
const strippedByBrowsers = /[\t\r\n]/g;

/**
 * Guards a post-login redirect target, which arrives from the query string and is
 * therefore attacker-supplied. Anything a browser could resolve to a different origin --
 * an absolute URL, a protocol-relative `//host`, or the backslash spelling browsers
 * normalize to it -- is refused.
 * @param path
 * @returns The path if it is a relative URL that stays on this Galaxy, otherwise undefined.
 */
export function safeRedirectPath(path: unknown): string | undefined {
    if (typeof path !== "string" || !path) {
        return undefined;
    }
    // Validate what the browser will actually see, not what we were handed.
    const candidate = path.replace(strippedByBrowsers, "").trim();
    if (!candidate.startsWith("/") || candidate[1] === "/" || candidate[1] === "\\") {
        return undefined;
    }
    return path;
}
