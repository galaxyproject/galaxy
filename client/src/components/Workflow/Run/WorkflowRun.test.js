import WorkflowRun from "./WorkflowRun.vue";
import { shallowMount, createLocalVue } from "@vue/test-utils";
import { watchForChange } from "jest/helpers";

import sampleRunData1 from "./testdata/run1.json";

import { getRunData } from "./services";
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
        wrapper = shallowMount(WorkflowRun, {
            propsData: propsData,
            localVue,
        });
    });

    it("loads run data from API and parses it into a WorkflowRunModel object", async () => {
        // waits for vue to render wrapper
        await localVue.nextTick();

        expect(wrapper.vm.loading).toBe(true);
        expect(wrapper.vm.error).toBeNull();
        expect(wrapper.vm.model).toBeNull();

        await watchForChange({ vm: wrapper.vm, propName: "loading" });

        expect(wrapper.vm.error).toBeNull();
        expect(wrapper.vm.loading).toBe(false);
        expect(wrapper.vm.simpleForm).toBe(false);
        const model = wrapper.vm.model;
        expect(model).not.toBeNull();
        expect(model.workflowId).toBe(run1WorkflowId);
        expect(model.name).toBe("Cool Test Workflow");
        expect(model.historyId).toBe("8f7a155755f10e73");
        expect(model.hasUpgradeMessages).toBe(false);
        expect(model.hasStepVersionChanges).toBe(false);
        expect(model.wpInputs.wf_param.label).toBe("wf_param");
        // all steps are expanded since data and parameter steps are expanded by default,
        // the same is true for tools with unconnected data inputs.
        model.steps.forEach((step) => {
            expect(step.expanded).toBe(true);
        });
    });

    it("displays submission error", async () => {
        // waits for vue to render wrapper
        await localVue.nextTick();

        expect(wrapper.vm.loading).toBe(true);
        expect(wrapper.vm.error).toBeNull();
        expect(wrapper.vm.model).toBeNull();

        await watchForChange({ vm: wrapper.vm, propName: "loading" });

        expect(wrapper.vm.error).toBeNull();
        expect(wrapper.vm.loading).toBe(false);
        expect(wrapper.find("b-alert-stub").exists()).toBe(false);
        wrapper.vm.handleSubmissionError("Some exception here");
        await localVue.nextTick();
        expect(wrapper.vm.submissionError).toBe("Some exception here");
        expect(wrapper.find("b-alert-stub").attributes("variant")).toEqual("danger");
    });
});
