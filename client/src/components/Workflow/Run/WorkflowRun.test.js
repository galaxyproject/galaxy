import { createTestingPinia } from "@pinia/testing";
import { createLocalVue, mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { PiniaVuePlugin } from "pinia";

import { getRunData } from "./services";
import sampleRunData1 from "./testdata/run1.json";

import WorkflowRun from "./WorkflowRun.vue";

jest.mock("./services");

getRunData.mockImplementation(async () => {
    return new Promise((resolve) => {
        setTimeout(() => {
            resolve(sampleRunData1);
        }, 0);
    });
});

jest.mock("app");

// WorkflowRunSuccess contains some bad code that automatically
// runs ajax calls, needs to be reworked and shallowMount doesn't
// seem to be stopping the event hooks from firing probably because the
// offending code runs immediately on loading
jest.mock("./WorkflowRunSuccess");

describe("WorkflowRun.vue", () => {
    let wrapper;
    let localVue;
    const run1WorkflowId = "ebab00128497f9d7";

    beforeEach(() => {
        const propsData = { workflowId: run1WorkflowId };
        localVue = createLocalVue();
        localVue.use(PiniaVuePlugin);
        wrapper = mount(WorkflowRun, {
            propsData: propsData,
            localVue,
            pinia: createTestingPinia(),
        });
    });

    it("loads run data from API and parses it into a WorkflowRunModel object", async () => {
        const loadingTag = "[data-description='loading message']";
        expect(wrapper.find(loadingTag).exists()).toBeTruthy();
        expect(wrapper.vm.workflowError).toBe("");
        expect(wrapper.vm.workflowModel).toBeNull();

        await flushPromises();
        await wrapper.vm.$nextTick();

        expect(wrapper.find(loadingTag).exists()).toBeFalsy();
        expect(wrapper.vm.simpleForm).toBe(false);

        const workflowModel = wrapper.vm.workflowModel;
        expect(workflowModel).not.toBeNull();
        expect(workflowModel.workflowId).toBe(run1WorkflowId);
        expect(workflowModel.name).toBe("Cool Test Workflow");
        expect(workflowModel.historyId).toBe("8f7a155755f10e73");
        expect(workflowModel.hasUpgradeMessages).toBe(false);
        expect(workflowModel.hasStepVersionChanges).toBe(false);
        expect(workflowModel.wpInputs.wf_param.label).toBe("wf_param");
        // all steps are expanded since data and parameter steps are expanded by default,
        // the same is true for tools with unconnected data inputs.
        workflowModel.steps.forEach((step) => {
            expect(step.expanded).toBe(true);
        });
    });

    it("displays submission error", async () => {
        // waits for vue to render wrapper
        await localVue.nextTick();

        expect(wrapper.vm.loading).toBe(true);
        expect(wrapper.vm.workflowError).toBe("");
        expect(wrapper.vm.workflowModel).toBeNull();

        await flushPromises();
        await wrapper.vm.$nextTick();

        expect(wrapper.vm.workflowError).toBe("");
        expect(wrapper.vm.loading).toBe(false);
        expect(wrapper.find(".alert-danger").exists()).toBe(false);
        wrapper.vm.handleSubmissionError("Some exception here");

        await localVue.nextTick();

        expect(wrapper.vm.submissionError).toBe("Some exception here");
        expect(wrapper.find(".alert-danger").exists()).toBe(true);
    });
});
