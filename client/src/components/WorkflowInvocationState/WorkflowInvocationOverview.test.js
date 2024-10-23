import { createTestingPinia } from "@pinia/testing";
import { shallowMount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { getLocalVue } from "tests/jest/helpers";

import invocationData from "../Workflow/test/json/invocation.json";
import WorkflowInvocationOverview from "./WorkflowInvocationOverview";

const localVue = getLocalVue();

// Constants
const workflowData = {
    id: "workflow-id",
    name: "Test Workflow",
    version: 0,
};
const selectors = {
    bAlertStub: "balert-stub",
};
const alertMessages = {
    unOwned: "Workflow is neither importable, nor owned by or shared with current user",
    nonExistent: "No workflow found for this invocation.",
};

// Mock the workflow store to return the expected workflow data given the stored workflow ID
jest.mock("@/stores/workflowStore", () => {
    const originalModule = jest.requireActual("@/stores/workflowStore");
    return {
        ...originalModule,
        useWorkflowStore: () => ({
            ...originalModule.useWorkflowStore(),
            getStoredWorkflowByInstanceId: jest.fn().mockImplementation((workflowId) => {
                if (["unowned-workflow", "nonexistant-workflow"].includes(workflowId)) {
                    return undefined;
                }
                return workflowData;
            }),
            fetchWorkflowForInstanceId: jest.fn().mockImplementation((workflowId) => {
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
            invocationAndJobTerminal: true,
            invocationSchedulingTerminal: true,
            jobStatesSummary: {},
        };
        const wrapper = shallowMount(WorkflowInvocationOverview, {
            propsData,
            localVue,
            pinia: createTestingPinia(),
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
        const alert = wrapper.find(selectors.bAlertStub);
        expect(alert.text()).toContain(alertMessages.unOwned);
    });

    it("displays an alert for a nonexistant workflow", async () => {
        const wrapper = await loadWrapper({ ...invocationData, workflow_id: "nonexistant-workflow" });
        expect(wrapper.find("[data-description='workflow invocation graph']").exists()).toBeFalsy();
        const alert = wrapper.find(selectors.bAlertStub);
        expect(alert.text()).toContain(alertMessages.nonExistent);
    });
});
