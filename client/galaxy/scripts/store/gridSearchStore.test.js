import store from "./index";

describe("store/gridSearchStore.js", () => {

    it("the searchTags in the store should be a Set object", () => {
        let searchTags = store.state.gridSearch.searchTags; // this is a Set()
        assert(searchTags instanceof Set, "searchTags wrong variable type, should be Set()");
    })

})
