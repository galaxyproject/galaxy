/** Thrown when the browser aborts a request (e.g. page navigation, component unmount). */
export class RequestAbortedError extends Error {
    constructor() {
        super("Request aborted");
        this.name = "RequestAbortedError";
    }
}

// Browsers leave statusText empty over HTTP/2, so the statuses proxies commonly
// answer with are described here rather than taken from the response.
const STATUS_MESSAGES: Record<number, string> = {
    400: "The request was not valid",
    401: "Authentication is required",
    403: "Access was denied",
    404: "The requested resource was not found",
    408: "The request timed out",
    413: "The request was too large",
    429: "Too many requests, please wait and try again",
    500: "An internal server error occurred",
    502: "Galaxy is temporarily unavailable",
    503: "Galaxy is temporarily unavailable",
    504: "Galaxy took too long to respond",
    // Cloudflare's own codes for failing to reach or hear back from the origin.
    520: "Galaxy is temporarily unavailable",
    521: "Galaxy is temporarily unavailable",
    522: "Galaxy is temporarily unavailable",
    523: "Galaxy is temporarily unavailable",
    524: "Galaxy took too long to respond",
};

/** Describes an HTTP status for a user, for responses that carry no Galaxy error message. */
export function statusMessage(status: number, statusText: string): string {
    const description = STATUS_MESSAGES[status] ?? statusText.trim();
    return description ? `${description} (${status})` : `The request failed (${status})`;
}

export function errorMessageAsString(e: any, defaultMessage = "Request failed.") {
    // Note that despite the name, this can actually currently return an object,
    // depending on what data.err_msg is (e.g. an object)
    let message = defaultMessage;
    if (e && e.response && e.response.data && e.response.data.err_msg) {
        message = e.response.data.err_msg;
    } else if (e && e.data && e.data.err_msg) {
        message = e.data.err_msg;
    } else if (e && e.err_msg) {
        message = e.err_msg;
    } else if (e && e.response) {
        message = statusMessage(e.response.status, e.response.statusText ?? "");
    } else if (e instanceof Error) {
        message = e.message;
    } else if (typeof e == "string") {
        message = e;
    }
    return message;
}

function isRequestAborted(e: any): boolean {
    // Only match genuine aborts (e.g. page navigation), not timeouts.
    // ECONNABORTED is also used for timeouts when clarifyTimeoutError is false
    // (the axios default), so check the message to distinguish.
    if (e?.code === "ERR_CANCELED" && !e?.message?.includes("timeout")) {
        return true;
    }
    if (e?.code === "ECONNABORTED" && e?.message === "Request aborted") {
        return true;
    }
    return false;
}

export function rethrowSimple(e: any): never {
    if (isRequestAborted(e)) {
        throw new RequestAbortedError();
    }
    if (process.env.NODE_ENV != "test") {
        console.debug(e);
    }
    throw Error(errorMessageAsString(e));
}

export class ApiError extends Error {
    status?: number;
    /** Server-requested delay from a numeric ``Retry-After`` header. */
    retryAfterMs?: number;
    constructor(message: string, status?: number) {
        super(message);
        this.status = status;
    }
}

/** Milliseconds from a numeric (delta-seconds) ``Retry-After`` header; undefined otherwise. */
export function parseRetryAfterMs(headers?: Headers): number | undefined {
    const value = headers?.get("Retry-After");
    if (value && /^\d+$/.test(value.trim())) {
        return parseInt(value, 10) * 1000;
    }
    return undefined;
}

/** An ``ApiError`` for a failed response, keeping its status and ``Retry-After``. */
export function apiErrorFromResponse(e: unknown, response?: { status: number; headers?: Headers }): ApiError {
    const error = new ApiError(errorMessageAsString(e), response?.status);
    error.retryAfterMs = parseRetryAfterMs(response?.headers);
    return error;
}

export function rethrowSimpleWithStatus(e: any, response?: { status: number; headers?: Headers }): never {
    if (isRequestAborted(e)) {
        throw new RequestAbortedError();
    }
    if (process.env.NODE_ENV != "test") {
        console.debug(e);
    }
    throw apiErrorFromResponse(e, response);
}

export type GalaxyApiResult<T> = { data: T; error: undefined } | { data: undefined; error: ApiError };

export const MAX_RETRIES = 3;
export const RETRY_BACKOFF_BASE_MS = 2000;
export const RETRY_BACKOFF_CAP_MS = 30_000;
const RETRYABLE_STATUSES = new Set([429, 500, 502, 503, 504]);

export function isRetryableApiError(error: Error): boolean {
    if (error instanceof ApiError && error.status !== undefined) {
        return RETRYABLE_STATUSES.has(error.status);
    }
    return false;
}

/**
 * Exponential backoff delay for a 1-based retry attempt: at least half the
 * backoff and at least ``retryAfterMs``, plus jitter of up to half the backoff
 * so concurrent failures don't retry in lockstep, even when they all carry the
 * same ``Retry-After``. Capped at ``capMs``; callers give up instead of retrying
 * when ``retryAfterMs`` exceeds ``capMs``.
 */
export function retryBackoffMs(
    attempt: number,
    retryAfterMs = 0,
    baseMs = RETRY_BACKOFF_BASE_MS,
    capMs = RETRY_BACKOFF_CAP_MS,
): number {
    const capped = Math.min(capMs, baseMs * 2 ** (attempt - 1));
    const jitter = capped * 0.5 * Math.random();
    return Math.min(capMs, Math.max(capped * 0.5, retryAfterMs) + jitter);
}
