/* global expect */

import Vuex from "vuex";
import { createLocalVue } from "@vue/test-utils";
import _l from "utils/localization";
import { tagStore } from "./tagStore";


describe("store/tagStore.js", () => {

    let localVue = createLocalVue();
    localVue.filter("localize", value => _l(value));
    localVue.use(Vuex);

    let testKey = "foo";
    let testTags = ["a","b","c"];

    describe("actions/updateTags", () => {

        it("should update the store with the tags we give it", () => {
            
            tagStore.dispatch("updateTags", { key: testKey, tags: testTags });
            console.log(tagStore.state);

            let retrievedTags = tagStore.getters.getTagsByKey(testKey);
            expect(retrievedTags.length).to.equal(testTags.length);
        });

    })

})
