import { composeStories } from "@storybook/vue3-vite";
import { type StoryOf, useStoryMount } from "@tests/vitest/stories";
import flushPromises from "flush-promises";
import { describe, expect, it, vi } from "vitest";

import { INVOCATION_HISTORY, OWN_WORKFLOW_RUNS, PUBLISHED_WORKFLOW } from "./test_fixtures";
import * as WorkflowAnnotationStories from "./WorkflowAnnotation.stories";

const stories = composeStories(WorkflowAnnotationStories);
const mountStory = useStoryMount();

/** The stories' Galaxy times, which carry no zone, as the UTC instants the dates' titles show. */
const EDITED_AT = "2026-08-31T10:00:00.000Z";
const INVOKED_AT = "2021-01-04T17:40:58.407Z";

const SELECTORS = {
    RUN_COUNT: ".workflow-invocations-count",
    INDICATORS_LINK: '[data-description="published owner badge"]',
    SWITCH_TO_HISTORY_LINK: "[data-description='switch to history link']",
    CURRENT_HISTORY_INDICATOR: "[data-description='current history indicator']",
    TIME_INFO: '[data-description="workflow annotation time info"]',
    DATE: '[data-description="workflow annotation date"]',
};

const VIEWS = [
    { view: "run_form", own: stories.RunForm, published: stories.PublishedRunForm },
    { view: "invocation", own: stories.Invocation, published: stories.PublishedInvocation },
];

/** Mounts a story and waits for the annotation's workflow and run count to load. */
async function mountWorkflowAnnotation(story: StoryOf<typeof stories>) {
    const wrapper = mountStory(story);
    await vi.waitFor(() => expect(wrapper.find(SELECTORS.TIME_INFO).exists()).toBe(true));
    await flushPromises();
    return wrapper;
}

describe("WorkflowAnnotation", () => {
    it.each(VIEWS)(
        "shows the run count but no published owner badge for the user's own workflow in the $view view",
        async ({ own }) => {
            const wrapper = await mountWorkflowAnnotation(own);

            // The count is requested once the workflow has loaded.
            await vi.waitFor(() =>
                expect(wrapper.find(SELECTORS.RUN_COUNT).text()).toContain(OWN_WORKFLOW_RUNS.scheduled.toString()),
            );
            expect(wrapper.find(SELECTORS.RUN_COUNT).text()).toContain("workflow runs:");
            expect(wrapper.find(SELECTORS.INDICATORS_LINK).exists()).toBe(false);
        },
    );

    it("does not link the target history in the run form view", async () => {
        const wrapper = await mountWorkflowAnnotation(stories.RunForm);

        expect(wrapper.find(SELECTORS.SWITCH_TO_HISTORY_LINK).exists()).toBe(false);
    });

    it("links the current target history by name in the invocation view", async () => {
        const wrapper = await mountWorkflowAnnotation(stories.Invocation);

        expect(wrapper.find(SELECTORS.SWITCH_TO_HISTORY_LINK).text()).toContain(INVOCATION_HISTORY.name);
        expect(wrapper.find(SELECTORS.CURRENT_HISTORY_INDICATOR).exists()).toBe(true);
    });

    it.each(VIEWS)(
        "shows the published owner badge but no run count for another user's workflow in the $view view",
        async ({ published }) => {
            const wrapper = await mountWorkflowAnnotation(published);

            const indicatorsLink = wrapper.find(SELECTORS.INDICATORS_LINK);
            expect(indicatorsLink.text()).toBe(PUBLISHED_WORKFLOW.owner);
            expect(indicatorsLink.attributes("title")).toContain(`Published by '${PUBLISHED_WORKFLOW.owner}'`);
            expect(wrapper.find(SELECTORS.RUN_COUNT).exists()).toBe(false);
        },
    );

    it("shows the time since the workflow was edited in the run form view", async () => {
        const wrapper = await mountWorkflowAnnotation(stories.RunForm);

        const timeInfo = wrapper.find(SELECTORS.TIME_INFO);
        expect(timeInfo.text()).toContain("edited");
        expect(timeInfo.find(SELECTORS.DATE).attributes("title")).toBe(EDITED_AT);
    });

    it("shows the time since the invocation in the invocation view", async () => {
        const wrapper = await mountWorkflowAnnotation(stories.Invocation);

        const timeInfo = wrapper.find(SELECTORS.TIME_INFO);
        expect(timeInfo.text()).toContain("invoked");
        expect(timeInfo.find(SELECTORS.DATE).attributes("title")).toBe(INVOKED_AT);
    });
});
