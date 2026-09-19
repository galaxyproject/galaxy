import axios, { type AxiosAdapter, type InternalAxiosRequestConfig } from "axios";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { installStaleCacheRetryInterceptor, isForeignHtmlResponse } from "./staleCacheRetry";

const HTML = "<!doctype html><html><body>failover</body></html>";
const JSON_BODY = { stats: { total_matches: 1 }, contents: [] };
const GALAXY_HEADERS = { "x-request-id": "3f2c0d1e9a8b4c7d8e6f5a4b3c2d1e0f" };
const MAX_REQUESTS_PER_CALL = 3;

function answer(config: InternalAxiosRequestConfig, data: unknown, contentType: string, extraHeaders = {}) {
    return { data, status: 200, statusText: "OK", headers: { "content-type": contentType, ...extraHeaders }, config };
}

/** Answers foreign HTML for the first `htmlCount` calls and Galaxy JSON afterwards. */
function createClient(htmlCount: number, htmlHeaders = {}) {
    const requests: InternalAxiosRequestConfig[] = [];
    const adapter: AxiosAdapter = async (config) => {
        requests.push(config);
        if (requests.length > MAX_REQUESTS_PER_CALL) {
            throw new Error(`runaway retry loop: ${requests.length} requests`);
        }
        return requests.length <= htmlCount
            ? answer(config, HTML, "text/html", htmlHeaders)
            : answer(config, JSON_BODY, "application/json", GALAXY_HEADERS);
    };
    const client = axios.create({ adapter });
    installStaleCacheRetryInterceptor(client);
    return { client, requests };
}

describe("isForeignHtmlResponse", () => {
    const poisoned = {
        method: "get",
        status: 200,
        contentType: "text/html; charset=utf-8",
        requestId: null,
    };

    it.each(["get", "GET", "head", "HEAD", undefined])(
        "matches a successful HTML %s without a request id",
        (method) => {
            expect(isForeignHtmlResponse({ ...poisoned, method })).toBe(true);
        },
    );

    it.each([
        ["a POST", { method: "post" }],
        ["a PUT", { method: "put" }],
        ["a DELETE", { method: "delete" }],
        ["a non-2xx status", { status: 503 }],
        ["a JSON body", { contentType: "application/json" }],
        ["a missing content type", { contentType: null }],
        ["HTML produced by Galaxy", { requestId: GALAXY_HEADERS["x-request-id"] }],
    ])("ignores %s", (_label, override) => {
        expect(isForeignHtmlResponse({ ...poisoned, ...override })).toBe(false);
    });
});

describe("installStaleCacheRetryInterceptor", () => {
    let consoleWarnSpy: ReturnType<typeof vi.spyOn>;

    beforeEach(() => {
        consoleWarnSpy = vi.spyOn(console, "warn").mockImplementation(() => {});
    });
    afterEach(() => {
        consoleWarnSpy.mockRestore();
    });

    it.each(["get", "head"] as const)(
        "retries a foreign HTML %s response with the cache bypassed and returns the retry",
        async (method) => {
            const { client, requests } = createClient(1);
            const { data } = await client[method]("/api/histories/abc/contents?v=dev&offset=0");
            expect(data).toEqual(JSON_BODY);
            expect(requests).toHaveLength(2);
            expect(requests[0]!.headers.get("Cache-Control")).toBeUndefined();
            expect(requests[1]!.headers.get("Cache-Control")).toBe("no-cache");
            expect(requests[1]!.headers.get("Pragma")).toBe("no-cache");
            expect(consoleWarnSpy).toHaveBeenCalledTimes(1);
        },
    );

    it("gives up after one retry", async () => {
        const { client, requests } = createClient(Infinity);
        const { data } = await client.get("/api/histories/abc/contents");
        expect(data).toBe(HTML);
        expect(requests).toHaveLength(2);
    });

    it("passes JSON responses through untouched", async () => {
        const { client, requests } = createClient(0);
        const { data } = await client.get("/api/histories/abc/contents");
        expect(data).toEqual(JSON_BODY);
        expect(requests).toHaveLength(1);
        expect(consoleWarnSpy).not.toHaveBeenCalled();
    });

    it("passes HTML produced by Galaxy through untouched", async () => {
        const { client, requests } = createClient(Infinity, GALAXY_HEADERS);
        const { data } = await client.get("/api/histories/h/contents/abc/display");
        expect(data).toBe(HTML);
        expect(requests).toHaveLength(1);
        expect(consoleWarnSpy).not.toHaveBeenCalled();
    });

    it.each([
        ["a POST", (client) => client.post("/api/histories", {})],
        ["a non-JSON responseType", (client) => client.get("/api/histories/abc/contents", { responseType: "text" })],
    ] as [string, (client: ReturnType<typeof createClient>["client"]) => Promise<unknown>][])(
        "does not retry %s",
        async (_label, call) => {
            const { client, requests } = createClient(Infinity);
            await call(client);
            expect(requests).toHaveLength(1);
            expect(consoleWarnSpy).not.toHaveBeenCalled();
        },
    );
});
