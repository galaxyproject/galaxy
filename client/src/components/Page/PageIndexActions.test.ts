import PageIndexActions from "./PageIndexActions.vue";
import { shallowMount } from "@vue/test-utils";
import { getLocalVue } from "tests/jest/helpers";

import "jest-location-mock";

const localVue = getLocalVue();

describe("PageIndexActions.vue", () => {
    let wrapper: any;
    const mockRouter = {
        push: jest.fn(),
    };

    beforeEach(async () => {
        wrapper = shallowMount(PageIndexActions, {
            mocks: {
                $router: mockRouter,
            },
            localVue,
        });
    });

    describe("navigation", () => {
        it("should create a page when create is clicked", async () => {
            await wrapper.find("#page-create").trigger("click");
            expect(mockRouter.push).toHaveBeenCalledTimes(1);
            expect(mockRouter.push).toHaveBeenCalledWith("/pages/create");
        });
    });
});
