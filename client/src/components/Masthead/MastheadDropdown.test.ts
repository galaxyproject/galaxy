import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";

import MastheadDropdown from "./MastheadDropdown.vue";

describe("MastheadDropdown.vue", () => {
    it("supports callback-backed and URL-backed menu items", async () => {
        const handler = vi.fn();
        const wrapper = mount(MastheadDropdown as object, {
            localVue: getLocalVue(),
            propsData: {
                id: "mixed-menu",
                menu: [
                    { title: "Callback", handler },
                    { title: "Destination", href: "https://example.org/root/?exact=true" },
                ],
            },
        });

        const items = wrapper.findAll("a.dropdown-item");
        expect(items.at(0).attributes("href")).toBe("#");
        expect(items.at(1).attributes("href")).toBe("https://example.org/root/?exact=true");

        await items.at(0).trigger("click");
        expect(handler).toHaveBeenCalledOnce();
    });
});
