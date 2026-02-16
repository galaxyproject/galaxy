import { getLocalVue } from "@tests/vitest/helpers";
import { shallowMount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import SectionPatchView from "./SectionPatchView.vue";

const localVue = getLocalVue();

const OLD = "# Intro\nOld intro text\n# Methods\nOld methods text\n# Results\nOld results text";
const NEW = "# Intro\nNew intro text\n# Methods\nOld methods text\n# Results\nNew results text";

function mountComponent(propsData = { original: OLD, proposed: NEW }) {
    return shallowMount(SectionPatchView as object, { localVue, propsData });
}

describe("SectionPatchView", () => {
    it("shows changed section count", () => {
        const wrapper = mountComponent();
        // Intro and Results changed, Methods unchanged
        expect(wrapper.text()).toContain("2 sections changed");
    });

    it("renders reject button", () => {
        const wrapper = mountComponent();
        expect(wrapper.find('[data-description="reject all patches"]').exists()).toBe(true);
    });

    it("renders apply button (disabled initially)", () => {
        const wrapper = mountComponent();
        const btn = wrapper.find('[data-description="apply selected patches"]');
        expect(btn.exists()).toBe(true);
        expect(btn.attributes("disabled")).toBeDefined();
    });

    it("emits reject on button click", async () => {
        const wrapper = mountComponent();
        await wrapper.find('[data-description="reject all patches"]').trigger("click");
        expect(wrapper.emitted("reject")).toHaveLength(1);
    });

    it("renders diff lines for changed sections", () => {
        const wrapper = mountComponent();
        const diffLines = wrapper.findAll(".diff-line");
        expect(diffLines.length).toBeGreaterThan(0);
    });

    it("shows per-section diff stats", () => {
        const wrapper = mountComponent();
        const statsElements = wrapper.findAll(".diff-stats-inline");
        expect(statsElements.length).toBe(2); // Intro + Results
    });

    it("handles single changed section", () => {
        const wrapper = mountComponent({
            original: "# A\nold",
            proposed: "# A\nnew",
        });
        expect(wrapper.text()).toContain("1 section changed");
    });

    it("handles all sections identical (no changed sections)", () => {
        const wrapper = mountComponent({
            original: "# A\nsame",
            proposed: "# A\nsame",
        });
        expect(wrapper.text()).toContain("0 sections changed");
    });
});
