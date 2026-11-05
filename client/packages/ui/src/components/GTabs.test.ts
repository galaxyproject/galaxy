import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import { h, nextTick } from "vue";

import GTab from "./GTab.vue";
import GTabs from "./GTabs.vue";

describe("GTabs", () => {
    it("keeps the managed tab attributes when titleLinkAttributes overlaps them", async () => {
        // One object for every slot render; GTab re-registers whenever this prop changes identity.
        const titleLinkAttributes = {
            id: "caller-id",
            role: "button",
            href: "/elsewhere",
            "data-description": "first tab",
        };
        // titleLinkAttributes is spread before the explicit bindings, so under Vue 3 source-order
        // v-bind the managed id/role/href win and anything else from the caller still applies.
        const wrapper = mount(GTabs, {
            slots: {
                default: () =>
                    h(GTab, {
                        title: "First",
                        id: "first-panel",
                        buttonId: "first-button",
                        titleLinkAttributes,
                    }),
            },
        });
        await nextTick();

        const link = wrapper.get("a.nav-link");
        expect(link.attributes("id")).toBe("first-button");
        expect(link.attributes("role")).toBe("tab");
        expect(link.attributes("href")).toBe("#");
        expect(link.attributes("aria-controls")).toBe("first-panel");
        expect(link.attributes("data-description")).toBe("first tab");
    });
});
