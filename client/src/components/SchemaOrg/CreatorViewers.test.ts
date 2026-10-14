import { mount, type VueWrapper } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";

import GrantViewer from "./GrantViewer.vue";
import OrganizationViewer from "./OrganizationViewer.vue";
import PersonViewer from "./PersonViewer.vue";
import GPopover from "@/components/BaseComponents/GPopover.vue";

let wrapper: VueWrapper | undefined;

const CASES = [
    {
        name: "PersonViewer",
        component: PersonViewer,
        propsData: { person: { givenName: "Ada", familyName: "Lovelace", email: "ada@example.org" } },
        prefix: "person-viewer-",
    },
    {
        name: "OrganizationViewer",
        component: OrganizationViewer,
        propsData: { organization: { name: "Example Institute", email: "info@example.org" } },
        prefix: "organization-viewer-",
    },
    {
        name: "GrantViewer",
        component: GrantViewer,
        propsData: { grant: { name: "Example Grant", identifier: "EX-123" } },
        prefix: "grant-viewer-",
    },
];

describe.each(CASES)("$name", ({ component, propsData, prefix }) => {
    afterEach(() => {
        wrapper?.unmount();
        wrapper = undefined;
        document.body.innerHTML = "";
    });

    it("anchors its popover to an element that is actually in the document", () => {
        wrapper = mount(component as object, { attachTo: document.body, propsData });

        const target = wrapper.findComponent(GPopover).props("target");

        // The old `$refs['button'] || 'works-lazily'` target never resolved: $refs is empty on first render.
        expect(target).toEqual(expect.stringContaining(prefix));
        expect(document.getElementById(target as string)).not.toBeNull();
    });

    it("anchors its popover to a named button so keyboard users can open it", async () => {
        wrapper = mount(component as object, { attachTo: document.body, propsData });
        await wrapper.vm.$nextTick();
        await wrapper.vm.$nextTick();

        const target = document.getElementById(wrapper.findComponent(GPopover).props("target") as string);

        expect(target?.tagName).toBe("BUTTON");
        expect(target?.getAttribute("title")).toEqual(expect.stringContaining("details"));
        expect(target?.getAttribute("aria-expanded")).toBe("false");
    });

    it("gives each instance a distinct popover target", () => {
        const first = mount(component as object, { attachTo: document.body, propsData });
        const second = mount(component as object, { attachTo: document.body, propsData });

        const firstTarget = first.findComponent(GPopover).props("target");
        const secondTarget = second.findComponent(GPopover).props("target");

        // Duplicate ids would anchor every creator's popover to the first icon.
        expect(firstTarget).not.toEqual(secondTarget);

        first.unmount();
        second.unmount();
    });
});
