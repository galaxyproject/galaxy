import { tagStore } from "./tagStore";

describe("store/tagStore.js", () => {
    const state = tagStore.state;
    const { reset } = tagStore.mutations;

    afterEach(() => {
        reset(state);
    });

    describe("mutations/setTags", () => {
        const { setTags } = tagStore.mutations;
        const testKey = "foo";
        const testTags = ["a", "b", "c", "b"];

        let stateTags;

        beforeEach(() => {
            setTags(state, { key: testKey, tags: testTags });
            stateTags = state.modelTagCache.get(testKey);
        });

        it("should update the state Map and store a Set", () => {
            assert(stateTags instanceof Set, "Stored list should be a Set");
            testTags.forEach((t) => {
                assert(stateTags.has(t), `Missing tag: ${t}`);
            });
        });

        it("that set should contain all the passed tags", () => {
            testTags.forEach((t) => {
                assert(stateTags.has(t), `Missing tag: ${t}`);
            });
        });

        it("should store a list of unique values", () => {
            assert(stateTags.size == 3, "Stored list should only consist of unique items");
        });
    });

    describe("getters/getTagsById", () => {
        const { getTagsById } = tagStore.getters;
        const { setTags } = tagStore.mutations;
        const testKey = "foo";
        const testTags = ["a", "b", "c", "b"];

        let thisGetter;

        beforeEach(() => {
            setTags(state, { key: testKey, tags: testTags });
            // getter functions are compound functions, need to build the getter first
            thisGetter = getTagsById(state);
        });

        it("should update the state Map and store a Set", () => {
            let tags = thisGetter(testKey);
            assert(tags instanceof Array, "returned result should be a simple array");
            assert((tags.length = 3));
        });
    });
});
