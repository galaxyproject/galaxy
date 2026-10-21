import { composeStories } from "@storybook/vue3-vite";
import { useStoryMount } from "@tests/vitest/stories";
import flushPromises from "flush-promises";
import { expect, it } from "vitest";

import { ensureDefined } from "@/utils/assertions";

import * as WorkflowInvocationStepsStories from "./WorkflowInvocationSteps.stories";

import GAlert from "@/components/BaseComponents/GAlert.vue";

const stories = composeStories(WorkflowInvocationStepsStories);
const mountStory = useStoryMount();

it("shows an error when the invocation graph fails to load", async () => {
    const wrapper = mountStory(stories.GraphRateLimited);
    await flushPromises();

    const errorAlert = ensureDefined(
        wrapper.findAllComponents(GAlert).find((alert) => alert.props("variant") === "danger"),
    );
    // nginx's page carries no Galaxy message, so the client describes the status instead.
    expect(errorAlert.text()).toContain("Too many requests, please wait and try again (429)");
});
