import { composeStories } from "@storybook/vue3-vite";
import { type StoryOf, useStoryMount } from "@tests/vitest/stories";
import flushPromises from "flush-promises";
import { describe, expect, it, vi } from "vitest";

import { INVOCATION_HISTORY } from "./test_fixtures";
import * as WorkflowAnnotationStories from "./WorkflowAnnotation.stories";

const stories = composeStories(WorkflowAnnotationStories);
const mountStory = useStoryMount();

const SELECTORS = {
    // Selenium's `history_target_link` and `current_history_indicator` (navigation.yml).
    SWITCH_TO_HISTORY_LINK: "[data-description='switch to history link']",
    CURRENT_HISTORY_INDICATOR: "[data-description='current history indicator']",
    TIME_INFO: '[data-description="workflow annotation time info"]',
};

/** Mounts a story and waits for the annotation's workflow to load. */
async function mountWorkflowAnnotation(story: StoryOf<typeof stories>) {
    const wrapper = mountStory(story);
    await vi.waitFor(() => expect(wrapper.find(SELECTORS.TIME_INFO).exists()).toBe(true));
    await flushPromises();
    return wrapper;
}

describe("WorkflowAnnotation", () => {
    it("does not link the target history in the run form view", async () => {
        const wrapper = await mountWorkflowAnnotation(stories.RunForm);

        expect(wrapper.find(SELECTORS.SWITCH_TO_HISTORY_LINK).exists()).toBe(false);
    });

    it("links the current target history by name in the invocation view", async () => {
        const wrapper = await mountWorkflowAnnotation(stories.Invocation);

        expect(wrapper.find(SELECTORS.SWITCH_TO_HISTORY_LINK).text()).toContain(INVOCATION_HISTORY.name);
        expect(wrapper.find(SELECTORS.CURRENT_HISTORY_INDICATOR).exists()).toBe(true);
    });
});
