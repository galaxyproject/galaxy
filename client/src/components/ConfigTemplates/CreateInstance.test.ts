import { getLocalVue } from "@tests/vitest/helpers";
import { shallowMount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import CreateInstance from "./CreateInstance.vue";

const localVue = getLocalVue(true);

describe("CreateInstance", () => {
    it("should render a loading message during loading", async () => {
        const wrapper = shallowMount(CreateInstance as object, {
            props: {
                loading: true,
                loadingMessage: "component loading...",
            },
            global: localVue,
        });
        const loadingSpan = wrapper.findComponent({ name: "LoadingSpan" }).exists();
        expect(loadingSpan).toBeTruthy();
    });

    it("should hide a loading message after loading", async () => {
        const wrapper = shallowMount(CreateInstance as object, {
            props: {
                loading: false,
                loadingMessage: "component loading...",
            },
            global: localVue,
        });
        const loadingSpan = wrapper.findComponent({ name: "LoadingSpan" }).exists();
        expect(loadingSpan).toBeFalsy();
    });
});
