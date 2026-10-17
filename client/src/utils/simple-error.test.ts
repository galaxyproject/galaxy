import axios from "axios";
import { http, HttpResponse } from "msw";
import { afterEach, describe, expect, it, vi } from "vitest";

import { useServerMock } from "@/api/client/__mocks__";

import {
    ApiError,
    apiErrorFromResponse,
    errorMessageAsString,
    rethrowSimpleWithStatus,
    RETRY_BACKOFF_CAP_MS,
    retryBackoffMs,
} from "./simple-error";

const { server } = useServerMock();

async function axiosError(response: Response) {
    server.use(http.get("/api/configuration", () => response));
    try {
        await axios.get("/api/configuration");
    } catch (e) {
        return e;
    }
    expect.unreachable("should have thrown");
}

describe("errorMessageAsString", () => {
    // Browsers leave statusText empty over HTTP/2, and msw's HttpResponse would fill it in.
    it.each([
        [413, "The request was too large (413)"],
        [524, "Galaxy took too long to respond (524)"],
        [418, "The request failed (418)"],
    ])("names a %d from axios without relying on the status text", async (status, message) => {
        const error = await axiosError(new Response("<html><body>nginx</body></html>", { status }));

        expect(errorMessageAsString(error)).toBe(message);
    });

    it("falls back to the status text for a status it has no wording for", async () => {
        const error = await axiosError(new HttpResponse("<html><body>teapot</body></html>", { status: 418 }));

        expect(errorMessageAsString(error)).toBe("I'm a Teapot (418)");
    });

    it("prefers the Galaxy error message in an axios response", async () => {
        const error = await axiosError(
            HttpResponse.json({ err_msg: "Quota exceeded", err_code: 403002 }, { status: 403 }),
        );

        expect(errorMessageAsString(error)).toBe("Quota exceeded");
    });
});

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
