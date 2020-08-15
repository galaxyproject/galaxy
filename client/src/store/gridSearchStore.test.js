import store from "./index";

describe("store/gridSearchStore.js", () => {
    test("the searchTags in the store should be a Set object", () => {
        const searchTags = store.state.gridSearch.searchTags; // this is a Set()
        expect(searchTags instanceof Set).toBeTruthy();
    });
});
