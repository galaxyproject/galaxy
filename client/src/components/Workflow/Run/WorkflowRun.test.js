import MockAdapter from "axios-mock-adapter";
import axios from "axios";
import { __RewireAPI__ as rewire } from "./WorkflowRun";
import WorkflowRun from "./WorkflowRun.vue";
import { mount, createLocalVue } from "@vue/test-utils";
import flushPromises from "flush-promises";

import sampleRunData1 from "./testdata/run1.json";

jest.mock("app");
const run1WorkflowId = "ebab00128497f9d7";

describe("WorkflowRun.vue", () => {
    let axiosMock;
    let wrapper;
    let localVue;

    beforeEach(() => {
        axiosMock = new MockAdapter(axios);
        rewire.__Rewire__("getAppRoot", () => "/");
        const propsData = { workflowId: run1WorkflowId };
        localVue = createLocalVue();
        axiosMock.onGet(`/api/workflows/${run1WorkflowId}/download?style=run`).reply(200, sampleRunData1);
        wrapper = mount(WorkflowRun, {
            propsData: propsData,
            localVue,
        });
    });

    afterEach(() => {
        axiosMock.restore();
    });

    it("loads run data from API and parses it into a WorkflowRunModel object", async () => {
        expect(wrapper.vm.loading).toBe(true);
        expect(wrapper.vm.error).toBeNull();
        expect(wrapper.vm.model).toBeNull();
        await flushPromises();
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
