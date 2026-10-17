import { afterEach, describe, expect, it, vi } from "vitest";

import {
    ApiError,
    apiErrorFromResponse,
    rethrowSimpleWithStatus,
    RETRY_BACKOFF_CAP_MS,
    retryBackoffMs,
} from "./simple-error";

function caught(fn: () => never): ApiError {
    try {
        fn();
    } catch (e) {
        return e as ApiError;
    }
    throw new Error("expected throw");
}

describe("rethrowSimpleWithStatus", () => {
    it("keeps status and parses a Retry-After seconds header", () => {
        const response = new Response(null, { status: 429, headers: { "Retry-After": "7" } });
        const error = caught(() => rethrowSimpleWithStatus({ err_msg: "slow down" }, response));
        expect(error).toBeInstanceOf(ApiError);
        expect(error.status).toBe(429);
        expect(error.retryAfterMs).toBe(7000);
    });

    it("leaves retryAfterMs undefined when header is absent or not a number of seconds", () => {
        expect(caught(() => rethrowSimpleWithStatus({}, new Response(null, { status: 429 }))).retryAfterMs).toBe(
            undefined,
        );
        const dated = new Response(null, { status: 429, headers: { "Retry-After": "Wed, 21 Oct 2015 07:28:00 GMT" } });
        expect(caught(() => rethrowSimpleWithStatus({}, dated)).retryAfterMs).toBe(undefined);
        expect(caught(() => rethrowSimpleWithStatus({}, { status: 503 })).retryAfterMs).toBe(undefined);
    });
});

describe("apiErrorFromResponse", () => {
    it("builds an ApiError with message, status and Retry-After", () => {
        const response = new Response(null, { status: 503, headers: { "Retry-After": "4" } });
        const error = apiErrorFromResponse({ err_msg: "Service Unavailable" }, response);
        expect(error).toBeInstanceOf(ApiError);
        expect(error.message).toBe("Service Unavailable");
        expect(error.status).toBe(503);
        expect(error.retryAfterMs).toBe(4000);
    });

    it("handles a missing response", () => {
        const error = apiErrorFromResponse({ err_msg: "boom" });
        expect(error.status).toBe(undefined);
        expect(error.retryAfterMs).toBe(undefined);
    });
});

describe("retryBackoffMs", () => {
    afterEach(() => {
        vi.restoreAllMocks();
    });

    it("waits at least Retry-After, capped", () => {
        vi.spyOn(Math, "random").mockReturnValue(0);
        expect(retryBackoffMs(1, 10_000)).toBe(10_000);
        expect(retryBackoffMs(1, 10 * RETRY_BACKOFF_CAP_MS)).toBe(RETRY_BACKOFF_CAP_MS);
        expect(retryBackoffMs(1, 1)).toBe(retryBackoffMs(1));
    });
});
