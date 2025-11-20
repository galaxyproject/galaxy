import type { MessageException } from "@/api";
import { GalaxyApi } from "@/api/client";
import { useServerMock } from "@/api/client/__mocks__";

import { DEFAULT_CONFIG } from "./rateLimiter";

const { server, http } = useServerMock();

/** Spy to count number of times a 429 response is returned */
const mock429ResponseSpy = jest.fn();

describe("Rate Limiter Middleware", () => {
    let consoleWarnSpy: jest.SpyInstance;
    let consoleErrorSpy: jest.SpyInstance;

    /** Helper to verify that there is a 429 response without retries */
    function ensure429AndNoRetries(response: Response, error: MessageException | undefined) {
        // Verify the request failed as expected
        expect(response.status).toBe(429);
        expect(error).toBeDefined();
        expect(error?.err_code).toBe(429);

        // Verify no retry behavior occurred by confirming console warns/errors were not called
        expect(consoleWarnSpy).not.toHaveBeenCalled();
        expect(consoleErrorSpy).not.toHaveBeenCalled();

        // Verify the mock 429 response was called only once (no retries)
        expect(mock429ResponseSpy).toHaveBeenCalledTimes(1);
    }

    beforeEach(() => {
        consoleWarnSpy = jest.spyOn(console, "warn").mockImplementation();
        consoleErrorSpy = jest.spyOn(console, "error").mockImplementation();
    });
    afterEach(() => {
        consoleWarnSpy.mockRestore();
        consoleErrorSpy.mockRestore();
        mock429ResponseSpy.mockReset();
    });

    it("should retry 429 GET responses", async () => {
        // Set up a mock GET endpoint that always returns 429
        server.use(
            http.get("/api/histories/{history_id}", ({ response }) => {
                mock429ResponseSpy();
                return response("4XX").json({ err_code: 429, err_msg: "Too Many Requests" }, { status: 429 });
            }),
        );

        const { error, response } = await GalaxyApi().GET("/api/histories/{history_id}", {
            params: {
                path: { history_id: "test" },
            },
        });

        // Verify the request failed as expected
        expect(response.status).toBe(429);
        expect(error).toBeDefined();
        expect(error?.err_code).toBe(429);

        // Verify retry behavior occurred by confirming console warns/errors
        expect(consoleWarnSpy).toHaveBeenCalledWith(
            expect.stringContaining(`Received 429 from server, waiting ${DEFAULT_CONFIG.retryDelay}ms before retry`),
        );

        for (let i = 1; i <= DEFAULT_CONFIG.maxRetries; i++) {
            expect(consoleWarnSpy).toHaveBeenCalledWith(expect.stringContaining(`Retry ${i} also received 429`));
        }

        expect(consoleErrorSpy).toHaveBeenCalledWith(
            expect.stringContaining(`Max retries reached for request to ${response.url}`),
        );

        // Verify the mock 429 response was called the first time and then for each retry
        expect(mock429ResponseSpy).toHaveBeenCalledTimes(DEFAULT_CONFIG.maxRetries + 1);
    });

    it("should not retry 429 POST responses", async () => {
        // Set up a mock POST endpoint that always returns 429
        server.use(
            http.post("/api/chat", ({ response }) => {
                mock429ResponseSpy();
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

        ensure429AndNoRetries(response, error);
    });

    it("should not retry 429 DELETE responses", async () => {
        // Set up a mock DELETE endpoint that always returns 429
        server.use(
            http.delete("/api/datasets/{dataset_id}", ({ response }) => {
                mock429ResponseSpy();
                return response("4XX").json({ err_code: 429, err_msg: "Too Many Requests" }, { status: 429 });
            }),
        );

        const { error, response } = await GalaxyApi().DELETE("/api/datasets/{dataset_id}", {
            params: {
                path: { dataset_id: "test_id" },
                query: { purge: true },
            },
        });

        ensure429AndNoRetries(response, error);
    });

    it("should not retry 429 PUT responses", async () => {
        // Set up a mock PUT endpoint that always returns 429
        server.use(
            http.put("/api/datasets/{dataset_id}", ({ response }) => {
                mock429ResponseSpy();
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

        ensure429AndNoRetries(response, error);
    });
});
