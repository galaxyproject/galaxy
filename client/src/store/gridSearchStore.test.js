import { createLocalVue } from "@vue/test-utils";
import Vuex from "vuex";
import { gridSearchStore } from "./gridSearchStore";

const localVue = createLocalVue();
localVue.use(Vuex);

const testStore = new Vuex.Store({
    modules: {
        gridSearchStore,
    },
});

describe("store/gridSearchStore.js", () => {
    test("the searchTags in the store should be a Set object", () => {
        const searchTags = testStore.state.gridSearchStore.searchTags; // this is a Set()
        expect(searchTags instanceof Set).toBeTruthy();
    });
});
