import { composeStories } from "@storybook/vue3-vite";
import { type StoryMountOptions, type StoryOf, useStoryMount } from "@tests/vitest/stories";
import { describe, expect, it } from "vitest";
import { nextTick } from "vue";

import type GButton from "@/components/BaseComponents/GButton.vue";

import * as componentStories from "./PageRevisionView.stories";
import { FAKE_PAGE_REVISION } from "./testData";

import PageRevisionView from "./PageRevisionView.vue";
import Markdown from "@/components/Markdown/Markdown.vue";

const stories = composeStories(componentStories);
const mountStory = useStoryMount();
const viewModeStories = {
    preview: stories.Preview,
    changes_current: stories.ComparedWithCurrent,
    changes_previous: stories.ComparedWithPrevious,
};

function mountRevisionView(story: StoryOf<typeof stories> = stories.Preview, options: StoryMountOptions = {}) {
    return mountStory(story, options).getComponent(PageRevisionView);
}

describe("PageRevisionView", () => {
    describe("preview mode (default)", () => {
        it("renders Markdown component, no diff elements", () => {
            const wrapper = mountRevisionView();
            expect(wrapper.findComponent(Markdown).exists()).toBe(true);
            expect(wrapper.find('[data-description="revision diff view"]').exists()).toBe(false);
        });
    });

    describe("changes_current mode", () => {
        it("renders diff stats and diff lines, no Markdown component", () => {
            const wrapper = mountRevisionView(stories.ComparedWithCurrent);
            expect(wrapper.findComponent(Markdown).exists()).toBe(false);
            expect(wrapper.find('[data-description="revision diff view"]').exists()).toBe(true);
            const text = wrapper.get(".diff-stats").text();
            expect(text).toContain("+3");
            expect(text).toContain("-2");
            expect(text).toContain("lines");
        });

        it("shows added lines with diff-added class", () => {
            const wrapper = mountRevisionView(stories.ComparedWithCurrent);
            expect(wrapper.findAll(".diff-added").length).toBeGreaterThan(0);
        });

        it("shows removed lines with diff-removed class", () => {
            const wrapper = mountRevisionView(stories.ComparedWithCurrent);
            expect(wrapper.findAll(".diff-removed").length).toBeGreaterThan(0);
        });

        it("shows 'No changes' when revision matches current content", () => {
            const wrapper = mountRevisionView(stories.MatchesCurrent);
            expect(wrapper.find('[data-description="revision no changes"]').exists()).toBe(true);
            expect(wrapper.find(".diff-stats").exists()).toBe(false);
            expect(wrapper.findAll(".diff-added").length).toBe(0);
            expect(wrapper.findAll(".diff-removed").length).toBe(0);
        });
    });

    describe("changes_previous mode", () => {
        it("renders diff vs previous content", () => {
            const wrapper = mountRevisionView(stories.ComparedWithPrevious);
            expect(wrapper.find('[data-description="revision diff view"]').exists()).toBe(true);
            expect(wrapper.find(".diff-stats").exists()).toBe(true);
            expect(wrapper.findAll(".diff-added").length).toBeGreaterThan(0);
            expect(wrapper.findAll(".diff-removed").length).toBeGreaterThan(0);
        });

        it("shows 'No changes' when revision matches previous content", () => {
            const wrapper = mountRevisionView(stories.MatchesPrevious);
            expect(wrapper.find('[data-description="revision no changes"]').exists()).toBe(true);
            expect(wrapper.find(".diff-stats").exists()).toBe(false);
        });
    });

    describe("toggle buttons", () => {
        it("preview button is always visible", () => {
            const wrapper = mountRevisionView();
            expect(wrapper.find('[data-description="revision preview button"]').exists()).toBe(true);
        });

        it("both compare buttons visible when not newest/oldest", () => {
            const wrapper = mountRevisionView();
            expect(wrapper.find('[data-description="revision compare current button"]').exists()).toBe(true);
            expect(wrapper.find('[data-description="revision compare previous button"]').exists()).toBe(true);
        });

        it("'Compare to Current' hidden when isNewestRevision", () => {
            const wrapper = mountRevisionView(stories.NewestRevision);
            expect(wrapper.find('[data-description="revision compare current button"]').exists()).toBe(false);
            expect(wrapper.find('[data-description="revision compare previous button"]').exists()).toBe(true);
        });

        it("'Compare to Previous' hidden when isOldestRevision", () => {
            const wrapper = mountRevisionView(stories.OldestRevision);
            expect(wrapper.find('[data-description="revision compare current button"]').exists()).toBe(true);
            expect(wrapper.find('[data-description="revision compare previous button"]').exists()).toBe(false);
        });

        it.each([
            ["preview", "revision preview button"],
            ["changes_current", "revision compare current button"],
            ["changes_previous", "revision compare previous button"],
        ] as const)("presses the selected toggle in %s mode", (viewMode, description) => {
            const wrapper = mountRevisionView(viewModeStories[viewMode]);
            const button = wrapper.getComponent<typeof GButton>(`[data-description="${description}"]`);
            expect(button.props("pressed")).toBe(true);
        });

        it.each([
            ["changes_current", "preview", "revision compare current button"],
            ["changes_previous", "preview", "revision compare previous button"],
            ["preview", "changes_current", "revision preview button"],
        ] as const)("emits %s when its toggle is clicked from %s", async (nextMode, viewMode, description) => {
            const wrapper = mountRevisionView(viewModeStories[viewMode]);
            wrapper.getComponent<typeof GButton>(`[data-description="${description}"]`).vm.$emit("click");
            await nextTick();
            expect(wrapper.emitted("update:viewMode")).toEqual([[nextMode]]);
        });
    });

    describe("action buttons", () => {
        it.each(["preview", "changes_current"] as const)("shows Restore in %s mode", (viewMode) => {
            const wrapper = mountRevisionView(viewModeStories[viewMode]);
            expect(wrapper.find('[data-description="revision restore button"]').exists()).toBe(true);
        });

        it("restore button is disabled when reverting", () => {
            const wrapper = mountRevisionView(stories.RestoringRevision, {
                // Preserve the original shallow-mount contract: the disabled prop reaches GButton.
                global: { stubs: { GButton: true } },
            });
            expect(wrapper.get('[data-description="revision restore button"]').attributes("disabled")).toBe("true");
        });

        it("restore button emits restore with revision id", async () => {
            const wrapper = mountRevisionView();
            wrapper.getComponent<typeof GButton>('[data-description="revision restore button"]').vm.$emit("click");
            await nextTick();
            expect(wrapper.emitted("restore")).toEqual([[FAKE_PAGE_REVISION.id]]);
        });

        it.each(["preview", "changes_current"] as const)("emits back from %s mode", async (viewMode) => {
            const wrapper = mountRevisionView(viewModeStories[viewMode]);
            wrapper.getComponent<typeof GButton>('[data-description="revision back button"]').vm.$emit("click");
            await nextTick();
            expect(wrapper.emitted("back")).toHaveLength(1);
        });
    });
});
