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

// eslint-disable-next-line no-control-regex
const controlCharacters = /[\u0000-\u001f\u007f]/;

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
    // A browser drops tabs and newlines before resolving a URL, so "/<TAB>/host" would
    // reach the network as the protocol-relative "//host". Refuse control characters
    // outright rather than accepting a value whose meaning changes later; surrounding
    // whitespace gets trimmed the same way.
    if (path !== path.trim() || controlCharacters.test(path)) {
        return undefined;
    }
    if (!path.startsWith("/") || path[1] === "/" || path[1] === "\\") {
        return undefined;
    }
    return path;
}

/**
 * Guards a post-login redirect target like `safeRedirectPath`, and also accepts an
 * absolute https URL whose host -- with the port, if it is not 443 -- is one of
 * `allowedHosts`, the admin-configured `allowed_login_redirect_hosts`. Mirrors
 * `is_safe_login_redirect` on the server.
 * @param target
 * @param allowedHosts
 * @returns The target if Galaxy may send the user there after login, otherwise undefined.
 */
export function safeLoginRedirect(target: unknown, allowedHosts: string[]): string | undefined {
    const path = safeRedirectPath(target);
    if (path || !allowedHosts.length || typeof target !== "string") {
        return path;
    }
    // Backslashes and credentials in the authority ("https://allowed@evil") are refused
    // rather than trusting every URL parser to agree on where the host ends.
    if (target !== target.trim() || controlCharacters.test(target) || target.includes("\\")) {
        return undefined;
    }
    const authority = /^https:\/\/([^/?#]+)/i.exec(target)?.[1];
    if (!authority || authority.includes("@")) {
        return undefined;
    }
    let url: URL;
    try {
        url = new URL(target);
    } catch {
        return undefined;
    }
    const allowed = allowedHosts.map((host) => host.toLowerCase());
    return allowed.includes(url.host) ? target : undefined;
}
