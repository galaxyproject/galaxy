import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

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
});
