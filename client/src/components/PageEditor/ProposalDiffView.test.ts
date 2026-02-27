import { getLocalVue } from "@tests/vitest/helpers";
import { shallowMount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import ProposalDiffView from "./ProposalDiffView.vue";

const localVue = getLocalVue();

const OLD = "# Title\nOld line 1\nOld line 2";
const NEW = "# Title\nNew line 1\nNew line 2\nExtra line";

function mountComponent(propsData = { original: OLD, proposed: NEW }) {
    return shallowMount(ProposalDiffView as object, { localVue, propsData });
}

describe("ProposalDiffView", () => {
    it("renders diff stats", () => {
        const wrapper = mountComponent();
        const text = wrapper.text();
        expect(text).toContain("+");
        expect(text).toContain("-");
        expect(text).toContain("lines");
    });

    it("renders accept and reject buttons", () => {
        const wrapper = mountComponent();
        expect(wrapper.find('[data-description="accept proposal"]').exists()).toBe(true);
        expect(wrapper.find('[data-description="reject proposal"]').exists()).toBe(true);
    });

    it("emits accept on button click", async () => {
        const wrapper = mountComponent();
        await wrapper.find('[data-description="accept proposal"]').trigger("click");
        expect(wrapper.emitted("accept")).toHaveLength(1);
    });

    it("emits reject on button click", async () => {
        const wrapper = mountComponent();
        await wrapper.find('[data-description="reject proposal"]').trigger("click");
        expect(wrapper.emitted("reject")).toHaveLength(1);
    });

    it("shows added lines with diff-added class", () => {
        const wrapper = mountComponent();
        const addedLines = wrapper.findAll(".diff-added");
        expect(addedLines.length).toBeGreaterThan(0);
    });

    it("shows removed lines with diff-removed class", () => {
        const wrapper = mountComponent();
        const removedLines = wrapper.findAll(".diff-removed");
        expect(removedLines.length).toBeGreaterThan(0);
    });

    it("shows context lines for unchanged content", () => {
        const wrapper = mountComponent();
        const contextLines = wrapper.findAll(".diff-context");
        expect(contextLines.length).toBeGreaterThan(0);
    });

    it("renders no diff lines for identical content", () => {
        const wrapper = mountComponent({ original: "same\n", proposed: "same\n" });
        expect(wrapper.findAll(".diff-added").length).toBe(0);
        expect(wrapper.findAll(".diff-removed").length).toBe(0);
    });
});
