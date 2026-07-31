import { mount, type Wrapper } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";
import type Vue from "vue";

import OrganizationViewer from "./OrganizationViewer.vue";
import PersonViewer from "./PersonViewer.vue";
import GPopover from "@/components/BaseComponents/GPopover.vue";

let wrapper: Wrapper<Vue> | undefined;

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
];

describe.each(CASES)("$name", ({ component, propsData, prefix }) => {
    afterEach(() => {
        wrapper?.destroy();
        wrapper = undefined;
        document.body.innerHTML = "";
    });

    it("anchors its popover to an element that is actually in the document", () => {
        wrapper = mount(component as object, { attachTo: document.body, propsData });

        const target = wrapper.findComponent(GPopover).props("target");

        // Regression guard. These viewers used to pass `$refs['button'] || 'works-lazily'`, but
        // $refs is empty on first render and is not reactive, so the target stayed the junk
        // string and the popover could never open until something else forced a re-render.
        expect(target).toEqual(expect.stringContaining(prefix));
        expect(document.getElementById(target)).not.toBeNull();
    });

    it("gives each instance a distinct popover target", () => {
        const first = mount(component as object, { attachTo: document.body, propsData });
        const second = mount(component as object, { attachTo: document.body, propsData });

        const firstTarget = first.findComponent(GPopover).props("target");
        const secondTarget = second.findComponent(GPopover).props("target");

        // A workflow can list several creators, and duplicate ids would make every popover
        // resolve to whichever icon happened to be first in the document.
        expect(firstTarget).not.toEqual(secondTarget);

        first.destroy();
        second.destroy();
    });
});
