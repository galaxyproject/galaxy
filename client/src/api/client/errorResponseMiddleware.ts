import type { Middleware } from "openapi-fetch";

import { REQUEST_ID_HEADER } from "@/api/staleCacheRetry";
import { statusMessage } from "@/utils/simple-error";

/** The error shape Galaxy's API returns. */
interface NormalizedApiError {
    err_msg: string;
    err_code: number;
}

function isGalaxyError(response: Response, body: string): boolean {
    // Galaxy stamps every response it produces with a request id; a proxy answering
    // in its place does not, even when what it writes happens to be JSON.
    if (!response.headers.has(REQUEST_ID_HEADER)) {
        return false;
    }
    try {
        const parsed = JSON.parse(body);
        return typeof parsed?.err_msg === "string";
    } catch {
        return false;
    }
}

/**
 * Replaces a failed response that is not a Galaxy API error with one in the
 * `{err_msg, err_code}` shape the API returns, so callers always receive an error
 * object rather than whatever happened to answer the request.
 */
export const errorResponseMiddleware: Middleware = {
    async onResponse({ response }) {
        if (response.ok) {
            return undefined;
        }

        // Cloned so the original stays readable when it is handed back untouched.
        const body = await response.clone().text();
        if (isGalaxyError(response, body)) {
            return undefined;
        }

        const normalized: NormalizedApiError = {
            err_msg: statusMessage(response.status, response.statusText),
            err_code: response.status,
        };

        // Keeps Retry-After and friends; the length and encoding described the old body.
        const headers = new Headers(response.headers);
        headers.delete("content-length");
        headers.delete("content-encoding");
        headers.set("content-type", "application/json");

        return new Response(JSON.stringify(normalized), {
            status: response.status,
            statusText: response.statusText,
            headers,
        });
    },
};
