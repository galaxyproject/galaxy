import { createTestingPinia } from "@pinia/testing";
import { composeStories } from "@storybook/vue3-vite";
import { getLocalVue, withPlugins } from "@tests/vitest/helpers";
import { useStoryMount } from "@tests/vitest/stories";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { describe, expect, it, onTestFinished, vi } from "vitest";

import { useWorkflowStore } from "@/stores/workflowStore";

import { INVOCATION, INVOKED_WORKFLOW } from "./test_fixtures";
import * as WorkflowInvocationOverviewStories from "./WorkflowInvocationOverview.stories";

import InvocationGraph from "../Workflow/Invocation/Graph/InvocationGraph.vue";
import WorkflowInvocationOverview from "./WorkflowInvocationOverview.vue";
import GAlert from "@/components/BaseComponents/GAlert.vue";

const stories = composeStories(WorkflowInvocationOverviewStories);
const mountStory = useStoryMount();

/** Mounts a story once the overview's workflow fetch, if any, has settled. */
async function mountOverview(story) {
    const wrapper = mountStory(story);
    await flushPromises();
    return { overview: wrapper.getComponent(WorkflowInvocationOverview), workflowStore: useWorkflowStore() };
}

describe("WorkflowInvocationOverview", () => {
    it("passes a workflow already in the store to the graph without fetching it", async () => {
        const { overview, workflowStore } = await mountOverview(stories.WorkflowGraph);

        const graph = overview.findComponent(InvocationGraph);
        expect(graph.exists()).toBe(true);
        expect(graph.props("workflow")).toEqual(INVOKED_WORKFLOW);
        expect(workflowStore.fetchWorkflowForInstanceId).not.toHaveBeenCalled();
    });

    it("fetches a workflow that is not accessible and shows the error as a danger alert", async () => {
        const { overview, workflowStore } = await mountOverview(stories.WorkflowNotAccessible);

        expect(workflowStore.fetchWorkflowForInstanceId).toHaveBeenCalledWith(INVOCATION.workflow_id);
        expect(overview.findComponent(GAlert).props("variant")).toBe("danger");
    });

    it("displays an info alert when fetching finds no workflow for the invocation", async () => {
        // Galaxy answers with a workflow or an error; the store ends up with neither only when a fetch
        // joins one that already failed (a bug), so this state stays a plain mount whose stubbed fetch
        // loads nothing.
        const pinia = createTestingPinia({ createSpy: vi.fn });
        const workflowStore = useWorkflowStore(pinia);
        const overview = mount(WorkflowInvocationOverview, {
            props: WorkflowInvocationOverviewStories.default.args,
            global: withPlugins(getLocalVue(), pinia),
        });
        onTestFinished(() => overview.unmount());
        await flushPromises();

        expect(workflowStore.fetchWorkflowForInstanceId).toHaveBeenCalledWith(INVOCATION.workflow_id);
        expect(overview.findComponent(InvocationGraph).exists()).toBe(false);
        const alert = overview.findComponent(GAlert);
        expect(alert.props("variant")).toBe("info");
        expect(alert.text()).toContain("No workflow found for this invocation.");
    });
});
