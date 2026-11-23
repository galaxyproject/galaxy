import { mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";

import GBadge from "./GBadge.vue";

// vitest throws on any read of an export the factory leaves out, as in specs that only mock useRouter.
vi.mock("vue-router", () => ({ useRouter: vi.fn() }));

describe("GBadge under a vue-router mock without RouterLink", () => {
    it.each([
        ["span", {}, "SPAN"],
        ["anchor", { href: "https://example.org" }, "A"],
        ["button", { button: true }, "BUTTON"],
    ])("renders a %s without reading RouterLink", (_name, props, tagName) => {
        const wrapper = mount(GBadge, { props, slots: { default: "label" } });

        expect(wrapper.element.tagName).toBe(tagName);
        expect(wrapper.text()).toBe("label");
    });
});
