import { getLocalVue } from "@tests/vitest/helpers";
import { enableAutoUnmount, mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";

import SectionPatchView from "./SectionPatchView.vue";

const localVue = getLocalVue();

const ORIGINAL_SECTIONS = "# Intro\nOld intro text\n# Methods\nOld methods text\n# Results\nOld results text";
const PROPOSED_SECTIONS = "# Intro\nNew intro text\n# Methods\nOld methods text\n# Results\nNew results text";

type SectionPatchProps = InstanceType<typeof SectionPatchView>["$props"];

const REJECT_BUTTON = '[data-description="reject all patches"]';
const APPLY_BUTTON = '[data-description="apply selected patches"]';

enableAutoUnmount(afterEach);

// GButton emits `click` from its own root handler, so the apply/reject buttons
// have to be really mounted for a click to reach this component.
function mountPatchView(overrides: Partial<SectionPatchProps> = {}) {
    return mount(SectionPatchView, {
        props: {
            original: ORIGINAL_SECTIONS,
            proposed: PROPOSED_SECTIONS,
            ...overrides,
        },
        global: localVue,
    });
}

describe("SectionPatchView", () => {
    it("counts the two changed sections and excludes the unchanged Methods section", () => {
        const wrapper = mountPatchView();
        expect(wrapper.text()).toContain("2 sections changed");
    });

    it("shows the reject button for a patch proposal", () => {
        const wrapper = mountPatchView();
        expect(wrapper.find(REJECT_BUTTON).exists()).toBe(true);
    });

    it("disables applying the proposal before any sections are selected", () => {
        const wrapper = mountPatchView();
        expect(wrapper.find(APPLY_BUTTON).exists()).toBe(true);
        expect(wrapper.get(APPLY_BUTTON).attributes("aria-disabled")).toBe("true");
    });

    it("emits reject when the reject button is clicked", async () => {
        const wrapper = mountPatchView();
        await wrapper.get(REJECT_BUTTON).trigger("click");
        expect(wrapper.emitted("reject")).toHaveLength(1);
    });

    it("renders diff lines for the changed sections", () => {
        const wrapper = mountPatchView();
        const diffLines = wrapper.findAll(".diff-line");
        expect(diffLines.length).toBeGreaterThan(0);
    });

    it("shows a diff summary for each of the two changed sections", () => {
        const wrapper = mountPatchView();
        expect(wrapper.findAll(".diff-stats-inline")).toHaveLength(2);
    });

    it("uses the singular section count when one section changes", () => {
        const wrapper = mountPatchView({
            original: "# A\nold",
            proposed: "# A\nnew",
        });
        expect(wrapper.text()).toContain("1 section changed");
    });

    it("counts no changed sections when the proposal matches the original", () => {
        const wrapper = mountPatchView({
            original: "# A\nsame",
            proposed: "# A\nsame",
        });
        expect(wrapper.text()).toContain("0 sections changed");
    });
});
