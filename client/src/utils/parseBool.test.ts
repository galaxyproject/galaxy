import { describe, expect, it } from "vitest";

import { parseBool } from "./parseBool";

describe("parseBool", () => {
    it.each([
        [true, true],
        [false, false],
    ])("preserves boolean %s", (input, expected) => {
        expect(parseBool(input)).toBe(expected);
    });

    it.each<[string, boolean]>([
        ["true", true],
        ["True", true],
        ["TRUE", true],
        ["false", false],
        ["yes", false],
        ["1", false],
        ["", false],
    ])("parses string %j as %s", (input, expected) => {
        expect(parseBool(input)).toBe(expected);
    });

    it.each([null, undefined, 0, 1])("returns false for non-boolean, non-string input %s", (input) => {
        expect(parseBool(input)).toBe(false);
    });
});
