import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import { useServerMock } from "@/api/client/__mocks__";
import { ApiError, errorMessageAsString, rethrowSimpleWithStatus } from "@/utils/simple-error";

import { GalaxyApi } from "./index";

const { server } = useServerMock();

function respondWith(body: string, status: number, contentType = "text/html") {
    server.use(
        http.get(
            "/api/configuration",
            () => new HttpResponse(body, { status, headers: { "content-type": contentType } }),
        ),
    );
}

async function fetchConfiguration() {
    return await GalaxyApi().GET("/api/configuration");
}

describe("errorResponseMiddleware", () => {
    // Every shape a gateway might answer with. None of them parse, so all take the
    // same branch -- listed out because these are the bodies seen in the wild.
    it.each([
        ["a whole HTML page", "<!DOCTYPE html><html><head><title>504</title></head><body>...</body></html>", 504],
        ["a fragment with no doctype", "<h1>504 Gateway Time-out</h1><hr><center>nginx</center>", 504],
        ["a page behind an XML prologue", '<?xml version="1.0"?><!DOCTYPE html><html></html>', 503],
        ["an empty body", "", 502],
        ["a body that claims to be JSON but does not parse", '{"err_msg": "upstream closed the conn', 502],
    ])("normalizes %s into an error object", async (_label, body, status) => {
        respondWith(body as string, status as number, "application/json");

        const { data, error } = await fetchConfiguration();

        expect(data).toBeUndefined();
        expect(typeof error).toBe("object");
        expect(error).toMatchObject({ err_code: status });
        expect(errorMessageAsString(error)).not.toContain("<");
    });

    it("names the failure in a way that suits a user", async () => {
        respondWith("<html><body>gateway timeout</body></html>", 504);

        const { error } = await fetchConfiguration();

        expect(errorMessageAsString(error)).toBe("Galaxy took too long to respond (504)");
    });

    it("leaves a genuine JSON API error untouched", async () => {
        respondWith(JSON.stringify({ err_msg: "Dataset not found", err_code: 404 }), 404, "application/json");

        const { error } = await fetchConfiguration();

        expect(errorMessageAsString(error)).toBe("Dataset not found");
    });

    it("passes through a JSON error that was mislabelled as text", async () => {
        respondWith(JSON.stringify({ err_msg: "Quota exceeded" }), 400, "text/plain");

        const { error } = await fetchConfiguration();

        expect(errorMessageAsString(error)).toBe("Quota exceeded");
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
