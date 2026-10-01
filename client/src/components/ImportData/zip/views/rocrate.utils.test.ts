import { describe, expect, it } from "vitest";

import { textValue } from "./rocrate.utils";

describe("textValue", () => {
    it("keeps a plain string", () => {
        expect(textValue("A crate")).toBe("A crate");
    });

    it("joins an array of strings and language-tagged values", () => {
        expect(textValue(["First part.", { "@value": "Second part.", "@language": "en" }])).toBe(
            "First part. Second part.",
        );
    });

    it("returns an empty string for missing or unusable values", () => {
        expect(textValue(undefined)).toBe("");
        expect(textValue({ "@id": "#something" })).toBe("");
        expect(textValue(42)).toBe("");
    });
});
