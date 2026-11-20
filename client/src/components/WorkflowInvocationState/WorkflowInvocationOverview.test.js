import { createTestingPinia } from "@pinia/testing";
import { getLocalVue } from "@tests/vitest/helpers";
import { shallowMount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { describe, expect, it, vi } from "vitest";
import { createMemoryHistory, createRouter } from "vue-router";

import invocationData from "../Workflow/test/json/invocation.json";

import WorkflowInvocationOverview from "./WorkflowInvocationOverview.vue";

const localVue = getLocalVue();

// Constants
const workflowData = {
    id: "workflow-id",
    name: "Test Workflow",
    version: 0,
};
const selectors = {
    gAlertStub: "g-alert-stub",
};
const alertMessages = {
    unOwned: "Workflow is neither importable, nor owned by or shared with current user",
    nonExistent: "No workflow found for this invocation.",
};

// Mock the workflow store to return the expected workflow data given the stored workflow ID
vi.mock("@/stores/workflowStore", async () => {
    const originalModule = await vi.importActual("@/stores/workflowStore");
    return {
        ...originalModule,
        useWorkflowStore: () => ({
            ...originalModule.useWorkflowStore(),
            getStoredWorkflowByInstanceId: vi.fn().mockImplementation((workflowId) => {
                if (["unowned-workflow", "nonexistant-workflow"].includes(workflowId)) {
                    return undefined;
                }
                return workflowData;
            }),
            fetchWorkflowForInstanceId: vi.fn().mockImplementation((workflowId) => {
                if (workflowId === "unowned-workflow") {
                    throw new Error(alertMessages.unOwned);
                }
            }),
        }),
    };
});

describe("WorkflowInvocationOverview.vue for a valid/invalid workflow", () => {
    async function loadWrapper(invocationData) {
        const propsData = {
            invocation: invocationData,
            invocationSchedulingTerminal: true,
            stepsJobsSummary: [],
            jobStatesSummary: {},
        };
        const wrapper = shallowMount(WorkflowInvocationOverview, {
            propsData,
            global: localVue,
            pinia: createTestingPinia({ createSpy: vi.fn }),
        });
        await flushPromises();
        return wrapper;
    }

    it("displays the workflow invocation graph for a valid workflow", async () => {
        const wrapper = await loadWrapper(invocationData);
        expect(wrapper.find("[data-description='workflow invocation graph']").exists()).toBeTruthy();
    });

    it("displays an alert for an unowned workflow", async () => {
        const wrapper = await loadWrapper({ ...invocationData, workflow_id: "unowned-workflow" });
        expect(wrapper.find("[data-description='workflow invocation graph']").exists()).toBeFalsy();
        const alert = wrapper.find(selectors.gAlertStub);
        expect(alert.text()).toContain(alertMessages.unOwned);
    });

    it("displays an alert for a nonexistant workflow", async () => {
        const wrapper = await loadWrapper({ ...invocationData, workflow_id: "nonexistant-workflow" });
        expect(wrapper.find("[data-description='workflow invocation graph']").exists()).toBeFalsy();
        const alert = wrapper.find(selectors.gAlertStub);
        expect(alert.text()).toContain(alertMessages.nonExistent);
    });
});

describe("WorkflowInvocationOverview subworkflow error links", () => {
    it.each([
        [3, { step_index: "3" }],
        [undefined, {}],
    ])("opens the subworkflow invocation with step %s selected", async (stepId, query) => {
        const router = createRouter({
            history: createMemoryHistory(),
            routes: [{ path: "/:path(.*)", component: {} }],
        });
        const wrapper = shallowMount(WorkflowInvocationOverview, {
            propsData: {
                invocation: invocationData,
                invocationAndJobTerminal: true,
                invocationSchedulingTerminal: true,
                stepsJobsSummary: [],
                jobStatesSummary: {},
                invocationMessages: [{ reason: "subworkflow_failed" }],
            },
            global: localVue,
            pinia: createTestingPinia({ createSpy: vi.fn }),
            router,
        });
        await flushPromises();
        wrapper
            .findComponent({ name: "WorkflowInvocationError" })
            .vm.$emit("view-subworkflow-invocation", "subworkflow-invocation", stepId);
        await flushPromises();
        expect(router.currentRoute.value.path).toBe("/workflows/invocations/subworkflow-invocation");
        expect(router.currentRoute.value.query).toEqual(query);
    });
});
