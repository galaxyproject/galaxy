import type { Middleware } from "openapi-fetch";

/** The error shape Galaxy's API returns. */
interface NormalizedApiError {
    err_msg: string;
    err_code: number;
}

const GATEWAY_MESSAGES: Record<number, string> = {
    502: "Galaxy is temporarily unavailable",
    503: "Galaxy is temporarily unavailable",
    504: "Galaxy took too long to respond",
};

function statusMessage(status: number, statusText: string): string {
    const description = GATEWAY_MESSAGES[status] ?? statusText?.trim();
    return description ? `${description} (${status})` : `The request failed (${status})`;
}

function hasStructuredBody(body: string): boolean {
    try {
        const parsed = JSON.parse(body);
        return parsed !== null && typeof parsed === "object";
    } catch {
        return false;
    }
}

/**
 * Normalizes a failed response whose body is not JSON into the `{err_msg, err_code}`
 * shape the API returns, so callers always receive an error object rather than
 * whatever happened to answer the request.
 */
export const errorResponseMiddleware: Middleware = {
    async onResponse({ response }) {
        if (response.ok) {
            return undefined;
        }

        // openapi-fetch decides string-or-object by whether the body parses rather
        // than by content-type, so the same question has to be asked here: a malformed
        // body labelled as JSON would otherwise still reach the caller as a string.
        // Cloned so the original stays readable when it is handed back untouched.
        const body = await response.clone().text();
        if (hasStructuredBody(body)) {
            return undefined;
        }

        const normalized: NormalizedApiError = {
            err_msg: statusMessage(response.status, response.statusText),
            err_code: response.status,
        };

        return new Response(JSON.stringify(normalized), {
            status: response.status,
            statusText: response.statusText,
            headers: { "content-type": "application/json" },
        });
    },
};
