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
    constructor(message: string, status?: number) {
        super(message);
        this.status = status;
    }
}

export function rethrowSimpleWithStatus(e: any, response?: { status: number }): never {
    if (isRequestAborted(e)) {
        throw new RequestAbortedError();
    }
    if (process.env.NODE_ENV != "test") {
        console.debug(e);
    }
    throw new ApiError(errorMessageAsString(e), response?.status);
}

export type GalaxyApiResult<T> = { data: T; error: undefined } | { data: undefined; error: ApiError };

export const MAX_RETRIES = 3;
const RETRYABLE_STATUSES = new Set([429, 500, 502, 503, 504]);

export function isRetryableApiError(error: Error): boolean {
    if (error instanceof ApiError && error.status !== undefined) {
        return RETRYABLE_STATUSES.has(error.status);
    }
    return false;
}
