import axios from "axios";

import { withPrefix } from "@/utils/redirect";
import { rethrowSimple } from "@/utils/simple-error";

export interface UrlDataOptions {
    url: string;
    headers?: Record<string, string>;
    params?: Record<string, string>;
    errorSimplify?: boolean;
}

export const USER_FILE_PREFIX = "gxuserfiles://";
// TODO: File sources can register custom URI schemes post https://github.com/galaxyproject/galaxy/pull/15497,
// as such this list should probably be calculated on that backend for correctness.
export const URI_PREFIXES = [
    "base64://",
    "http://",
    "https://",
    "ftp://",
    "file://",
    "gxfiles://",
    "gximport://",
    "gxuserimport://",
    USER_FILE_PREFIX,
    "gxftp://",
    "drs://",
    "invenio://",
    "zenodo://",
    "dataverse://",
    "elabftw://",
    "zip://",
    "ascp://",
    "iiif://",
];

export function isUrl(content: string): boolean {
    return URI_PREFIXES.some((prefix) => content.startsWith(prefix));
}

const NETWORK_SCHEMES = ["http://", "https://", "ftp://", "ftps://"];

export function isNetworkUrl(content: string): boolean {
    return NETWORK_SCHEMES.some((prefix) => content.startsWith(prefix));
}

/**
 * Structural validation for http(s)/ftp(s) URLs destined for the server
 * fetch endpoint. Rejects empty DNS labels (leading/trailing dot, consecutive
 * dots, or pure punctuation) that would otherwise crash server-side idna
 * encoding and surface as an opaque 500.
 */
export function isValidNetworkUrl(content: string): boolean {
    const prefix = NETWORK_SCHEMES.find((p) => content.startsWith(p));
    if (!prefix) {
        return false;
    }
    const afterScheme = content.slice(prefix.length);
    const authorityEnd = afterScheme.search(/[/?#]/);
    const authority = authorityEnd === -1 ? afterScheme : afterScheme.slice(0, authorityEnd);
    const hostAndPort = authority.includes("@") ? authority.slice(authority.lastIndexOf("@") + 1) : authority;
    let host = hostAndPort;
    if (!host.startsWith("[")) {
        const portIdx = host.lastIndexOf(":");
        if (portIdx !== -1) {
            host = host.slice(0, portIdx);
        }
    }
    if (!host) {
        return false;
    }
    // IPv6 literals are bracketed; they have no DNS labels to validate.
    if (host.startsWith("[")) {
        return true;
    }
    return !host.split(".").some((label) => label.length === 0);
}

export async function urlData<R>({ url, headers, params, errorSimplify = true }: UrlDataOptions): Promise<R> {
    try {
        headers = headers || {};
        params = params || {};
        const { data } = await axios.get(withPrefix(url), { headers, params });
        return data as R;
    } catch (e) {
        if (errorSimplify) {
            rethrowSimple(e);
        } else {
            throw e;
        }
    }
}

/**
 * Adds search parameters to url.
 *
 * @param original url
 * @param params which will be added to the url
 * @returns
 */
export function addSearchParams(url: string, params: Record<string, string>) {
    const placeholder = url.indexOf("?") == -1 ? "?" : "&";
    const searchParams = new URLSearchParams(params);
    const searchString = searchParams.toString();
    return searchString ? `${url}${placeholder}${searchString}` : url;
}

/**
 * URL validation result interface
 */
export interface UrlValidationResult {
    isValid: boolean;
    message: string | null;
}

/**
 * Validates a URL string for use in upload flows. Accepts any URI whose scheme
 * appears in URI_PREFIXES (including Galaxy file-source schemes like
 * gxfiles://, drs://, zenodo://, etc.). For http(s)/ftp(s) URLs it also applies
 * a structural host check to reject empty DNS labels that would crash
 * server-side idna encoding.
 */
export function validateUrl(url: string): UrlValidationResult {
    const trimmed = url.trim();
    if (!trimmed) {
        return { isValid: false, message: "URL is required" };
    }
    if (!isUrl(trimmed)) {
        return { isValid: false, message: "URL format is invalid or missing protocol" };
    }
    if (isNetworkUrl(trimmed) && !isValidNetworkUrl(trimmed)) {
        return { isValid: false, message: "URL must include a valid hostname" };
    }
    return { isValid: true, message: null };
}

/**
 * Simplified URL validation that returns only a boolean.
 *
 * @param url - The URL string to validate
 * @returns true if URL is valid, false otherwise
 *
 * @example
 * ```typescript
 * if (isValidUrl("https://example.org/data.txt")) {
 *   // Process valid URL
 * }
 * ```
 */
export function isValidUrl(url: string): boolean {
    return validateUrl(url).isValid;
}

/**
 * Extracts a meaningful filename from a URL.
 * Attempts to get the last path segment and decode it.
 * Falls back to the full URL if extraction fails.
 *
 * @param url - The URL to extract the name from
 * @returns The extracted filename or the full URL as fallback
 *
 * @example
 * ```typescript
 * extractNameFromUrl("https://example.org/path/to/data.txt") // returns "data.txt"
 * extractNameFromUrl("https://example.org/file%20name.txt") // returns "file name.txt"
 * extractNameFromUrl("https://example.org/") // returns "https://example.org/"
 * ```
 */
export function extractNameFromUrl(url: string): string {
    try {
        const urlObj = new URL(url);
        const pathname = urlObj.pathname;
        const segments = pathname.split("/").filter((s) => s.length > 0);

        if (segments.length > 0) {
            const lastSegment = segments[segments.length - 1];
            if (lastSegment) {
                // Decode URI component to handle encoded characters
                return decodeURIComponent(lastSegment);
            }
        }
    } catch {
        // If URL parsing fails, fall through to return the full URL
    }
    return url;
}
