import { describe, expect, it } from "vitest";

import { capitalizeFirstLetter, pluralize } from "./strings";

describe("capitalizeFirstLetter", () => {
    it.each([
        { name: "normal string", input: "google", expected: "Google" },
        { name: "surrounding whitespace", input: "  google  ", expected: "Google" },
        { name: "undefined input", input: undefined, expected: "" },
        { name: "empty string", input: "", expected: "" },
    ])("capitalizes $name", ({ input, expected }) => {
        expect(capitalizeFirstLetter(input)).toBe(expected);
    });

    it("returns an empty string for null at runtime", () => {
        // @ts-expect-error Null can arrive from untyped callers despite the string API.
        expect(capitalizeFirstLetter(null)).toBe("");
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
