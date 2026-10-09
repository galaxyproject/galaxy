import { describe, expect, it } from "vitest";

import { isValidUrl } from "./zipExplorer";

describe("zipExplorer.isValidUrl", () => {
    it.each(["http://example.com", "https://example.com"])("accepts the HTTP or HTTPS URL %j", (url) => {
        expect(isValidUrl(url)).toBe(true);
    });

    it.each(["invalid-url", "htp://example.com"])("rejects the malformed URL or unsupported scheme %j", (url) => {
        expect(isValidUrl(url)).toBe(false);
    });

    it.each(["", null, undefined])("rejects the missing URL %j", (url) => {
        expect(isValidUrl(url)).toBe(false);
    });

    it.each(["http://example.com\nhttp://example2.com", "https://example.com https://example2.com"])(
        "rejects multiple URLs in %j",
        (url) => {
            expect(isValidUrl(url)).toBe(false);
        },
    );
});
