import { getLocalVue } from "@tests/vitest/helpers";
import { mount, shallowMount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";

import { sanitizeHtml } from "@/directives/sanitizeHtml";

import NodeInvocationText from "./NodeInvocationText.vue";

describe("NodeInvocationText", () => {
    it("renders input step text through v-sanitize-html", () => {
        vi.mocked(sanitizeHtml).mockImplementation((html) => `<span class="sanitized">${html}</span>`);
        const wrapper = shallowMount(NodeInvocationText as object, {
            localVue: getLocalVue(),
            propsData: { invocationStep: { type: "data_input", nodeText: "1: <b>input.fastq</b>" } },
        });

        expect(sanitizeHtml).toHaveBeenCalledWith(expect.any(String), "default");
        expect(wrapper.find(".sanitized").exists()).toBe(true);
    });

    it("renders a color swatch for a hex color input value", () => {
        const wrapper = mount(NodeInvocationText as object, {
            localVue: getLocalVue(),
            propsData: { invocationStep: { type: "parameter_input", nodeText: "#ff0000" } },
        });

        const swatch = wrapper.find("input[type=color]");
        expect(swatch.exists()).toBe(true);
        expect((swatch.element as HTMLInputElement).value).toBe("#ff0000");
    });
});
