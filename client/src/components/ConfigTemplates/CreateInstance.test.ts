import { mount, shallowMount } from "@vue/test-utils";
import { getLocalVue } from "tests/jest/helpers";

import CreateInstance from "./CreateInstance.vue";

const { global } = getLocalVue(true);

describe("CreateInstance", () => {
    it("should render a loading message during loading", async () => {
        const wrapper = mount(CreateInstance as object, {
            props: {
                loading: true,
                loadingMessage: "component loading...",
            },
            global,
        });
        const loadingSpan = wrapper.find('[data-description="loading message"]').exists();
        expect(loadingSpan).toBeTruthy();
    });

    it("should hide a loading message after loading", async () => {
        const wrapper = mount(CreateInstance as object, {
            props: {
                loading: false,
                loadingMessage: "component loading...",
            },
            global,
        });
        const loadingSpan = wrapper.find('[data-description="loading message"]').exists();
        expect(loadingSpan).toBeFalsy();
    });
});
