import { describe, expect, it } from "vitest";

import { capitalizeFirstLetter } from "./strings";

describe("capitalizeFirstLetter", () => {
    it("capitalizes a normal string", () => {
        expect(capitalizeFirstLetter("google")).toBe("Google");
    });

    it("trims whitespace", () => {
        expect(capitalizeFirstLetter("  google  ")).toBe("Google");
    });

    it("returns empty string for undefined input", () => {
        expect(capitalizeFirstLetter(undefined as unknown as string)).toBe("");
    });

    it("returns empty string for null input", () => {
        expect(capitalizeFirstLetter(null as unknown as string)).toBe("");
    });

    it("returns empty string for empty string", () => {
        expect(capitalizeFirstLetter("")).toBe("");
    });
});
