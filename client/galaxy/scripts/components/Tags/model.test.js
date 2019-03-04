import { createTag, diffTags } from "./model";

describe("Tags/model.js", () => {
    // Basic props

    describe("tag model", () => {
        it("should have a string representation equal to text prop", () => {
            let testLabel = "abc";
            let model = createTag(testLabel);
            assert.equal(model, testLabel);
            assert.equal(model.text, testLabel);
            assert.equal(model.toString(), testLabel);
        });
    });

    // Factory Function

    describe("createTag", () => {
        it("should build a model from a string", () => {
            let label = "floob";
            let model = createTag(label);
            expect(model.text).to.equal(label);
        });

        it("should build a model from an object", () => {
            let data = { text: "floob" };
            let model = createTag(data);
            expect(model.text).to.equal(data.text);
        });
    });

    // Filtered select function, currently used in component to remove
    // selected items from a list of returned autocomplete options

    describe("diffTags", () => {
        let source, selected;

        beforeEach(() => {
            source = ["a", "b", "c", "d"].map(createTag);
            selected = ["a", "d", "f"].map(createTag);
        });

        it("should remove duplicates from a passed array", () => {
            let result = diffTags(source, selected);
            expect(result.length).to.equal(2);
            assert(result[0].equals(source[1]), true);
            assert(result[0].equals(createTag("b")), true);
            assert(result[1].equals(source[2]), true);
            assert(result[1].equals(createTag("c")), true);
        });
    });
});
