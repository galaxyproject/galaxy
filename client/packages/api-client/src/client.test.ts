import createClient from "openapi-fetch";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { createGalaxyApi } from "./client";

const mockApiClient = vi.hoisted(() => ({
    GET: vi.fn(),
    POST: vi.fn(),
    PUT: vi.fn(),
    DELETE: vi.fn(),
    PATCH: vi.fn(),
}));

vi.mock("openapi-fetch", () => ({
    default: vi.fn(() => mockApiClient),
}));

describe("createGalaxyApi", () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    afterEach(() => {
        vi.unstubAllGlobals();
    });

    it("uses the browser origin when no base URL is supplied", () => {
        vi.stubGlobal("window", { location: { origin: "https://test-galaxy.org" } });

        createGalaxyApi();

        expect(createClient).toHaveBeenCalledWith({ baseUrl: "https://test-galaxy.org", headers: {} });
    });

    it("uses a custom base URL", () => {
        createGalaxyApi("https://usegalaxy.org");

        expect(createClient).toHaveBeenCalledWith({ baseUrl: "https://usegalaxy.org", headers: {} });
    });

    it("strips the trailing slash from a custom base URL", () => {
        createGalaxyApi("https://usegalaxy.org/");

        expect(createClient).toHaveBeenCalledWith({ baseUrl: "https://usegalaxy.org", headers: {} });
    });

    it("returns the configured client with its HTTP methods", () => {
        const api = createGalaxyApi();

        expect(api).toEqual(mockApiClient);
        expect(api).toHaveProperty("GET");
        expect(api).toHaveProperty("POST");
        expect(api).toHaveProperty("PUT");
        expect(api).toHaveProperty("DELETE");
        expect(api).toHaveProperty("PATCH");
    });
});
