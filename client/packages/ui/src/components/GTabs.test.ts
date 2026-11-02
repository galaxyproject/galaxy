import { flushPromises, mount } from "@vue/test-utils";
import { afterAll, beforeAll, describe, expect, it } from "vitest";
import { configureCompat, defineComponent, h, nextTick } from "vue";

import GTab from "./GTab.vue";
import GTabs from "./GTabs.vue";

// Vue 3 (and the Tool Shed, which runs it without compat) renders a bound `false` as attr="false"
// instead of dropping it, so check the tab ARIA under that behavior.
beforeAll(() => configureCompat({ ATTR_FALSE_VALUE: false }));
afterAll(() => configureCompat({ ATTR_FALSE_VALUE: true }));

async function mountTabs() {
    const Parent = defineComponent({
        components: { GTabs, GTab },
        template: `<GTabs><GTab title="One">one</GTab><GTab title="Two">two</GTab><GTab title="Three" disabled>three</GTab></GTabs>`,
    });
    const wrapper = mount(Parent);
    await flushPromises();
    return wrapper.findAll(".nav-link");
}

describe("GTabs", () => {
    it("marks only the active tab as selected", async () => {
        const links = await mountTabs();

        expect(links.map((link) => link.attributes("aria-selected"))).toEqual(["true", "false", "false"]);
    });

    it("sets aria-disabled only on disabled tabs", async () => {
        const links = await mountTabs();

        expect(links[0]!.attributes("aria-disabled")).toBeUndefined();
        expect(links[1]!.attributes("aria-disabled")).toBeUndefined();
        expect(links[2]!.attributes("aria-disabled")).toBe("true");
    });

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
