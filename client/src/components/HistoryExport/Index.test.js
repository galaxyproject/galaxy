import { shallowMount } from "@vue/test-utils";
import Index from "./Index.vue";
import { getLocalVue } from "jest/helpers";

const localVue = getLocalVue();

describe("Index.vue", () => {
    it("should render tabs", () => {
        // just make sure the component renders to catch obvious big errors
        const wrapper = shallowMount(Index, {
            propsData: {
                historyId: "test_id",
            },
            localVue,
        });
        expect(wrapper.exists("b-tabs-stub")).toBeTruthy();
    });
});
