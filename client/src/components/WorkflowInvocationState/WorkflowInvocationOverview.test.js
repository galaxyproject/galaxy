import { createTestingPinia } from "@pinia/testing";
import { getLocalVue, withPlugins } from "@tests/vitest/helpers";
import { shallowMount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { describe, expect, it, vi } from "vitest";

import { useWorkflowStore } from "@/stores/workflowStore";

import invocationData from "../Workflow/test/json/invocation.json";

import InvocationGraph from "../Workflow/Invocation/Graph/InvocationGraph.vue";
import WorkflowInvocationOverview from "./WorkflowInvocationOverview.vue";
import GAlert from "@/components/BaseComponents/GAlert.vue";

const localVue = getLocalVue();

const WORKFLOW = {
    id: "workflow-id",
    name: "Test Workflow",
    version: 0,
};
const UNOWNED_MESSAGE = "Workflow is neither importable, nor owned by or shared with current user";

/**
 * Mounts the overview for `invocationData`, with `storedWorkflow` already in the workflow store
 * when given. Store actions stay stubbed, so a missing workflow is fetched by a spy that loads
 * nothing unless `fetchError` makes it reject.
 */
async function mountOverview({ storedWorkflow = null, fetchError = null } = {}) {
    const workflowsByInstanceId = storedWorkflow ? { [invocationData.workflow_id]: storedWorkflow } : {};
    const pinia = createTestingPinia({
        createSpy: vi.fn,
        initialState: { workflowStore: { workflowsByInstanceId } },
    });
    const workflowStore = useWorkflowStore(pinia);
    if (fetchError) {
        workflowStore.fetchWorkflowForInstanceId.mockRejectedValueOnce(fetchError);
    }
    const wrapper = shallowMount(WorkflowInvocationOverview, {
        props: {
            invocation: invocationData,
            invocationAndJobTerminal: true,
            stepsJobsSummary: [],
        },
        global: withPlugins(localVue, pinia),
    });
    await flushPromises();
    return { wrapper, fetchWorkflow: workflowStore.fetchWorkflowForInstanceId };
}

describe("WorkflowInvocationOverview", () => {
    it("displays the invocation graph for a workflow already in the store", async () => {
        const { wrapper, fetchWorkflow } = await mountOverview({ storedWorkflow: WORKFLOW });

        const graph = wrapper.findComponent(InvocationGraph);
        expect(graph.exists()).toBe(true);
        expect(graph.attributes("data-description")).toBe("workflow invocation graph");
        expect(graph.props("workflow")).toEqual(WORKFLOW);
        expect(wrapper.findComponent(GAlert).exists()).toBe(false);
        expect(fetchWorkflow).not.toHaveBeenCalled();
    });

    it("displays the fetch error in a danger alert when the workflow is not accessible", async () => {
        const { wrapper, fetchWorkflow } = await mountOverview({ fetchError: new Error(UNOWNED_MESSAGE) });

        expect(fetchWorkflow).toHaveBeenCalledWith(invocationData.workflow_id);
        expect(wrapper.findComponent(InvocationGraph).exists()).toBe(false);
        const alert = wrapper.findComponent(GAlert);
        expect(alert.props("variant")).toBe("danger");
        expect(alert.text()).toContain(UNOWNED_MESSAGE);
    });

    it("displays an info alert when fetching finds no workflow for the invocation", async () => {
        const { wrapper, fetchWorkflow } = await mountOverview();

        expect(fetchWorkflow).toHaveBeenCalledWith(invocationData.workflow_id);
        expect(wrapper.findComponent(InvocationGraph).exists()).toBe(false);
        const alert = wrapper.findComponent(GAlert);
        expect(alert.props("variant")).toBe("info");
        expect(alert.text()).toContain("No workflow found for this invocation.");
    });
});
