import { http as rawHttp } from "msw";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { MessageException } from "@/api";
import { GalaxyApi } from "@/api/client";
import { HttpResponse, useServerMock } from "@/api/client/__mocks__";

import { createRateLimiterMiddleware, DEFAULT_CONFIG } from "./rateLimiter";

const { server, http } = useServerMock();

const rateLimitedRequestSpy = vi.fn();

describe("Rate Limiter Middleware", () => {
    let consoleWarnSpy: ReturnType<typeof vi.spyOn>;
    let consoleErrorSpy: ReturnType<typeof vi.spyOn>;

    function expectRateLimitedWithoutRetries(response: Response, error: MessageException | undefined) {
        expect(response.status).toBe(429);
        expect(error).toBeDefined();
        expect(error?.err_code).toBe(429);

        expect(consoleWarnSpy).not.toHaveBeenCalled();
        expect(consoleErrorSpy).not.toHaveBeenCalled();

        expect(rateLimitedRequestSpy).toHaveBeenCalledTimes(1);
    }

    beforeEach(() => {
        rateLimitedRequestSpy.mockClear();
        consoleWarnSpy = vi.spyOn(console, "warn").mockImplementation(() => {});
        consoleErrorSpy = vi.spyOn(console, "error").mockImplementation(() => {});
    });
    afterEach(() => {
        consoleWarnSpy.mockRestore();
        consoleErrorSpy.mockRestore();
        rateLimitedRequestSpy.mockReset();
        vi.useRealTimers();
        vi.restoreAllMocks();
    });

    it("retries rate-limited GET requests until the retry limit is reached", async () => {
        server.use(
            http.get("/api/histories/{history_id}", ({ response }) => {
                rateLimitedRequestSpy();
                return response("4XX").json({ err_code: 429, err_msg: "Too Many Requests" }, { status: 429 });
            }),
        );

        // Maximal jitter makes the first delay exactly `retryDelay`; fake timers skip the backoff waits.
        vi.spyOn(Math, "random").mockReturnValue(1);
        vi.useFakeTimers({ toFake: ["setTimeout"] });
        let settled = false;
        const request = GalaxyApi()
            .GET("/api/histories/{history_id}", {
                params: {
                    path: { history_id: "test" },
                },
            })
            .finally(() => (settled = true));
        while (!settled) {
            await vi.advanceTimersByTimeAsync(DEFAULT_CONFIG.retryDelay);
        }
        const { error, response } = await request;

        expect(response.status).toBe(429);
        expect(error).toBeDefined();
        expect(error?.err_code).toBe(429);

        expect(consoleWarnSpy).toHaveBeenCalledWith(
            expect.stringContaining(`Received 429 from server, waiting ${DEFAULT_CONFIG.retryDelay}ms before retry`),
        );

        for (let retry = 1; retry <= DEFAULT_CONFIG.maxRetries; retry++) {
            expect(consoleWarnSpy).toHaveBeenCalledWith(expect.stringContaining(`Retry ${retry} also received 429`));
        }

        expect(consoleErrorSpy).toHaveBeenCalledWith(
            expect.stringContaining(`Max retries reached for request to ${response.url}`),
        );

        expect(rateLimitedRequestSpy).toHaveBeenCalledTimes(DEFAULT_CONFIG.maxRetries + 1);
    });

    it("returns a rate-limited POST response without retrying", async () => {
        server.use(
            http.post("/api/chat", ({ response }) => {
                rateLimitedRequestSpy();
                return response("4XX").json({ err_code: 429, err_msg: "Too Many Requests" }, { status: 429 });
            }),
        );

        const { error, response } = await GalaxyApi().POST("/api/chat", {
            params: {
                query: { job_id: "test" },
            },
            body: {
                query: "test message",
                context: "test",
            },
        });

        expectRateLimitedWithoutRetries(response, error);
    });

    it("returns a rate-limited DELETE response without retrying", async () => {
        server.use(
            http.delete("/api/datasets/{dataset_id}", ({ response }) => {
                rateLimitedRequestSpy();
                return response("4XX").json({ err_code: 429, err_msg: "Too Many Requests" }, { status: 429 });
            }),
        );

        const { error, response } = await GalaxyApi().DELETE("/api/datasets/{dataset_id}", {
            params: {
                path: { dataset_id: "test_id" },
                query: { purge: true },
            },
        });

        expectRateLimitedWithoutRetries(response, error);
    });

    it("returns a rate-limited PUT response without retrying", async () => {
        server.use(
            http.put("/api/datasets/{dataset_id}", ({ response }) => {
                rateLimitedRequestSpy();
                return response("4XX").json({ err_code: 429, err_msg: "Too Many Requests" }, { status: 429 });
            }),
        );

        const { error, response } = await GalaxyApi().PUT("/api/datasets/{dataset_id}", {
            params: {
                path: { dataset_id: "test_id" },
            },
            body: {
                deleted: false,
            },
        });

        expectRateLimitedWithoutRetries(response, error);
    });
});

describe("Rate Limiter Middleware retry timing", () => {
    const START = new Date("2026-01-01T00:00:00Z").getTime();
    let requestTimes: number[];

    function respond429(headers: Record<string, string> = {}) {
        return new HttpResponse(null, { status: 429, headers });
    }

    /** Answers GETs with `responses` in order, then 200; records request times (ms since START). */
    function serve(...responses: Response[]) {
        // A plain msw handler: the typed one loses the headers of a body-less response on its way to the client.
        server.use(
            rawHttp.get("/api/histories/:history_id", () => {
                requestTimes.push(Date.now() - START);
                return responses.shift() ?? HttpResponse.json({});
            }),
        );
    }

    /** Issues a GET and runs timers until it settles, retries included. */
    async function get() {
        const result = GalaxyApi().GET("/api/histories/{history_id}", { params: { path: { history_id: "test" } } });
        await vi.runAllTimersAsync();
        return (await result).response;
    }

    beforeEach(() => {
        requestTimes = [];
        vi.useFakeTimers();
        vi.setSystemTime(START);
        vi.spyOn(console, "warn").mockImplementation(() => {});
        vi.spyOn(console, "error").mockImplementation(() => {});
    });
    afterEach(() => {
        vi.useRealTimers();
        vi.restoreAllMocks();
    });

    it.each([
        { retryAfter: undefined, expected: [500, 750, 1000] },
        { retryAfter: "1", expected: [1000, 1250, 1500] },
    ])("spreads retries of concurrent 429s with Retry-After $retryAfter", async ({ retryAfter, expected }) => {
        serve();
        vi.spyOn(Math, "random").mockReturnValueOnce(0).mockReturnValueOnce(0.5).mockReturnValueOnce(1);

        // Calls the middleware directly: msw draws on Math.random for request ids, which would
        // take the mocked values if the initial requests went through GalaxyApi.
        const middleware = createRateLimiterMiddleware();
        const onResponse = middleware.onResponse as (params: {
            request: Request;
            response: Response;
        }) => Promise<Response>;
        const request = () => new Request(`${window.location.origin}/api/histories/test`);
        const headers: Record<string, string> = retryAfter ? { "Retry-After": retryAfter } : {};
        const results = Promise.all(
            [1, 2, 3].map(() => onResponse({ request: request(), response: respond429(headers) })),
        );
        await vi.runAllTimersAsync();
        const responses = await results;

        expect(responses.map((r) => r.status)).toEqual([200, 200, 200]);
        expect(requestTimes).toEqual(expected);
    });

    it("backs off exponentially between successive retries", async () => {
        serve(respond429(), respond429(), respond429(), respond429());
        vi.spyOn(Math, "random").mockReturnValue(1);

        expect((await get()).status).toBe(429);
        expect(requestTimes).toEqual([0, 1000, 3000, 7000]);
    });

    it("honors Retry-After seconds when longer than the backoff", async () => {
        serve(respond429({ "Retry-After": "3" }), respond429({ "Retry-After": "2" }));
        vi.spyOn(Math, "random").mockReturnValue(0);

        expect((await get()).status).toBe(200);
        // 3s from the first response's header, then 2s from the retried response's header.
        expect(requestTimes).toEqual([0, 3000, 5000]);
    });

    it("falls back to backoff for an HTTP-date Retry-After", async () => {
        serve(respond429({ "Retry-After": new Date(START + 2000).toUTCString() }));
        vi.spyOn(Math, "random").mockReturnValue(1);

        expect((await get()).status).toBe(200);
        expect(requestTimes).toEqual([0, 1000]);
    });

    it("falls back to backoff for an unparseable Retry-After", async () => {
        serve(respond429({ "Retry-After": "soon" }));
        vi.spyOn(Math, "random").mockReturnValue(1);

        expect((await get()).status).toBe(200);
        expect(requestTimes).toEqual([0, 1000]);
    });

    it("retries after a Retry-After equal to maxRetryDelay", async () => {
        serve(respond429({ "Retry-After": `${5000 / 1000}` }));
        vi.spyOn(Math, "random").mockReturnValue(0);

        expect((await get()).status).toBe(200);
        expect(requestTimes).toEqual([0, 5000]);
    });

    it("gives up without retrying when Retry-After exceeds maxRetryDelay", async () => {
        serve(respond429({ "Retry-After": "86400" }));

        expect((await get()).status).toBe(429);
        expect(requestTimes).toEqual([0]);
        expect(console.warn).toHaveBeenCalledWith(expect.stringContaining("Retry-After"));
    });

    it("stops retrying when a retry's Retry-After exceeds maxRetryDelay", async () => {
        serve(respond429(), respond429({ "Retry-After": "60" }));
        vi.spyOn(Math, "random").mockReturnValue(1);

        const response = await get();

        expect(response.status).toBe(429);
        expect(response.headers.get("Retry-After")).toBe("60");
        expect(requestTimes).toEqual([0, 1000]);
    });

    it("returns the last 429 when retries run out", async () => {
        serve(respond429(), respond429(), respond429(), respond429({ "Retry-After": "60" }));
        vi.spyOn(Math, "random").mockReturnValue(1);

        const response = await get();

        expect(response.status).toBe(429);
        expect(response.headers.get("Retry-After")).toBe("60");
        expect(requestTimes).toEqual([0, 1000, 3000, 7000]);
    });
});
