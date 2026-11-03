import { getLocalVue } from "@tests/vitest/helpers";
import { enableAutoUnmount, shallowMount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";

import CreateInstance from "./CreateInstance.vue";

const localVue = getLocalVue(true);

describe("CreateInstance", () => {
    enableAutoUnmount(afterEach);

    it("should render a loading message during loading", () => {
        const wrapper = shallowMount(CreateInstance, {
            props: {
                loading: true,
                loadingMessage: "component loading...",
            },
            global: localVue,
        });
        expect(wrapper.findComponent({ name: "LoadingSpan" }).exists()).toBeTruthy();
    });

    it("should hide a loading message after loading", () => {
        const wrapper = shallowMount(CreateInstance, {
            props: {
                loading: false,
                loadingMessage: "component loading...",
            },
            global: localVue,
        });
        expect(wrapper.findComponent({ name: "LoadingSpan" }).exists()).toBeFalsy();
    });
});
