import { describe, expect, it } from "vitest";

import { capitalizeFirstLetter } from "./strings";

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
