import { createTestingPinia } from "@pinia/testing";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import sampleRunData1 from "./testdata/run1.json";

import WorkflowRun from "./WorkflowRun.vue";

vi.mock("./services", () => ({
    getRunData: vi.fn(async () => {
        return new Promise((resolve) => {
            setTimeout(() => {
                resolve(sampleRunData1);
            }, 0);
        });
    }),
}));

vi.mock("app", () => ({}));

// WorkflowRunSuccess contains some bad code that automatically
// runs ajax calls, needs to be reworked and shallowMount doesn't
// seem to be stopping the event hooks from firing probably because the
// offending code runs immediately on loading
vi.mock("./WorkflowRunSuccess", () => ({
    default: {},
}));

describe("WorkflowRun.vue", () => {
    let wrapper;
    const run1WorkflowId = "ebab00128497f9d7";

    beforeEach(() => {
        vi.useFakeTimers();
        wrapper = mount(WorkflowRun, {
            props: {
                workflowId: run1WorkflowId,
            },
            global: {
                plugins: [createTestingPinia({ createSpy: vi.fn })],
            },
        });
    });

    afterEach(() => {
        vi.useRealTimers();
    });

    it("loads run data from API and parses it into a WorkflowRunModel object", async () => {
        const loadingTag = "[data-description='loading message']";
        expect(wrapper.find(loadingTag).exists()).toBeTruthy();
        expect(wrapper.vm.workflowError).toBe("");
        expect(wrapper.vm.workflowModel).toBeNull();

        // Advance timers to trigger setTimeout
        await vi.runAllTimersAsync();
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
        await wrapper.vm.$nextTick();

        expect(wrapper.vm.loading).toBe(true);
        expect(wrapper.vm.workflowError).toBe("");
        expect(wrapper.vm.workflowModel).toBeNull();

        // Advance timers to trigger setTimeout
        await vi.runAllTimersAsync();
        await flushPromises();
        await wrapper.vm.$nextTick();

        expect(wrapper.vm.workflowError).toBe("");
        expect(wrapper.vm.loading).toBe(false);
        expect(wrapper.find(".alert-danger").exists()).toBe(false);
        wrapper.vm.handleSubmissionError("Some exception here");

        await wrapper.vm.$nextTick();

        expect(wrapper.vm.submissionError).toBe("Some exception here");
        expect(wrapper.find(".alert-danger").exists()).toBe(true);
    });
});
