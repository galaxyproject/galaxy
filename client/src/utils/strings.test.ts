import { describe, expect, it } from "vitest";

import { capitalizeFirstLetter, pluralize } from "./strings";

describe("capitalizeFirstLetter", () => {
    it("capitalizes a normal string", () => {
        expect(capitalizeFirstLetter("google")).toBe("Google");
    });

    it("trims whitespace", () => {
        expect(capitalizeFirstLetter("  google  ")).toBe("Google");
    });

    it("returns empty string for undefined input", () => {
        expect(capitalizeFirstLetter(undefined)).toBe("");
    });

    it("returns empty string for null input", () => {
        expect(capitalizeFirstLetter(null as unknown as string)).toBe("");
    });

    it("returns empty string for empty string", () => {
        expect(capitalizeFirstLetter("")).toBe("");
    });
});

describe("pluralize", () => {
    it("uses the singular for exactly one", () => {
        expect(pluralize(1, "workflow")).toBe("workflow");
    });

    it("appends s by default for other counts", () => {
        expect(pluralize(0, "workflow")).toBe("workflows");
        expect(pluralize(2, "workflow")).toBe("workflows");
    });

    it("uses an explicit plural when given", () => {
        expect(pluralize(3, "history", "histories")).toBe("histories");
        expect(pluralize(1, "history", "histories")).toBe("history");
    });
});
