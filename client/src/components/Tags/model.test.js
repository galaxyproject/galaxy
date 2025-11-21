import { createTag, diffTags, VALID_TAG_RE } from "./model";

describe("Tags/model.js", () => {
    // Basic props

    describe("tag model", () => {
        it("should have a string representation equal to text prop", () => {
            const testLabel = "abc";
            const model = createTag(testLabel);
            expect(model == testLabel).toBeTruthy();
            expect(model.text).toEqual(testLabel);
            expect(model.toString()).toEqual(testLabel);
        });
    });

    // Factory Function

    describe("createTag", () => {
        it("should build a model from a string", () => {
            const label = "floob";
            const model = createTag(label);
            expect(model.text).toBe(label);
        });

        it("should build a model from an object", () => {
            const data = { text: "floob" };
            const model = createTag(data);
            expect(model.text).toBe(data.text);
        });
    });

    // Filtered select function, currently used in component to remove
    // selected items from a list of returned autocomplete options

    describe("diffTags", () => {
        let source;
        let selected;

        beforeEach(() => {
            source = ["a", "b", "c", "d"].map(createTag);
            selected = ["a", "d", "f"].map(createTag);
        });

        it("should remove duplicates from a passed array", () => {
            const result = diffTags(source, selected);
            expect(result.length).toBe(2);
            expect(result[0].equals(source[1])).toBeTruthy();
            expect(result[0].equals(createTag("b"))).toBeTruthy();
            expect(result[1].equals(source[2])).toBeTruthy();
            expect(result[1].equals(createTag("c"))).toBeTruthy();
        });
    });

    describe("handles name tags", () => {
        it("should accept a #label", () => {
            const testLabel = "#abc";
            const expectedLabel = "name:abc";
            const model = createTag(testLabel);
            expect(model == expectedLabel).toBeTruthy();
            expect(model.text).toEqual(expectedLabel);
            expect(model.toString()).toEqual(expectedLabel);
        });
    });

    describe("Tag matching regular expression tests", () => {
        it("Should allow valid tags", () => {
            const validTags = [
                "tag1",
                "tag.subtag",
                "tag.subtag.subtag",
                "tag.subtag:value",
                "🌌",
                "name:🌌",
                "🌌.🌌",
                "name:value..separated",
            ];
            for (const tag of validTags) {
                expect(VALID_TAG_RE.test(tag)).toBeTruthy();
            }
        });
        it("Should not allow invalid tags", () => {
            const invalidTags = [
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
            ];
            for (const tag of invalidTags) {
                expect(VALID_TAG_RE.test(tag)).toBeFalsy();
            }
        });
    });
});
