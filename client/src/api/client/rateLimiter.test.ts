import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { MessageException } from "@/api";
import { GalaxyApi } from "@/api/client";
import { useServerMock } from "@/api/client/__mocks__";

import { DEFAULT_CONFIG } from "./rateLimiter";

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
    });

    it("retries rate-limited GET requests until the retry limit is reached", async () => {
        server.use(
            http.get("/api/histories/{history_id}", ({ response }) => {
                rateLimitedRequestSpy();
                return response("4XX").json({ err_code: 429, err_msg: "Too Many Requests" }, { status: 429 });
            }),
        );

        const { error, response } = await GalaxyApi().GET("/api/histories/{history_id}", {
            params: {
                path: { history_id: "test" },
            },
        });

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
