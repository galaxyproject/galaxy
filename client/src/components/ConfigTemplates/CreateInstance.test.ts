import { shallowMount } from "@vue/test-utils";
import { getLocalVue } from "tests/jest/helpers";

import CreateInstance from "./CreateInstance.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

const localVue = getLocalVue(true);

describe("CreateInstance", () => {
    it("should render a loading message during loading", async () => {
        const wrapper = shallowMount(CreateInstance as any, {
            propsData: {
                loading: true,
                loadingMessage: "component loading...",
            },
            localVue,
        });
        const loadingSpan = wrapper.findComponent(LoadingSpan).exists();
        expect(loadingSpan).toBeTruthy();
    });

    it("should hide a loading message after loading", async () => {
        const wrapper = shallowMount(CreateInstance as any, {
            propsData: {
                loading: false,
                loadingMessage: "component loading...",
            },
            localVue,
        });
        const loadingSpan = wrapper.findComponent(LoadingSpan).exists();
        expect(loadingSpan).toBeFalsy();
    });
});
