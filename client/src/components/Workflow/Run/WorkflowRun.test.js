import MockAdapter from "axios-mock-adapter";
import axios from "axios";
import WorkflowRun from "./WorkflowRun.vue";
import { shallowMount, createLocalVue } from "@vue/test-utils";
import { watchForChange } from "jest/helpers";

import sampleRunData1 from "./testdata/run1.json";

import { getRunData } from "./services"
jest.mock("./services");

getRunData.mockImplementation(async () => {
    return new Promise(resolve => {
        setTimeout(() => {
            resolve(sampleRunData1);
        }, 0);
    })
});


jest.mock("app");
const run1WorkflowId = "ebab00128497f9d7";

describe("WorkflowRun.vue", () => {
    let axiosMock;
    let wrapper;
    let localVue;

    beforeEach(() => {
        axiosMock = new MockAdapter(axios);
        const propsData = { workflowId: run1WorkflowId };
        localVue = createLocalVue();
        axiosMock.onGet(`/api/workflows/${run1WorkflowId}/download?style=run`).reply(200, sampleRunData1);
        wrapper = shallowMount(WorkflowRun, {
            propsData: propsData,
            localVue,
        });
    });

    afterEach(() => {
        axiosMock.restore();
    });

    it("loads run data from API and parses it into a WorkflowRunModel object", async () => {
        // waits for vue to render wrapper
        await localVue.nextTick();

        expect(wrapper.vm.loading).toBe(true);
        expect(wrapper.vm.error).toBeNull();
        expect(wrapper.vm.model).toBeNull();

        await watchForChange(wrapper.vm, "loading");

        expect(wrapper.vm.error).toBeNull();
        expect(wrapper.vm.loading).toBe(false);
        const model = wrapper.vm.model;
        expect(model).not.toBeNull();
        expect(model.workflowId).toBe(run1WorkflowId);
        expect(model.name).toBe("Cool Test Workflow");
        expect(model.historyId).toBe("8f7a155755f10e73");
        expect(model.hasUpgradeMessages).toBe(false);
        expect(model.hasStepVersionChanges).toBe(false);
        expect(model.wpInputs.wf_param.label).toBe("wf_param");
    });
});
