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

        test("should update the state Map and store a Set", () => {
            expect(stateTags instanceof Set).toBeTruthy();
            testTags.forEach((t) => {
                expect(stateTags.has(t)).toBeTruthy();
            });
        });

        test("that set should contain all the passed tags", () => {
            testTags.forEach((t) => {
                expect(stateTags.has(t)).toBeTruthy();
            });
        });

        test("should store a list of unique values", () => {
            expect(stateTags.size == 3).toBeTruthy();
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

        test("should update the state Map and store a Set", () => {
            const tags = thisGetter(testKey);
            expect(tags instanceof Array).toBeTruthy();
            expect((tags.length = 3)).toBeTruthy();
        });
    });
});
