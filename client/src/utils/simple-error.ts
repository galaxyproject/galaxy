/** Thrown when the browser aborts a request (e.g. page navigation, component unmount). */
export class RequestAbortedError extends Error {
    constructor() {
        super("Request aborted");
        this.name = "RequestAbortedError";
    }
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
        message = `${e.response.statusText} (${e.response.status})`;
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
 * Exponential backoff delay for a 1-based retry attempt, with jitter in
 * [50%, 100%] so concurrent failures don't retry in lockstep. Capped at
 * ``capMs``, otherwise never shorter than ``retryAfterMs``; callers give up
 * instead of retrying when ``retryAfterMs`` exceeds ``capMs``.
 */
export function retryBackoffMs(
    attempt: number,
    retryAfterMs = 0,
    baseMs = RETRY_BACKOFF_BASE_MS,
    capMs = RETRY_BACKOFF_CAP_MS,
): number {
    const capped = Math.min(capMs, baseMs * 2 ** (attempt - 1));
    const backoff = capped * (0.5 + Math.random() * 0.5);
    return Math.min(capMs, Math.max(backoff, retryAfterMs));
}
