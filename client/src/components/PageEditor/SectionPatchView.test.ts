import { composeStories } from "@storybook/vue3-vite";
import { type StoryOf, useStoryMount } from "@tests/vitest/stories";
import { describe, expect, it } from "vitest";

import * as componentStories from "./SectionPatchView.stories";

import SectionPatchView from "./SectionPatchView.vue";

const stories = composeStories(componentStories);
const mountStory = useStoryMount();

const REJECT_BUTTON = '[data-description="reject all patches"]';
const APPLY_BUTTON = '[data-description="apply selected patches"]';

function mountPatchView(story: StoryOf<typeof stories> = stories.TwoSectionProposal) {
    return mountStory(story).getComponent(SectionPatchView);
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
        const wrapper = mountPatchView(stories.SingleSectionProposal);
        expect(wrapper.text()).toContain("1 section changed");
    });

    it("counts no changed sections when the proposal matches the original", () => {
        const wrapper = mountPatchView(stories.UnchangedProposal);
        expect(wrapper.text()).toContain("0 sections changed");
    });
});
