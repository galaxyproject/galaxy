import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import { useServerMock } from "@/api/client/__mocks__";
import { ApiError, errorMessageAsString, rethrowSimpleWithStatus } from "@/utils/simple-error";

import { GalaxyApi } from "./index";

const { server } = useServerMock();

const FROM_GALAXY = { "X-Request-ID": "3f2a9c" };

function respondWith(body: string, status: number, headers: Record<string, string> = {}) {
    server.use(
        http.get(
            "/api/configuration",
            () => new HttpResponse(body, { status, headers: { "content-type": "text/html", ...headers } }),
        ),
    );
}

async function fetchConfiguration() {
    return await GalaxyApi().GET("/api/configuration");
}

describe("errorResponseMiddleware", () => {
    // What a proxy answering in Galaxy's place might write. None carry a request id.
    it.each([
        ["a whole HTML page", "<!DOCTYPE html><html><head><title>504</title></head><body>...</body></html>", 504],
        ["a fragment with no doctype", "<h1>504 Gateway Time-out</h1><hr><center>nginx</center>", 504],
        ["a page behind an XML prologue", '<?xml version="1.0"?><!DOCTYPE html><html></html>', 503],
        ["a body that claims to be JSON but does not parse", '{"err_msg": "upstream closed the conn', 502],
        ["valid JSON in some other shape", '{"message": "upstream timeout"}', 504],
        ["JSON in Galaxy's shape", '{"err_msg": "not really Galaxy", "err_code": 0}', 502],
    ])("normalizes %s into an error object", async (_label, body, status) => {
        respondWith(body as string, status as number, { "content-type": "application/json" });

        const { data, error } = await fetchConfiguration();

        expect(data).toBeUndefined();
        expect(error).toEqual({ err_msg: expect.stringContaining(`(${status})`), err_code: status });
    });

    it("names the failure in a way that suits a user", async () => {
        respondWith("<html><body>gateway timeout</body></html>", 504);

        const { error } = await fetchConfiguration();

        expect(errorMessageAsString(error)).toBe("Galaxy took too long to respond (504)");
    });

    // Browsers leave statusText empty over HTTP/2, and msw's HttpResponse would fill it in.
    // A DELETE, because the rate limiter retries a GET that gets a 429.
    it.each([
        [400, "The request was not valid (400)"],
        [401, "Authentication is required (401)"],
        [403, "Access was denied (403)"],
        [404, "The requested resource was not found (404)"],
        [408, "The request timed out (408)"],
        [413, "The request was too large (413)"],
        [429, "Too many requests, please wait and try again (429)"],
        [500, "An internal server error occurred (500)"],
        [502, "Galaxy is temporarily unavailable (502)"],
        [520, "Galaxy is temporarily unavailable (520)"],
        [521, "Galaxy is temporarily unavailable (521)"],
        [522, "Galaxy is temporarily unavailable (522)"],
        [523, "Galaxy is temporarily unavailable (523)"],
        [524, "Galaxy took too long to respond (524)"],
        [418, "The request failed (418)"],
    ])("names a %d without relying on the status text", async (status, message) => {
        server.use(
            http.delete(
                "/api/histories/:history_id",
                () => new Response("<html><body>nginx</body></html>", { status }),
            ),
        );

        const { error } = await GalaxyApi().DELETE("/api/histories/{history_id}", {
            params: { path: { history_id: "f2db41e1fa331b3e" } },
        });

        expect(errorMessageAsString(error)).toBe(message);
    });

    it("falls back to the status text for a status it has no wording for", async () => {
        respondWith("<html><body>teapot</body></html>", 418);

        const { error } = await fetchConfiguration();

        expect(errorMessageAsString(error)).toBe("I'm a Teapot (418)");
    });

    it("leaves a Galaxy API error untouched, whatever its content type says", async () => {
        respondWith(JSON.stringify({ err_msg: "Quota exceeded", err_code: 403002 }), 403, {
            ...FROM_GALAXY,
            "content-type": "text/plain",
        });

        const { error } = await fetchConfiguration();

        expect(error).toEqual({ err_msg: "Quota exceeded", err_code: 403002 });
    });

    it("normalizes a Galaxy error whose message is not a string", async () => {
        respondWith(JSON.stringify({ err_msg: { detail: "nested" }, err_code: 0 }), 500, {
            ...FROM_GALAXY,
            "content-type": "application/json",
        });

        const { error } = await fetchConfiguration();

        expect(errorMessageAsString(error)).toBe("An internal server error occurred (500)");
    });

    it("normalizes a Galaxy response that is not an API error", async () => {
        respondWith(JSON.stringify({ detail: "Not Found" }), 404, {
            ...FROM_GALAXY,
            "content-type": "application/json",
        });

        const { error } = await fetchConfiguration();

        expect(errorMessageAsString(error)).toBe("The requested resource was not found (404)");
    });

    it("keeps the original headers but not the length of the body it replaced", async () => {
        respondWith("", 503, { "Retry-After": "120", "Content-Length": "0" });

        const { error, response } = await fetchConfiguration();

        expect(response.headers.get("Retry-After")).toBe("120");
        expect(errorMessageAsString(error)).toBe("Galaxy is temporarily unavailable (503)");
    });

    it("gives rethrowSimpleWithStatus a readable message and the status", async () => {
        respondWith("<html><body>gateway timeout</body></html>", 504);

        const { error, response } = await fetchConfiguration();

        try {
            rethrowSimpleWithStatus(error, response);
            expect.unreachable("should have thrown");
        } catch (thrown) {
            expect(thrown).toBeInstanceOf(ApiError);
            expect((thrown as ApiError).message).toBe("Galaxy took too long to respond (504)");
            expect((thrown as ApiError).status).toBe(504);
        }
    });

    it("does not disturb a successful response", async () => {
        server.use(http.get("/api/configuration", () => HttpResponse.json({ brand: "Galaxy" })));

        const { data, error } = await fetchConfiguration();

        expect(error).toBeUndefined();
        expect(data).toMatchObject({ brand: "Galaxy" });
    });
});
