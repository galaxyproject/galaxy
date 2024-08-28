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

describe("WorkflowInvocationOverview.vue with terminal invocation", () => {
    let wrapper;
    let propsData;

    beforeEach(async () => {
        propsData = {
            invocation: invocationData,
            invocationAndJobTerminal: true,
            invocationSchedulingTerminal: true,
            jobStatesSummary: {},
        };
        wrapper = shallowMount(WorkflowInvocationOverview, {
            propsData,
            localVue,
            pinia: createTestingPinia(),
        });
    });

    it("displays pdf report links", async () => {
        expect(wrapper.find(".invocation-pdf-link").exists()).toBeTruthy();
    });

    it("doesn't show cancel invocation button", async () => {
        expect(wrapper.find(".cancel-workflow-scheduling").exists()).toBeFalsy();
    });
});

describe("WorkflowInvocationOverview.vue with invocation scheduling running", () => {
    let wrapper;
    let propsData;
    let store;

    beforeEach(async () => {
        propsData = {
            invocation: invocationData,
            invocationAndJobTerminal: false,
            invocationSchedulingTerminal: false,
            jobStatesSummary: {},
        };
        wrapper = shallowMount(WorkflowInvocationOverview, {
            store,
            propsData,
            localVue,
        });
    });

    it("does not display pdf report links", async () => {
        expect(wrapper.find(".invocation-pdf-link").exists()).toBeFalsy();
    });

    it("shows cancel invocation button", async () => {
        expect(wrapper.find(".cancel-workflow-scheduling").exists()).toBeTruthy();
    });
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
