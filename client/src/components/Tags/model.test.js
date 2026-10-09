import { describe, expect, it } from "vitest";

import { createTag, diffTags, VALID_TAG_RE } from "./model";

describe("Tags/model.js", () => {
    describe("tag model", () => {
        it("represents its text through coercion and toString", () => {
            const testLabel = "abc";
            const model = createTag(testLabel);
            expect(model == testLabel).toBe(true);
            expect(model.text).toEqual(testLabel);
            expect(model.toString()).toEqual(testLabel);
        });
    });

    describe("createTag", () => {
        it("creates a tag from a string", () => {
            const label = "floob";
            const model = createTag(label);
            expect(model.text).toBe(label);
        });

        it("creates a tag from an object", () => {
            const data = { text: "floob" };
            const model = createTag(data);
            expect(model.text).toBe(data.text);
        });
    });

    describe("diffTags", () => {
        it("returns unselected tags in source order", () => {
            const source = ["a", "b", "c", "d"].map(createTag);
            const selected = ["a", "d", "f"].map(createTag);

            const result = diffTags(source, selected);

            expect(result).toHaveLength(2);
            expect(result[0].equals(source[1])).toBe(true);
            expect(result[0].equals(createTag("b"))).toBe(true);
            expect(result[1].equals(source[2])).toBe(true);
            expect(result[1].equals(createTag("c"))).toBe(true);
        });
    });

    describe("name tags", () => {
        it("normalizes a #label to a name tag", () => {
            const testLabel = "#abc";
            const expectedLabel = "name:abc";
            const model = createTag(testLabel);
            expect(model == expectedLabel).toBe(true);
            expect(model.text).toEqual(expectedLabel);
            expect(model.toString()).toEqual(expectedLabel);
        });
    });

    describe("VALID_TAG_RE", () => {
        it.each([
            "tag1",
            "tag.subtag",
            "tag.subtag.subtag",
            "tag.subtag:value",
            "🌌",
            "name:🌌",
            "🌌.🌌",
            "name:value..separated",
        ])("accepts %j", (tag) => {
            expect(VALID_TAG_RE.test(tag)).toBe(true);
        });

        it.each([
            "",
            " ",
            ".",
            "..",
            "...",
            ":",
            ":value",
            "tag:",
            "tag.",
            ".tag",
            "tag..subtag:value",
            "tag:no spaces in value",
        ])("rejects %j", (tag) => {
            expect(VALID_TAG_RE.test(tag)).toBe(false);
        });
    });
});
