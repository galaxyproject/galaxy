import PageIndexActions from "./PageIndexActions";
import { shallowMount } from "@vue/test-utils";
import { getLocalVue } from "jest/helpers";

import "jest-location-mock";

const localVue = getLocalVue();

describe("PageIndexActions.vue", () => {
    let wrapper;

    beforeEach(async () => {
        const propsData = {
            root: "/rootprefix/",
        };
        wrapper = shallowMount(PageIndexActions, {
            propsData,
            localVue,
        });
    });

    describe("naviation", () => {
        it("should create a page when create is clicked", async () => {
            await wrapper.find("#page-create").trigger("click");
            expect(window.location).toBeAt("/rootprefix/pages/create");
        });
    });
});
