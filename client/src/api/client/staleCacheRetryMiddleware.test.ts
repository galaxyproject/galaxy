import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { GalaxyApi } from "@/api/client";
import { HttpResponse, useServerMock } from "@/api/client/__mocks__";
import { REQUEST_ID_HEADER } from "@/api/staleCacheRetry";

const { server, http } = useServerMock();

const HTML = "<!doctype html><html><body>failover</body></html>";
const HISTORY = { id: "abc", name: "recovered" };
const GALAXY_HEADERS = { [REQUEST_ID_HEADER]: "3f2c0d1e9a8b4c7d8e6f5a4b3c2d1e0f" };

/** Answers foreign HTML for the first `htmlCount` requests and Galaxy JSON afterwards. */
function serveHtmlThenJson(htmlCount: number, htmlHeaders = {}) {
    const cacheControlHeaders: (string | null)[] = [];
    server.use(
        http.get("/api/histories/{history_id}", ({ request, response }) => {
            cacheControlHeaders.push(request.headers.get("Cache-Control"));
            if (cacheControlHeaders.length <= htmlCount) {
                return response.untyped(
                    new HttpResponse(HTML, { headers: { "Content-Type": "text/html", ...htmlHeaders } }),
                );
            }
            return response(200).json(HISTORY as never, { headers: GALAXY_HEADERS });
        }),
    );
    return cacheControlHeaders;
}

const HISTORY_PARAMS = { params: { path: { history_id: "abc" } } };

describe("staleCacheRetryMiddleware", () => {
    let consoleWarnSpy: ReturnType<typeof vi.spyOn>;

    beforeEach(() => {
        consoleWarnSpy = vi.spyOn(console, "warn").mockImplementation(() => {});
    });
    afterEach(() => {
        consoleWarnSpy.mockRestore();
    });

    it("retries a foreign HTML GET response with the cache bypassed", async () => {
        const cacheControlHeaders = serveHtmlThenJson(1);

        const { data, response } = await GalaxyApi().GET("/api/histories/{history_id}", HISTORY_PARAMS);

        expect(response.status).toBe(200);
        expect(data).toMatchObject(HISTORY);
        // happy-dom's Request has no `cache` property, so only the header is observable.
        expect(cacheControlHeaders).toEqual([null, "no-cache"]);
        expect(consoleWarnSpy).toHaveBeenCalledTimes(1);
    });

    it("does not retry JSON responses", async () => {
        const cacheControlHeaders = serveHtmlThenJson(0);

        const { data } = await GalaxyApi().GET("/api/histories/{history_id}", HISTORY_PARAMS);

        expect(data).toMatchObject(HISTORY);
        expect(cacheControlHeaders).toEqual([null]);
        expect(consoleWarnSpy).not.toHaveBeenCalled();
    });

    it("does not retry HTML produced by Galaxy", async () => {
        const cacheControlHeaders = serveHtmlThenJson(Infinity, GALAXY_HEADERS);

        const { data } = await GalaxyApi().GET("/api/histories/{history_id}", { ...HISTORY_PARAMS, parseAs: "text" });

        expect(data).toBe(HTML);
        expect(cacheControlHeaders).toEqual([null]);
        expect(consoleWarnSpy).not.toHaveBeenCalled();
    });

    it("does not retry when the caller asked for HTML", async () => {
        const cacheControlHeaders = serveHtmlThenJson(Infinity);

        const { data } = await GalaxyApi().GET("/api/histories/{history_id}", {
            ...HISTORY_PARAMS,
            headers: { Accept: "text/html" },
            parseAs: "text",
        });

        expect(data).toBe(HTML);
        expect(cacheControlHeaders).toEqual([null]);
        expect(consoleWarnSpy).not.toHaveBeenCalled();
    });
});
