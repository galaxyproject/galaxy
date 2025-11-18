import { isValidUrl } from "./zipExplorer";

describe("useZipExplorer", () => {
    describe("isValidUrl", () => {
        it("should return true for valid URLs", () => {
            expect(isValidUrl("http://example.com")).toBe(true);
            expect(isValidUrl("https://example.com")).toBe(true);
        });

        it("should return false for invalid URLs", () => {
            expect(isValidUrl("invalid-url")).toBe(false);
            expect(isValidUrl("htp://example.com")).toBe(false);
        });

        it("should return false for empty strings", () => {
            expect(isValidUrl("")).toBe(false);
        });

        it("should return false for null or undefined values", () => {
            expect(isValidUrl(null)).toBe(false);
            expect(isValidUrl(undefined)).toBe(false);
        });

        it("should return false for multiple URLs", () => {
            expect(isValidUrl("http://example.com\nhttp://example2.com")).toBe(false);
            expect(isValidUrl("https://example.com https://example2.com")).toBe(false);
        });
    });
});
