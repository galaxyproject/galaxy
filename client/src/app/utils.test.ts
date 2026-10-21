import { describe, expect, it } from "vitest";

import { getFullAppUrl } from "./utils";

describe("getFullAppUrl", () => {
    it("returns the app root when no path is provided", () => {
        const appUrl = getFullAppUrl();
        expect(appUrl).toBe("http://localhost/");
    });

    it("appends a relative path to the app root", () => {
        const appUrl = getFullAppUrl("home");
        expect(appUrl).toBe("http://localhost/home");
    });
});
