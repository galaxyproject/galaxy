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
];

export function isUrl(content: string): boolean {
    return URI_PREFIXES.some((prefix) => content.startsWith(prefix));
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
 * Validates a URL string and returns detailed validation results.
 * Checks for required fields, valid hostname, and meaningful content.
 *
 * @param url - The URL string to validate
 * @returns Validation result with isValid flag and error message
 *
 * @example
 * ```typescript
 * const result = validateUrl("https://example.org/data.txt");
 * if (!result.isValid) {
 *   console.error(result.message);
 * }
 * ```
 */
export function validateUrl(url: string): UrlValidationResult {
    if (!url.trim()) {
        return { isValid: false, message: "URL is required" };
    }

    try {
        const urlObj = new URL(url);

        if (!urlObj.host) {
            return { isValid: false, message: "URL must include a valid hostname" };
        }

        const hasContent = urlObj.pathname !== "/" || urlObj.search || urlObj.hash;
        if (!hasContent) {
            return { isValid: false, message: "URL should point to a specific file or resource" };
        }

        return { isValid: true, message: null };
    } catch {
        return { isValid: false, message: "URL format is invalid or missing protocol" };
    }
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
