import { GAlert } from "@galaxyproject/galaxy-ui";
import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import { h } from "vue";

import LoadingSpan from "./LoadingSpan.vue";

describe("LoadingSpan", () => {
    it("announces its message as a status", () => {
        const wrapper = mount(LoadingSpan, { props: { message: "Loading datasets" } });

        expect(wrapper.attributes("role")).toBe("status");
        expect(wrapper.text()).toBe("Loading datasets...");
    });

    it("keeps a visually hidden message when spinner-only", () => {
        const wrapper = mount(LoadingSpan, { props: { spinnerOnly: true } });

        expect(wrapper.attributes("role")).toBe("status");
        expect(wrapper.find(".loading-message").exists()).toBe(false);
        expect(wrapper.find(".sr-only").text()).toBe("Loading...");
    });

    it("leaves the role to an enclosing GAlert", () => {
        const wrapper = mount(GAlert, { slots: { default: () => h(LoadingSpan, { message: "Loading datasets" }) } });
        const span = wrapper.findComponent(LoadingSpan);

        expect(span.attributes("role")).toBeUndefined();
        expect(span.text()).toBe("Loading datasets...");
    });
});
