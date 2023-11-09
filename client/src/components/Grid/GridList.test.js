import { mount } from "@vue/test-utils";
import { getLocalVue } from "tests/jest/helpers";

import MountTarget from "./GridList.vue";

const localVue = getLocalVue();

function createTarget(propsData) {
    return mount(MountTarget, {
        localVue,
        propsData,
        stubs: {
            Icon: true,
        },
    });
}

describe("GridList", () => {
    it("basic rendering", async () => {
        const wrapper = createTarget({
            id: "visualizations",
        });
        const findInput = wrapper.find("[data-description='filter text input']");
        expect(findInput.attributes().placeholder).toBe("search visualizations");
        expect(wrapper.find(".loading-message").text()).toBe("Loading...");
        const findAction = wrapper.find("[data-description='grid action create']");
        expect(findAction.text()).toBe("Create");
    });
});
