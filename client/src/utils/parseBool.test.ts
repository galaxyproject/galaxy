import { describe, expect, it } from "vitest";

import { parseBool } from "./parseBool";

describe("parseBool", () => {
    it("should return true for boolean true", () => {
        expect(parseBool(true)).toBe(true);
    });

    it("should return false for boolean false", () => {
        expect(parseBool(false)).toBe(false);
    });

    it("should return true for string 'true'", () => {
        expect(parseBool("true")).toBe(true);
    });

    it("should return true for string 'True' (case-insensitive)", () => {
        expect(parseBool("True")).toBe(true);
        expect(parseBool("TRUE")).toBe(true);
    });

    it("should return false for string 'false'", () => {
        expect(parseBool("false")).toBe(false);
    });

    it("should return false for other strings", () => {
        expect(parseBool("yes")).toBe(false);
        expect(parseBool("1")).toBe(false);
        expect(parseBool("")).toBe(false);
    });

    it("should return false for non-boolean non-string values", () => {
        expect(parseBool(null)).toBe(false);
        expect(parseBool(undefined)).toBe(false);
        expect(parseBool(0)).toBe(false);
        expect(parseBool(1)).toBe(false);
    });
});
